import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from talent_radar.models import NormalizedItem, RawItem, Source
from talent_radar.schemas import ImportBatchRequest, ImportBatchResult, ImportRecord


def load_import_file(path: Path) -> list[ImportRecord]:
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [ImportRecord.model_validate(row) for row in csv.DictReader(handle)]
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        rows = data.get("records", data) if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise ValueError("JSON import must be a list or an object with a records list")
        return [ImportRecord.model_validate(row) for row in rows]
    raise ValueError("Import file must be .csv or .json")


def run_import_batch(db: Session, payload: ImportBatchRequest) -> ImportBatchResult:
    batch_id = payload.import_batch_id or f"import_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
    raw_item_ids: list[str] = []
    normalized_item_ids: list[str] = []
    skipped_duplicates = 0

    for index, record in enumerate(payload.records, start=1):
        source = db.get(Source, record.source_id)
        if source is None:
            raise ValueError(f"Unknown source_id: {record.source_id}")

        content_hash = _content_hash(record)
        duplicate = db.scalar(
            select(RawItem).where(RawItem.source_id == record.source_id, RawItem.content_hash == content_hash)
        )
        if duplicate is not None:
            skipped_duplicates += 1
            continue

        record_batch_id = record.import_batch_id or batch_id
        raw_id = _item_id("raw", record, record_batch_id, index)
        normalized_id = _item_id("norm", record, record_batch_id, index)
        collected_at = record.collected_at or datetime.now(UTC)
        raw_item = RawItem(
            id=raw_id,
            source_id=record.source_id,
            platform=record.platform,
            external_id=record.external_id,
            item_type=record.item_type,
            parent_external_id=record.parent_external_id,
            raw_content=record.content_text,
            raw_metadata=record.raw_metadata,
            content_hash=content_hash,
            permalink=record.permalink,
            import_batch_id=record_batch_id,
            published_at=record.published_at,
            collected_at=collected_at,
        )
        normalized_item = NormalizedItem(
            id=normalized_id,
            raw_item_id=raw_id,
            source_id=record.source_id,
            platform=record.platform,
            item_type=record.item_type,
            parent_item_id=record.parent_item_id,
            author_hash=record.author_hash or _hash_author(record.author_id),
            content_text=record.content_text.strip(),
            permalink=record.permalink,
            import_batch_id=record_batch_id,
            published_at=record.published_at,
            collected_at=collected_at,
            provenance_status="complete" if record.permalink or record.external_id else "import_only",
        )
        db.add(raw_item)
        db.add(normalized_item)
        raw_item_ids.append(raw_id)
        normalized_item_ids.append(normalized_id)

    db.commit()
    return ImportBatchResult(
        import_batch_id=batch_id,
        received=len(payload.records),
        inserted=len(raw_item_ids),
        skipped_duplicates=skipped_duplicates,
        raw_item_ids=raw_item_ids,
        normalized_item_ids=normalized_item_ids,
    )


def _content_hash(record: ImportRecord) -> str:
    basis = "|".join(
        [
            record.source_id,
            record.platform,
            record.item_type,
            record.external_id or "",
            record.content_text.strip().casefold(),
        ]
    )
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def _hash_author(author_id: str | None) -> str | None:
    if not author_id:
        return None
    return "sha256:" + hashlib.sha256(author_id.encode("utf-8")).hexdigest()


def _item_id(prefix: str, record: ImportRecord, batch_id: str, index: int) -> str:
    if record.external_id:
        basis = f"{prefix}|{record.source_id}|{record.external_id}"
    else:
        basis = f"{prefix}|{batch_id}|{index}|{record.content_text.strip()}"
    return f"{prefix}_{hashlib.sha256(basis.encode('utf-8')).hexdigest()[:24]}"
