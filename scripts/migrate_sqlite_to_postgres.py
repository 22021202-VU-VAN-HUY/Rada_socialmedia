from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from talent_radar.models import (
    AuthSession,
    CollectionJob,
    ContentItem,
    ContentMetricSnapshot,
    ContentTopicMatch,
    OAuthState,
    PlatformConnection,
    RawItem,
    RunConfiguration,
    SocialAccount,
    Source,
    User,
)


DEFAULT_TARGET_URL = (
    "postgresql+psycopg://talent_radar:talent_radar@localhost:5432/talent_radar"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy the legacy Talent Radar SQLite data into an empty PostgreSQL schema."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("data/talent_radar.sqlite3"),
        help="Path to the legacy SQLite database.",
    )
    parser.add_argument(
        "--target-url",
        default=DEFAULT_TARGET_URL,
        help="SQLAlchemy PostgreSQL URL. The target schema must already be migrated.",
    )
    args = parser.parse_args()
    report = migrate(args.source, args.target_url)
    print(json.dumps(report, ensure_ascii=False, indent=2))


def migrate(source_path: Path, target_url: str) -> dict[str, int]:
    source_path = source_path.resolve()
    if not source_path.is_file():
        raise SystemExit(f"SQLite source does not exist: {source_path}")
    if not target_url.startswith(("postgresql://", "postgresql+psycopg://")):
        raise SystemExit("Target URL must point to PostgreSQL.")

    source = sqlite3.connect(f"file:{source_path.as_posix()}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    target_engine = create_engine(target_url, future=True, pool_pre_ping=True)

    with Session(target_engine) as target:
        existing_users = target.scalar(select(func.count()).select_from(User)) or 0
        if existing_users:
            raise SystemExit(
                "PostgreSQL target is not empty. Migration stopped to prevent duplicate data."
            )
        report = _copy_database(source, target)
        target.commit()

    source.close()
    return report


def _copy_database(source: sqlite3.Connection, target: Session) -> dict[str, int]:
    report: dict[str, int] = {}

    users = _rows(source, "users")
    for row in users:
        target.add(
            User(
                id=row["id"],
                email=row["email"],
                password_hash=row["password_hash"],
                is_active=bool(row["is_active"]),
                created_at=_datetime(row["created_at"]),
                updated_at=_datetime(row["updated_at"]),
            )
        )
    target.flush()
    report["users"] = len(users)
    fallback_user_id = users[0]["id"] if len(users) == 1 else None

    sessions = _rows(source, "auth_sessions")
    for row in sessions:
        target.add(
            AuthSession(
                id=row["id"],
                user_id=row["user_id"],
                token_hash=row["token_hash"],
                expires_at=_datetime(row["expires_at"]),
                revoked_at=_datetime(row["revoked_at"]),
                created_at=_datetime(row["created_at"]),
                updated_at=_datetime(row["updated_at"]),
            )
        )
    report["auth_sessions"] = len(sessions)

    sources = _rows(source, "sources")
    source_platforms: dict[str, str] = {}
    for row in sources:
        platform = row["platform"]
        source_platforms[row["id"]] = platform
        target.add(
            Source(
                id=row["id"],
                platform=platform,
                external_id=_source_external_id(platform, row["source_url"]),
                source_kind=row["source_kind"],
                source_name=row["source_name"],
                handle=_source_handle(platform, row["source_url"]),
                source_url=row["source_url"],
                source_type=row["source_type"],
                access_basis=row["access_basis"],
                authorization_status=row["authorization_status"],
                collection_method=row["collection_method"],
                enabled=bool(row["enabled"]),
                priority=row["priority"],
                crawl_frequency=row["crawl_frequency"],
                lookback_hours=row["lookback_hours"],
                comment_policy=_json(row["comment_policy"]),
                privacy=_json(row["privacy"]),
                owner=_json(row["owner"]),
                platform_metadata={},
                created_at=_datetime(row["created_at"]),
                updated_at=_datetime(row["updated_at"]),
            )
        )
    target.flush()
    report["sources"] = len(sources)

    connections = _rows(source, "platform_connections")
    for row in connections:
        target.add(
            PlatformConnection(
                id=row["id"],
                user_id=row["user_id"],
                platform=row["platform"],
                status=row["status"],
                auth_method=row["auth_method"],
                profile_dir=row["profile_dir"],
                login_url=row["login_url"],
                browser_process_id=row["browser_process_id"],
                last_connected_at=_datetime(row["last_connected_at"]),
                last_checked_at=_datetime(row["last_checked_at"]),
                last_error=row["last_error"],
                connection_metadata=_json(row["connection_metadata"]),
                created_at=_datetime(row["created_at"]),
                updated_at=_datetime(row["updated_at"]),
            )
        )
    target.flush()
    report["platform_connections"] = len(connections)

    oauth_states = _rows(source, "oauth_states")
    for row in oauth_states:
        target.add(
            OAuthState(
                id=row["id"],
                user_id=row["user_id"],
                connection_id=row["connection_id"],
                provider=row["provider"],
                state_hash=row["state_hash"],
                expires_at=_datetime(row["expires_at"]),
                used_at=_datetime(row["used_at"]),
                created_at=_datetime(row["created_at"]),
                updated_at=_datetime(row["updated_at"]),
            )
        )
    report["oauth_states"] = len(oauth_states)

    configurations = _rows(source, "collection_schedules")
    for row in configurations:
        target.add(
            RunConfiguration(
                id=row["id"],
                user_id=row["user_id"],
                connection_id=row["connection_id"],
                source_id=row["source_id"],
                max_posts=row["max_posts"],
                max_comments_per_post=100,
                lookback_hours=24,
                include_replies=True,
                filters={},
                is_archived=row["last_status"] == "deleted",
                last_run_at=_datetime(row["last_run_at"]),
                last_status=row["last_status"],
                last_error=row["last_error"],
                created_at=_datetime(row["created_at"]),
                updated_at=_datetime(row["updated_at"]),
            )
        )
    target.flush()
    report["run_configurations"] = len(configurations)

    jobs = _rows(source, "collection_jobs")
    job_users: dict[str, str] = {}
    for row in jobs:
        job_users[row["id"]] = row["user_id"]
        target.add(
            CollectionJob(
                id=row["id"],
                user_id=row["user_id"],
                run_configuration_id=row["schedule_id"],
                connection_id=row["connection_id"],
                source_id=row["source_id"],
                platform=source_platforms.get(row["source_id"], "manual"),
                status=row["status"],
                trigger=row["trigger"],
                started_at=_datetime(row["started_at"]),
                completed_at=_datetime(row["completed_at"]),
                posts_collected=row["posts_collected"],
                comments_collected=row["comments_collected"],
                replies_collected=0,
                records_inserted=0,
                duplicates_skipped=0,
                output_path=row["output_path"],
                error_summary=row["error_summary"],
                result_metadata={},
                created_at=_datetime(row["created_at"]),
                updated_at=_datetime(row["updated_at"]),
            )
        )
    target.flush()
    report["collection_jobs"] = len(jobs)

    raw_rows = {row["id"]: row for row in _rows(source, "raw_items")}
    normalized_rows = _rows(source, "normalized_items")
    accounts: dict[tuple[str, str], SocialAccount] = {}
    items_by_external: dict[tuple[str | None, str, str], ContentItem] = {}
    pending_relations: list[tuple[ContentItem, str | None]] = []

    for normalized in normalized_rows:
        raw = raw_rows[normalized["raw_item_id"]]
        metadata = _json(raw["raw_metadata"])
        user_id = job_users.get(normalized["import_batch_id"]) or fallback_user_id
        author_hash = normalized["author_hash"]
        author = None
        if author_hash:
            account_key = (normalized["platform"], author_hash)
            author = accounts.get(account_key)
            if author is None:
                author = SocialAccount(
                    id=_stable_id("account", *account_key),
                    platform=normalized["platform"],
                    external_id=None,
                    username=None,
                    display_name=metadata.get("author_display_name"),
                    profile_url=None,
                    account_hash=author_hash,
                    is_anonymous=True,
                    platform_metadata={},
                )
                accounts[account_key] = author
                target.add(author)

        raw_item = RawItem(
            id=raw["id"],
            owner_user_id=user_id,
            source_id=raw["source_id"],
            collection_job_id=(
                raw["import_batch_id"] if raw["import_batch_id"] in job_users else None
            ),
            platform=raw["platform"],
            external_id=raw["external_id"],
            item_type=raw["item_type"],
            parent_external_id=raw["parent_external_id"],
            raw_content=raw["raw_content"],
            raw_payload=metadata,
            content_hash=raw["content_hash"],
            permalink=raw["permalink"],
            import_batch_id=raw["import_batch_id"],
            published_at=_datetime(raw["published_at"]),
            collected_at=_datetime(raw["collected_at"]) or datetime.now(UTC),
            created_at=_datetime(raw["created_at"]),
            updated_at=_datetime(raw["updated_at"]),
        )
        content_item = ContentItem(
            id=normalized["id"],
            raw_item_id=raw["id"],
            owner_user_id=user_id,
            source_id=normalized["source_id"],
            platform=normalized["platform"],
            external_id=raw["external_id"],
            item_type=normalized["item_type"],
            parent_item_id=None,
            root_item_id=None,
            author=author,
            content_text=normalized["content_text"],
            content_language=None,
            permalink=normalized["permalink"],
            import_batch_id=normalized["import_batch_id"],
            published_at=_datetime(normalized["published_at"]),
            collected_at=_datetime(normalized["collected_at"]) or datetime.now(UTC),
            provenance_status=normalized["provenance_status"],
            platform_metadata={},
            created_at=_datetime(normalized["created_at"]),
            updated_at=_datetime(normalized["updated_at"]),
        )
        target.add_all([raw_item, content_item])
        if raw["external_id"]:
            items_by_external[(user_id, raw["source_id"], raw["external_id"])] = content_item
        pending_relations.append((content_item, raw["parent_external_id"]))
        _add_metric(target, content_item, metadata)
        _add_topic(target, content_item, metadata)

    target.flush()
    for item, parent_external_id in pending_relations:
        if not parent_external_id:
            continue
        parent = items_by_external.get(
            (item.owner_user_id, item.source_id, parent_external_id)
        )
        if parent is None:
            continue
        item.parent_item_id = parent.id
        item.root_item_id = parent.id if parent.item_type == "post" else parent.root_item_id

    report["raw_items"] = len(raw_rows)
    report["content_items"] = len(normalized_rows)
    report["social_accounts"] = len(accounts)
    report["content_metric_snapshots"] = len(normalized_rows)
    report["content_topic_matches"] = sum(
        1
        for row in normalized_rows
        if (_json(raw_rows[row["raw_item_id"]]["raw_metadata"]).get("relevance") or {})
    )
    return report


def _add_metric(target: Session, item: ContentItem, metadata: dict[str, Any]) -> None:
    target.add(
        ContentMetricSnapshot(
            id=_stable_id("metric", item.id, item.collected_at.isoformat()),
            content_item=item,
            observed_at=item.collected_at,
            reaction_count=_int(metadata.get("reaction_count")),
            like_count=_int(metadata.get("like_count")),
            comment_count=_int(metadata.get("reported_comment_count")),
            collected_comment_count=_int(metadata.get("collected_comment_count")),
            reply_count=_int(metadata.get("reply_count")),
            share_count=_int(metadata.get("share_count")),
            view_count=_int(metadata.get("view_count")),
            save_count=_int(metadata.get("save_count")),
            platform_metrics={},
        )
    )


def _add_topic(target: Session, item: ContentItem, metadata: dict[str, Any]) -> None:
    relevance = metadata.get("relevance") or {}
    if not relevance:
        return
    topic_key = relevance.get("topic") or "unclassified"
    target.add(
        ContentTopicMatch(
            id=_stable_id("topic", item.id, topic_key),
            content_item=item,
            topic_key=topic_key,
            matched_terms=relevance.get("matched_terms") or [],
            matched_groups=relevance.get("matched_groups") or [],
            score=1.0,
        )
    )


def _rows(connection: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    return list(connection.execute(f'SELECT * FROM "{table}"'))


def _json(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    return json.loads(value)


def _datetime(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


def _source_external_id(platform: str, url: str | None) -> str | None:
    if not url:
        return None
    parts = [part for part in urlparse(url).path.split("/") if part]
    if platform == "facebook" and "groups" in parts:
        index = parts.index("groups")
        return parts[index + 1] if len(parts) > index + 1 else None
    return parts[-1].removeprefix("@") if parts else None


def _source_handle(platform: str, url: str | None) -> str | None:
    if platform not in {"tiktok", "threads"} or not url:
        return None
    parts = [part for part in urlparse(url).path.split("/") if part]
    return parts[-1].removeprefix("@") if parts else None


if __name__ == "__main__":
    main()
