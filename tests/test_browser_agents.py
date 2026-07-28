from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from talent_radar.models import PlatformConnection, Source
from talent_radar.schemas import (
    BrowserAgentClaimRequest,
    BrowserAgentHeartbeat,
    BrowserAgentItemBatch,
    BrowserAgentJobComplete,
    BrowserAgentPairRequest,
    BrowserPlatformConnection,
    ImportRecord,
    RunConfigurationCreate,
)
from talent_radar.services.auth import register_user
from talent_radar.services.browser_agents import (
    authenticate_agent,
    claim_job,
    complete_job,
    create_pairing_code,
    heartbeat_agent,
    import_job_items,
    pair_agent,
    reconcile_connections,
    reset_connections_for_login,
)
from talent_radar.services.collection import (
    create_run_configuration,
    enqueue_job,
    next_queued_job,
)


def test_agent_pairs_claims_and_streams_job_items(db: Session) -> None:
    user = register_user(db, "extension@example.com", "correct-horse-2026")
    source = Source(
        id="facebook_agent_source",
        platform="facebook",
        source_kind="group",
        source_name="Agent source",
        source_url="https://www.facebook.com/groups/example/",
        enabled=True,
    )
    connection = PlatformConnection(
        id="facebook_agent_connection",
        user_id=user.id,
        platform="facebook",
        status="connected",
        auth_method="browser_extension",
        profile_dir="",
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
            max_posts=10,
        ),
    )
    job = enqueue_job(db, user, configuration.id)

    pairing_code, _ = create_pairing_code(db, user)
    raw_token, agent = pair_agent(
        db,
        BrowserAgentPairRequest(
            pairing_code=pairing_code,
            name="Coc Coc Huy",
            browser="coccoc",
            capabilities=["facebook"],
        ),
    )

    assert authenticate_agent(db, raw_token).id == agent.id
    heartbeat_agent(
        db,
        agent,
        BrowserAgentHeartbeat(version="136.0", capabilities=["facebook"]),
    )
    claimed = claim_job(
        db,
        agent,
        BrowserAgentClaimRequest(supported_platforms=["facebook"]),
    )

    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.source_url == source.source_url
    assert claimed.published_since.hour == 0

    updated_job = import_job_items(
        db,
        agent,
        job.id,
        BrowserAgentItemBatch(
            records=[
                ImportRecord(
                    source_id=source.id,
                    platform="facebook",
                    item_type="post",
                    external_id="post_1",
                    content_text="VSF is hiring.",
                    published_at=datetime.now(UTC),
                ),
                ImportRecord(
                    source_id=source.id,
                    platform="facebook",
                    item_type="comment",
                    external_id="comment_1",
                    parent_external_id="post_1",
                    root_external_id="post_1",
                    content_text="A comment on the relevant post.",
                    published_at=datetime.now(UTC),
                ),
                ImportRecord(
                    source_id=source.id,
                    platform="facebook",
                    item_type="post",
                    external_id="post_2",
                    content_text="An unrelated post.",
                    published_at=datetime.now(UTC),
                ),
                ImportRecord(
                    source_id=source.id,
                    platform="facebook",
                    item_type="post",
                    external_id="post_3",
                    content_text="An old post.",
                    published_at=datetime.now(UTC) - timedelta(days=1),
                ),
            ]
        ),
    )
    assert updated_job.records_inserted == 3
    assert updated_job.posts_collected == 2
    assert updated_job.comments_collected == 1

    completed = complete_job(
        db,
        agent,
        job.id,
        BrowserAgentJobComplete(status="completed", posts_collected=2),
    )
    assert completed.status == "completed"
    assert completed.browser_agent_id == agent.id


def test_new_jobs_are_not_claimed_by_legacy_worker(db: Session) -> None:
    user = register_user(db, "worker@example.com", "correct-horse-2026")
    source = Source(
        id="worker_source",
        platform="facebook",
        source_kind="group",
        source_name="Worker source",
        source_url="https://www.facebook.com/groups/example/",
        enabled=True,
    )
    connection = PlatformConnection(
        id="worker_connection",
        user_id=user.id,
        platform="facebook",
        status="connected",
        profile_dir="",
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

    job = enqueue_job(db, user, configuration.id)

    assert job.executor == "browser_extension"
    assert next_queued_job(db) is None


def test_heartbeat_is_the_source_of_truth_for_platform_connections(
    db: Session,
) -> None:
    user = register_user(db, "connection-check@example.com", "correct-horse-2026")
    pairing_code, _ = create_pairing_code(db, user)
    _, agent = pair_agent(
        db,
        BrowserAgentPairRequest(
            pairing_code=pairing_code,
            name="Coc Coc Huy",
            browser="coccoc",
            capabilities=["facebook", "tiktok", "threads"],
        ),
    )

    heartbeat_agent(
        db,
        agent,
        BrowserAgentHeartbeat(
            connections=[
                BrowserPlatformConnection(
                    platform="facebook",
                    connected=True,
                    account_id="facebook-user-1",
                ),
                BrowserPlatformConnection(platform="tiktok", connected=False),
                BrowserPlatformConnection(platform="threads", connected=False),
            ]
        ),
    )
    connections = {item.platform: item for item in reconcile_connections(db, user)}

    assert connections["facebook"].status == "connected"
    assert connections["facebook"].connection_metadata["connected_account_id"] == (
        "facebook-user-1"
    )
    assert connections["tiktok"].status == "disconnected"
    assert connections["threads"].status == "disconnected"

    reset_connections_for_login(db, user)
    assert reconcile_connections(db, user)[0].status == "disconnected"
