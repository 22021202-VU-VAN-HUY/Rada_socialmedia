from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from talent_radar.models import Source
from talent_radar.schemas import SourceCreate


def load_source_registry(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return list(data.get("sources") or [])


def upsert_sources(db: Session, source_data: list[dict[str, Any]]) -> list[Source]:
    sources: list[Source] = []
    for item in source_data:
        payload = SourceCreate(**item).model_dump()
        source = db.get(Source, payload["id"])
        if source is None:
            source = Source(**payload)
            db.add(source)
        else:
            for key, value in payload.items():
                setattr(source, key, value)
        sources.append(source)
    db.commit()
    return sources
