from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


Platform = Literal["facebook", "tiktok", "threads", "manual"]


class SourceBase(BaseModel):
    id: str
    platform: Platform
    source_kind: str = "unknown"
    source_name: str
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


class SourceCreate(SourceBase):
    pass


class SourceRead(SourceBase):
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class Evidence(BaseModel):
    item_id: str
    source_id: str
    platform: Platform
    item_type: str
    published_at: datetime | None = None
    permalink: str | None = None
    import_batch_id: str | None = None
    quote_policy: str = "paraphrase_by_default"
    safe_excerpt: str | None = None


class ClassificationRequest(BaseModel):
    text: str
    item_id: str = "preview_item"
    source_id: str = "preview_source"
    platform: Platform = "manual"
    item_type: str = "comment"
    published_at: datetime | None = None
    permalink: str | None = None
    import_batch_id: str | None = None


class ClassificationResult(BaseModel):
    relevance: dict[str, Any]
    sentiment: dict[str, Any]
    voice: dict[str, Any]
    risk: dict[str, Any]
    recommendation: dict[str, Any]
    evidence: Evidence
    review_status: str
