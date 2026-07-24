from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, Response
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
    launch_login_browser,
    verify_platform_login,
)
from talent_radar.services.collection import (
    CollectionServiceError,
    create_schedule as create_collection_schedule,
    delete_schedule as delete_collection_schedule,
    enqueue_job,
    update_schedule as update_collection_schedule,
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
    for platform in PLATFORM_LOGIN_URLS:
        connection_for_platform(db, settings, user, platform)
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
        connection = launch_login_browser(db, settings, connection)
        return ConnectionActionResult(
            connection=connection_read(connection),
            message=(
                "Da mo dung profile Coc Coc Huy. Dang nhap Facebook va giu "
                "cua so mo, sau do bam Xac nhan."
            ),
        )
    except BrowserProfileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/connections/{platform}/confirm", response_model=ConnectionActionResult)
def confirm_platform(
    platform: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ConnectionActionResult:
    try:
        connection = connection_for_platform(db, settings, user, platform)
        verified = verify_platform_login(settings, connection)
    except BrowserProfileError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not verified:
        connection.status = "pending_login"
        connection.last_checked_at = datetime.now(UTC)
        connection.last_error = (
            "Chua phat hien phien Facebook da dang nhap tren profile Huy."
        )
        db.commit()
        raise HTTPException(status_code=400, detail=connection.last_error)
    connection.status = "connected"
    connection.last_connected_at = datetime.now(UTC)
    connection.last_checked_at = datetime.now(UTC)
    connection.last_error = None
    connection.browser_process_id = None
    connection.connection_metadata = {
        **(connection.connection_metadata or {}),
        "login_verified": True,
        "login_verified_at": datetime.now(UTC).isoformat(),
    }
    db.commit()
    db.refresh(connection)
    return ConnectionActionResult(
        connection=connection_read(connection),
        message="Da kiem tra Facebook dang nhap tren dung profile Coc Coc Huy.",
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
