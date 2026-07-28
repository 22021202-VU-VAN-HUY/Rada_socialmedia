from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from talent_radar.core.config import get_settings
from talent_radar.core.database import get_db, upgrade_database
from talent_radar.models import (
    AuthSession,
    BrowserAgent,
    CollectionJob,
    PlatformConnection,
    RunConfiguration,
    Source,
    User,
)
from talent_radar.schemas import (
    AuthResult,
    BrowserAgentClaimRequest,
    BrowserAgentHeartbeat,
    BrowserAgentItemBatch,
    BrowserAgentJob,
    BrowserAgentJobComplete,
    BrowserAgentPairRequest,
    BrowserAgentPairResult,
    BrowserAgentPairingCodeRead,
    BrowserAgentRead,
    ConnectionActionResult,
    ContentPage,
    ImportBatchRequest,
    ImportBatchResult,
    JobRead,
    OverviewRead,
    PlatformConnectionRead,
    RunConfigurationCreate,
    RunConfigurationRead,
    RunConfigurationUpdate,
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
)
from talent_radar.services.browser_agents import (
    BrowserAgentError,
    authenticate_agent,
    claim_job,
    complete_job,
    create_pairing_code,
    heartbeat_agent,
    import_job_items,
    list_agents,
    pair_agent,
    reconcile_connections,
    reset_connections_for_login,
    revoke_agent,
)
from talent_radar.services.collection import (
    CollectionServiceError,
    create_run_configuration,
    delete_run_configuration,
    enqueue_default_facebook_group_job,
    enqueue_job,
    update_run_configuration,
)
from talent_radar.services.content_queries import count_content, list_content
from talent_radar.services.facebook_oauth import (
    FacebookOAuthError,
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
    upgrade_database()
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


def current_browser_agent(
    x_agent_token: str | None = Header(default=None, alias="X-Agent-Token"),
    db: Session = Depends(get_db),
) -> BrowserAgent:
    if not x_agent_token:
        raise HTTPException(status_code=401, detail="Thieu browser agent token.")
    try:
        return authenticate_agent(db, x_agent_token)
    except BrowserAgentError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


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
        reset_connections_for_login(db, user)
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
def import_batch(
    payload: ImportBatchRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ImportBatchResult:
    try:
        return run_import_batch(db, payload, owner_user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/browser-agents", response_model=list[BrowserAgentRead])
def get_browser_agents(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[BrowserAgent]:
    return list_agents(db, user)


@app.post(
    "/browser-agents/pairing-codes",
    response_model=BrowserAgentPairingCodeRead,
    status_code=201,
)
def new_browser_agent_pairing_code(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> BrowserAgentPairingCodeRead:
    code, pairing = create_pairing_code(db, user)
    return BrowserAgentPairingCodeRead(
        pairing_code=code,
        expires_at=pairing.expires_at,
    )


@app.delete("/browser-agents/{agent_id}", status_code=204)
def delete_browser_agent(
    agent_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    try:
        revoke_agent(db, user, agent_id)
    except BrowserAgentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@app.post("/browser-agent/pair", response_model=BrowserAgentPairResult)
def pair_browser_agent(
    payload: BrowserAgentPairRequest,
    db: Session = Depends(get_db),
) -> BrowserAgentPairResult:
    try:
        token, agent = pair_agent(db, payload)
        return BrowserAgentPairResult(agent_token=token, agent=agent)
    except BrowserAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/browser-agent/heartbeat", response_model=BrowserAgentRead)
def browser_agent_heartbeat(
    payload: BrowserAgentHeartbeat,
    agent: BrowserAgent = Depends(current_browser_agent),
    db: Session = Depends(get_db),
) -> BrowserAgent:
    return heartbeat_agent(db, agent, payload)


@app.post("/browser-agent/jobs/claim", response_model=BrowserAgentJob | None)
def claim_browser_agent_job(
    payload: BrowserAgentClaimRequest,
    agent: BrowserAgent = Depends(current_browser_agent),
    db: Session = Depends(get_db),
) -> BrowserAgentJob | None:
    return claim_job(db, agent, payload)


@app.post("/browser-agent/jobs/{job_id}/items", response_model=JobRead)
def add_browser_agent_job_items(
    job_id: str,
    payload: BrowserAgentItemBatch,
    agent: BrowserAgent = Depends(current_browser_agent),
    db: Session = Depends(get_db),
) -> CollectionJob:
    try:
        return import_job_items(db, agent, job_id, payload)
    except (BrowserAgentError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/browser-agent/jobs/{job_id}/complete", response_model=JobRead)
def complete_browser_agent_job(
    job_id: str,
    payload: BrowserAgentJobComplete,
    agent: BrowserAgent = Depends(current_browser_agent),
    db: Session = Depends(get_db),
) -> CollectionJob:
    try:
        return complete_job(db, agent, job_id, payload)
    except BrowserAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/connections", response_model=list[PlatformConnectionRead])
def list_connections(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[PlatformConnectionRead]:
    for platform, login_url in PLATFORM_LOGIN_URLS.items():
        connection = db.scalar(
            select(PlatformConnection).where(
                PlatformConnection.user_id == user.id,
                PlatformConnection.platform == platform,
            )
        )
        if connection is None:
            db.add(
                PlatformConnection(
                    id=f"connection_{uuid4().hex}",
                    user_id=user.id,
                    platform=platform,
                    status="disconnected",
                    auth_method="browser_extension",
                    profile_dir="",
                    login_url=login_url,
                )
            )
    db.commit()
    connections = reconcile_connections(db, user)
    return [connection_read(connection) for connection in connections]


@app.post("/connections/{platform}/connect", response_model=ConnectionActionResult)
def connect_platform(
    platform: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ConnectionActionResult:
    try:
        connection = connection_for_platform(db, settings, user, platform)
        connection.auth_method = "browser_extension"
        connection = launch_login_browser(db, settings, connection)
        message = (
            "Da mo trang dang nhap trong trinh duyet mac dinh. "
            "Talent Radar chi bao da ket noi sau khi extension xac minh phien dang nhap."
        )
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
    configurations = db.scalars(
        select(RunConfiguration).where(
            RunConfiguration.user_id == user.id,
            RunConfiguration.connection_id == connection.id,
        )
    ).all()
    for configuration in configurations:
        configuration.is_archived = True
        configuration.last_status = "deleted"
    db.commit()
    db.refresh(connection)
    return ConnectionActionResult(
        connection=connection_read(connection),
        message="Da ngat ket noi va tat cac lich lien quan. Profile dang nhap van duoc giu.",
    )


@app.get("/run-configurations", response_model=list[RunConfigurationRead])
def list_run_configurations(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[RunConfiguration]:
    return list(
        db.scalars(
            select(RunConfiguration)
            .where(
                RunConfiguration.user_id == user.id,
                RunConfiguration.is_archived.is_(False),
            )
            .order_by(RunConfiguration.created_at.desc())
        ).all()
    )


@app.post(
    "/run-configurations",
    response_model=RunConfigurationRead,
    status_code=201,
)
def create_configuration(
    payload: RunConfigurationCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> RunConfiguration:
    try:
        return create_run_configuration(db, user, payload)
    except CollectionServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch(
    "/run-configurations/{configuration_id}",
    response_model=RunConfigurationRead,
)
def update_configuration(
    configuration_id: str,
    payload: RunConfigurationUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> RunConfiguration:
    try:
        return update_run_configuration(db, user, configuration_id, payload)
    except CollectionServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/run-configurations/{configuration_id}", status_code=204)
def delete_configuration(
    configuration_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    try:
        delete_run_configuration(db, user, configuration_id)
    except CollectionServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@app.post(
    "/run-configurations/{configuration_id}/run-now",
    response_model=JobRead,
)
def run_configuration_now(
    configuration_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> CollectionJob:
    try:
        return enqueue_job(db, user, configuration_id)
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


@app.get("/jobs/{job_id}", response_model=JobRead)
def get_job(
    job_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> CollectionJob:
    job = db.scalar(
        select(CollectionJob).where(
            CollectionJob.id == job_id,
            CollectionJob.user_id == user.id,
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Khong tim thay job.")
    return job


@app.get("/posts", response_model=ContentPage)
def list_posts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
    source_id: str | None = None,
    published_after: datetime | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ContentPage:
    return list_content(
        db,
        user,
        kind="posts",
        page=page,
        page_size=page_size,
        search=search,
        source_id=source_id,
        published_after=published_after,
    )


@app.get("/comments", response_model=ContentPage)
def list_comments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    search: str | None = Query(default=None, max_length=200),
    source_id: str | None = None,
    published_after: datetime | None = None,
    post_external_id: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> ContentPage:
    return list_content(
        db,
        user,
        kind="comments",
        page=page,
        page_size=page_size,
        search=search,
        source_id=source_id,
        published_after=published_after,
        post_external_id=post_external_id,
    )


@app.get("/overview", response_model=OverviewRead)
def overview(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> OverviewRead:
    active_jobs = db.scalar(
        select(func.count())
        .select_from(CollectionJob)
        .where(
            CollectionJob.user_id == user.id,
            CollectionJob.status.in_(("queued", "running")),
        )
    )
    saved_configurations = db.scalar(
        select(func.count())
        .select_from(RunConfiguration)
        .where(
            RunConfiguration.user_id == user.id,
            RunConfiguration.is_archived.is_(False),
        )
    )
    connected_platforms = db.scalar(
        select(func.count())
        .select_from(PlatformConnection)
        .where(
            PlatformConnection.user_id == user.id,
            PlatformConnection.status == "connected",
        )
    )
    return OverviewRead(
        posts=count_content(db, user, kind="posts"),
        comments=count_content(db, user, kind="comments"),
        active_jobs=active_jobs or 0,
        saved_configurations=saved_configurations or 0,
        connected_platforms=connected_platforms or 0,
    )


frontend_directory = Path(__file__).resolve().parents[1] / "web"
app.mount(
    "/",
    StaticFiles(directory=frontend_directory, html=True, check_dir=False),
    name="frontend",
)
