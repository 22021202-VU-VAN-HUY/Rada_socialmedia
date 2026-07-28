from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    literal_column,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from talent_radar.core.database import Base


JSON_DOCUMENT = JSON().with_variant(JSONB, "postgresql")
PLATFORM_CHECK = "platform IN ('facebook', 'tiktok', 'threads', 'manual')"
CONTENT_TYPE_CHECK = "item_type IN ('post', 'comment', 'reply')"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
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
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlatformConnection(TimestampMixin, Base):
    __tablename__ = "platform_connections"
    __table_args__ = (
        UniqueConstraint("user_id", "platform", name="uq_connection_user_platform"),
        CheckConstraint(PLATFORM_CHECK, name="ck_platform_connections_platform"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40), default="disconnected", index=True)
    auth_method: Mapped[str] = mapped_column(String(40), default="browser_profile")
    profile_dir: Mapped[str] = mapped_column(Text)
    login_url: Mapped[str] = mapped_column(Text)
    browser_process_id: Mapped[int | None] = mapped_column(Integer)
    last_connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    connection_metadata: Mapped[dict] = mapped_column(JSON_DOCUMENT, default=dict)


class OAuthState(TimestampMixin, Base):
    __tablename__ = "oauth_states"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("platform_connections.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(40), index=True)
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BrowserAgent(TimestampMixin, Base):
    __tablename__ = "browser_agents"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    browser: Mapped[str] = mapped_column(String(80), default="chromium")
    version: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="online", index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    capabilities: Mapped[list] = mapped_column(JSON_DOCUMENT, default=list)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BrowserAgentPairingCode(TimestampMixin, Base):
    __tablename__ = "browser_agent_pairing_codes"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Source(TimestampMixin, Base):
    __tablename__ = "sources"
    __table_args__ = (
        UniqueConstraint("platform", "external_id", name="uq_sources_platform_external_id"),
        CheckConstraint(PLATFORM_CHECK, name="ck_sources_platform"),
        Index("ix_sources_platform_kind_enabled", "platform", "source_kind", "enabled"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    platform: Mapped[str] = mapped_column(String(40), index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    source_kind: Mapped[str] = mapped_column(String(40), default="unknown")
    source_name: Mapped[str] = mapped_column(String(255))
    handle: Mapped[str | None] = mapped_column(String(255), index=True)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(80), default="public_earned")
    access_basis: Mapped[str] = mapped_column(String(80), default="pending")
    authorization_status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    collection_method: Mapped[str] = mapped_column(String(80), default="import")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[str] = mapped_column(String(20), default="P1")
    crawl_frequency: Mapped[str] = mapped_column(String(40), default="manual")
    lookback_hours: Mapped[int] = mapped_column(Integer, default=24)
    comment_policy: Mapped[dict] = mapped_column(JSON_DOCUMENT, default=dict)
    privacy: Mapped[dict] = mapped_column(JSON_DOCUMENT, default=dict)
    owner: Mapped[dict] = mapped_column(JSON_DOCUMENT, default=dict)
    platform_metadata: Mapped[dict] = mapped_column(JSON_DOCUMENT, default=dict)

    raw_items: Mapped[list["RawItem"]] = relationship(back_populates="source")
    content_items: Mapped[list["ContentItem"]] = relationship(back_populates="source")


class RunConfiguration(TimestampMixin, Base):
    __tablename__ = "run_configurations"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "connection_id",
            "source_id",
            name="uq_run_configurations_user_connection_source",
        ),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("platform_connections.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    max_posts: Mapped[int] = mapped_column(Integer, default=5)
    max_comments_per_post: Mapped[int] = mapped_column(Integer, default=100)
    lookback_hours: Mapped[int] = mapped_column(Integer, default=24)
    include_replies: Mapped[bool] = mapped_column(Boolean, default=True)
    filters: Mapped[dict] = mapped_column(JSON_DOCUMENT, default=dict)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status: Mapped[str] = mapped_column(String(40), default="never")
    last_error: Mapped[str | None] = mapped_column(Text)


class CollectionJob(TimestampMixin, Base):
    __tablename__ = "collection_jobs"
    __table_args__ = (
        CheckConstraint(PLATFORM_CHECK, name="ck_collection_jobs_platform"),
        Index("ix_collection_jobs_user_status_created", "user_id", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    run_configuration_id: Mapped[str] = mapped_column(
        ForeignKey("run_configurations.id"), index=True
    )
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("platform_connections.id"), index=True
    )
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    platform: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    trigger: Mapped[str] = mapped_column(String(40), default="manual")
    executor: Mapped[str] = mapped_column(
        String(40), default="browser_extension", index=True
    )
    browser_agent_id: Mapped[str | None] = mapped_column(
        ForeignKey("browser_agents.id", ondelete="SET NULL"), index=True
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    posts_collected: Mapped[int] = mapped_column(Integer, default=0)
    comments_collected: Mapped[int] = mapped_column(Integer, default=0)
    replies_collected: Mapped[int] = mapped_column(Integer, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, default=0)
    output_path: Mapped[str | None] = mapped_column(Text)
    error_summary: Mapped[str | None] = mapped_column(Text)
    result_metadata: Mapped[dict] = mapped_column(JSON_DOCUMENT, default=dict)


class SocialAccount(TimestampMixin, Base):
    __tablename__ = "social_accounts"
    __table_args__ = (
        UniqueConstraint("platform", "account_hash", name="uq_social_accounts_platform_hash"),
        CheckConstraint(PLATFORM_CHECK, name="ck_social_accounts_platform"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    platform: Mapped[str] = mapped_column(String(40), index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    username: Mapped[str | None] = mapped_column(String(255), index=True)
    display_name: Mapped[str | None] = mapped_column(String(500))
    profile_url: Mapped[str | None] = mapped_column(Text)
    account_hash: Mapped[str] = mapped_column(String(128), index=True)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    platform_metadata: Mapped[dict] = mapped_column(JSON_DOCUMENT, default=dict)


class RawItem(TimestampMixin, Base):
    __tablename__ = "raw_items"
    __table_args__ = (
        UniqueConstraint(
            "owner_user_id",
            "source_id",
            "content_hash",
            name="uq_raw_items_owner_source_content_hash",
        ),
        CheckConstraint(PLATFORM_CHECK, name="ck_raw_items_platform"),
        CheckConstraint(CONTENT_TYPE_CHECK, name="ck_raw_items_item_type"),
        Index("ix_raw_items_source_external", "source_id", "item_type", "external_id"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    owner_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    collection_job_id: Mapped[str | None] = mapped_column(
        ForeignKey("collection_jobs.id", ondelete="SET NULL"), index=True
    )
    platform: Mapped[str] = mapped_column(String(40), index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    item_type: Mapped[str] = mapped_column(String(40), default="post")
    parent_external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    raw_content: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict] = mapped_column(JSON_DOCUMENT, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    permalink: Mapped[str | None] = mapped_column(Text)
    import_batch_id: Mapped[str | None] = mapped_column(String(120), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    source: Mapped[Source] = relationship(back_populates="raw_items")
    content_item: Mapped["ContentItem"] = relationship(back_populates="raw_item")

    @property
    def raw_metadata(self) -> dict:
        return self.raw_payload

    @raw_metadata.setter
    def raw_metadata(self, value: dict) -> None:
        self.raw_payload = value


class ContentItem(TimestampMixin, Base):
    __tablename__ = "content_items"
    __table_args__ = (
        UniqueConstraint(
            "owner_user_id",
            "source_id",
            "item_type",
            "external_id",
            name="uq_content_items_owner_source_type_external",
        ),
        CheckConstraint(PLATFORM_CHECK, name="ck_content_items_platform"),
        CheckConstraint(CONTENT_TYPE_CHECK, name="ck_content_items_item_type"),
        Index("ix_content_items_user_type_published", "owner_user_id", "item_type", "published_at"),
        Index("ix_content_items_source_type_collected", "source_id", "item_type", "collected_at"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    raw_item_id: Mapped[str] = mapped_column(
        ForeignKey("raw_items.id", ondelete="CASCADE"), unique=True
    )
    owner_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    platform: Mapped[str] = mapped_column(String(40), index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    item_type: Mapped[str] = mapped_column(String(40), default="post")
    parent_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_items.id", ondelete="SET NULL"), index=True
    )
    root_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("content_items.id", ondelete="SET NULL"), index=True
    )
    author_id: Mapped[str | None] = mapped_column(
        ForeignKey("social_accounts.id", ondelete="SET NULL"), index=True
    )
    content_text: Mapped[str] = mapped_column(Text)
    content_language: Mapped[str | None] = mapped_column(String(20), index=True)
    permalink: Mapped[str | None] = mapped_column(Text)
    import_batch_id: Mapped[str | None] = mapped_column(String(120), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provenance_status: Mapped[str] = mapped_column(String(40), default="complete")
    platform_metadata: Mapped[dict] = mapped_column(JSON_DOCUMENT, default=dict)

    raw_item: Mapped[RawItem] = relationship(back_populates="content_item")
    source: Mapped[Source] = relationship(back_populates="content_items")
    author: Mapped[SocialAccount | None] = relationship()
    metric_snapshots: Mapped[list["ContentMetricSnapshot"]] = relationship(
        back_populates="content_item", cascade="all, delete-orphan"
    )
    topic_matches: Mapped[list["ContentTopicMatch"]] = relationship(
        back_populates="content_item", cascade="all, delete-orphan"
    )

    @property
    def author_hash(self) -> str | None:
        return self.author.account_hash if self.author else None


content_text_search_index = Index(
    "ix_content_items_text_search",
    func.to_tsvector(
        literal_column("'simple'"),
        literal_column("content_text"),
    ),
    postgresql_using="gin",
).ddl_if(dialect="postgresql")
ContentItem.__table__.append_constraint(content_text_search_index)


class ContentMetricSnapshot(TimestampMixin, Base):
    __tablename__ = "content_metric_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "content_item_id", "observed_at", name="uq_content_metric_item_observed"
        ),
        Index("ix_content_metric_item_observed", "content_item_id", "observed_at"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    content_item_id: Mapped[str] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), index=True
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    reaction_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    collected_comment_count: Mapped[int] = mapped_column(Integer, default=0)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    share_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    save_count: Mapped[int] = mapped_column(Integer, default=0)
    platform_metrics: Mapped[dict] = mapped_column(JSON_DOCUMENT, default=dict)

    content_item: Mapped[ContentItem] = relationship(back_populates="metric_snapshots")


class ContentTopicMatch(TimestampMixin, Base):
    __tablename__ = "content_topic_matches"
    __table_args__ = (
        UniqueConstraint("content_item_id", "topic_key", name="uq_content_topic_item_topic"),
        Index("ix_content_topic_topic_score", "topic_key", "score"),
    )

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    content_item_id: Mapped[str] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), index=True
    )
    topic_key: Mapped[str] = mapped_column(String(120), index=True)
    matched_terms: Mapped[list] = mapped_column(JSON_DOCUMENT, default=list)
    matched_groups: Mapped[list] = mapped_column(JSON_DOCUMENT, default=list)
    score: Mapped[float] = mapped_column(Float, default=1.0)
    filter_version: Mapped[str | None] = mapped_column(String(80))

    content_item: Mapped[ContentItem] = relationship(back_populates="topic_matches")


# Compatibility import for services and integrations that still use the old class name.
NormalizedItem = ContentItem
