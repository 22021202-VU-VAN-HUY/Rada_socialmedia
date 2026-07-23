import json
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from talent_radar.core.database import Base
from talent_radar.models import NormalizedItem, RawItem, Source
from talent_radar.schemas import ImportBatchRequest, ImportRecord
from talent_radar.services.import_adapter import load_import_file, run_import_batch


def test_load_import_file_accepts_csv_text_alias() -> None:
    path = Path("data/samples/test_import_items.csv")
    try:
        path.write_text(
            "source_id,platform,item_type,text,external_id\n"
            "fb_group_vsf_001,facebook,comment,VSF deadline dang ky khi nao?,cmt_1\n",
            encoding="utf-8",
        )

        records = load_import_file(path)
    finally:
        path.unlink(missing_ok=True)

    assert records[0].content_text == "VSF deadline dang ky khi nao?"
    assert records[0].platform == "facebook"


def test_load_import_file_accepts_coccoc_export(tmp_path: Path) -> None:
    path = tmp_path / "facebook_coccoc.json"
    path.write_text(
        json.dumps(
            {
                "crawler": "coccoc-ui",
                "source_id": "fb_group_laptrinhvienit",
                "collected_at": "2026-07-23T10:00:00+07:00",
                "posts": [
                    {
                        "post": {
                            "external_id": "post_1",
                            "author": "Anonymous",
                            "content": "Sample post",
                            "url": "https://www.facebook.com/groups/example/posts/post_1/",
                        },
                        "comments": [
                            {
                                "external_id": "comment_1",
                                "parent_external_id": "post_1",
                                "author": "Member",
                                "content": "Sample comment",
                                "is_reply": False,
                            },
                            {
                                "external_id": "comment_2",
                                "parent_external_id": "post_1",
                                "author": "Member 2",
                                "content": "",
                                "is_reply": False,
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    records = load_import_file(path)

    assert [record.item_type for record in records] == ["post", "comment", "comment"]
    assert records[1].parent_external_id == "post_1"
    assert records[1].raw_metadata["author_display_name"] == "Member"
    assert records[2].content_text == "[non-text comment]"
    assert records[2].raw_metadata["non_text"] is True


def test_run_import_batch_inserts_raw_and_normalized_items() -> None:
    db = _session()
    db.add(
        Source(
            id="fb_group_vsf_001",
            platform="facebook",
            source_name="Example group",
            authorization_status="approved",
            collection_method="import",
        )
    )
    db.commit()

    result = run_import_batch(
        db,
        ImportBatchRequest(
            import_batch_id="batch_test",
            records=[
                ImportRecord(
                    source_id="fb_group_vsf_001",
                    platform="facebook",
                    item_type="comment",
                    content_text="VSF deadline dang ky khi nao?",
                    external_id="cmt_1",
                    permalink="https://example.test/post/1",
                    author_id="user_123",
                )
            ],
        ),
    )

    raw_item = db.scalar(select(RawItem))
    normalized_item = db.scalar(select(NormalizedItem))
    assert result.inserted == 1
    assert raw_item is not None
    assert normalized_item is not None
    assert normalized_item.raw_item_id == raw_item.id
    assert normalized_item.author_hash is not None
    assert normalized_item.provenance_status == "complete"


def test_run_import_batch_skips_duplicate_content() -> None:
    db = _session()
    db.add(
        Source(
            id="fb_group_laptrinhvienit",
            platform="facebook",
            source_name="Facebook group",
            authorization_status="approved",
            collection_method="import",
        )
    )
    db.commit()
    payload = ImportBatchRequest(
        import_batch_id="batch_test",
        records=[
            ImportRecord(
                source_id="fb_group_laptrinhvienit",
                platform="facebook",
                content_text="Bai viet tu group Facebook",
                external_id="post_1",
            )
        ],
    )

    first = run_import_batch(db, payload)
    second = run_import_batch(db, payload)

    assert first.inserted == 1
    assert second.inserted == 0
    assert second.skipped_duplicates == 1
    assert len(db.scalars(select(RawItem)).all()) == 1


def _session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return session_factory()
