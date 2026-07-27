from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from talent_radar.core.config import Settings
from talent_radar.models import (
    CollectionJob,
    PlatformConnection,
    RunConfiguration,
    Source,
    User,
)
from talent_radar.schemas import (
    ImportBatchRequest,
    RunConfigurationCreate,
    RunConfigurationUpdate,
)
from talent_radar.services.facebook_collector import (
    FacebookCollector,
    LoginRequiredError,
)
from talent_radar.services.import_adapter import (
    load_import_file,
    records_from_coccoc_export,
    run_import_batch,
)


class CollectionServiceError(ValueError):
    pass


def create_run_configuration(
    db: Session,
    user: User,
    payload: RunConfigurationCreate,
) -> RunConfiguration:
    connection = _owned_connection(db, user.id, payload.connection_id)
    source = db.get(Source, payload.source_id)
    if source is None:
        raise CollectionServiceError("Khong tim thay nguon du lieu.")
    if connection.platform != source.platform:
        raise CollectionServiceError("Nen tang cua connection va source khong khop.")
    configuration = RunConfiguration(
        id=f"configuration_{uuid4().hex}",
        user_id=user.id,
        connection_id=connection.id,
        source_id=source.id,
        max_posts=payload.max_posts,
        max_comments_per_post=payload.max_comments_per_post,
        lookback_hours=payload.lookback_hours,
        include_replies=payload.include_replies,
        filters=payload.filters,
    )
    db.add(configuration)
    db.commit()
    db.refresh(configuration)
    return configuration


def update_run_configuration(
    db: Session,
    user: User,
    configuration_id: str,
    payload: RunConfigurationUpdate,
) -> RunConfiguration:
    configuration = _owned_run_configuration(db, user.id, configuration_id)
    if configuration.is_archived:
        raise CollectionServiceError("Cau hinh thu thap da bi xoa.")
    updates = payload.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(configuration, field, value)
    db.commit()
    db.refresh(configuration)
    return configuration


def delete_run_configuration(
    db: Session,
    user: User,
    configuration_id: str,
) -> None:
    configuration = _owned_run_configuration(db, user.id, configuration_id)
    configuration.is_archived = True
    configuration.last_status = "deleted"
    configuration.last_error = None
    db.commit()


def enqueue_job(
    db: Session,
    user: User,
    configuration_id: str,
) -> CollectionJob:
    configuration = _owned_run_configuration(db, user.id, configuration_id)
    if configuration.is_archived:
        raise CollectionServiceError("Cau hinh thu thap da bi xoa.")
    connection = _owned_connection(db, user.id, configuration.connection_id)
    if connection.status != "connected":
        raise CollectionServiceError("Nen tang chua duoc ket noi.")
    existing = db.scalar(
        select(CollectionJob).where(
            CollectionJob.run_configuration_id == configuration.id,
            CollectionJob.status.in_(("queued", "running")),
        )
    )
    if existing is not None:
        return existing
    job = CollectionJob(
        id=f"job_{uuid4().hex}",
        user_id=user.id,
        run_configuration_id=configuration.id,
        connection_id=connection.id,
        source_id=configuration.source_id,
        platform=connection.platform,
        status="queued",
        trigger="manual",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def enqueue_default_facebook_group_job(
    db: Session,
    user: User,
    *,
    max_posts: int = 200,
) -> CollectionJob:
    connection = db.scalar(
        select(PlatformConnection)
        .where(
            PlatformConnection.user_id == user.id,
            PlatformConnection.platform == "facebook",
            PlatformConnection.status == "connected",
        )
        .order_by(PlatformConnection.last_connected_at.desc())
    )
    if connection is None:
        raise CollectionServiceError("Hay lien ket Facebook truoc khi lay du lieu.")

    source = db.scalar(
        select(Source)
        .where(
            Source.platform == "facebook",
            Source.source_kind == "group",
            Source.enabled.is_(True),
        )
        .order_by(Source.priority, Source.created_at)
    )
    if source is None:
        raise CollectionServiceError(
            "Khong tim thay Facebook group dang bat trong source registry."
        )

    configuration = db.scalar(
        select(RunConfiguration)
        .where(
            RunConfiguration.user_id == user.id,
            RunConfiguration.connection_id == connection.id,
            RunConfiguration.source_id == source.id,
            RunConfiguration.is_archived.is_(False),
        )
        .order_by(RunConfiguration.created_at.desc())
    )
    if configuration is None:
        configuration = create_run_configuration(
            db,
            user,
            RunConfigurationCreate(
                connection_id=connection.id,
                source_id=source.id,
                max_posts=max_posts,
            ),
        )
    elif configuration.max_posts != max_posts:
        configuration.max_posts = max_posts
        db.commit()
    return enqueue_job(db, user, configuration.id)


def next_queued_job(db: Session) -> CollectionJob | None:
    return db.scalar(
        select(CollectionJob)
        .where(CollectionJob.status == "queued")
        .order_by(CollectionJob.created_at)
        .limit(1)
    )


def run_job(db: Session, settings: Settings, job: CollectionJob) -> None:
    configuration = db.get(RunConfiguration, job.run_configuration_id)
    connection = db.get(PlatformConnection, job.connection_id)
    source = db.get(Source, job.source_id)
    if configuration is None or connection is None or source is None:
        _fail_job(
            db,
            job,
            configuration,
            "Job tham chieu du lieu khong con ton tai.",
        )
        return

    job.status = "running"
    job.started_at = datetime.now(UTC)
    configuration.last_status = "running"
    configuration.last_error = None
    db.commit()

    try:
        if connection.status != "connected":
            raise CollectionServiceError("Nen tang chua duoc ket noi.")
        if connection.platform != "facebook":
            raise CollectionServiceError(
                f"Collector cho {connection.platform} chua duoc ho tro trong ban nay."
            )
        local_now = datetime.now(ZoneInfo(settings.collection_timezone))
        since = local_now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        ).astimezone(UTC)
        output_path = _new_export_path(
            settings.crawl_output_directory,
            job.id,
        )
        job.output_path = str(output_path)
        db.commit()

        def persist_progress(progress: dict) -> None:
            _write_export(output_path, progress)
            records = records_from_coccoc_export(progress)
            import_result = run_import_batch(
                db,
                ImportBatchRequest(import_batch_id=job.id, records=records),
            )
            job.posts_collected = len(progress.get("posts", []))
            comments = [
                comment
                for item in progress.get("posts", [])
                for comment in item.get("comments", [])
            ]
            job.comments_collected = sum(not comment.get("is_reply") for comment in comments)
            job.replies_collected = sum(bool(comment.get("is_reply")) for comment in comments)
            job.records_inserted += import_result.inserted
            job.duplicates_skipped += import_result.skipped_duplicates
            db.commit()

        payload = FacebookCollector(settings).collect(
            connection,
            source,
            configuration.max_posts,
            since=since,
            on_progress=persist_progress,
        )
        _write_export(output_path, payload)
        records = load_import_file(output_path)
        import_result = run_import_batch(
            db,
            ImportBatchRequest(import_batch_id=job.id, records=records),
        )

        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        job.posts_collected = len(payload.get("posts", []))
        comments = [
            comment
            for item in payload.get("posts", [])
            for comment in item.get("comments", [])
        ]
        job.comments_collected = sum(not comment.get("is_reply") for comment in comments)
        job.replies_collected = sum(bool(comment.get("is_reply")) for comment in comments)
        job.records_inserted += import_result.inserted
        job.duplicates_skipped += import_result.skipped_duplicates
        job.output_path = str(output_path)
        connection.last_checked_at = datetime.now(UTC)
        connection.last_error = None
        configuration.last_run_at = job.completed_at
        configuration.last_status = "completed"
        configuration.last_error = None
        db.commit()
    except LoginRequiredError as exc:
        connection.status = "reauth_required"
        connection.last_error = str(exc)
        _fail_job(db, job, configuration, str(exc))
    except Exception as exc:
        connection.last_error = str(exc)
        _fail_job(db, job, configuration, str(exc))


def _new_export_path(directory: Path, job_id: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return directory / f"facebook_playwright_{timestamp}_{job_id[-8:]}.json"


def _write_export(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    temporary.replace(path)


def _fail_job(
    db: Session,
    job: CollectionJob,
    configuration: RunConfiguration | None,
    error: str,
) -> None:
    job.status = "failed"
    job.completed_at = datetime.now(UTC)
    job.error_summary = error[:4000]
    if configuration is not None:
        configuration.last_run_at = job.completed_at
        configuration.last_status = "failed"
        configuration.last_error = error[:4000]
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


def _owned_run_configuration(
    db: Session,
    user_id: str,
    configuration_id: str,
) -> RunConfiguration:
    configuration = db.scalar(
        select(RunConfiguration).where(
            RunConfiguration.id == configuration_id,
            RunConfiguration.user_id == user_id,
        )
    )
    if configuration is None:
        raise CollectionServiceError("Khong tim thay cau hinh thu thap.")
    return configuration


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
