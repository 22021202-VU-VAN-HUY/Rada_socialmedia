from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from talent_radar.core.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Source(TimestampMixin, Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    platform: Mapped[str] = mapped_column(String(40), index=True)
    source_kind: Mapped[str] = mapped_column(String(40), default="unknown")
    source_name: Mapped[str] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(80), default="public_earned")
    access_basis: Mapped[str] = mapped_column(String(80), default="pending")
    authorization_status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    collection_method: Mapped[str] = mapped_column(String(80), default="import")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[str] = mapped_column(String(20), default="P1")
    crawl_frequency: Mapped[str] = mapped_column(String(40), default="daily")
    lookback_hours: Mapped[int] = mapped_column(Integer, default=24)
    comment_policy: Mapped[dict] = mapped_column(JSON, default=dict)
    privacy: Mapped[dict] = mapped_column(JSON, default=dict)
    owner: Mapped[dict] = mapped_column(JSON, default=dict)

    raw_items: Mapped[list["RawItem"]] = relationship(back_populates="source")


class CrawlRun(TimestampMixin, Base):
    __tablename__ = "crawl_runs"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), default="pending")
    lookback_hours: Mapped[int] = mapped_column(Integer, default=24)
    posts_collected: Mapped[int] = mapped_column(Integer, default=0)
    comments_collected: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)
    result_summary: Mapped[dict] = mapped_column(JSON, default=dict)


class RawItem(TimestampMixin, Base):
    __tablename__ = "raw_items"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    crawl_run_id: Mapped[str | None] = mapped_column(ForeignKey("crawl_runs.id"), index=True)
    platform: Mapped[str] = mapped_column(String(40), index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    item_type: Mapped[str] = mapped_column(String(40), default="post")
    parent_external_id: Mapped[str | None] = mapped_column(String(255))
    raw_content: Mapped[str | None] = mapped_column(Text)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    permalink: Mapped[str | None] = mapped_column(Text)
    import_batch_id: Mapped[str | None] = mapped_column(String(120), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    source: Mapped[Source] = relationship(back_populates="raw_items")
    normalized_item: Mapped["NormalizedItem"] = relationship(back_populates="raw_item")


class NormalizedItem(TimestampMixin, Base):
    __tablename__ = "normalized_items"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    raw_item_id: Mapped[str] = mapped_column(ForeignKey("raw_items.id"), unique=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    platform: Mapped[str] = mapped_column(String(40), index=True)
    item_type: Mapped[str] = mapped_column(String(40), default="post")
    parent_item_id: Mapped[str | None] = mapped_column(String(120), index=True)
    author_hash: Mapped[str | None] = mapped_column(String(128))
    content_text: Mapped[str] = mapped_column(Text)
    permalink: Mapped[str | None] = mapped_column(Text)
    import_batch_id: Mapped[str | None] = mapped_column(String(120), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    provenance_status: Mapped[str] = mapped_column(String(40), default="complete")

    raw_item: Mapped[RawItem] = relationship(back_populates="normalized_item")
