from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from talent_radar.models import (
    BrowserAgent,
    BrowserAgentPairingCode,
    CollectionJob,
    PlatformConnection,
    RunConfiguration,
    Source,
    User,
)
from talent_radar.schemas import (
    BrowserAgentClaimRequest,
    BrowserAgentHeartbeat,
    BrowserAgentItemBatch,
    BrowserAgentJob,
    BrowserAgentJobComplete,
    BrowserAgentPairRequest,
    BrowserPlatformConnection,
    ImportBatchRequest,
    ImportRecord,
)
from talent_radar.services.browser_profiles import PLATFORM_LOGIN_URLS
from talent_radar.services.import_adapter import run_import_batch


PAIRING_CODE_TTL = timedelta(minutes=10)
AGENT_ONLINE_WINDOW = timedelta(minutes=2)
CONNECTION_FRESHNESS_WINDOW = timedelta(minutes=3)
PAIRING_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
VIETNAM = ZoneInfo("Asia/Ho_Chi_Minh")


class BrowserAgentError(ValueError):
    pass


def create_pairing_code(
    db: Session,
    user: User,
) -> tuple[str, BrowserAgentPairingCode]:
    now = datetime.now(UTC)
    unused_codes = db.scalars(
        select(BrowserAgentPairingCode).where(
            BrowserAgentPairingCode.user_id == user.id,
            BrowserAgentPairingCode.used_at.is_(None),
        )
    ).all()
    for existing in unused_codes:
        existing.used_at = now

    raw_code = "".join(secrets.choice(PAIRING_ALPHABET) for _ in range(8))
    display_code = f"{raw_code[:4]}-{raw_code[4:]}"
    pairing = BrowserAgentPairingCode(
        id=f"pairing_{uuid4().hex}",
        user_id=user.id,
        code_hash=_hash_secret(raw_code),
        expires_at=now + PAIRING_CODE_TTL,
    )
    db.add(pairing)
    db.commit()
    db.refresh(pairing)
    return display_code, pairing


def pair_agent(
    db: Session,
    payload: BrowserAgentPairRequest,
) -> tuple[str, BrowserAgent]:
    now = datetime.now(UTC)
    pairing = db.scalar(
        select(BrowserAgentPairingCode).where(
            BrowserAgentPairingCode.code_hash
            == _hash_secret(_normalize_pairing_code(payload.pairing_code)),
            BrowserAgentPairingCode.used_at.is_(None),
        )
    )
    if pairing is None or _aware(pairing.expires_at) <= now:
        raise BrowserAgentError("Ma ghep noi khong hop le hoac da het han.")

    raw_token = secrets.token_urlsafe(40)
    agent = BrowserAgent(
        id=f"agent_{uuid4().hex}",
        user_id=pairing.user_id,
        name=payload.name.strip(),
        browser=payload.browser.strip().casefold(),
        version=payload.version,
        status="online",
        token_hash=_hash_secret(raw_token),
        capabilities=sorted(set(payload.capabilities)),
        last_seen_at=now,
    )
    pairing.used_at = now
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return raw_token, agent


def authenticate_agent(db: Session, raw_token: str) -> BrowserAgent:
    agent = db.scalar(
        select(BrowserAgent).where(
            BrowserAgent.token_hash == _hash_secret(raw_token),
            BrowserAgent.revoked_at.is_(None),
        )
    )
    if agent is None:
        raise BrowserAgentError("Browser agent token khong hop le.")
    return agent


def heartbeat_agent(
    db: Session,
    agent: BrowserAgent,
    payload: BrowserAgentHeartbeat,
) -> BrowserAgent:
    if payload.name is not None:
        agent.name = payload.name.strip()
    if payload.browser is not None:
        agent.browser = payload.browser.strip().casefold()
    if payload.version is not None:
        agent.version = payload.version
    if payload.capabilities is not None:
        agent.capabilities = sorted(set(payload.capabilities))
    now = datetime.now(UTC)
    agent.status = "online"
    agent.last_seen_at = now
    if payload.connections is not None:
        _sync_platform_connections(db, agent, payload.connections, now)
    db.commit()
    db.refresh(agent)
    return agent


def list_agents(db: Session, user: User) -> list[BrowserAgent]:
    agents = list(
        db.scalars(
            select(BrowserAgent)
            .where(
                BrowserAgent.user_id == user.id,
                BrowserAgent.revoked_at.is_(None),
            )
            .order_by(BrowserAgent.created_at.desc())
        ).all()
    )
    now = datetime.now(UTC)
    changed = False
    for agent in agents:
        effective_status = (
            "online"
            if now - _aware(agent.last_seen_at) <= AGENT_ONLINE_WINDOW
            else "offline"
        )
        if agent.status != effective_status:
            agent.status = effective_status
            changed = True
    if changed:
        db.commit()
    return agents


def reset_connections_for_login(db: Session, user: User) -> None:
    connections = db.scalars(
        select(PlatformConnection).where(
            PlatformConnection.user_id == user.id,
        )
    ).all()
    for connection in connections:
        connection.status = "disconnected"
        connection.last_checked_at = None
        connection.last_error = None
    db.commit()


def reconcile_connections(db: Session, user: User) -> list[PlatformConnection]:
    connections = list(
        db.scalars(
            select(PlatformConnection)
            .where(PlatformConnection.user_id == user.id)
            .order_by(PlatformConnection.platform)
        ).all()
    )
    now = datetime.now(UTC)
    changed = False
    for connection in connections:
        if connection.auth_method != "browser_extension":
            continue
        checked_at = connection.last_checked_at
        is_fresh = (
            checked_at is not None
            and now - _aware(checked_at) <= CONNECTION_FRESHNESS_WINDOW
        )
        if connection.status == "connected" and not is_fresh:
            connection.status = "disconnected"
            changed = True
    if changed:
        db.commit()
    return connections


def revoke_agent(db: Session, user: User, agent_id: str) -> None:
    agent = db.scalar(
        select(BrowserAgent).where(
            BrowserAgent.id == agent_id,
            BrowserAgent.user_id == user.id,
            BrowserAgent.revoked_at.is_(None),
        )
    )
    if agent is None:
        raise BrowserAgentError("Khong tim thay browser agent.")
    now = datetime.now(UTC)
    agent.status = "revoked"
    agent.revoked_at = now
    jobs = db.scalars(
        select(CollectionJob).where(
            CollectionJob.browser_agent_id == agent.id,
            CollectionJob.status == "running",
        )
    ).all()
    for job in jobs:
        job.status = "queued"
        job.browser_agent_id = None
        job.claimed_at = None
        job.started_at = None
    db.commit()


def claim_job(
    db: Session,
    agent: BrowserAgent,
    payload: BrowserAgentClaimRequest,
) -> BrowserAgentJob | None:
    supported = set(payload.supported_platforms or agent.capabilities)
    supported.intersection_update(agent.capabilities)
    if not supported:
        heartbeat_agent(db, agent, BrowserAgentHeartbeat())
        return None

    job = db.scalar(
        select(CollectionJob)
        .where(
            CollectionJob.user_id == agent.user_id,
            CollectionJob.executor == "browser_extension",
            CollectionJob.status == "queued",
            CollectionJob.platform.in_(supported),
        )
        .order_by(CollectionJob.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    agent.status = "online"
    agent.last_seen_at = datetime.now(UTC)
    if job is None:
        db.commit()
        return None

    configuration = db.get(RunConfiguration, job.run_configuration_id)
    source = db.get(Source, job.source_id)
    if configuration is None or source is None or not source.source_url:
        job.status = "failed"
        job.completed_at = datetime.now(UTC)
        job.error_summary = "Job thieu cau hinh hoac URL nguon."
        db.commit()
        return None

    now = datetime.now(UTC)
    published_since = datetime.now(VIETNAM).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    job.status = "running"
    job.browser_agent_id = agent.id
    job.claimed_at = now
    job.started_at = now
    job.result_metadata = {
        **(job.result_metadata or {}),
        "published_since": published_since.isoformat(),
    }
    configuration.last_status = "running"
    configuration.last_error = None
    db.commit()
    return BrowserAgentJob(
        id=job.id,
        platform=job.platform,
        source_id=source.id,
        source_name=source.source_name,
        source_url=source.source_url,
        max_posts=configuration.max_posts,
        max_comments_per_post=configuration.max_comments_per_post,
        lookback_hours=configuration.lookback_hours,
        include_replies=configuration.include_replies,
        published_since=published_since,
        filters=configuration.filters or {},
    )


def import_job_items(
    db: Session,
    agent: BrowserAgent,
    job_id: str,
    payload: BrowserAgentItemBatch,
) -> CollectionJob:
    job = _claimed_job(db, agent, job_id)
    for record in payload.records:
        if record.source_id != job.source_id or record.platform != job.platform:
            raise BrowserAgentError("Du lieu gui len khong khop voi job.")
        record.import_batch_id = job.id
    records = _filter_today_records(
        payload.records,
        _job_published_since(job),
    )
    result = run_import_batch(
        db,
        ImportBatchRequest(import_batch_id=job.id, records=records),
        owner_user_id=agent.user_id,
    )
    job.records_inserted += result.inserted
    job.duplicates_skipped += result.skipped_duplicates
    job.posts_collected += sum(record.item_type == "post" for record in records)
    job.comments_collected += sum(
        record.item_type == "comment" for record in records
    )
    job.replies_collected += sum(record.item_type == "reply" for record in records)
    db.commit()
    db.refresh(job)
    return job


def complete_job(
    db: Session,
    agent: BrowserAgent,
    job_id: str,
    payload: BrowserAgentJobComplete,
) -> CollectionJob:
    job = _claimed_job(db, agent, job_id)
    configuration = db.get(RunConfiguration, job.run_configuration_id)
    connection = db.get(PlatformConnection, job.connection_id)
    now = datetime.now(UTC)
    job.status = payload.status
    job.completed_at = now
    job.error_summary = payload.error
    job.result_metadata = {
        **payload.metadata,
        "observed_counts": {
            "posts": payload.posts_collected,
            "comments": payload.comments_collected,
            "replies": payload.replies_collected,
        },
    }
    if configuration is not None:
        configuration.last_run_at = now
        configuration.last_status = payload.status
        configuration.last_error = payload.error
    if connection is not None:
        connection.last_checked_at = now
        connection.last_error = payload.error
    agent.last_seen_at = now
    db.commit()
    db.refresh(job)
    return job


def _claimed_job(db: Session, agent: BrowserAgent, job_id: str) -> CollectionJob:
    job = db.scalar(
        select(CollectionJob).where(
            CollectionJob.id == job_id,
            CollectionJob.user_id == agent.user_id,
            CollectionJob.browser_agent_id == agent.id,
            CollectionJob.executor == "browser_extension",
            CollectionJob.status == "running",
        )
    )
    if job is None:
        raise BrowserAgentError("Job khong ton tai hoac khong thuoc agent nay.")
    return job


def _filter_today_records(
    records: list[ImportRecord],
    published_since: datetime,
) -> list[ImportRecord]:
    matched_post_ids: set[str] = set()
    kept: list[ImportRecord] = []

    for record in records:
        if record.item_type != "post":
            continue
        if record.published_at is None:
            continue
        if _aware(record.published_at) < published_since.astimezone(UTC):
            continue
        kept.append(record)
        if record.external_id:
            matched_post_ids.add(record.external_id)

    for record in records:
        if record.item_type == "post":
            continue
        if record.root_external_id in matched_post_ids:
            kept.append(record)
            continue
        if record.parent_external_id in matched_post_ids:
            kept.append(record)
    return kept


def _job_published_since(job: CollectionJob) -> datetime:
    raw_value = (job.result_metadata or {}).get("published_since")
    if isinstance(raw_value, str):
        try:
            return datetime.fromisoformat(raw_value)
        except ValueError:
            pass
    return datetime.now(VIETNAM).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


def _sync_platform_connections(
    db: Session,
    agent: BrowserAgent,
    reported_connections: list[BrowserPlatformConnection],
    now: datetime,
) -> None:
    existing = {
        connection.platform: connection
        for connection in db.scalars(
            select(PlatformConnection).where(
                PlatformConnection.user_id == agent.user_id,
            )
        ).all()
    }
    for report in reported_connections:
        if report.platform == "manual":
            continue
        connection = existing.get(report.platform)
        if connection is None:
            connection = PlatformConnection(
                id=f"connection_{uuid4().hex}",
                user_id=agent.user_id,
                platform=report.platform,
                status="disconnected",
                auth_method="browser_extension",
                profile_dir="",
                login_url=PLATFORM_LOGIN_URLS[report.platform],
            )
            db.add(connection)
            existing[report.platform] = connection

        was_connected = connection.status == "connected"
        connection.status = "connected" if report.connected else "disconnected"
        connection.auth_method = "browser_extension"
        connection.last_checked_at = now
        connection.last_error = None
        if report.connected and not was_connected:
            connection.last_connected_at = now
        metadata = {
            **(connection.connection_metadata or {}),
            "session_verified_by_agent_id": agent.id,
            "session_verified_at": now.isoformat(),
        }
        if report.account_id:
            metadata["connected_account_id"] = report.account_id
        else:
            metadata.pop("connected_account_id", None)
        if report.account_name:
            metadata["connected_account_name"] = report.account_name
        else:
            metadata.pop("connected_account_name", None)
        connection.connection_metadata = metadata


def _normalize_pairing_code(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalnum())


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
