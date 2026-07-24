from datetime import datetime
from zoneinfo import ZoneInfo

from talent_radar.services.facebook_collector import (
    _chronological_group_url,
    _published_at,
)


VIETNAM = ZoneInfo("Asia/Ho_Chi_Minh")


def test_relative_facebook_time_is_resolved_from_local_now() -> None:
    now = datetime(2026, 7, 24, 15, 0, tzinfo=VIETNAM)

    published = _published_at({"published_label": "2 giờ"}, now=now)

    assert published == datetime(2026, 7, 24, 13, 0, tzinfo=VIETNAM)


def test_absolute_vietnamese_facebook_time_uses_local_timezone() -> None:
    now = datetime(2026, 7, 24, 15, 0, tzinfo=VIETNAM)

    published = _published_at(
        {"published_label": "24 tháng 7 lúc 08:30"},
        now=now,
    )

    assert published == datetime(2026, 7, 24, 8, 30, tzinfo=VIETNAM)


def test_facebook_iso_timestamp_takes_precedence_over_label() -> None:
    now = datetime(2026, 7, 24, 15, 0, tzinfo=VIETNAM)

    published = _published_at(
        {
            "published_at": "2026-07-24T01:15:00Z",
            "published_label": "2 ngày",
        },
        now=now,
    )

    assert published == datetime.fromisoformat("2026-07-24T01:15:00+00:00")


def test_full_vietnamese_accessibility_timestamp_is_parsed() -> None:
    now = datetime(2026, 7, 24, 15, 0, tzinfo=VIETNAM)

    published = _published_at(
        {"published_label": "Thứ Sáu, 24 Tháng 7, 2026 lúc 14:35"},
        now=now,
    )

    assert published == datetime(2026, 7, 24, 14, 35, tzinfo=VIETNAM)


def test_group_feed_is_requested_in_chronological_order() -> None:
    result = _chronological_group_url(
        "https://web.facebook.com/groups/laptrinhvienit/"
    )

    assert result == (
        "https://web.facebook.com/groups/laptrinhvienit/"
        "?sorting_setting=CHRONOLOGICAL"
    )
