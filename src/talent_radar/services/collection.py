from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from talent_radar.core.config import Settings
from talent_radar.models import (
    CollectionJob,
    CollectionSchedule,
    PlatformConnection,
    Source,
    User,
)
from talent_radar.schemas import ImportBatchRequest, ScheduleCreate, ScheduleUpdate
from talent_radar.services.facebook_collector import (
    FacebookCollector,
    LoginRequiredError,
)
from talent_radar.services.import_adapter import load_import_file, run_import_batch


class CollectionServiceError(ValueError):
    pass


def create_schedule(
    db: Session,
    user: User,
    payload: ScheduleCreate,
) -> CollectionSchedule:
    connection = _owned_connection(db, user.id, payload.connection_id)
    source = db.get(Source, payload.source_id)
    if source is None:
        raise CollectionServiceError("Khong tim thay nguon du lieu.")
    if connection.platform != source.platform:
        raise CollectionServiceError("Nen tang cua connection va source khong khop.")
    now = datetime.now(UTC)
    schedule = CollectionSchedule(
        id=f"schedule_{uuid4().hex}",
        user_id=user.id,
        connection_id=connection.id,
        source_id=source.id,
        enabled=payload.enabled,
        interval_minutes=payload.interval_minutes,
        max_posts=payload.max_posts,
        next_run_at=now if payload.enabled else None,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def update_schedule(
    db: Session,
    user: User,
    schedule_id: str,
    payload: ScheduleUpdate,
) -> CollectionSchedule:
    schedule = _owned_schedule(db, user.id, schedule_id)
    if schedule.last_status == "deleted":
        raise CollectionServiceError("Lich thu thap da bi xoa.")
    updates = payload.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(schedule, field, value)
    if "enabled" in updates:
        schedule.next_run_at = datetime.now(UTC) if schedule.enabled else None
    db.commit()
    db.refresh(schedule)
    return schedule


def delete_schedule(db: Session, user: User, schedule_id: str) -> None:
    schedule = _owned_schedule(db, user.id, schedule_id)
    schedule.enabled = False
    schedule.next_run_at = None
    schedule.last_status = "deleted"
    schedule.last_error = None
    db.commit()


def enqueue_job(
    db: Session,
    user: User,
    schedule_id: str,
    trigger: str = "manual",
) -> CollectionJob:
    schedule = _owned_schedule(db, user.id, schedule_id)
    if schedule.last_status == "deleted":
        raise CollectionServiceError("Lich thu thap da bi xoa.")
    connection = _owned_connection(db, user.id, schedule.connection_id)
    if connection.status != "connected":
        raise CollectionServiceError("Nen tang chua duoc ket noi.")
    existing = db.scalar(
        select(CollectionJob).where(
            CollectionJob.schedule_id == schedule.id,
            CollectionJob.status.in_(("queued", "running")),
        )
    )
    if existing is not None:
        return existing
    job = CollectionJob(
        id=f"job_{uuid4().hex}",
        user_id=user.id,
        schedule_id=schedule.id,
        connection_id=connection.id,
        source_id=schedule.source_id,
        status="queued",
        trigger=trigger,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def enqueue_due_schedules(db: Session) -> int:
    now = datetime.now(UTC)
    count = 0
    schedules = db.scalars(
        select(CollectionSchedule).where(CollectionSchedule.enabled.is_(True))
    ).all()
    for schedule in schedules:
        next_run = _aware(schedule.next_run_at)
        if next_run is not None and next_run > now:
            continue
        active = db.scalar(
            select(CollectionJob).where(
                CollectionJob.schedule_id == schedule.id,
                CollectionJob.status.in_(("queued", "running")),
            )
        )
        schedule.next_run_at = now + timedelta(minutes=schedule.interval_minutes)
        if active is None:
            db.add(
                CollectionJob(
                    id=f"job_{uuid4().hex}",
                    user_id=schedule.user_id,
                    schedule_id=schedule.id,
                    connection_id=schedule.connection_id,
                    source_id=schedule.source_id,
                    status="queued",
                    trigger="scheduled",
                )
            )
            count += 1
    db.commit()
    return count


def next_queued_job(db: Session) -> CollectionJob | None:
    return db.scalar(
        select(CollectionJob)
        .where(CollectionJob.status == "queued")
        .order_by(CollectionJob.created_at)
        .limit(1)
    )


def run_job(db: Session, settings: Settings, job: CollectionJob) -> None:
    schedule = db.get(CollectionSchedule, job.schedule_id)
    connection = db.get(PlatformConnection, job.connection_id)
    source = db.get(Source, job.source_id)
    if schedule is None or connection is None or source is None:
        _fail_job(db, job, schedule, "Job tham chieu du lieu khong con ton tai.")
        return

    job.status = "running"
    job.started_at = datetime.now(UTC)
    schedule.last_status = "running"
    schedule.last_error = None
    db.commit()

    try:
        if connection.status != "connected":
            raise CollectionServiceError("Nen tang chua duoc ket noi.")
        if connection.platform != "facebook":
            raise CollectionServiceError(
                f"Collector cho {connection.platform} chua duoc ho tro trong ban nay."
            )
        payload = FacebookCollector(settings).collect(connection, source, schedule.max_posts)
        output_path = _write_export(settings.crawl_output_directory, payload, job.id)
        records = load_import_file(output_path)
        run_import_batch(
            db,
            ImportBatchRequest(import_batch_id=job.id, records=records),
        )

        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        job.posts_collected = len(payload.get("posts", []))
        job.comments_collected = sum(
            len(item.get("comments", [])) for item in payload.get("posts", [])
        )
        job.output_path = str(output_path)
        connection.last_checked_at = datetime.now(UTC)
        connection.last_error = None
        schedule.last_run_at = job.completed_at
        schedule.last_status = "completed"
        schedule.last_error = None
        db.commit()
    except LoginRequiredError as exc:
        connection.status = "reauth_required"
        connection.last_error = str(exc)
        _fail_job(db, job, schedule, str(exc))
    except Exception as exc:
        connection.last_error = str(exc)
        _fail_job(db, job, schedule, str(exc))


def _write_export(directory: Path, payload: dict, job_id: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = directory / f"facebook_playwright_{timestamp}_{job_id[-8:]}.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return path


def _fail_job(
    db: Session,
    job: CollectionJob,
    schedule: CollectionSchedule | None,
    error: str,
) -> None:
    job.status = "failed"
    job.completed_at = datetime.now(UTC)
    job.error_summary = error[:4000]
    if schedule is not None:
        schedule.last_run_at = job.completed_at
        schedule.last_status = "failed"
        schedule.last_error = error[:4000]
    db.commit()


def _owned_connection(db: Session, user_id: str, connection_id: str) -> PlatformConnection:
    connection = db.scalar(
        select(PlatformConnection).where(
            PlatformConnection.id == connection_id,
            PlatformConnection.user_id == user_id,
        )
    )
    if connection is None:
        raise CollectionServiceError("Khong tim thay connection.")
    return connection


def _owned_schedule(db: Session, user_id: str, schedule_id: str) -> CollectionSchedule:
    schedule = db.scalar(
        select(CollectionSchedule).where(
            CollectionSchedule.id == schedule_id,
            CollectionSchedule.user_id == user_id,
        )
    )
    if schedule is None:
        raise CollectionServiceError("Khong tim thay lich thu thap.")
    return schedule


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
