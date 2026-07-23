from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from talent_radar.core.config import get_settings
from talent_radar.core.database import SessionLocal, create_all
from talent_radar.models import CrawlRun, Source
from talent_radar.services.source_registry import load_source_registry, upsert_sources


def run_daily_collect(db: Session, lookback_hours: int | None = None) -> CrawlRun:
    settings = get_settings()
    source_data = load_source_registry(settings.source_registry_path)
    upsert_sources(db, source_data)

    run = CrawlRun(
        id=f"crawl_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}",
        started_at=datetime.now(UTC),
        status="running",
        lookback_hours=lookback_hours or settings.crawl_lookback_hours,
    )
    db.add(run)
    db.commit()

    enabled_sources = (
        db.query(Source)
        .filter(Source.enabled.is_(True), Source.authorization_status == "approved")
        .all()
    )

    # The Coc Coc crawler writes exports that can be imported by the API.
    run.completed_at = datetime.now(UTC)
    run.status = "completed"
    run.error_summary = None
    run.result_summary = {
        "enabled_sources": len(enabled_sources),
        "note": "Source registry synced. Browser collection runs separately.",
    }
    db.commit()
    db.refresh(run)
    return run


def main() -> None:
    create_all()
    with SessionLocal() as db:
        run = run_daily_collect(db)
        print(
            {
                "crawl_run_id": run.id,
                "status": run.status,
                "lookback_hours": run.lookback_hours,
                "result_summary": run.result_summary,
            }
        )


if __name__ == "__main__":
    main()
