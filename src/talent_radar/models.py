from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
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
    candidates_sent_to_ai: Mapped[int] = mapped_column(Integer, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)
    cost_summary: Mapped[dict] = mapped_column(JSON, default=dict)


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


class FilterMatch(TimestampMixin, Base):
    __tablename__ = "filter_matches"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("normalized_items.id"), index=True)
    relevance_label: Mapped[str] = mapped_column(String(40))
    filter_score: Mapped[float] = mapped_column(Float, default=0.0)
    matched_terms: Mapped[list] = mapped_column(JSON, default=list)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)


class AiRun(TimestampMixin, Base):
    __tablename__ = "ai_runs"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    provider: Mapped[str] = mapped_column(String(80), default="rule")
    model_name: Mapped[str] = mapped_column(String(120), default="rule")
    status: Mapped[str] = mapped_column(String(40), default="completed")
    items_processed: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)


class AiAnnotation(TimestampMixin, Base):
    __tablename__ = "ai_annotations"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("normalized_items.id"), index=True)
    ai_run_id: Mapped[str | None] = mapped_column(ForeignKey("ai_runs.id"), index=True)
    relevance: Mapped[dict] = mapped_column(JSON, default=dict)
    sentiment: Mapped[dict] = mapped_column(JSON, default=dict)
    voice: Mapped[dict] = mapped_column(JSON, default=dict)
    risk: Mapped[dict] = mapped_column(JSON, default=dict)
    recommendation: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    review_status: Mapped[str] = mapped_column(String(40), default="needs_review")


class Insight(TimestampMixin, Base):
    __tablename__ = "insights"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    signal_type: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(40), default="new")
    summary: Mapped[str] = mapped_column(Text)
    evidence_item_ids: Mapped[list] = mapped_column(JSON, default=list)
    recommended_actions: Mapped[list] = mapped_column(JSON, default=list)


class Alert(TimestampMixin, Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(40), index=True)
    risk_type: Mapped[str | None] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(40), default="open")
    why_now: Mapped[str | None] = mapped_column(Text)
    evidence_item_ids: Mapped[list] = mapped_column(JSON, default=list)
    recommended_actions: Mapped[list] = mapped_column(JSON, default=list)


class Action(TimestampMixin, Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    target_type: Mapped[str] = mapped_column(String(40))
    target_id: Mapped[str] = mapped_column(String(120), index=True)
    action_type: Mapped[str] = mapped_column(String(80))
    owner: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40), default="pending")
    instruction: Mapped[str] = mapped_column(Text)


class Review(TimestampMixin, Base):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    target_type: Mapped[str] = mapped_column(String(40))
    target_id: Mapped[str] = mapped_column(String(120), index=True)
    decision: Mapped[str] = mapped_column(String(40))
    decided_by: Mapped[str | None] = mapped_column(String(120))
    note: Mapped[str | None] = mapped_column(Text)
    before: Mapped[dict] = mapped_column(JSON, default=dict)
    after: Mapped[dict] = mapped_column(JSON, default=dict)


class DailyDigest(TimestampMixin, Base):
    __tablename__ = "daily_digests"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    digest_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    title: Mapped[str] = mapped_column(String(255))
    markdown: Mapped[str] = mapped_column(Text)
    supporting_item_ids: Mapped[list] = mapped_column(JSON, default=list)
    cost_summary: Mapped[dict] = mapped_column(JSON, default=dict)


class CostLog(TimestampMixin, Base):
    __tablename__ = "cost_logs"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    crawl_run_id: Mapped[str | None] = mapped_column(ForeignKey("crawl_runs.id"), index=True)
    provider: Mapped[str] = mapped_column(String(80))
    model_name: Mapped[str | None] = mapped_column(String(120))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
