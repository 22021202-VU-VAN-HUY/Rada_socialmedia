from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from talent_radar.core.config import get_settings
from talent_radar.core.database import create_all, get_db
from talent_radar.models import Source
from talent_radar.schemas import (
    ClassificationRequest,
    ClassificationResult,
    ImportBatchRequest,
    ImportBatchResult,
    SourceCreate,
    SourceRead,
)
from talent_radar.services.import_adapter import run_import_batch
from talent_radar.services.query_pack import QueryPackMatcher, load_query_pack
from talent_radar.services.rule_classifier import RuleClassifier
from talent_radar.services.source_registry import load_source_registry, upsert_sources

app = FastAPI(title="Talent Radar API", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    create_all()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sources", response_model=list[SourceRead])
def list_sources(db: Session = Depends(get_db)) -> list[Source]:
    return list(db.scalars(select(Source).order_by(Source.platform, Source.source_name)).all())


@app.post("/sources", response_model=SourceRead)
def create_source(payload: SourceCreate, db: Session = Depends(get_db)) -> Source:
    source = db.get(Source, payload.id)
    if source is None:
        source = Source(**payload.model_dump())
        db.add(source)
    else:
        for key, value in payload.model_dump().items():
            setattr(source, key, value)
    db.commit()
    db.refresh(source)
    return source


@app.post("/sources/sync", response_model=list[SourceRead])
def sync_sources(db: Session = Depends(get_db)) -> list[Source]:
    settings = get_settings()
    source_data = load_source_registry(settings.source_registry_path)
    return upsert_sources(db, source_data)


@app.post("/classify", response_model=ClassificationResult)
def classify(payload: ClassificationRequest) -> ClassificationResult:
    settings = get_settings()
    pack = load_query_pack(settings.query_pack_path)
    classifier = RuleClassifier(QueryPackMatcher(pack))
    return classifier.classify(payload)


@app.post("/imports", response_model=ImportBatchResult)
def import_batch(payload: ImportBatchRequest, db: Session = Depends(get_db)) -> ImportBatchResult:
    try:
        return run_import_batch(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
