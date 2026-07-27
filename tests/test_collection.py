import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from talent_radar.core.config import Settings
from talent_radar.models import (
    CollectionJob,
    CollectionSchedule,
    PlatformConnection,
    RawItem,
    Source,
)
from talent_radar.schemas import ScheduleCreate, ScheduleUpdate
from talent_radar.services.auth import register_user
from talent_radar.services.collection import (
    CollectionServiceError,
    create_schedule,
    delete_schedule,
    enqueue_default_facebook_group_job,
    enqueue_due_schedules,
    enqueue_job,
    run_job,
    update_schedule,
)


def add_source_and_connection(
    db: Session,
    user_id: str,
    *,
    suffix: str = "one",
) -> tuple[Source, PlatformConnection]:
    source = Source(
        id=f"fb_source_{suffix}",
        platform="facebook",
        source_kind="group",
        source_name=f"Facebook source {suffix}",
        source_url="https://www.facebook.com/groups/example/",
        enabled=True,
    )
    connection = PlatformConnection(
        id=f"connection_{suffix}",
        user_id=user_id,
        platform="facebook",
        status="connected",
        profile_dir=f"data/browser_profiles/{user_id}/facebook",
        login_url="https://www.facebook.com/",
    )
    db.add_all([source, connection])
    db.commit()
    return source, connection


def test_user_cannot_update_another_users_schedule(db: Session) -> None:
    owner = register_user(db, "owner@example.com", "correct-horse-2026")
    stranger = register_user(db, "stranger@example.com", "correct-horse-2026")
    source, connection = add_source_and_connection(db, owner.id)
    schedule = create_schedule(
        db,
        owner,
        ScheduleCreate(connection_id=connection.id, source_id=source.id),
    )

    with pytest.raises(CollectionServiceError):
        update_schedule(db, stranger, schedule.id, ScheduleUpdate(enabled=False))
    with pytest.raises(CollectionServiceError):
        enqueue_job(db, stranger, schedule.id)


def test_due_schedule_is_enqueued_only_once(db: Session) -> None:
    user = register_user(db, "huy@example.com", "correct-horse-2026")
    source, connection = add_source_and_connection(db, user.id)
    schedule = create_schedule(
        db,
        user,
        ScheduleCreate(connection_id=connection.id, source_id=source.id, interval_minutes=30),
    )
    schedule.next_run_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()

    assert enqueue_due_schedules(db) == 1
    assert enqueue_due_schedules(db) == 0
    assert len(db.scalars(select(CollectionJob)).all()) == 1


def test_default_facebook_group_action_creates_one_manual_background_job(
    db: Session,
) -> None:
    user = register_user(db, "one-click@example.com", "correct-horse-2026")
    source, _connection = add_source_and_connection(db, user.id, suffix="one_click")

    first = enqueue_default_facebook_group_job(db, user)
    second = enqueue_default_facebook_group_job(db, user)

    schedule = db.scalar(
        select(CollectionSchedule).where(CollectionSchedule.id == first.schedule_id)
    )
    assert first.id == second.id
    assert first.status == "queued"
    assert first.trigger == "manual"
    assert first.source_id == source.id
    assert schedule is not None
    assert schedule.enabled is False
    assert schedule.interval_minutes == 1440
    assert schedule.max_posts == 200


def test_delete_schedule_preserves_job_history(db: Session) -> None:
    user = register_user(db, "history@example.com", "correct-horse-2026")
    source, connection = add_source_and_connection(db, user.id, suffix="history")
    schedule = create_schedule(
        db,
        user,
        ScheduleCreate(connection_id=connection.id, source_id=source.id),
    )
    job = enqueue_job(db, user, schedule.id)

    delete_schedule(db, user, schedule.id)

    db.refresh(schedule)
    assert schedule.last_status == "deleted"
    assert schedule.enabled is False
    assert db.get(CollectionJob, job.id) is not None
    with pytest.raises(CollectionServiceError):
        enqueue_job(db, user, schedule.id)


def test_facebook_job_writes_export_and_imports_records(
    db: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = register_user(db, "huy@example.com", "correct-horse-2026")
    source, connection = add_source_and_connection(db, user.id)
    schedule = create_schedule(
        db,
        user,
        ScheduleCreate(connection_id=connection.id, source_id=source.id),
    )
    job = enqueue_job(db, user, schedule.id)
    progress_snapshots = []
    progress_database_counts = []

    def fake_collect(*_args, **kwargs):
        payload = {
            "crawler": "coccoc-playwright",
            "collected_at": datetime.now(UTC).isoformat(),
            "source_id": source.id,
            "posts": [
                {
                    "post": {
                        "external_id": "post_1",
                        "author": "Member",
                        "content": "A collected post",
                        "url": "https://www.facebook.com/groups/example/posts/1/",
                        "collected_comment_count": 1,
                    },
                    "comments": [
                        {
                            "external_id": "comment_1",
                            "author": "Commenter",
                            "content": "A collected comment",
                            "is_reply": False,
                        }
                    ],
                }
            ],
            "failures": [],
        }
        kwargs["on_progress"](payload)
        progress_database_counts.append(len(db.scalars(select(RawItem)).all()))
        progress_file = next(tmp_path.glob("facebook_playwright_*.json"))
        progress_snapshots.append(
            json.loads(progress_file.read_text(encoding="utf-8"))
        )
        return payload

    monkeypatch.setattr(
        "talent_radar.services.collection.FacebookCollector.collect",
        fake_collect,
    )
    settings = Settings(
        _env_file=None,
        crawl_output_directory=tmp_path,
        background_worker_enabled=False,
    )

    run_job(db, settings, job)

    db.refresh(job)
    assert job.status == "completed"
    assert job.posts_collected == 1
    assert job.comments_collected == 1
    assert job.output_path is not None
    assert Path(job.output_path).is_file()
    assert len(progress_snapshots) == 1
    assert len(progress_snapshots[0]["posts"]) == 1
    assert progress_database_counts == [2]
    assert len(db.scalars(select(RawItem)).all()) == 2
