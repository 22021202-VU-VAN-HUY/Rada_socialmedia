import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from talent_radar.models import (
    CollectionJob,
    ContentItem,
    ContentMetricSnapshot,
    ContentTopicMatch,
    RawItem,
    SocialAccount,
    Source,
)
from talent_radar.schemas import ImportBatchRequest, ImportBatchResult, ImportRecord


def load_import_file(path: Path) -> list[ImportRecord]:
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [ImportRecord.model_validate(row) for row in csv.DictReader(handle)]
    if suffix == ".json":
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
        if isinstance(data, dict) and data.get("crawler") in {"coccoc-ui", "coccoc-playwright"}:
            return records_from_coccoc_export(data)
        rows = data.get("records", data) if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise ValueError("JSON import must be a list or an object with a records list")
        return [ImportRecord.model_validate(row) for row in rows]
    raise ValueError("Import file must be .csv or .json")


def records_from_coccoc_export(data: dict) -> list[ImportRecord]:
    source_id = data.get("source_id")
    if not source_id:
        raise ValueError("Coc Coc export must include source_id")

    records: list[ImportRecord] = []
    for item in data.get("posts", []):
        post = item.get("post") or {}
        collected_at = item.get("collected_at") or data.get("collected_at")
        relevance = post.get("relevance") or {}
        if post.get("content"):
            records.append(
                ImportRecord(
                    source_id=source_id,
                    platform="facebook",
                    item_type="post",
                    content_text=post["content"],
                    external_id=post.get("external_id"),
                    permalink=post.get("url"),
                    published_at=post.get("published_at"),
                    collected_at=collected_at,
                    author_id=post.get("author"),
                    author_display_name=post.get("author"),
                    reaction_count=post.get("reaction_count", 0),
                    comment_count=post.get("reported_comment_count", 0),
                    collected_comment_count=post.get("collected_comment_count", 0),
                    topic=relevance.get("topic"),
                    matched_terms=relevance.get("matched_terms") or [],
                    matched_groups=relevance.get("matched_groups") or [],
                    raw_metadata={
                        "author_display_name": post.get("author"),
                        "group": post.get("group"),
                        "published_label": post.get("published_label"),
                        "reaction_count": post.get("reaction_count", 0),
                        "reported_comment_count": post.get("reported_comment_count", 0),
                        "collected_comment_count": post.get("collected_comment_count", 0),
                        "relevance": post.get("relevance"),
                    },
                )
            )

        for comment in item.get("comments", []):
            content = comment.get("content") or "[non-text comment]"
            records.append(
                ImportRecord(
                    source_id=source_id,
                    platform="facebook",
                    item_type="reply" if comment.get("is_reply") else "comment",
                    content_text=content,
                    external_id=comment.get("external_id"),
                    parent_external_id=comment.get("parent_external_id")
                    or post.get("external_id"),
                    root_external_id=post.get("external_id"),
                    permalink=comment.get("permalink"),
                    published_at=comment.get("published_at"),
                    collected_at=collected_at,
                    author_id=comment.get("author"),
                    author_display_name=comment.get("author"),
                    reaction_count=comment.get("reaction_count", 0),
                    like_count=comment.get("like_count", 0),
                    raw_metadata={
                        "author_display_name": comment.get("author"),
                        "published_label": comment.get("published_label"),
                        "parent_author": comment.get("parent_author"),
                        "aria_label": comment.get("aria_label"),
                        "non_text": not bool(comment.get("content")),
                    },
                )
            )
    return records


def run_import_batch(
    db: Session,
    payload: ImportBatchRequest,
    *,
    owner_user_id: str | None = None,
) -> ImportBatchResult:
    batch_id = payload.import_batch_id or (
        f"import_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    )
    job = db.get(CollectionJob, batch_id)
    resolved_user_id = owner_user_id or (job.user_id if job else None)
    raw_item_ids: list[str] = []
    content_item_ids: list[str] = []
    skipped_duplicates = 0

    for index, record in enumerate(payload.records, start=1):
        source = db.get(Source, record.source_id)
        if source is None:
            raise ValueError(f"Unknown source_id: {record.source_id}")
        if source.platform != record.platform and record.platform != "manual":
            raise ValueError(
                f"Platform mismatch for source {record.source_id}: "
                f"{source.platform} != {record.platform}"
            )

        collected_at = record.collected_at or datetime.now(UTC)
        content_hash = _content_hash(record)
        duplicate = db.scalar(
            select(RawItem).where(
                RawItem.owner_user_id == resolved_user_id,
                RawItem.source_id == record.source_id,
                RawItem.content_hash == content_hash,
            )
        )
        if duplicate is not None:
            duplicate.raw_payload = _raw_payload(record)
            duplicate.permalink = record.permalink or duplicate.permalink
            duplicate.collected_at = collected_at
            if record.published_at is not None:
                duplicate.published_at = record.published_at
            content_item = db.scalar(
                select(ContentItem).where(ContentItem.raw_item_id == duplicate.id)
            )
            if content_item is not None:
                _update_content_item(db, content_item, record, collected_at)
                _upsert_metric_snapshot(db, content_item, record, collected_at)
                _upsert_topic_match(db, content_item, record)
            skipped_duplicates += 1
            continue

        record_batch_id = record.import_batch_id or batch_id
        raw_id = _item_id("raw", record, record_batch_id, index)
        content_id = _item_id("content", record, record_batch_id, index)
        parent = _resolve_related_item(
            db,
            owner_user_id=resolved_user_id,
            source_id=record.source_id,
            external_id=record.parent_external_id,
        )
        root = _resolve_related_item(
            db,
            owner_user_id=resolved_user_id,
            source_id=record.source_id,
            external_id=record.root_external_id,
        )
        if root is None and parent is not None:
            root = parent if parent.item_type == "post" else _root_for(db, parent)

        raw_item = RawItem(
            id=raw_id,
            owner_user_id=resolved_user_id,
            source_id=record.source_id,
            collection_job_id=job.id if job else None,
            platform=record.platform,
            external_id=record.external_id,
            item_type=record.item_type,
            parent_external_id=record.parent_external_id,
            raw_content=record.content_text,
            raw_payload=_raw_payload(record),
            content_hash=content_hash,
            permalink=record.permalink,
            import_batch_id=record_batch_id,
            published_at=record.published_at,
            collected_at=collected_at,
        )
        content_item = ContentItem(
            id=content_id,
            raw_item_id=raw_id,
            owner_user_id=resolved_user_id,
            source_id=record.source_id,
            platform=record.platform,
            external_id=record.external_id,
            item_type=record.item_type,
            parent_item_id=record.parent_item_id or (parent.id if parent else None),
            root_item_id=root.id if root else None,
            author=_upsert_social_account(db, record),
            content_text=record.content_text.strip(),
            content_language=record.content_language,
            permalink=record.permalink,
            import_batch_id=record_batch_id,
            published_at=record.published_at,
            collected_at=collected_at,
            provenance_status="complete" if record.permalink or record.external_id else "import_only",
            platform_metadata=record.platform_metadata,
        )
        db.add_all([raw_item, content_item])
        db.flush()
        _upsert_metric_snapshot(db, content_item, record, collected_at)
        _upsert_topic_match(db, content_item, record)
        raw_item_ids.append(raw_id)
        content_item_ids.append(content_id)

    db.commit()
    return ImportBatchResult(
        import_batch_id=batch_id,
        received=len(payload.records),
        inserted=len(raw_item_ids),
        skipped_duplicates=skipped_duplicates,
        raw_item_ids=raw_item_ids,
        normalized_item_ids=content_item_ids,
    )


def _update_content_item(
    db: Session,
    item: ContentItem,
    record: ImportRecord,
    collected_at: datetime,
) -> None:
    item.content_text = record.content_text.strip()
    item.permalink = record.permalink or item.permalink
    item.collected_at = collected_at
    item.published_at = record.published_at or item.published_at
    item.content_language = record.content_language or item.content_language
    item.platform_metadata = record.platform_metadata or item.platform_metadata
    account = _upsert_social_account(db, record)
    if account is not None:
        item.author = account
    parent = _resolve_related_item(
        db,
        owner_user_id=item.owner_user_id,
        source_id=item.source_id,
        external_id=record.parent_external_id,
    )
    if parent is not None:
        item.parent_item_id = parent.id
        root = parent if parent.item_type == "post" else _root_for(db, parent)
        item.root_item_id = root.id if root else None


def _upsert_social_account(db: Session, record: ImportRecord) -> SocialAccount | None:
    display_name = record.author_display_name or record.raw_metadata.get("author_display_name")
    identity = record.author_id or record.author_username or display_name
    account_hash = record.author_hash or _hash_author(identity)
    if not account_hash:
        return None
    account = db.scalar(
        select(SocialAccount).where(
            SocialAccount.platform == record.platform,
            SocialAccount.account_hash == account_hash,
        )
    )
    if account is None:
        account = SocialAccount(
            id="account_" + hashlib.sha256(
                f"{record.platform}|{account_hash}".encode("utf-8")
            ).hexdigest()[:24],
            platform=record.platform,
            external_id=record.author_id,
            username=record.author_username,
            display_name=display_name,
            profile_url=record.author_profile_url,
            account_hash=account_hash,
            is_anonymous=not bool(record.author_id or record.author_username),
        )
        db.add(account)
        db.flush()
    else:
        account.display_name = display_name or account.display_name
        account.username = record.author_username or account.username
        account.profile_url = record.author_profile_url or account.profile_url
        account.external_id = record.author_id or account.external_id
    return account


def _upsert_metric_snapshot(
    db: Session,
    item: ContentItem,
    record: ImportRecord,
    observed_at: datetime,
) -> None:
    metadata = record.raw_metadata
    values = {
        "reaction_count": record.reaction_count
        or _integer(metadata.get("reaction_count")),
        "like_count": record.like_count or _integer(metadata.get("like_count")),
        "comment_count": record.comment_count
        or _integer(metadata.get("reported_comment_count")),
        "collected_comment_count": record.collected_comment_count
        or _integer(metadata.get("collected_comment_count")),
        "reply_count": record.reply_count or _integer(metadata.get("reply_count")),
        "share_count": record.share_count or _integer(metadata.get("share_count")),
        "view_count": record.view_count or _integer(metadata.get("view_count")),
        "save_count": record.save_count or _integer(metadata.get("save_count")),
    }
    snapshot = db.scalar(
        select(ContentMetricSnapshot).where(
            ContentMetricSnapshot.content_item_id == item.id,
            ContentMetricSnapshot.observed_at == observed_at,
        )
    )
    if snapshot is None:
        snapshot = ContentMetricSnapshot(
            id="metric_" + hashlib.sha256(
                f"{item.id}|{observed_at.isoformat()}".encode("utf-8")
            ).hexdigest()[:24],
            content_item_id=item.id,
            observed_at=observed_at,
            platform_metrics=record.platform_metadata,
            **values,
        )
        db.add(snapshot)
    else:
        for key, value in values.items():
            setattr(snapshot, key, value)
        snapshot.platform_metrics = record.platform_metadata


def _upsert_topic_match(db: Session, item: ContentItem, record: ImportRecord) -> None:
    relevance = record.raw_metadata.get("relevance") or {}
    topic = record.topic or relevance.get("topic")
    matched_terms = record.matched_terms or relevance.get("matched_terms") or []
    matched_groups = record.matched_groups or relevance.get("matched_groups") or []
    if not topic and not matched_terms:
        return
    topic_key = topic or "unclassified"
    match = db.scalar(
        select(ContentTopicMatch).where(
            ContentTopicMatch.content_item_id == item.id,
            ContentTopicMatch.topic_key == topic_key,
        )
    )
    if match is None:
        match = ContentTopicMatch(
            id="topic_" + hashlib.sha256(
                f"{item.id}|{topic_key}".encode("utf-8")
            ).hexdigest()[:24],
            content_item_id=item.id,
            topic_key=topic_key,
        )
        db.add(match)
    match.matched_terms = [str(value) for value in matched_terms]
    match.matched_groups = [str(value) for value in matched_groups]
    match.score = record.topic_score


def _resolve_related_item(
    db: Session,
    *,
    owner_user_id: str | None,
    source_id: str,
    external_id: str | None,
) -> ContentItem | None:
    if not external_id:
        return None
    return db.scalar(
        select(ContentItem).where(
            ContentItem.owner_user_id == owner_user_id,
            ContentItem.source_id == source_id,
            ContentItem.external_id == external_id,
        )
    )


def _root_for(db: Session, item: ContentItem) -> ContentItem | None:
    if item.item_type == "post":
        return item
    if item.root_item_id:
        return db.get(ContentItem, item.root_item_id)
    if item.parent_item_id:
        parent = db.get(ContentItem, item.parent_item_id)
        if parent is not None:
            return _root_for(db, parent)
    return None


def _raw_payload(record: ImportRecord) -> dict:
    payload = dict(record.raw_metadata)
    if record.platform_metadata:
        payload["platform_metadata"] = record.platform_metadata
    return payload


def _content_hash(record: ImportRecord) -> str:
    basis = "|".join(
        [
            record.source_id,
            record.platform,
            record.item_type,
            record.external_id or "",
            record.content_text.strip().casefold(),
        ]
    )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def _hash_author(author_id: str | None) -> str | None:
    if not author_id:
        return None
    return "sha256:" + hashlib.sha256(author_id.encode("utf-8")).hexdigest()


def _item_id(prefix: str, record: ImportRecord, batch_id: str, index: int) -> str:
    if record.external_id:
        basis = f"{prefix}|{record.source_id}|{record.external_id}"
    else:
        basis = f"{prefix}|{batch_id}|{index}|{record.content_text.strip()}"
    return f"{prefix}_{hashlib.sha256(basis.encode('utf-8')).hexdigest()[:24]}"


def _integer(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
