from datetime import UTC, datetime

from sqlalchemy.orm import Session

from talent_radar.models import PlatformConnection, Source
from talent_radar.schemas import (
    ImportBatchRequest,
    ImportRecord,
    RunConfigurationCreate,
)
from talent_radar.services.auth import register_user
from talent_radar.services.collection import create_run_configuration, enqueue_job
from talent_radar.services.content_queries import count_content, list_content
from talent_radar.services.import_adapter import run_import_batch


def _job_for_user(db: Session, email: str, suffix: str):
    user = register_user(db, email, "correct-horse-2026")
    source = Source(
        id=f"source_{suffix}",
        platform="facebook",
        source_kind="group",
        source_name=f"Group {suffix}",
        source_url=f"https://www.facebook.com/groups/{suffix}/",
        enabled=True,
    )
    connection = PlatformConnection(
        id=f"connection_{suffix}",
        user_id=user.id,
        platform="facebook",
        status="connected",
        profile_dir="Default",
        login_url="https://www.facebook.com/",
    )
    db.add_all([source, connection])
    db.commit()
    configuration = create_run_configuration(
        db,
        user,
        RunConfigurationCreate(
            connection_id=connection.id,
            source_id=source.id,
        ),
    )
    return user, source, enqueue_job(db, user, configuration.id)


def test_content_queries_are_paginated_and_scoped_to_user(db: Session) -> None:
    user, source, job = _job_for_user(db, "owner@example.com", "owner")
    other_user, other_source, other_job = _job_for_user(
        db,
        "other@example.com",
        "other",
    )
    now = datetime.now(UTC)
    run_import_batch(
        db,
        ImportBatchRequest(
            import_batch_id=job.id,
            records=[
                ImportRecord(
                    source_id=source.id,
                    platform="facebook",
                    item_type="post",
                    content_text="VSF community update",
                    external_id="post_owner",
                    published_at=now,
                    author_id="Member A",
                    raw_metadata={
                        "author_display_name": "Member A",
                        "group": "IT Viec",
                        "reaction_count": 12,
                        "relevance": {
                            "topic": "vsf",
                            "matched_terms": ["VSF"],
                        },
                    },
                ),
                ImportRecord(
                    source_id=source.id,
                    platform="facebook",
                    item_type="comment",
                    content_text="Interested",
                    external_id="comment_owner",
                    parent_external_id="post_owner",
                    author_id="Member B",
                    raw_metadata={"author_display_name": "Member B"},
                ),
            ],
        ),
    )
    run_import_batch(
        db,
        ImportBatchRequest(
            import_batch_id=other_job.id,
            records=[
                ImportRecord(
                    source_id=other_source.id,
                    platform="facebook",
                    item_type="post",
                    content_text="Other user's post",
                    external_id="post_other",
                )
            ],
        ),
    )

    posts = list_content(
        db,
        user,
        kind="posts",
        page=1,
        page_size=20,
        search="community",
    )
    comments = list_content(
        db,
        user,
        kind="comments",
        page=1,
        page_size=20,
        post_external_id="post_owner",
    )

    assert posts.total == 1
    assert posts.items[0].author == "Member A"
    assert posts.items[0].group_name == "IT Viec"
    assert posts.items[0].matched_terms == ["VSF"]
    assert comments.total == 1
    assert comments.items[0].parent_external_id == "post_owner"
    assert count_content(db, user, kind="posts") == 1
    assert count_content(db, other_user, kind="posts") == 1
