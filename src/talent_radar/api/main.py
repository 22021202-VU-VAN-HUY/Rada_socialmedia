from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from talent_radar.core.config import get_settings
from talent_radar.core.database import create_all, get_db
from talent_radar.models import (
    AuthSession,
    CollectionJob,
    CollectionSchedule,
    PlatformConnection,
    Source,
    User,
)
from talent_radar.schemas import (
    AuthResult,
    ConnectionActionResult,
    ImportBatchRequest,
    ImportBatchResult,
    JobRead,
    PlatformConnectionRead,
    ScheduleCreate,
    ScheduleRead,
    ScheduleUpdate,
    SourceCreate,
    SourceRead,
    UserCredentials,
    UserRead,
)
from talent_radar.services.auth import (
    AuthenticationError,
    authenticate_token,
    authenticate_user,
    create_session,
    register_user,
    revoke_session,
)
from talent_radar.services.background_worker import BackgroundWorker
from talent_radar.services.browser_profiles import (
    BrowserProfileError,
    PLATFORM_LOGIN_URLS,
    connection_read,
    connection_for_platform,
    launch_coccoc_url,
    launch_login_browser,
)
from talent_radar.services.collection import (
    CollectionServiceError,
    create_schedule as create_collection_schedule,
    delete_schedule as delete_collection_schedule,
    enqueue_default_facebook_group_job,
    enqueue_job,
    update_schedule as update_collection_schedule,
)
from talent_radar.services.facebook_oauth import (
    FacebookOAuthError,
    begin_facebook_oauth,
    complete_facebook_oauth,
    mark_facebook_oauth_error,
)
from talent_radar.services.import_adapter import run_import_batch
from talent_radar.services.source_registry import load_source_registry, upsert_sources


security = HTTPBearer(auto_error=False)
settings = get_settings()
worker = BackgroundWorker(settings)


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_all()
    if settings.background_worker_enabled:
        worker.start()
    yield
    if settings.background_worker_enabled:
        worker.stop()


app = FastAPI(title="Talent Radar API", version="0.2.0", lifespan=lifespan)


def current_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> tuple[User, AuthSession]:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise HTTPException(status_code=401, detail="Can dang nhap.")
    try:
        return authenticate_token(db, credentials.credentials)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def current_user(auth: tuple[User, AuthSession] = Depends(current_auth)) -> User:
    return auth[0]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register", response_model=AuthResult, status_code=201)
def register(payload: UserCredentials, db: Session = Depends(get_db)) -> AuthResult:
    try:
        user = register_user(db, payload.email, payload.password)
        token, auth_session = create_session(db, user, settings.auth_session_hours)
        return AuthResult(
            access_token=token,
            expires_at=auth_session.expires_at,
            user=UserRead.model_validate(user),
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/auth/login", response_model=AuthResult)
def login(payload: UserCredentials, db: Session = Depends(get_db)) -> AuthResult:
    try:
        user = authenticate_user(db, payload.email, payload.password)
        token, auth_session = create_session(db, user, settings.auth_session_hours)
        return AuthResult(
            access_token=token,
            expires_at=auth_session.expires_at,
            user=UserRead.model_validate(user),
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/auth/me", response_model=UserRead)
def me(user: User = Depends(current_user)) -> User:
    return user


@app.post("/auth/logout", status_code=204)
def logout(
    auth: tuple[User, AuthSession] = Depends(current_auth),
    db: Session = Depends(get_db),
) -> Response:
    revoke_session(db, auth[1])
    return Response(status_code=204)


@app.get("/sources", response_model=list[SourceRead])
def list_sources(db: Session = Depends(get_db)) -> list[Source]:
    return list(db.scalars(select(Source).order_by(Source.platform, Source.source_name)).all())


@app.post("/sources", response_model=SourceRead)
def create_source(payload: SourceCreate, db: Session = Depends(get_db)) -> Source:
    source = db.get(Source, payload.id)
    if source is None:
        source = Source(**payload.model_dump())
        db.add(source)
    else:
        for key, value in payload.model_dump().items():
            setattr(source, key, value)
    db.commit()
    db.refresh(source)
    return source


@app.post("/sources/sync", response_model=list[SourceRead])
def sync_sources(db: Session = Depends(get_db)) -> list[Source]:
    source_data = load_source_registry(settings.source_registry_path)
    return upsert_sources(db, source_data)


@app.post("/imports", response_model=ImportBatchResult)
def import_batch(payload: ImportBatchRequest, db: Session = Depends(get_db)) -> ImportBatchResult:
    try:
        return run_import_batch(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/connections", response_model=list[PlatformConnectionRead])
def list_connections(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[PlatformConnectionRead]:
    try:
        for platform in PLATFORM_LOGIN_URLS:
            connection_for_platform(db, settings, user, platform)
    except BrowserProfileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    connections = db.scalars(
        select(PlatformConnection)
        .where(PlatformConnection.user_id == user.id)
        .order_by(PlatformConnection.platform)
    ).all()
    return [connection_read(connection) for connection in connections]


@app.post("/connections/{platform}/connect", response_model=ConnectionActionResult)
def connect_platform(
    platform: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ConnectionActionResult:
    try:
        connection = connection_for_platform(db, settings, user, platform)
        if platform.casefold() == "facebook":
            oauth_url = begin_facebook_oauth(db, settings, connection)
            connection.browser_process_id = launch_coccoc_url(settings, oauth_url)
            db.commit()
            db.refresh(connection)
            message = (
                "Da mo cua so cap quyen Facebook trong trinh duyet mac dinh. "
                "Ket noi chi hoan tat sau khi Facebook chuyen ve Talent Radar."
            )
        else:
            connection = launch_login_browser(db, settings, connection)
            message = "Da mo trang dang nhap trong trinh duyet mac dinh."
        return ConnectionActionResult(
            connection=connection_read(connection),
            message=message,
        )
    except (BrowserProfileError, FacebookOAuthError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/connections/facebook/callback")
def facebook_callback(
    state: str = "",
    code: str = "",
    error: str = "",
    error_description: str = "",
    db: Session = Depends(get_db),
) -> HTMLResponse:
    if error or not code or not state:
        message = error_description or error or "Facebook khong cap quyen."
        if state:
            mark_facebook_oauth_error(db, state=state, message=message)
        return _oauth_completion_page(success=False)
    try:
        complete_facebook_oauth(
            db,
            settings,
            state=state,
            code=code,
        )
    except FacebookOAuthError as exc:
        mark_facebook_oauth_error(db, state=state, message=str(exc))
        return _oauth_completion_page(success=False)
    return _oauth_completion_page(success=True)


def _oauth_completion_page(*, success: bool) -> HTMLResponse:
    title = "Da lien ket Facebook" if success else "Chua lien ket duoc Facebook"
    detail = (
        "Talent Radar da xac minh tai khoan. Tab nay se tu dong dong."
        if success
        else "Quay lai Talent Radar de xem chi tiet va thu lai."
    )
    close_script = (
        "<script>setTimeout(() => window.close(), 1200);</script>"
        if success
        else ""
    )
    return HTMLResponse(
        f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f7f8fa; color: #1c2530; }}
    main {{ max-width: 560px; margin: 16vh auto; padding: 32px; }}
    h1 {{ font-size: 28px; letter-spacing: 0; }}
    p {{ line-height: 1.5; color: #53606d; }}
  </style>
</head>
<body><main><h1>{title}</h1><p>{detail}</p></main>{close_script}</body>
</html>"""
    )


@app.post("/connections/{platform}/disconnect", response_model=ConnectionActionResult)
def disconnect_platform(
    platform: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ConnectionActionResult:
    try:
        connection = connection_for_platform(db, settings, user, platform)
    except BrowserProfileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    connection.status = "disconnected"
    connection.browser_process_id = None
    if connection.platform == "facebook":
        metadata = connection.connection_metadata or {}
        connection.connection_metadata = {
            key: value
            for key, value in metadata.items()
            if not key.startswith("facebook_") and not key.startswith("oauth_")
        }
    schedules = db.scalars(
        select(CollectionSchedule).where(
            CollectionSchedule.user_id == user.id,
            CollectionSchedule.connection_id == connection.id,
        )
    ).all()
    for schedule in schedules:
        schedule.enabled = False
        schedule.next_run_at = None
    db.commit()
    db.refresh(connection)
    return ConnectionActionResult(
        connection=connection_read(connection),
        message="Da ngat ket noi va tat cac lich lien quan. Profile dang nhap van duoc giu.",
    )


@app.get("/schedules", response_model=list[ScheduleRead])
def list_schedules(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[CollectionSchedule]:
    return list(
        db.scalars(
            select(CollectionSchedule)
            .where(
                CollectionSchedule.user_id == user.id,
                CollectionSchedule.last_status != "deleted",
            )
            .order_by(CollectionSchedule.created_at.desc())
        ).all()
    )


@app.post("/schedules", response_model=ScheduleRead, status_code=201)
def create_schedule(
    payload: ScheduleCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> CollectionSchedule:
    try:
        return create_collection_schedule(db, user, payload)
    except CollectionServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/schedules/{schedule_id}", response_model=ScheduleRead)
def update_schedule(
    schedule_id: str,
    payload: ScheduleUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> CollectionSchedule:
    try:
        return update_collection_schedule(db, user, schedule_id, payload)
    except CollectionServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    try:
        delete_collection_schedule(db, user, schedule_id)
    except CollectionServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@app.post("/schedules/{schedule_id}/run-now", response_model=JobRead)
def run_schedule_now(
    schedule_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> CollectionJob:
    try:
        return enqueue_job(db, user, schedule_id)
    except CollectionServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/collection/facebook/run-now", response_model=JobRead)
def run_default_facebook_group_now(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> CollectionJob:
    source_data = load_source_registry(settings.source_registry_path)
    upsert_sources(db, source_data)
    try:
        return enqueue_default_facebook_group_job(
            db,
            user,
            max_posts=settings.crawl_max_posts_per_source,
        )
    except CollectionServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/jobs", response_model=list[JobRead])
def list_jobs(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[CollectionJob]:
    return list(
        db.scalars(
            select(CollectionJob)
            .where(CollectionJob.user_id == user.id)
            .order_by(CollectionJob.created_at.desc())
            .limit(100)
        ).all()
    )
