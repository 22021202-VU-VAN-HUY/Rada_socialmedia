from datetime import UTC, datetime, timedelta

from talent_radar.dashboard.formatting import relative_published


def test_relative_published_changes_only_with_new_reference() -> None:
    published = datetime(2026, 7, 24, 10, 0, tzinfo=UTC)
    post = {
        "published_at": published.isoformat(),
        "published_label": "27 ph\u00fat",
    }

    initial = relative_published(
        post,
        published + timedelta(minutes=27),
    )
    synchronized = relative_published(
        post,
        published + timedelta(minutes=30),
    )

    assert initial == "27 ph\u00fat"
    assert synchronized == "30 ph\u00fat"
