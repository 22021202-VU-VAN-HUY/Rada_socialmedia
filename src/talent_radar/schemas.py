from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


Platform = Literal["facebook", "tiktok", "threads", "manual"]


class SourceBase(BaseModel):
    id: str
    platform: Platform
    external_id: str | None = None
    source_kind: str = "unknown"
    source_name: str
    handle: str | None = None
    source_url: str | None = None
    source_type: str = "public_earned"
    access_basis: str = "pending"
    authorization_status: str = "pending"
    collection_method: str = "import"
    enabled: bool = False
    priority: str = "P1"
    crawl_frequency: str = "daily"
    lookback_hours: int = 24
    comment_policy: dict[str, Any] = Field(default_factory=dict)
    privacy: dict[str, Any] = Field(default_factory=dict)
    owner: dict[str, Any] = Field(default_factory=dict)
    platform_metadata: dict[str, Any] = Field(default_factory=dict)


class SourceCreate(SourceBase):
    pass


class SourceRead(SourceBase):
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ImportRecord(BaseModel):
    source_id: str
    platform: Platform
    item_type: str = "post"
    content_text: str
    external_id: str | None = None
    parent_external_id: str | None = None
    root_external_id: str | None = None
    parent_item_id: str | None = None
    permalink: str | None = None
    import_batch_id: str | None = None
    published_at: datetime | None = None
    collected_at: datetime | None = None
    author_id: str | None = None
    author_hash: str | None = None
    author_display_name: str | None = None
    author_username: str | None = None
    author_profile_url: str | None = None
    content_language: str | None = None
    reaction_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    collected_comment_count: int = 0
    reply_count: int = 0
    share_count: int = 0
    view_count: int = 0
    save_count: int = 0
    topic: str | None = None
    matched_terms: list[str] = Field(default_factory=list)
    matched_groups: list[str] = Field(default_factory=list)
    topic_score: float = 1.0
    platform_metadata: dict[str, Any] = Field(default_factory=dict)
    raw_metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def coerce_content_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data.get("content_text"):
            for key in ("text", "content", "raw_content", "message", "caption"):
                if data.get(key):
                    data = {**data, "content_text": data[key]}
                    break
        return data


class ImportBatchRequest(BaseModel):
    import_batch_id: str | None = None
    records: list[ImportRecord]


class ImportBatchResult(BaseModel):
    import_batch_id: str
    received: int
    inserted: int
    skipped_duplicates: int
    raw_item_ids: list[str]
    normalized_item_ids: list[str]


class UserCredentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class UserRead(BaseModel):
    id: str
    email: str
    is_active: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class AuthResult(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserRead


class PlatformConnectionRead(BaseModel):
    id: str
    platform: str
    status: str
    auth_method: str
    last_connected_at: datetime | None = None
    last_checked_at: datetime | None = None
    last_error: str | None = None
    profile_directory: str | None = None
    profile_name: str | None = None
    profile_account_name: str | None = None
    connected_account_id: str | None = None
    connected_account_name: str | None = None

    model_config = {"from_attributes": True}


class ConnectionActionResult(BaseModel):
    connection: PlatformConnectionRead
    message: str


class BrowserAgentRead(BaseModel):
    id: str
    name: str
    browser: str
    version: str | None = None
    status: str
    capabilities: list[str]
    last_seen_at: datetime
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class BrowserAgentPairingCodeRead(BaseModel):
    pairing_code: str
    expires_at: datetime


class BrowserAgentPairRequest(BaseModel):
    pairing_code: str = Field(min_length=8, max_length=32)
    name: str = Field(min_length=1, max_length=160)
    browser: str = Field(default="chromium", min_length=1, max_length=80)
    version: str | None = Field(default=None, max_length=80)
    capabilities: list[Platform] = Field(default_factory=list)


class BrowserAgentPairResult(BaseModel):
    agent_token: str
    agent: BrowserAgentRead


class BrowserPlatformConnection(BaseModel):
    platform: Platform
    connected: bool
    account_id: str | None = Field(default=None, max_length=255)
    account_name: str | None = Field(default=None, max_length=255)


class BrowserAgentHeartbeat(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    browser: str | None = Field(default=None, min_length=1, max_length=80)
    version: str | None = Field(default=None, max_length=80)
    capabilities: list[Platform] | None = None
    connections: list[BrowserPlatformConnection] | None = None


class BrowserAgentClaimRequest(BaseModel):
    supported_platforms: list[Platform] = Field(default_factory=list)


class BrowserAgentJob(BaseModel):
    id: str
    platform: str
    source_id: str
    source_name: str
    source_url: str
    max_posts: int
    max_comments_per_post: int
    lookback_hours: int
    include_replies: bool
    published_since: datetime
    filters: dict[str, Any] = Field(default_factory=dict)


class BrowserAgentItemBatch(BaseModel):
    records: list[ImportRecord] = Field(min_length=1, max_length=500)


class BrowserAgentJobComplete(BaseModel):
    status: Literal["completed", "failed"]
    error: str | None = Field(default=None, max_length=4000)
    posts_collected: int = Field(default=0, ge=0)
    comments_collected: int = Field(default=0, ge=0)
    replies_collected: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunConfigurationCreate(BaseModel):
    connection_id: str
    source_id: str
    max_posts: int = Field(default=5, ge=1, le=200)
    max_comments_per_post: int = Field(default=100, ge=0, le=5000)
    lookback_hours: int = Field(default=24, ge=1, le=24 * 365)
    include_replies: bool = True
    filters: dict[str, Any] = Field(default_factory=dict)


class RunConfigurationUpdate(BaseModel):
    max_posts: int | None = Field(default=None, ge=1, le=200)
    max_comments_per_post: int | None = Field(default=None, ge=0, le=5000)
    lookback_hours: int | None = Field(default=None, ge=1, le=24 * 365)
    include_replies: bool | None = None
    filters: dict[str, Any] | None = None


class RunConfigurationRead(BaseModel):
    id: str
    connection_id: str
    source_id: str
    max_posts: int
    max_comments_per_post: int
    lookback_hours: int
    include_replies: bool
    filters: dict[str, Any]
    last_run_at: datetime | None = None
    last_status: str
    last_error: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class JobRead(BaseModel):
    id: str
    run_configuration_id: str
    source_id: str
    platform: str
    status: str
    trigger: str
    executor: str
    browser_agent_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    posts_collected: int
    comments_collected: int
    replies_collected: int
    records_inserted: int
    duplicates_skipped: int
    output_path: str | None = None
    error_summary: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class ContentItemRead(BaseModel):
    id: str
    source_id: str
    source_name: str
    platform: str
    item_type: str
    external_id: str | None = None
    parent_external_id: str | None = None
    author: str | None = None
    content: str
    permalink: str | None = None
    published_at: datetime | None = None
    collected_at: datetime | None = None
    published_label: str | None = None
    group_name: str | None = None
    reaction_count: int = 0
    reported_comment_count: int = 0
    collected_comment_count: int = 0
    topic: str | None = None
    matched_terms: list[str] = Field(default_factory=list)
    is_reply: bool = False


class ContentPage(BaseModel):
    items: list[ContentItemRead]
    total: int
    page: int
    page_size: int
    pages: int


class OverviewRead(BaseModel):
    posts: int
    comments: int
    active_jobs: int
    saved_configurations: int
    connected_platforms: int
