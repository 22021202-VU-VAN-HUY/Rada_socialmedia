from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import requests
import streamlit as st


APP_VERSION = "ui-control-room-v1"
BACKEND_URL = os.getenv("TALENT_RADAR_API_URL", "http://127.0.0.1:8000")

PLATFORM_LABELS = {
    "facebook": "Facebook",
    "tiktok": "TikTok",
    "threads": "Threads",
    "manual": "Manual",
}

SEVERITY_ORDER = ["critical", "high", "medium", "low", "watch"]
SENTIMENT_ORDER = ["negative", "neutral", "positive", "unclear"]
REVIEW_ACTIONS = {
    "needs_review": "Cần duyệt",
    "approved": "Đã duyệt",
    "edited": "Đã sửa nhãn",
    "dismissed": "Bỏ qua",
}


st.set_page_config(
    page_title="Talent Radar | VSF Control Room",
    layout="wide",
    initial_sidebar_state="expanded",
)


def now() -> datetime:
    return datetime(2026, 7, 20, 9, 30)


@st.cache_data(show_spinner=False)
def demo_sources() -> list[dict[str, Any]]:
    return [
        {
            "id": "fb_group_vsf_students",
            "platform": "facebook",
            "source_kind": "group",
            "source_name": "VSF Student Community",
            "source_url": "https://www.facebook.com/groups/vsf-students",
            "source_type": "public_earned",
            "access_basis": "member_export",
            "authorization_status": "approved",
            "collection_method": "api_or_export",
            "enabled": True,
            "priority": "P0",
            "crawl_frequency": "daily",
            "lookback_hours": 24,
            "comment_policy": "include_top_level_and_replies",
            "owner": "Ops",
            "last_status": "success",
            "last_collected_at": now() - timedelta(hours=1),
        },
        {
            "id": "fb_profile_public_alumni",
            "platform": "facebook",
            "source_kind": "profile",
            "source_name": "Public alumni profiles",
            "source_url": "import://facebook/public-profiles",
            "source_type": "public_earned",
            "access_basis": "manual_import",
            "authorization_status": "pending",
            "collection_method": "csv_import",
            "enabled": True,
            "priority": "P1",
            "crawl_frequency": "daily",
            "lookback_hours": 24,
            "comment_policy": "post_comments_only",
            "owner": "Community",
            "last_status": "partial",
            "last_collected_at": now() - timedelta(hours=3),
        },
        {
            "id": "tt_keyword_vsf",
            "platform": "tiktok",
            "source_kind": "keyword",
            "source_name": "TikTok keyword pack",
            "source_url": "https://www.tiktok.com/tag/vsf",
            "source_type": "public_earned",
            "access_basis": "public_search",
            "authorization_status": "pending_review",
            "collection_method": "approved_connector_or_import",
            "enabled": True,
            "priority": "P0",
            "crawl_frequency": "daily",
            "lookback_hours": 24,
            "comment_policy": "video_comments_if_available",
            "owner": "Ops",
            "last_status": "success",
            "last_collected_at": now() - timedelta(minutes=45),
        },
        {
            "id": "threads_vsf_mentions",
            "platform": "threads",
            "source_kind": "keyword",
            "source_name": "Threads VSF mentions",
            "source_url": "https://www.threads.net/search?q=VSF",
            "source_type": "public_earned",
            "access_basis": "public_search",
            "authorization_status": "pending_review",
            "collection_method": "approved_connector_or_import",
            "enabled": True,
            "priority": "P1",
            "crawl_frequency": "daily",
            "lookback_hours": 24,
            "comment_policy": "post_and_replies",
            "owner": "Ops",
            "last_status": "failed",
            "last_collected_at": now() - timedelta(days=1),
        },
    ]


@st.cache_data(show_spinner=False)
def demo_items() -> list[dict[str, Any]]:
    base = now()
    return [
        {
            "item_id": "fb-20260720-001",
            "source_id": "fb_group_vsf_students",
            "platform": "facebook",
            "item_type": "comment",
            "parent_item_id": "fb-post-8842",
            "author_hash": "usr_7b1a",
            "content_text": "VSF xử lý hồ sơ khá nhanh, mình hỏi deadline được admin trả lời rõ.",
            "safe_excerpt": "VSF xử lý hồ sơ khá nhanh... deadline được admin trả lời rõ.",
            "permalink": "https://www.facebook.com/groups/vsf-students/posts/8842?comment_id=131",
            "import_batch_id": None,
            "published_at": base - timedelta(hours=2, minutes=10),
            "collected_at": base - timedelta(hours=1, minutes=2),
            "provenance_status": "permalink_ok",
            "relevance": "core",
            "sentiment": "positive",
            "voice_signal": "student_experience",
            "danger_level": "low",
            "risk_type": "none",
            "recommended_action": "Ghi nhận phản hồi tích cực, gom vào daily digest.",
            "confidence": 0.86,
            "review_status": "approved",
        },
        {
            "item_id": "fb-20260720-002",
            "source_id": "fb_group_vsf_students",
            "platform": "facebook",
            "item_type": "post",
            "parent_item_id": None,
            "author_hash": "usr_91de",
            "content_text": "Có ai bị chậm email xác nhận từ công ty ở Technopark không? Mình nộp VSF 5 ngày rồi.",
            "safe_excerpt": "Có ai bị chậm email xác nhận từ công ty ở Technopark không?...",
            "permalink": "https://www.facebook.com/groups/vsf-students/posts/8843",
            "import_batch_id": None,
            "published_at": base - timedelta(hours=4, minutes=40),
            "collected_at": base - timedelta(hours=3, minutes=55),
            "provenance_status": "permalink_ok",
            "relevance": "core",
            "sentiment": "negative",
            "voice_signal": "question_repeated",
            "danger_level": "medium",
            "risk_type": "process_confusion",
            "recommended_action": "Chuẩn bị câu trả lời về SLA email xác nhận và kiểm tra backlog hồ sơ.",
            "confidence": 0.74,
            "review_status": "needs_review",
        },
        {
            "item_id": "tt-20260720-014",
            "source_id": "tt_keyword_vsf",
            "platform": "tiktok",
            "item_type": "comment",
            "parent_item_id": "tt-video-421",
            "author_hash": "usr_f0a2",
            "content_text": "Vin đỏ nghe bảo vòng phỏng vấn căng lắm, có thật không mọi người?",
            "safe_excerpt": "Vin đỏ nghe bảo vòng phỏng vấn căng lắm...",
            "permalink": "https://www.tiktok.com/@creator/video/421",
            "import_batch_id": None,
            "published_at": base - timedelta(hours=6),
            "collected_at": base - timedelta(hours=4, minutes=30),
            "provenance_status": "permalink_ok",
            "relevance": "contextual",
            "sentiment": "unclear",
            "voice_signal": "alias_trend",
            "danger_level": "watch",
            "risk_type": "slang_alias",
            "recommended_action": "Thêm alias 'Vin đỏ' vào query pack và theo dõi xem có gắn trực tiếp với VSF không.",
            "confidence": 0.62,
            "review_status": "needs_review",
        },
        {
            "item_id": "th-20260720-007",
            "source_id": "threads_vsf_mentions",
            "platform": "threads",
            "item_type": "reply",
            "parent_item_id": "th-post-221",
            "author_hash": "usr_2f66",
            "content_text": "Mình thích cách VSF phản hồi lịch phỏng vấn, không bị mơ hồ như vài chương trình khác.",
            "safe_excerpt": "Mình thích cách VSF phản hồi lịch phỏng vấn...",
            "permalink": "https://www.threads.net/@sample/post/221",
            "import_batch_id": None,
            "published_at": base - timedelta(hours=7, minutes=20),
            "collected_at": base - timedelta(hours=6),
            "provenance_status": "permalink_ok",
            "relevance": "core",
            "sentiment": "positive",
            "voice_signal": "program_comparison",
            "danger_level": "low",
            "risk_type": "none",
            "recommended_action": "Lưu làm minh chứng tích cực cho insight về communication quality.",
            "confidence": 0.82,
            "review_status": "approved",
        },
        {
            "item_id": "fb-20260719-031",
            "source_id": "fb_profile_public_alumni",
            "platform": "facebook",
            "item_type": "comment",
            "parent_item_id": "fb-post-7719",
            "author_hash": "usr_8c44",
            "content_text": "Công ty công nghệ Vin này có yêu cầu đóng phí trước khi vào chương trình không?",
            "safe_excerpt": "Công ty công nghệ Vin này có yêu cầu đóng phí trước khi vào chương trình không?",
            "permalink": None,
            "import_batch_id": "manual-20260719-fb-alumni",
            "published_at": base - timedelta(days=1, hours=3),
            "collected_at": base - timedelta(days=1, hours=1),
            "provenance_status": "import_batch_only",
            "relevance": "contextual",
            "sentiment": "negative",
            "voice_signal": "faq_fee",
            "danger_level": "high",
            "risk_type": "trust_and_fee",
            "recommended_action": "Ưu tiên phản hồi công khai bằng thông tin chính thức về phí và quy trình.",
            "confidence": 0.79,
            "review_status": "needs_review",
        },
        {
            "item_id": "tt-20260719-018",
            "source_id": "tt_keyword_vsf",
            "platform": "tiktok",
            "item_type": "comment",
            "parent_item_id": "tt-video-393",
            "author_hash": "usr_1bc9",
            "content_text": "Nếu không nhận được kết quả thì inbox ai bên VSF vậy?",
            "safe_excerpt": "Nếu không nhận được kết quả thì inbox ai bên VSF vậy?",
            "permalink": "https://www.tiktok.com/@creator/video/393",
            "import_batch_id": None,
            "published_at": base - timedelta(days=1, hours=6),
            "collected_at": base - timedelta(days=1, hours=2),
            "provenance_status": "permalink_ok",
            "relevance": "core",
            "sentiment": "neutral",
            "voice_signal": "question_repeated",
            "danger_level": "medium",
            "risk_type": "support_routing",
            "recommended_action": "Tạo macro trả lời kênh hỗ trợ chính thức và SLA phản hồi.",
            "confidence": 0.81,
            "review_status": "edited",
        },
    ]


@st.cache_data(show_spinner=False)
def demo_runs() -> list[dict[str, Any]]:
    base = now()
    return [
        {
            "crawl_run_id": "crawl-20260720-0800",
            "status": "partial",
            "started_at": base - timedelta(hours=2),
            "completed_at": base - timedelta(hours=1, minutes=12),
            "lookback_hours": 24,
            "sources_success": 3,
            "sources_failed": 1,
            "posts_collected": 42,
            "comments_collected": 318,
            "candidates_sent_to_ai": 91,
            "error_summary": "Threads connector chờ quyền API; dùng import batch dự phòng.",
            "estimated_cost_usd": 0.09,
        },
        {
            "crawl_run_id": "crawl-20260719-0800",
            "status": "success",
            "started_at": base - timedelta(days=1, hours=2),
            "completed_at": base - timedelta(days=1, hours=1, minutes=5),
            "lookback_hours": 24,
            "sources_success": 4,
            "sources_failed": 0,
            "posts_collected": 57,
            "comments_collected": 402,
            "candidates_sent_to_ai": 128,
            "error_summary": "",
            "estimated_cost_usd": 0.13,
        },
    ]


@st.cache_data(show_spinner=False)
def demo_insights() -> list[dict[str, Any]]:
    return [
        {
            "insight_id": "ins-20260720-01",
            "signal_type": "positive_feedback",
            "status": "active",
            "title": "Phản hồi tốt về tốc độ trả lời deadline",
            "summary": "Nhiều bình luận khen admin phản hồi rõ về deadline và lịch phỏng vấn.",
            "evidence_item_ids": ["fb-20260720-001", "th-20260720-007"],
            "recommended_actions": "Đưa vào Daily Digest và dùng làm ví dụ chuẩn cho đội support.",
        },
        {
            "insight_id": "ins-20260720-02",
            "signal_type": "repeated_question",
            "status": "active",
            "title": "Câu hỏi lặp lại về email xác nhận và đầu mối hỗ trợ",
            "summary": "Người dùng hỏi nhiều về chậm email xác nhận, kết quả và inbox ai.",
            "evidence_item_ids": ["fb-20260720-002", "tt-20260719-018"],
            "recommended_actions": "Viết FAQ ngắn, gắn kênh hỗ trợ chính thức và SLA phản hồi.",
        },
    ]


@st.cache_data(show_spinner=False)
def demo_alerts() -> list[dict[str, Any]]:
    return [
        {
            "alert_id": "alt-20260720-01",
            "severity": "high",
            "risk_type": "trust_and_fee",
            "status": "open",
            "title": "Nghi ngờ có hiểu nhầm về phí tham gia",
            "why_now": "Xuất hiện câu hỏi về đóng phí trước khi vào chương trình, confidence 0.79.",
            "evidence_item_ids": ["fb-20260719-031"],
            "recommended_actions": "Duyệt evidence, xác nhận chính sách phí, phản hồi bằng nguồn chính thức.",
        },
        {
            "alert_id": "alt-20260720-02",
            "severity": "medium",
            "risk_type": "process_confusion",
            "status": "triage",
            "title": "Chậm email xác nhận hồ sơ",
            "why_now": "Câu hỏi bắt đầu lặp lại trong group Facebook và TikTok.",
            "evidence_item_ids": ["fb-20260720-002", "tt-20260719-018"],
            "recommended_actions": "Kiểm tra backlog, cập nhật macro trả lời và deadline dự kiến.",
        },
    ]


@st.cache_data(show_spinner=False)
def demo_cost_logs() -> list[dict[str, Any]]:
    return [
        {
            "date": "2026-07-20",
            "provider": "OpenAI",
            "model_name": "gpt-4.1-mini",
            "items_classified": 91,
            "input_tokens": 109_200,
            "output_tokens": 18_200,
            "estimated_cost_usd": 0.09,
            "budget_usd": 1.00,
        },
        {
            "date": "2026-07-19",
            "provider": "OpenAI",
            "model_name": "gpt-4.1-mini",
            "items_classified": 128,
            "input_tokens": 153_600,
            "output_tokens": 25_600,
            "estimated_cost_usd": 0.13,
            "budget_usd": 1.00,
        },
    ]


def api_get(path: str) -> Any | None:
    try:
        response = requests.get(f"{BACKEND_URL}{path}", timeout=1.5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def api_post(path: str, payload: dict[str, Any]) -> tuple[bool, Any]:
    try:
        response = requests.post(f"{BACKEND_URL}{path}", json=payload, timeout=5)
        response.raise_for_status()
        return True, response.json()
    except requests.RequestException as exc:
        return False, str(exc)


def load_sources_frame() -> pd.DataFrame:
    api_sources = api_get("/sources")
    data = api_sources if api_sources else demo_sources()
    frame = pd.DataFrame(data)
    if "last_collected_at" not in frame.columns:
        frame["last_collected_at"] = pd.NaT
    frame["last_collected_at"] = pd.to_datetime(frame["last_collected_at"], errors="coerce")
    return frame


def as_frame(data: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(data)
    for column in ["published_at", "collected_at", "started_at", "completed_at"]:
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return frame


def status_dot(value: str) -> str:
    color = {
        "success": "#0f766e",
        "approved": "#0f766e",
        "open": "#b91c1c",
        "failed": "#b91c1c",
        "critical": "#b91c1c",
        "high": "#c2410c",
        "partial": "#b45309",
        "triage": "#b45309",
        "medium": "#b45309",
        "needs_review": "#4338ca",
        "edited": "#4338ca",
        "positive": "#15803d",
        "negative": "#b91c1c",
        "low": "#0f766e",
        "watch": "#6d28d9",
    }.get(str(value).lower(), "#475569")
    return (
        f"<span class='status-dot' style='background:{color}'></span>"
        f"<span>{value}</span>"
    )


def inject_css() -> None:
    st.markdown(
        """
<style>
    :root {
        --border: #d8dee8;
        --ink: #172033;
        --muted: #667085;
        --panel: #ffffff;
        --band: #f6f8fb;
    }
    .main .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }
    h1, h2, h3 {
        letter-spacing: 0;
        color: var(--ink);
    }
    section[data-testid="stSidebar"] {
        background: #f3f6fa;
        border-right: 1px solid var(--border);
    }
    div[data-testid="stMetric"] {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 12px 14px;
        min-height: 96px;
    }
    .tr-band {
        background: var(--band);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 14px 16px;
        margin: 8px 0 16px;
    }
    .section-kicker {
        color: var(--muted);
        font-size: 0.82rem;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0;
    }
    .status-line {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        white-space: nowrap;
    }
    .status-dot {
        width: 9px;
        height: 9px;
        border-radius: 999px;
        display: inline-block;
    }
    .evidence-box {
        border-left: 4px solid #2563eb;
        background: #f8fbff;
        padding: 12px 14px;
        border-radius: 0 8px 8px 0;
        margin: 8px 0;
    }
    .small-muted {
        color: var(--muted);
        font-size: 0.88rem;
    }
</style>
        """,
        unsafe_allow_html=True,
    )


def render_title() -> None:
    health = api_get("/health")
    api_state = "online" if health else "demo"
    cols = st.columns([3, 1, 1])
    with cols[0]:
        st.title("Talent Radar | VSF Control Room")
        st.caption("Theo dõi người ngoài nói gì về VSF trên Facebook, TikTok và Threads.")
    cols[1].metric("API", api_state)
    cols[2].metric("UI version", APP_VERSION)


def render_filters(items: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.markdown("### Bộ lọc")
    platform_options = ["all"] + sorted(items["platform"].dropna().unique().tolist())
    selected_platform = st.sidebar.selectbox("Platform", platform_options, format_func=lambda x: "Tất cả" if x == "all" else PLATFORM_LABELS.get(x, x))
    danger_options = ["all"] + SEVERITY_ORDER
    selected_danger = st.sidebar.selectbox("Danger level", danger_options, format_func=lambda x: "Tất cả" if x == "all" else x)
    review_options = ["all"] + sorted(items["review_status"].dropna().unique().tolist())
    selected_review = st.sidebar.selectbox("Review status", review_options, format_func=lambda x: "Tất cả" if x == "all" else REVIEW_ACTIONS.get(x, x))
    min_confidence = st.sidebar.slider("AI confidence tối thiểu", 0.0, 1.0, 0.0, 0.05)

    filtered = items.copy()
    if selected_platform != "all":
        filtered = filtered[filtered["platform"] == selected_platform]
    if selected_danger != "all":
        filtered = filtered[filtered["danger_level"] == selected_danger]
    if selected_review != "all":
        filtered = filtered[filtered["review_status"] == selected_review]
    filtered = filtered[filtered["confidence"] >= min_confidence]
    return filtered


def render_overview(items: pd.DataFrame, sources: pd.DataFrame, runs: pd.DataFrame, alerts: pd.DataFrame) -> None:
    st.markdown("<div class='section-kicker'>Overview</div>", unsafe_allow_html=True)
    metric_cols = st.columns(6)
    metric_cols[0].metric("Items 24h", len(items))
    metric_cols[1].metric("Sources bật", int(sources["enabled"].sum()) if "enabled" in sources else len(sources))
    metric_cols[2].metric("High/Critical", int(items["danger_level"].isin(["high", "critical"]).sum()))
    metric_cols[3].metric("Cần human review", int((items["review_status"] == "needs_review").sum()))
    metric_cols[4].metric("Tín hiệu tích cực", int((items["sentiment"] == "positive").sum()))
    metric_cols[5].metric("Chi phí hôm nay", f"${runs.iloc[0]['estimated_cost_usd']:.2f}" if not runs.empty else "$0.00")

    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Dòng tín hiệu")
        trend = (
            items.groupby(["platform", "sentiment"], dropna=False)
            .size()
            .reset_index(name="count")
            .sort_values(["platform", "count"], ascending=[True, False])
        )
        st.dataframe(trend, width="stretch", hide_index=True)
    with right:
        st.subheader("Alert đang mở")
        alert_view = alerts[["severity", "risk_type", "status", "title"]].copy()
        st.dataframe(alert_view, width="stretch", hide_index=True)

    st.subheader("Daily Digest")
    digest_cols = st.columns(4)
    latest_run = runs.iloc[0].to_dict() if not runs.empty else {}
    digest_cols[0].metric("Nguồn thành công", latest_run.get("sources_success", 0))
    digest_cols[1].metric("Nguồn thất bại", latest_run.get("sources_failed", 0))
    digest_cols[2].metric("Bài viết", latest_run.get("posts_collected", 0))
    digest_cols[3].metric("Comment", latest_run.get("comments_collected", 0))

    st.markdown(
        """
<div class='tr-band'>
    <b>Hướng xử lý hôm nay:</b> ưu tiên duyệt alert về phí, cập nhật FAQ email xác nhận,
    và lưu các phản hồi tích cực về chất lượng phản hồi vào báo cáo ngày.
</div>
        """,
        unsafe_allow_html=True,
    )


def render_sources(sources: pd.DataFrame) -> None:
    st.markdown("<div class='section-kicker'>Sources</div>", unsafe_allow_html=True)
    columns = [
        "id",
        "platform",
        "source_kind",
        "source_name",
        "source_url",
        "access_basis",
        "authorization_status",
        "collection_method",
        "enabled",
        "priority",
        "crawl_frequency",
        "lookback_hours",
        "comment_policy",
        "owner",
        "last_status",
    ]
    st.dataframe(
        sources[[column for column in columns if column in sources.columns]],
        width="stretch",
        hide_index=True,
    )

    st.subheader("Thêm hoặc cập nhật source")
    with st.form("source-form", clear_on_submit=False):
        form_cols = st.columns(3)
        source_id = form_cols[0].text_input("source_id", value="fb_group_new")
        platform = form_cols[1].selectbox("platform", ["facebook", "tiktok", "threads", "manual"])
        source_kind = form_cols[2].selectbox("source_kind", ["group", "profile", "keyword", "hashtag", "manual_batch"])
        source_name = st.text_input("source_name", value="Nguồn mới")
        source_url = st.text_input("source_url hoặc import path", value="https://")
        cols = st.columns(4)
        access_basis = cols[0].selectbox("access_basis", ["public_search", "member_export", "manual_import", "official_api", "pending"])
        authorization_status = cols[1].selectbox("authorization_status", ["approved", "pending_review", "pending", "blocked"])
        collection_method = cols[2].selectbox("collection_method", ["api_or_export", "csv_import", "approved_connector_or_import", "manual"])
        priority = cols[3].selectbox("priority", ["P0", "P1", "P2"])
        cols = st.columns(4)
        enabled = cols[0].toggle("enabled", value=True)
        crawl_frequency = cols[1].selectbox("crawl_frequency", ["daily", "twice_daily", "weekly", "manual"])
        lookback_hours = cols[2].number_input("lookback_hours", min_value=1, max_value=168, value=24)
        owner = cols[3].text_input("owner", value="Ops")
        comment_policy = st.text_input("comment_policy", value="include_top_level_and_replies")
        submitted = st.form_submit_button("Lưu source")

    if submitted:
        payload = {
            "id": source_id,
            "platform": platform,
            "source_kind": source_kind,
            "source_name": source_name,
            "source_url": source_url,
            "source_type": "public_earned",
            "access_basis": access_basis,
            "authorization_status": authorization_status,
            "collection_method": collection_method,
            "enabled": enabled,
            "priority": priority,
            "crawl_frequency": crawl_frequency,
            "lookback_hours": int(lookback_hours),
            "comment_policy": {"mode": comment_policy},
            "privacy": {"store_author_hash_only": True},
            "owner": {"team": owner},
        }
        ok, result = api_post("/sources", payload)
        if ok:
            st.success(f"Đã gửi source `{result['id']}` vào API.")
        else:
            st.warning("API chưa sẵn sàng, source mới chỉ được dùng để mô phỏng trên UI.")
            st.code(str(result), language="text")


def render_daily_crawl(runs: pd.DataFrame, sources: pd.DataFrame) -> None:
    st.markdown("<div class='section-kicker'>Daily Crawl</div>", unsafe_allow_html=True)
    run_cols = [
        "crawl_run_id",
        "status",
        "started_at",
        "completed_at",
        "lookback_hours",
        "sources_success",
        "sources_failed",
        "posts_collected",
        "comments_collected",
        "candidates_sent_to_ai",
        "estimated_cost_usd",
        "error_summary",
    ]
    st.dataframe(runs[run_cols], width="stretch", hide_index=True)

    st.subheader("Runbook")
    st.code("python -m talent_radar.jobs.daily_collect", language="powershell")
    st.subheader("Nguồn cần xử lý")
    failed = sources[sources["last_status"].isin(["failed", "partial"])] if "last_status" in sources else sources.iloc[0:0]
    if failed.empty:
        st.success("Không có source lỗi trong dữ liệu hiện tại.")
    else:
        st.dataframe(
            failed[["id", "platform", "authorization_status", "collection_method", "last_status", "owner"]],
            width="stretch",
            hide_index=True,
        )


def render_feed(items: pd.DataFrame) -> None:
    st.markdown("<div class='section-kicker'>Feed</div>", unsafe_allow_html=True)
    if items.empty:
        st.info("Không có item nào khớp bộ lọc hiện tại.")
        return

    columns = [
        "item_id",
        "platform",
        "item_type",
        "source_id",
        "published_at",
        "relevance",
        "sentiment",
        "voice_signal",
        "danger_level",
        "risk_type",
        "confidence",
        "review_status",
        "content_text",
    ]
    st.dataframe(items[columns], width="stretch", hide_index=True)

    selected_id = st.selectbox("item_id", items["item_id"].tolist())
    item = items[items["item_id"] == selected_id].iloc[0].to_dict()
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Nội dung")
        st.markdown(f"<div class='evidence-box'>{item['safe_excerpt']}</div>", unsafe_allow_html=True)
        st.write(item["content_text"])
    with right:
        st.subheader("AI phân loại")
        st.json(
            {
                "relevance": item["relevance"],
                "sentiment": item["sentiment"],
                "voice_signal": item["voice_signal"],
                "danger_level": item["danger_level"],
                "risk_type": item["risk_type"],
                "recommended_action": item["recommended_action"],
                "confidence": item["confidence"],
                "review_status": item["review_status"],
            }
        )


def render_insights(insights: pd.DataFrame, items: pd.DataFrame) -> None:
    st.markdown("<div class='section-kicker'>Insights</div>", unsafe_allow_html=True)
    st.dataframe(insights, width="stretch", hide_index=True)
    selected = st.selectbox("insight_id", insights["insight_id"].tolist())
    insight = insights[insights["insight_id"] == selected].iloc[0].to_dict()
    evidence_ids = insight["evidence_item_ids"]
    st.subheader(insight["title"])
    st.write(insight["summary"])
    st.markdown("**Minh chứng**")
    evidence = items[items["item_id"].isin(evidence_ids)]
    st.dataframe(
        evidence[["item_id", "platform", "published_at", "safe_excerpt", "permalink", "import_batch_id"]],
        width="stretch",
        hide_index=True,
    )
    st.markdown("**Hướng xử lý**")
    st.write(insight["recommended_actions"])


def render_alerts(alerts: pd.DataFrame, items: pd.DataFrame) -> None:
    st.markdown("<div class='section-kicker'>Alerts</div>", unsafe_allow_html=True)
    st.dataframe(
        alerts[["alert_id", "severity", "risk_type", "status", "title", "why_now"]],
        width="stretch",
        hide_index=True,
    )
    selected = st.selectbox("alert_id", alerts["alert_id"].tolist())
    alert = alerts[alerts["alert_id"] == selected].iloc[0].to_dict()
    st.subheader(alert["title"])
    st.markdown(
        f"<p class='status-line'>{status_dot(alert['severity'])}</p>",
        unsafe_allow_html=True,
    )
    st.write(alert["why_now"])
    st.markdown("**Recommended action**")
    st.write(alert["recommended_actions"])
    st.markdown("**Evidence**")
    evidence = items[items["item_id"].isin(alert["evidence_item_ids"])]
    st.dataframe(
        evidence[["item_id", "source_id", "platform", "published_at", "permalink", "import_batch_id", "safe_excerpt"]],
        width="stretch",
        hide_index=True,
    )


def render_review(items: pd.DataFrame) -> None:
    st.markdown("<div class='section-kicker'>Human Review</div>", unsafe_allow_html=True)
    queue = items[items["review_status"] == "needs_review"].copy()
    if queue.empty:
        st.success("Không có item cần duyệt.")
        return

    st.session_state.setdefault("review_decisions", {})
    selected = st.selectbox("Item cần duyệt", queue["item_id"].tolist())
    item = queue[queue["item_id"] == selected].iloc[0].to_dict()

    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("Evidence")
        st.markdown(f"<div class='evidence-box'>{item['safe_excerpt']}</div>", unsafe_allow_html=True)
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "item_id": item["item_id"],
                        "source_id": item["source_id"],
                        "platform": item["platform"],
                        "published_at": item["published_at"],
                        "permalink": item["permalink"],
                        "import_batch_id": item["import_batch_id"],
                    }
                ]
            ),
            width="stretch",
            hide_index=True,
        )
    with right:
        st.subheader("Duyệt nhãn")
        sentiment = st.selectbox("sentiment", SENTIMENT_ORDER, index=SENTIMENT_ORDER.index(item["sentiment"]))
        danger = st.selectbox("danger_level", SEVERITY_ORDER, index=SEVERITY_ORDER.index(item["danger_level"]))
        action = st.text_area("recommended_action", value=item["recommended_action"], height=120)
        decision = st.radio("Quyết định", ["approved", "edited", "dismissed"], horizontal=True)
        if st.button("Lưu quyết định", type="primary"):
            st.session_state["review_decisions"][selected] = {
                "decision": decision,
                "sentiment": sentiment,
                "danger_level": danger,
                "recommended_action": action,
                "reviewed_at": datetime.now().isoformat(timespec="seconds"),
            }
            st.success(f"Đã lưu quyết định review cho `{selected}` trong session.")

    if st.session_state["review_decisions"]:
        st.subheader("Quyết định trong phiên")
        st.dataframe(
            pd.DataFrame.from_dict(st.session_state["review_decisions"], orient="index"),
            width="stretch",
        )


def render_cost(costs: pd.DataFrame, items: pd.DataFrame) -> None:
    st.markdown("<div class='section-kicker'>Cost</div>", unsafe_allow_html=True)
    budget = st.number_input("Daily AI budget USD", min_value=0.0, max_value=50.0, value=1.0, step=0.1)
    total_cost = float(costs["estimated_cost_usd"].sum())
    daily_cost = float(costs.iloc[0]["estimated_cost_usd"]) if not costs.empty else 0.0
    cols = st.columns(4)
    cols[0].metric("Chi phí hôm nay", f"${daily_cost:.2f}")
    cols[1].metric("Budget hôm nay", f"${budget:.2f}")
    cols[2].metric("Items gửi AI", int(costs.iloc[0]["items_classified"]) if not costs.empty else 0)
    cols[3].metric("Tổng log demo", f"${total_cost:.2f}")
    st.dataframe(costs, width="stretch", hide_index=True)

    st.subheader("Giảm chi phí")
    savings = pd.DataFrame(
        [
            {"control": "Keyword/query pack trước AI", "effect": "Chỉ gửi candidate liên quan", "impact": "High"},
            {"control": "Rule classifier trước LLM", "effect": "Tự xử lý case rõ ràng", "impact": "High"},
            {"control": "Batch classification", "effect": "Giảm overhead prompt", "impact": "Medium"},
            {"control": "Human review theo threshold", "effect": "Chỉ duyệt item rủi ro hoặc confidence thấp", "impact": "Medium"},
        ]
    )
    st.dataframe(savings, width="stretch", hide_index=True)


def render_evidence(items: pd.DataFrame) -> None:
    st.markdown("<div class='section-kicker'>Evidence</div>", unsafe_allow_html=True)
    evidence = items[
        [
            "item_id",
            "source_id",
            "platform",
            "published_at",
            "permalink",
            "import_batch_id",
            "provenance_status",
            "safe_excerpt",
        ]
    ].copy()
    evidence["has_trace"] = evidence["permalink"].notna() | evidence["import_batch_id"].notna()
    st.dataframe(evidence, width="stretch", hide_index=True)
    cols = st.columns(3)
    cols[0].metric("Evidence rows", len(evidence))
    cols[1].metric("Có permalink", int(evidence["permalink"].notna().sum()))
    cols[2].metric("Có import batch", int(evidence["import_batch_id"].notna().sum()))


def render_classifier_lab() -> None:
    st.markdown("<div class='section-kicker'>Classifier Lab</div>", unsafe_allow_html=True)
    text = st.text_area(
        "Comment hoặc bài viết",
        value="Công ty ở Technopark có deadline xác nhận hồ sơ VSF khi nào vậy?",
        height=140,
    )
    cols = st.columns(4)
    platform = cols[0].selectbox("platform", ["manual", "facebook", "tiktok", "threads"])
    item_id = cols[1].text_input("item_id", value="preview_item")
    source_id = cols[2].text_input("source_id", value="preview_source")
    item_type = cols[3].selectbox("item_type", ["comment", "post", "reply", "video_caption"])

    if st.button("Phân loại thử", type="primary"):
        ok, result = api_post(
            "/classify",
            {
                "text": text,
                "item_id": item_id,
                "source_id": source_id,
                "platform": platform,
                "item_type": item_type,
            },
        )
        if ok:
            st.json(result)
        else:
            st.warning("API classifier chưa chạy. Bật FastAPI để test nhãn thật.")
            st.code(str(result), language="text")


def main() -> None:
    inject_css()
    sources = load_sources_frame()
    items = as_frame(demo_items())
    runs = as_frame(demo_runs())
    insights = pd.DataFrame(demo_insights())
    alerts = pd.DataFrame(demo_alerts())
    costs = pd.DataFrame(demo_cost_logs())

    render_title()
    filtered_items = render_filters(items)

    st.sidebar.markdown("### Điều hướng")
    page = st.sidebar.radio(
        "Màn hình",
        [
            "Overview",
            "Sources",
            "Daily Crawl",
            "Feed",
            "Insights",
            "Alerts",
            "Review",
            "Cost",
            "Evidence",
            "Classifier Lab",
        ],
    )

    if page == "Overview":
        render_overview(filtered_items, sources, runs, alerts)
    elif page == "Sources":
        render_sources(sources)
    elif page == "Daily Crawl":
        render_daily_crawl(runs, sources)
    elif page == "Feed":
        render_feed(filtered_items)
    elif page == "Insights":
        render_insights(insights, items)
    elif page == "Alerts":
        render_alerts(alerts, items)
    elif page == "Review":
        render_review(items)
    elif page == "Cost":
        render_cost(costs, items)
    elif page == "Evidence":
        render_evidence(items)
    elif page == "Classifier Lab":
        render_classifier_lab()


if __name__ == "__main__":
    main()
