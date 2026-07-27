from __future__ import annotations

from datetime import datetime
from math import ceil

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from talent_radar.models import CollectionJob, NormalizedItem, RawItem, Source, User
from talent_radar.schemas import ContentItemRead, ContentPage


def list_content(
    db: Session,
    user: User,
    *,
    kind: str,
    page: int,
    page_size: int,
    search: str | None = None,
    source_id: str | None = None,
    published_after: datetime | None = None,
    post_external_id: str | None = None,
) -> ContentPage:
    item_types = ("post",) if kind == "posts" else ("comment", "reply")
    owned_batches = select(CollectionJob.id).where(CollectionJob.user_id == user.id)
    conditions = [
        NormalizedItem.item_type.in_(item_types),
        NormalizedItem.import_batch_id.in_(owned_batches),
    ]
    if search:
        conditions.append(NormalizedItem.content_text.ilike(f"%{search.strip()}%"))
    if source_id:
        conditions.append(NormalizedItem.source_id == source_id)
    if published_after:
        conditions.append(
            func.coalesce(
                NormalizedItem.published_at,
                NormalizedItem.collected_at,
            )
            >= published_after
        )
    if post_external_id and kind == "comments":
        conditions.append(RawItem.parent_external_id == post_external_id)

    base = (
        select(NormalizedItem, RawItem, Source)
        .join(RawItem, RawItem.id == NormalizedItem.raw_item_id)
        .join(Source, Source.id == NormalizedItem.source_id)
        .where(*conditions)
    )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(
        base.order_by(
            func.coalesce(
                NormalizedItem.published_at,
                NormalizedItem.collected_at,
            ).desc(),
            NormalizedItem.created_at.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [_content_item(normalized, raw, source) for normalized, raw, source in rows]
    return ContentPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, ceil(total / page_size)),
    )


def count_content(db: Session, user: User, *, kind: str) -> int:
    item_types = ("post",) if kind == "posts" else ("comment", "reply")
    owned_batches = select(CollectionJob.id).where(CollectionJob.user_id == user.id)
    return (
        db.scalar(
            select(func.count())
            .select_from(NormalizedItem)
            .where(
                NormalizedItem.item_type.in_(item_types),
                NormalizedItem.import_batch_id.in_(owned_batches),
            )
        )
        or 0
    )


def _content_item(
    normalized: NormalizedItem,
    raw: RawItem,
    source: Source,
) -> ContentItemRead:
    metadata = raw.raw_metadata or {}
    relevance = metadata.get("relevance") or {}
    matched_terms = relevance.get("matched_terms") or []
    return ContentItemRead(
        id=normalized.id,
        source_id=normalized.source_id,
        source_name=source.source_name,
        platform=normalized.platform,
        item_type=normalized.item_type,
        external_id=raw.external_id,
        parent_external_id=raw.parent_external_id,
        author=metadata.get("author_display_name"),
        content=normalized.content_text,
        permalink=normalized.permalink,
        published_at=normalized.published_at,
        collected_at=normalized.collected_at,
        published_label=metadata.get("published_label"),
        group_name=metadata.get("group"),
        reaction_count=int(metadata.get("reaction_count") or 0),
        reported_comment_count=int(metadata.get("reported_comment_count") or 0),
        collected_comment_count=int(metadata.get("collected_comment_count") or 0),
        topic=relevance.get("topic"),
        matched_terms=[str(term) for term in matched_terms],
        is_reply=normalized.item_type == "reply",
    )
