from pathlib import Path

import pytest

from talent_radar.core.config import Settings
from talent_radar.models import PlatformConnection, Source
from talent_radar.services.facebook_collector import (
    FacebookCollector,
    _annotate_topic_relevance,
)
from talent_radar.services.topic_filter import TopicKeywordFilter, normalize_topic_text


FILTER_PATH = Path("config/vsf_keywords.yaml")


@pytest.fixture
def topic_filter() -> TopicKeywordFilter:
    return TopicKeywordFilter.from_yaml(FILTER_PATH)


@pytest.mark.parametrize(
    ("content", "expected_group"),
    [
        ("Mọi người review giúp môi trường VSF với ạ", "identity"),
        ("Có ai đang làm ở VinSmart Future không?", "identity"),
        ("Quy trình phỏng vấn Vin-Smart Future gồm mấy vòng?", "identity"),
        ("Cho mình hỏi chế độ bên vinsmartfuture", "identity"),
        ("Anh em Vin đỏ cho xin review dự án", "colloquial"),
        ("Anh em vin do cho xin review dự án", "colloquial"),
    ],
)
def test_vsf_variants_are_matched(
    topic_filter: TopicKeywordFilter,
    content: str,
    expected_group: str,
) -> None:
    match = topic_filter.match(content)

    assert match.matched is True
    assert expected_group in match.matched_groups


@pytest.mark.parametrize(
    "content",
    [
        "Review môi trường làm việc ngành phần mềm",
        "Mã đơn hàng VSF123 đã được giao",
        "VinFast màu đỏ nhìn khá đẹp",
        "",
    ],
)
def test_unrelated_posts_are_rejected(
    topic_filter: TopicKeywordFilter,
    content: str,
) -> None:
    assert topic_filter.match(content).matched is False


def test_matching_post_is_annotated_for_audit(
    topic_filter: TopicKeywordFilter,
) -> None:
    post = {"content": "Review lương thưởng ở VSF"}

    assert _annotate_topic_relevance(post, topic_filter) is True
    assert post["relevance"]["topic"] == "vsf"
    assert post["relevance"]["matched_terms"] == ["VSF"]


def test_rejected_post_is_not_annotated(
    topic_filter: TopicKeywordFilter,
) -> None:
    post = {"content": "Một bài viết tuyển dụng không liên quan"}

    assert _annotate_topic_relevance(post, topic_filter) is False
    assert "relevance" not in post


def test_normalization_handles_vietnamese_and_punctuation() -> None:
    assert normalize_topic_text("  VIN-ĐỎ!!! ") == "vin do"


def test_collector_expands_comments_only_for_matching_posts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakePage:
        current_url = ""
        url = "https://www.facebook.com/groups/example/posts/1/"

        def set_default_timeout(self, _timeout: int) -> None:
            pass

        def set_default_navigation_timeout(self, _timeout: int) -> None:
            pass

        def close(self) -> None:
            pass

    page = FakePage()

    class FakeContext:
        def new_page(self) -> FakePage:
            return page

    class FakeBrowser:
        contexts = [FakeContext()]

    class FakeChromium:
        def connect_over_cdp(self, _url: str) -> FakeBrowser:
            return FakeBrowser()

    class FakePlaywright:
        chromium = FakeChromium()

    class FakePlaywrightManager:
        def __enter__(self) -> FakePlaywright:
            return FakePlaywright()

        def __exit__(self, *_args) -> None:
            pass

    monkeypatch.setattr(
        "talent_radar.services.facebook_collector.ensure_controlled_coccoc",
        lambda *_args, **_kwargs: (9223, None),
    )
    monkeypatch.setattr(
        "talent_radar.services.facebook_collector.sync_playwright",
        FakePlaywrightManager,
    )
    collector = FacebookCollector(Settings(_env_file=None))
    urls = ["https://example.test/related", "https://example.test/unrelated"]
    contents = {
        urls[0]: "Xin review môi trường VSF",
        urls[1]: "Tuyển lập trình viên Python",
    }
    expanded_urls: list[str] = []
    progress: list[dict] = []

    monkeypatch.setattr(collector, "_post_urls", lambda *_args: urls)

    def preview(_page: FakePage, url: str) -> dict:
        _page.current_url = url
        return {"post": {"content": contents[url]}, "comments": []}

    def comments(_page: FakePage) -> dict:
        expanded_urls.append(_page.current_url)
        return {
            "post": {
                "content": contents[_page.current_url],
                "external_id": "post-related",
            },
            "comments": [{"content": "Một bình luận"}],
        }

    monkeypatch.setattr(collector, "_collect_post_preview", preview)
    monkeypatch.setattr(collector, "_collect_loaded_post_comments", comments)
    connection = PlatformConnection(
        id="connection",
        user_id="user",
        platform="facebook",
        status="connected",
        profile_dir="profile",
        login_url="https://www.facebook.com/",
    )
    source = Source(
        id="source",
        platform="facebook",
        source_name="Source",
        source_url="https://www.facebook.com/groups/example/",
    )

    payload = collector.collect(
        connection,
        source,
        max_posts=10,
        on_progress=progress.append,
    )

    assert expanded_urls == [urls[0]]
    assert len(payload["posts"]) == 1
    assert payload["posts"][0]["post"]["relevance"]["topic"] == "vsf"
    assert payload["content_filter"] == {
        "topic": "vsf",
        "topic_label": "VinSmart Future (VSF)",
        "posts_scanned": 2,
        "posts_matched": 1,
        "posts_filtered_out": 1,
    }
    assert len(progress) == 2
