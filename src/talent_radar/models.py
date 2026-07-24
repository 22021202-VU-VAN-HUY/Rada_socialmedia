from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from talent_radar.core.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuthSession(TimestampMixin, Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlatformConnection(TimestampMixin, Base):
    __tablename__ = "platform_connections"
    __table_args__ = (UniqueConstraint("user_id", "platform", name="uq_connection_user_platform"),)

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    platform: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40), default="disconnected", index=True)
    auth_method: Mapped[str] = mapped_column(String(40), default="browser_profile")
    profile_dir: Mapped[str] = mapped_column(Text)
    login_url: Mapped[str] = mapped_column(Text)
    browser_process_id: Mapped[int | None] = mapped_column(Integer)
    last_connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    connection_metadata: Mapped[dict] = mapped_column(JSON, default=dict)


class OAuthState(TimestampMixin, Base):
    __tablename__ = "oauth_states"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("platform_connections.id"), index=True
    )
    provider: Mapped[str] = mapped_column(String(40), index=True)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CollectionSchedule(TimestampMixin, Base):
    __tablename__ = "collection_schedules"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    connection_id: Mapped[str] = mapped_column(ForeignKey("platform_connections.id"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    interval_minutes: Mapped[int] = mapped_column(Integer, default=60)
    max_posts: Mapped[int] = mapped_column(Integer, default=5)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str] = mapped_column(String(40), default="never")
    last_error: Mapped[str | None] = mapped_column(Text)


class CollectionJob(TimestampMixin, Base):
    __tablename__ = "collection_jobs"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    schedule_id: Mapped[str] = mapped_column(ForeignKey("collection_schedules.id"), index=True)
    connection_id: Mapped[str] = mapped_column(ForeignKey("platform_connections.id"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    trigger: Mapped[str] = mapped_column(String(40), default="scheduled")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    posts_collected: Mapped[int] = mapped_column(Integer, default=0)
    comments_collected: Mapped[int] = mapped_column(Integer, default=0)
    output_path: Mapped[str | None] = mapped_column(Text)
    error_summary: Mapped[str | None] = mapped_column(Text)


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
