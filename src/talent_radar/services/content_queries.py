from __future__ import annotations

from datetime import datetime
from math import ceil

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from talent_radar.models import (
    ContentItem,
    ContentMetricSnapshot,
    ContentTopicMatch,
    RawItem,
    SocialAccount,
    Source,
    User,
)
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
    conditions = [
        ContentItem.item_type.in_(item_types),
        ContentItem.owner_user_id == user.id,
    ]
    if search:
        query = search.strip()
        if db.bind is not None and db.bind.dialect.name == "postgresql":
            conditions.append(
                func.to_tsvector("simple", ContentItem.content_text).op("@@")(
                    func.plainto_tsquery("simple", query)
                )
            )
        else:
            conditions.append(ContentItem.content_text.ilike(f"%{query}%"))
    if source_id:
        conditions.append(ContentItem.source_id == source_id)
    if published_after:
        conditions.append(
            func.coalesce(ContentItem.published_at, ContentItem.collected_at)
            >= published_after
        )
    if post_external_id and kind == "comments":
        conditions.append(RawItem.parent_external_id == post_external_id)

    latest_metric_id = (
        select(ContentMetricSnapshot.id)
        .where(ContentMetricSnapshot.content_item_id == ContentItem.id)
        .order_by(ContentMetricSnapshot.observed_at.desc())
        .limit(1)
        .correlate(ContentItem)
        .scalar_subquery()
    )
    first_topic_id = (
        select(ContentTopicMatch.id)
        .where(ContentTopicMatch.content_item_id == ContentItem.id)
        .order_by(ContentTopicMatch.score.desc(), ContentTopicMatch.created_at)
        .limit(1)
        .correlate(ContentItem)
        .scalar_subquery()
    )
    base = (
        select(
            ContentItem,
            RawItem,
            Source,
            SocialAccount,
            ContentMetricSnapshot,
            ContentTopicMatch,
        )
        .join(RawItem, RawItem.id == ContentItem.raw_item_id)
        .join(Source, Source.id == ContentItem.source_id)
        .outerjoin(SocialAccount, SocialAccount.id == ContentItem.author_id)
        .outerjoin(ContentMetricSnapshot, ContentMetricSnapshot.id == latest_metric_id)
        .outerjoin(ContentTopicMatch, ContentTopicMatch.id == first_topic_id)
        .where(*conditions)
    )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(
        base.order_by(
            func.coalesce(ContentItem.published_at, ContentItem.collected_at).desc(),
            ContentItem.created_at.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [_content_item(*row) for row in rows]
    return ContentPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, ceil(total / page_size)),
    )


def count_content(db: Session, user: User, *, kind: str) -> int:
    item_types = ("post",) if kind == "posts" else ("comment", "reply")
    return (
        db.scalar(
            select(func.count())
            .select_from(ContentItem)
            .where(
                ContentItem.item_type.in_(item_types),
                ContentItem.owner_user_id == user.id,
            )
        )
        or 0
    )


def _content_item(
    item: ContentItem,
    raw: RawItem,
    source: Source,
    author: SocialAccount | None,
    metric: ContentMetricSnapshot | None,
    topic: ContentTopicMatch | None,
) -> ContentItemRead:
    metadata = raw.raw_payload or {}
    return ContentItemRead(
        id=item.id,
        source_id=item.source_id,
        source_name=source.source_name,
        platform=item.platform,
        item_type=item.item_type,
        external_id=item.external_id,
        parent_external_id=raw.parent_external_id,
        author=author.display_name if author else None,
        content=item.content_text,
        permalink=item.permalink,
        published_at=item.published_at,
        collected_at=item.collected_at,
        published_label=metadata.get("published_label"),
        group_name=metadata.get("group") or source.source_name,
        reaction_count=metric.reaction_count if metric else 0,
        reported_comment_count=metric.comment_count if metric else 0,
        collected_comment_count=metric.collected_comment_count if metric else 0,
        topic=topic.topic_key if topic else None,
        matched_terms=[str(term) for term in (topic.matched_terms if topic else [])],
        is_reply=item.item_type == "reply",
    )
