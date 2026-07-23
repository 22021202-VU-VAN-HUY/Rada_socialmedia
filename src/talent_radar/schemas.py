from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


Platform = Literal["facebook", "manual"]


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


class ImportRecord(BaseModel):
    source_id: str
    platform: Platform
    item_type: str = "post"
    content_text: str
    external_id: str | None = None
    parent_external_id: str | None = None
    parent_item_id: str | None = None
    permalink: str | None = None
    import_batch_id: str | None = None
    published_at: datetime | None = None
    collected_at: datetime | None = None
    author_id: str | None = None
    author_hash: str | None = None
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
