from __future__ import annotations

import html
import json
import os
import re
import secrets
from collections import Counter
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.parse import urlencode, urlparse

import pandas as pd
import requests
import streamlit as st


ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = ROOT / "data" / "samples" / "dashboard_mock_data.json"
ENV_PATH = ROOT / ".env"
DEFAULT_PUBLIC_GROUP_URL = "https://www.facebook.com/groups/782850425639223/"
APP_VERSION = "ui-v8-group-keyword-scanner-2026-07-17"
FACEBOOK_LOGIN_URL = "https://www.facebook.com/login/"
FACEBOOK_DOCS_URL = "https://developers.facebook.com/docs/facebook-login/"
FACEBOOK_GRAPH_DOCS_URL = "https://developers.facebook.com/docs/graph-api/"

TIER_ORDER = ["core", "contextual", "watchlist", "irrelevant"]
SENTIMENT_ORDER = ["positive", "neutral", "negative", "unclear"]
STOPWORDS = {
    "và",
    "là",
    "của",
    "cho",
    "các",
    "một",
    "những",
    "trong",
    "được",
    "với",
    "không",
    "facebook",
    "group",
    "groups",
    "https",
    "www",
    "com",
    "the",
    "and",
    "you",
    "are",
    "for",
    "that",
    "this",
}


def load_local_env(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_local_env()


st.set_page_config(
    page_title="Talent Radar — Dashboard VSF",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_mock_data(path: Path = DATA_PATH) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def to_datetime(value: str | None) -> pd.Timestamp | pd.NaT:
    if not value:
        return pd.NaT
    return pd.to_datetime(value)


def prepare_frames(data: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    posts = pd.DataFrame(data["posts"])
    sources = pd.DataFrame(data["sources"])
    digests = pd.DataFrame(data["daily_digests"])
    reviews = pd.DataFrame(data["review_queue"])

    for column in ["published_at", "collected_at"]:
        posts[column] = posts[column].apply(to_datetime)
    sources["last_collected_at"] = sources["last_collected_at"].apply(to_datetime)

    posts["published_date"] = posts["published_at"].dt.date
    posts["collection_lag_minutes"] = (
        posts["collected_at"] - posts["published_at"]
    ).dt.total_seconds() / 60

    return posts, sources, digests, reviews


def chip(label: str, tone: str = "default") -> str:
    colors = {
        "core": ("#d1fae5", "#065f46"),
        "contextual": ("#dbeafe", "#1e40af"),
        "watchlist": ("#fef3c7", "#92400e"),
        "irrelevant": ("#f3f4f6", "#4b5563"),
        "negative": ("#fee2e2", "#991b1b"),
        "positive": ("#dcfce7", "#166534"),
        "neutral": ("#e5e7eb", "#374151"),
        "unclear": ("#f3e8ff", "#6b21a8"),
        "default": ("#eef2ff", "#3730a3"),
    }
    background, color = colors.get(tone, colors["default"])
    return (
        f"<span style='background:{background};color:{color};"
        "padding:0.2rem 0.55rem;border-radius:999px;"
        "font-size:0.78rem;font-weight:700'>"
        f"{label}</span>"
    )


def strip_html(raw_html: str) -> str:
    without_scripts = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", raw_html)
    without_tags = re.sub(r"(?s)<[^>]+>", " ", without_scripts)
    unescaped = html.unescape(without_tags)
    return re.sub(r"\s+", " ", unescaped).strip()


def extract_meta(raw_html: str) -> dict[str, str]:
    def first(pattern: str) -> str:
        match = re.search(pattern, raw_html, flags=re.IGNORECASE | re.DOTALL)
        return html.unescape(match.group(1).strip()) if match else ""

    return {
        "title": first(r"<title[^>]*>(.*?)</title>"),
        "description": first(
            r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\'](.*?)["\']'
        ),
        "og_title": first(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']'),
    }


def summarize_text(text: str, max_sentences: int = 4) -> list[str]:
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?。！？])\s+", text)
        if len(sentence.strip()) >= 40
    ]
    if not sentences:
        return []

    words = [
        word.lower()
        for word in re.findall(r"[\wÀ-ỹ]+", text, flags=re.UNICODE)
        if len(word) >= 3 and word.lower() not in STOPWORDS
    ]
    frequencies = Counter(words)

    ranked = []
    for index, sentence in enumerate(sentences[:80]):
        sentence_words = re.findall(r"[\wÀ-ỹ]+", sentence.lower(), flags=re.UNICODE)
        score = sum(frequencies.get(word, 0) for word in sentence_words)
        ranked.append((score, index, sentence))

    top = sorted(ranked, reverse=True)[:max_sentences]
    return [sentence for _, _, sentence in sorted(top, key=lambda item: item[1])]


def top_keywords(text: str, limit: int = 12) -> list[tuple[str, int]]:
    words = [
        word.lower()
        for word in re.findall(r"[\wÀ-ỹ]+", text, flags=re.UNICODE)
        if len(word) >= 3 and word.lower() not in STOPWORDS
    ]
    return Counter(words).most_common(limit)


def validate_public_url(url: str) -> tuple[bool, str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False, "URL phải bắt đầu bằng http hoặc https."
    if "facebook.com" not in parsed.netloc.lower():
        return False, "Prototype này đang giới hạn ở URL facebook.com để tránh crawl nhầm nguồn."
    return True, ""


def init_account_state() -> None:
    st.session_state.setdefault("account", None)
    st.session_state.setdefault("auth_mode", None)
    st.session_state.setdefault("nav_page", "Cài đặt")
    st.session_state.setdefault(
        "connections",
        {
            "facebook": {"status": "Chưa liên kết", "profile": None, "last_error": None},
            "tiktok": {"status": "Chưa liên kết", "profile": None, "last_error": None},
            "threads": {"status": "Chưa liên kết", "profile": None, "last_error": None},
        },
    )
    st.session_state.setdefault(
        "group_scan",
        {
            "group_url": os.getenv("FACEBOOK_DEFAULT_GROUP_URL", DEFAULT_PUBLIC_GROUP_URL),
            "last_status": "Chưa quét",
            "last_error": None,
            "last_scan_at": None,
            "last_results": [],
        },
    )
    st.session_state.setdefault(
        "keyword_rules",
        [
            {
                "keyword": "spring boot",
                "source": "manual",
                "active": True,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "last_scanned_at": None,
                "last_window": None,
                "last_match_count": 0,
            },
            {
                "keyword": "java",
                "source": "manual",
                "active": True,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "last_scanned_at": None,
                "last_window": None,
                "last_match_count": 0,
            },
        ],
    )


def render_auth_controls() -> None:
    init_account_state()
    st.sidebar.markdown("## Talent Radar")
    facebook_config = get_facebook_oauth_config()

    account = st.session_state["account"]
    if account:
        st.sidebar.success(f"Đã đăng nhập: {account['name']}")
        auth_cols = st.sidebar.columns(2)
        if auth_cols[0].button("Cài đặt", use_container_width=True):
            st.session_state["nav_page"] = "Cài đặt"
            st.rerun()
        if auth_cols[1].button("Đăng xuất", use_container_width=True):
            st.session_state["account"] = None
            st.session_state["auth_mode"] = None
            st.session_state.pop("facebook_oauth_state", None)
            st.rerun()
        st.sidebar.divider()
        return

    if facebook_config["app_id"]:
        st.sidebar.caption("Facebook Login đã cấu hình.")
        st.sidebar.link_button(
            "Đăng nhập bằng Facebook",
            build_facebook_oauth_url(facebook_config),
            type="primary",
            use_container_width=True,
        )
        if not facebook_config["app_secret"]:
            st.sidebar.warning("Thiếu FACEBOOK_APP_SECRET nên callback chưa đổi token được.")
        st.sidebar.divider()
    else:
        st.sidebar.caption("Chưa có FACEBOOK_APP_ID; chỉ dùng đăng nhập demo.")

    auth_cols = st.sidebar.columns(2)
    if auth_cols[0].button("Đăng nhập demo", use_container_width=True):
        st.session_state["auth_mode"] = "login"
    if auth_cols[1].button("Đăng ký demo", use_container_width=True):
        st.session_state["auth_mode"] = "register"

    mode = st.session_state.get("auth_mode")
    if mode == "login":
        with st.sidebar.form("sidebar-login-form"):
            email = st.text_input("Email", value="monitoring@example.com")
            password = st.text_input("Mật khẩu", type="password", value="demo-password")
            submitted = st.form_submit_button("Vào dashboard")
            if submitted:
                st.session_state["account"] = {
                    "name": "VSF Monitoring User",
                    "email": email,
                    "role": "Admin",
                }
                st.session_state["auth_mode"] = None
                st.session_state["nav_page"] = "Cài đặt"
                st.rerun()
    elif mode == "register":
        with st.sidebar.form("sidebar-register-form"):
            name = st.text_input("Tên hiển thị", value="VSF Monitoring User")
            email = st.text_input("Email", value="monitoring@example.com")
            password = st.text_input("Mật khẩu", type="password", value="demo-password")
            submitted = st.form_submit_button("Tạo tài khoản")
            if submitted:
                st.session_state["account"] = {"name": name, "email": email, "role": "Admin"}
                st.session_state["auth_mode"] = None
                st.session_state["nav_page"] = "Cài đặt"
                st.rerun()

    st.sidebar.caption("Prototype auth chỉ lưu trong session hiện tại; chưa có database người dùng.")
    st.sidebar.divider()


def get_facebook_oauth_config() -> dict[str, str]:
    redirect_uri = os.getenv("FACEBOOK_REDIRECT_URI", "http://localhost:8501/")
    graph_version = os.getenv("FACEBOOK_GRAPH_API_VERSION", "v20.0")
    scopes = os.getenv("FACEBOOK_SCOPES", "public_profile")
    return {
        "app_id": os.getenv("FACEBOOK_APP_ID", ""),
        "app_secret": os.getenv("FACEBOOK_APP_SECRET", ""),
        "redirect_uri": redirect_uri,
        "graph_version": graph_version,
        "scopes": scopes,
    }


def build_facebook_oauth_url(config: dict[str, str]) -> str:
    state = st.session_state.setdefault("facebook_oauth_state", secrets.token_urlsafe(24))
    st.session_state["facebook_oauth_redirect_uri"] = config["redirect_uri"]
    params = {
        "client_id": config["app_id"],
        "redirect_uri": config["redirect_uri"],
        "state": state,
        "scope": config["scopes"],
        "response_type": "code",
    }
    return f"https://www.facebook.com/{config['graph_version']}/dialog/oauth?{urlencode(params)}"


def exchange_facebook_code(code: str, config: dict[str, str], redirect_uri: str | None = None) -> dict:
    token_url = f"https://graph.facebook.com/{config['graph_version']}/oauth/access_token"
    token_response = requests.get(
        token_url,
        params={
            "client_id": config["app_id"],
            "client_secret": config["app_secret"],
            "redirect_uri": redirect_uri or config["redirect_uri"],
            "code": code,
        },
        timeout=20,
    )
    if not token_response.ok:
        raise RuntimeError(format_facebook_error(token_response, "đổi OAuth code lấy access token"))
    token_payload = token_response.json()
    access_token = token_payload["access_token"]

    profile_response = requests.get(
        f"https://graph.facebook.com/{config['graph_version']}/me",
        params={"fields": "id,name", "access_token": access_token},
        timeout=20,
    )
    if not profile_response.ok:
        raise RuntimeError(format_facebook_error(profile_response, "đọc Facebook profile"))
    profile = profile_response.json()

    return {
        "profile": profile,
        "access_token": access_token,
        "expires_in": token_payload.get("expires_in"),
        "token_type": token_payload.get("token_type"),
    }


def format_facebook_error(response: requests.Response, action: str) -> str:
    try:
        payload = response.json()
    except ValueError:
        body = response.text[:500]
        return f"Facebook lỗi khi {action}: HTTP {response.status_code}. Nội dung: {body}"

    error = payload.get("error", payload)
    message = error.get("message") if isinstance(error, dict) else str(error)
    error_type = error.get("type") if isinstance(error, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    subcode = error.get("error_subcode") if isinstance(error, dict) else None

    details = [f"Facebook lỗi khi {action}: HTTP {response.status_code}"]
    if message:
        details.append(f"message={message}")
    if error_type:
        details.append(f"type={error_type}")
    if code:
        details.append(f"code={code}")
    if subcode:
        details.append(f"subcode={subcode}")
    return " · ".join(details)


def complete_facebook_login_if_present() -> None:
    init_account_state()
    params = st.query_params
    code = params.get("code")
    oauth_error = params.get("error")
    oauth_error_description = params.get("error_description")

    if oauth_error:
        st.session_state["facebook_login_error"] = (
            oauth_error_description or f"Facebook trả về lỗi OAuth: {oauth_error}"
        )
        st.query_params.clear()
        return

    if not code:
        return

    config = get_facebook_oauth_config()
    if not config["app_id"] or not config["app_secret"]:
        st.session_state["facebook_login_error"] = (
            "Facebook callback đã trả về code, nhưng app thiếu FACEBOOK_APP_ID hoặc "
            "FACEBOOK_APP_SECRET để đổi code lấy access token."
        )
        return

    state = params.get("state")
    expected_state = st.session_state.get("facebook_oauth_state")
    if expected_state and state and state != expected_state:
        st.session_state["facebook_login_error"] = (
            "OAuth state không khớp. App đã chặn callback để tránh request giả mạo."
        )
        st.query_params.clear()
        return

    try:
        redirect_uri_used = st.session_state.get("facebook_oauth_redirect_uri") or config["redirect_uri"]
        result = exchange_facebook_code(code, config, redirect_uri=redirect_uri_used)
    except (requests.RequestException, RuntimeError) as exc:
        st.session_state["facebook_login_error"] = f"Không đăng nhập Facebook được: {exc}"
        st.query_params.clear()
        return

    profile = result["profile"]
    st.session_state["account"] = {
        "name": profile.get("name", "Facebook User"),
        "email": profile.get("email") or f"facebook-{profile.get('id', 'user')}@facebook.local",
        "role": "Admin",
    }
    st.session_state["connections"]["facebook"] = {
        "status": "Đã liên kết",
        "profile": profile,
        "access_token": result["access_token"],
        "expires_in": result.get("expires_in"),
        "last_error": None,
    }
    st.session_state["auth_mode"] = None
    st.session_state["nav_page"] = "Cài đặt"
    st.session_state["facebook_login_success"] = (
        f"Đã đăng nhập bằng Facebook: {profile.get('name', 'Facebook User')}"
    )
    st.query_params.clear()
    st.rerun()


def render_connector_card(platform: str, status: str, description: str, disabled: bool = False) -> None:
    with st.container(border=True):
        st.markdown(f"### {platform}")
        st.caption(description)
        st.metric("Trạng thái", status)
        if disabled:
            st.button(f"Liên kết {platform}", disabled=True, key=f"disabled-{platform}")


@st.cache_data(ttl=300, show_spinner=False)
def crawl_public_url(url: str) -> dict:
    ok, reason = validate_public_url(url)
    if not ok:
        return {"ok": False, "reason": reason}

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; TalentRadarPrototype/0.1; "
            "+https://example.local/talent-radar)"
        ),
        "Accept-Language": "vi,en;q=0.8",
    }
    try:
        response = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
    except requests.RequestException as exc:
        return {"ok": False, "reason": f"Không gọi được URL: {exc}"}

    text = strip_html(response.text)
    meta = extract_meta(response.text)
    escaped_group_path = re.escape(urlparse(url).path.strip("/"))
    post_urls = sorted(
        set(
            re.findall(
                rf"https?:\\?/\\?/www\.facebook\.com\\?/{escaped_group_path}\\?/posts\\?/[^\"<>\s]+",
                response.text,
                flags=re.IGNORECASE,
            )
        )
    )
    login_or_blocked = any(
        marker in text.lower()
        for marker in [
            "log in to facebook",
            "đăng nhập facebook",
            "you must log in",
            "content isn't available",
            "nội dung này hiện không hiển thị",
        ]
    )

    return {
        "ok": True,
        "url": url,
        "final_url": response.url,
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type", ""),
        "html_length": len(response.text),
        "text_length": len(text),
        "meta": meta,
        "text_preview": text[:2500],
        "summary": summarize_text(text),
        "keywords": top_keywords(text),
        "post_url_count": len(post_urls),
        "post_urls": post_urls[:10],
        "likely_blocked": login_or_blocked or len(text) < 300,
    }


def parse_facebook_group_id(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    if value.isdigit():
        return value

    parsed = urlparse(value)
    path_parts = [part for part in parsed.path.split("/") if part]
    if "groups" in path_parts:
        index = path_parts.index("groups")
        if len(path_parts) > index + 1:
            candidate = path_parts[index + 1]
            return candidate if candidate else None
    return None


def get_active_keywords() -> list[str]:
    return [
        rule["keyword"].strip()
        for rule in st.session_state.get("keyword_rules", [])
        if rule.get("active") and rule.get("keyword", "").strip()
    ]


def fetch_facebook_group_posts(
    group_id: str,
    access_token: str,
    graph_version: str,
    limit: int = 25,
) -> list[dict]:
    response = requests.get(
        f"https://graph.facebook.com/{graph_version}/{group_id}/feed",
        params={
            "fields": "id,message,story,created_time,permalink_url,from{name,id}",
            "limit": limit,
            "access_token": access_token,
        },
        timeout=20,
    )
    if not response.ok:
        raise RuntimeError(format_facebook_error(response, "đọc feed group Facebook"))
    return response.json().get("data", [])


def filter_posts_by_keywords(posts: list[dict], keywords: list[str], start_dt: datetime, end_dt: datetime) -> list[dict]:
    results: list[dict] = []
    lowered_keywords = [keyword.lower() for keyword in keywords]

    for post in posts:
        created_raw = post.get("created_time")
        created_at = None
        if created_raw:
            try:
                created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00")).replace(tzinfo=None)
            except ValueError:
                created_at = None
        if created_at and not (start_dt <= created_at <= end_dt):
            continue

        text = " ".join([post.get("message", ""), post.get("story", "")]).strip()
        text_lower = text.lower()
        matched = [keyword for keyword in lowered_keywords if keyword in text_lower]
        if not matched:
            continue

        results.append(
            {
                "post_id": post.get("id", ""),
                "created_time": created_raw or "",
                "message": text,
                "matched_keywords": ", ".join(matched),
                "permalink_url": post.get("permalink_url", ""),
                "author": (post.get("from") or {}).get("name", "Không rõ"),
            }
        )
    return results


def update_keyword_scan_stats(keywords: list[str], results: list[dict], start_dt: datetime, end_dt: datetime) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    window = f"{start_dt.strftime('%d/%m/%Y %H:%M')} → {end_dt.strftime('%d/%m/%Y %H:%M')}"
    counts = Counter()
    for result in results:
        for keyword in result["matched_keywords"].split(", "):
            if keyword:
                counts[keyword.lower()] += 1

    for rule in st.session_state["keyword_rules"]:
        keyword = rule["keyword"].lower()
        if keyword in [item.lower() for item in keywords]:
            rule["last_scanned_at"] = now
            rule["last_window"] = window
            rule["last_match_count"] = counts.get(keyword, 0)


def suggest_keywords_from_text(text: str, existing: set[str], limit: int = 8) -> list[str]:
    candidates = []
    for word, count in top_keywords(text, limit=40):
        if count < 1:
            continue
        if word.lower() in existing:
            continue
        if word.isdigit():
            continue
        candidates.append(word)
        if len(candidates) >= limit:
            break
    return candidates


def apply_sidebar_filters(posts: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.title("🎛️ Bộ lọc")

    min_date = posts["published_date"].min()
    max_date = posts["published_date"].max()
    date_range = st.sidebar.date_input(
        "Khoảng ngày xuất bản",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = min_date, max_date

    sources = st.sidebar.multiselect(
        "Nguồn dữ liệu",
        options=sorted(posts["source_name"].unique()),
        default=sorted(posts["source_name"].unique()),
    )
    tiers = st.sidebar.multiselect(
        "Tầng liên quan",
        options=[tier for tier in TIER_ORDER if tier in set(posts["relevance_tier"])],
        default=[tier for tier in TIER_ORDER if tier in set(posts["relevance_tier"])],
    )
    sentiments = st.sidebar.multiselect(
        "Sắc thái",
        options=[sentiment for sentiment in SENTIMENT_ORDER if sentiment in set(posts["sentiment"])],
        default=[sentiment for sentiment in SENTIMENT_ORDER if sentiment in set(posts["sentiment"])],
    )
    topics = st.sidebar.multiselect(
        "Chủ đề",
        options=sorted(posts["topic"].unique()),
        default=sorted(posts["topic"].unique()),
    )
    search_text = st.sidebar.text_input(
        "Tìm trong tiêu đề/nội dung/bằng chứng",
        placeholder="VD: workshop",
    )

    filtered = posts[
        posts["published_date"].between(start_date, end_date)
        & posts["source_name"].isin(sources)
        & posts["relevance_tier"].isin(tiers)
        & posts["sentiment"].isin(sentiments)
        & posts["topic"].isin(topics)
    ].copy()

    if search_text:
        haystack = (
            filtered["title"].fillna("")
            + " "
            + filtered["text"].fillna("")
            + " "
            + filtered["evidence"].fillna("")
        ).str.lower()
        filtered = filtered[haystack.str.contains(search_text.lower(), regex=False)]

    st.sidebar.caption(
        "Dữ liệu mẫu dùng để mô phỏng dashboard. Tab crawl công khai dùng request thật nhưng "
        "không đăng nhập hoặc né chặn."
    )
    return filtered.sort_values("published_at", ascending=False)


def render_overview(posts: pd.DataFrame, filtered: pd.DataFrame, sources: pd.DataFrame) -> None:
    st.subheader("Tổng quan")
    core_count = int((filtered["relevance_tier"] == "core").sum())
    review_count = int(filtered["review_status"].str.contains("review|pending", case=False).sum())
    avg_score = filtered["relevance_score"].mean() if not filtered.empty else 0
    active_sources = int((sources["authorization_status"] == "approved").sum())
    failed_sources = int(sources["last_status"].str.contains("blocked|fail|paused", case=False).sum())

    left, mid, right, far = st.columns(4)
    left.metric("Item sau lọc", f"{len(filtered)}", f"{len(posts)} tổng")
    mid.metric("Nhắc trực tiếp VSF", core_count)
    right.metric("Cần rà soát", review_count)
    far.metric("Nguồn đã duyệt", active_sources, f"{failed_sources} cần chú ý")

    score_col, lag_col = st.columns(2)
    score_col.metric("Điểm liên quan TB", f"{avg_score:.2f}")
    lag_col.metric(
        "Độ trễ thu thập TB",
        f"{filtered['collection_lag_minutes'].mean():.0f} phút" if not filtered.empty else "0 phút",
    )

    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.markdown("**Phân bổ theo tầng liên quan**")
        tier_counts = filtered["relevance_tier"].value_counts().reindex(TIER_ORDER).fillna(0)
        st.bar_chart(tier_counts)

    with chart_right:
        st.markdown("**Sắc thái theo dữ liệu đang lọc**")
        sentiment_counts = filtered["sentiment"].value_counts().reindex(SENTIMENT_ORDER).fillna(0)
        st.bar_chart(sentiment_counts)


def render_feed(filtered: pd.DataFrame) -> None:
    st.subheader("Dòng nội dung VSF")
    st.caption("Mỗi item hiển thị bằng chứng liên quan để tránh dashboard chỉ là số đẹp.")

    export_columns = [
        "post_id",
        "published_at",
        "source_name",
        "title",
        "relevance_tier",
        "relevance_score",
        "topic",
        "sentiment",
        "sentiment_target",
        "evidence",
        "permalink",
        "review_status",
        "analysis_version",
    ]
    st.download_button(
        "⬇️ Xuất CSV theo bộ lọc hiện tại",
        data=filtered[export_columns].to_csv(index=False).encode("utf-8-sig"),
        file_name="talent_radar_filtered_posts.csv",
        mime="text/csv",
        disabled=filtered.empty,
    )

    if filtered.empty:
        st.info("Không có item nào khớp bộ lọc.")
        return

    for _, row in filtered.iterrows():
        with st.container(border=True):
            title_col, meta_col = st.columns([3, 1])
            with title_col:
                st.markdown(f"### {row['title']}")
                st.markdown(
                    " ".join(
                        [
                            chip(row["relevance_tier"], row["relevance_tier"]),
                            chip(row["sentiment"], row["sentiment"]),
                            chip(row["topic"]),
                        ]
                    ),
                    unsafe_allow_html=True,
                )
            with meta_col:
                st.metric("Điểm", f"{row['relevance_score']:.2f}")
                st.caption(row["published_at"].strftime("%d/%m/%Y %H:%M"))

            st.write(row["text"])
            st.markdown(f"**Bằng chứng:** “{row['evidence']}”")
            st.caption(
                f"Nguồn: {row['source_name']} · Thực thể: {row['matched_entity']} · "
                f"Rà soát: {row['review_status']} · Phiên bản: {row['analysis_version']}"
            )
            if str(row["permalink"]).startswith(("http://", "https://")):
                st.link_button("Mở permalink", row["permalink"])
            else:
                st.caption("Mã tham chiếu nguồn")
                st.code(row["permalink"], language=None)


def render_digest(digests: pd.DataFrame, posts: pd.DataFrame) -> None:
    st.subheader("Bản tóm tắt hằng ngày")
    selected_date = st.selectbox("Chọn ngày", options=digests["date"].tolist())
    digest = digests[digests["date"] == selected_date].iloc[0]

    st.markdown(f"### {digest['headline']}")
    st.caption(f"Cửa sổ dữ liệu: {digest['window']} · Mức rủi ro: {digest['risk_level']}")
    st.write(digest["summary"])

    st.markdown("**Việc nên làm**")
    for item in digest["action_items"]:
        st.checkbox(item, value=False, key=f"{selected_date}-{item}", disabled=True)

    st.markdown("**Bài nguồn hỗ trợ nhận định**")
    supporting = posts[posts["post_id"].isin(digest["supporting_post_ids"])]
    st.dataframe(
        supporting[["post_id", "title", "source_name", "relevance_tier", "evidence"]],
        use_container_width=True,
        hide_index=True,
    )


def render_review_queue(reviews: pd.DataFrame, posts: pd.DataFrame) -> None:
    st.subheader("Hàng chờ rà soát")
    joined = reviews.merge(posts, on="post_id", how="left")

    if joined.empty:
        st.success("Không có item cần rà soát.")
        return

    for _, row in joined.iterrows():
        with st.expander(
            f"{row['priority'].upper()} · {row['title']}",
            expanded=row["priority"] == "high",
        ):
            st.write(row["text"])
            st.markdown(f"**Lý do:** {row['reason']}")
            st.markdown(f"**Gợi ý xử lý:** {row['suggested_action']}")
            st.markdown(f"**Bằng chứng:** “{row['evidence']}”")
            decision = st.radio(
                "Quyết định mẫu",
                options=["Duyệt", "Loại", "Giữ lại để rà soát"],
                horizontal=True,
                key=f"decision-{row['review_id']}",
                disabled=True,
            )
            st.caption(
                f"Prototype chỉ hiển thị workflow; chưa ghi quyết định thật. Đang chọn: {decision}"
            )


def render_source_health(sources: pd.DataFrame) -> None:
    st.subheader("Sức khỏe nguồn dữ liệu")
    display = sources[
        [
            "name",
            "platform",
            "priority",
            "authorization_status",
            "collection_method",
            "last_status",
            "last_collected_at",
            "items_24h",
            "stale_hours",
        ]
    ].copy()
    display = display.rename(
        columns={
            "name": "Tên nguồn",
            "platform": "Nền tảng",
            "priority": "Ưu tiên",
            "authorization_status": "Trạng thái quyền",
            "collection_method": "Cách thu thập",
            "last_status": "Lần chạy gần nhất",
            "last_collected_at": "Thu thập lần cuối",
            "items_24h": "Item 24h",
            "stale_hours": "Độ cũ (giờ)",
        }
    )
    display["Thu thập lần cuối"] = display["Thu thập lần cuối"].dt.strftime("%d/%m/%Y %H:%M")
    st.dataframe(display, use_container_width=True, hide_index=True)

    blocked = sources[sources["authorization_status"].isin(["pending", "blocked"])]
    if not blocked.empty:
        st.warning(
            "Một số nguồn đang pending/blocked. Theo plan, collector không nên chạy khi "
            "`authorization_status` chưa phải `approved`."
        )


def render_group_keyword_scanner() -> None:
    init_account_state()
    st.subheader("Quét group & từ khóa")
    st.caption(
        "Màn hình này quản lý keyword và thử đọc bài viết group qua Facebook Graph API. "
        "Nếu Meta không cấp quyền đọc group feed, app sẽ báo blocked thay vì dùng cookie/scraping."
    )

    facebook_config = get_facebook_oauth_config()
    facebook_connection = st.session_state["connections"]["facebook"]
    access_token = facebook_connection.get("access_token")

    with st.container(border=True):
        st.markdown("### Nguồn group")
        group_url = st.text_input(
            "Facebook Group URL hoặc Group ID",
            value=st.session_state["group_scan"].get("group_url", DEFAULT_PUBLIC_GROUP_URL),
        )
        st.session_state["group_scan"]["group_url"] = group_url
        group_id = parse_facebook_group_id(group_url)
        st.caption(f"Group ID nhận diện được: `{group_id or 'chưa xác định'}`")

        status_cols = st.columns(4)
        status_cols[0].metric("Facebook", facebook_connection.get("status", "Chưa liên kết"))
        status_cols[1].metric("Scope", facebook_config["scopes"])
        status_cols[2].metric("Lần quét gần nhất", st.session_state["group_scan"].get("last_scan_at") or "Chưa có")
        status_cols[3].metric("Trạng thái quét", st.session_state["group_scan"].get("last_status", "Chưa quét"))
        if "groups_access_member_info" not in facebook_config["scopes"]:
            st.warning(
                "Scope hiện tại chưa có `groups_access_member_info`. Login vẫn được, nhưng đọc feed group "
                "qua Graph API nhiều khả năng sẽ bị Facebook chặn quyền. Chỉ thêm scope này khi Meta app của bạn "
                "đã được cấp quyền/advanced access phù hợp."
            )

    st.markdown("### Keyword")
    add_col, auto_col = st.columns([1, 1])
    with add_col:
        with st.form("add-keyword-form"):
            keyword = st.text_input("Thêm keyword thủ công", placeholder="VD: spring security")
            submitted = st.form_submit_button("Thêm keyword")
            if submitted and keyword.strip():
                existing = {rule["keyword"].lower() for rule in st.session_state["keyword_rules"]}
                if keyword.strip().lower() not in existing:
                    st.session_state["keyword_rules"].append(
                        {
                            "keyword": keyword.strip(),
                            "source": "manual",
                            "active": True,
                            "created_at": datetime.now().isoformat(timespec="seconds"),
                            "last_scanned_at": None,
                            "last_window": None,
                            "last_match_count": 0,
                        }
                    )
                    st.success(f"Đã thêm keyword `{keyword.strip()}`")
                    st.rerun()
                else:
                    st.warning("Keyword đã tồn tại.")

    with auto_col:
        st.caption("Gợi ý tự động dùng metadata public/HTML đọc được, không cần login.")
        if st.button("Gợi ý keyword tự động từ group", use_container_width=True):
            public_result = crawl_public_url(group_url)
            if not public_result.get("ok"):
                st.error(public_result.get("reason", "Không đọc được group public."))
            else:
                meta = public_result.get("meta", {})
                seed_text = " ".join(
                    [
                        meta.get("title", ""),
                        meta.get("description", ""),
                        public_result.get("text_preview", ""),
                    ]
                )
                existing = {rule["keyword"].lower() for rule in st.session_state["keyword_rules"]}
                suggestions = suggest_keywords_from_text(seed_text, existing)
                if not suggestions:
                    st.info("Chưa tìm thấy keyword mới đáng tin cậy từ metadata public.")
                else:
                    for suggestion in suggestions:
                        st.session_state["keyword_rules"].append(
                            {
                                "keyword": suggestion,
                                "source": "auto",
                                "active": True,
                                "created_at": datetime.now().isoformat(timespec="seconds"),
                                "last_scanned_at": None,
                                "last_window": None,
                                "last_match_count": 0,
                            }
                        )
                    st.success("Đã thêm gợi ý: " + ", ".join(suggestions))
                    st.rerun()

    if st.session_state["keyword_rules"]:
        st.markdown("**Danh sách keyword & lịch sử quét**")
        for index, rule in enumerate(st.session_state["keyword_rules"]):
            cols = st.columns([0.7, 2, 1, 1.4, 1.8, 1.2, 0.8])
            active = cols[0].checkbox("Bật", value=rule["active"], key=f"kw-active-{index}")
            if active != rule["active"]:
                rule["active"] = active
            cols[1].markdown(f"**{rule['keyword']}**")
            cols[2].caption(rule["source"])
            cols[3].caption(rule.get("last_scanned_at") or "Chưa quét")
            cols[4].caption(rule.get("last_window") or "Chưa có khoảng")
            cols[5].metric("Match", rule.get("last_match_count", 0))
            if cols[6].button("Xóa", key=f"kw-delete-{index}"):
                st.session_state["keyword_rules"].pop(index)
                st.rerun()

    st.markdown("### Chạy quét")
    default_end = datetime.now()
    default_start = default_end - timedelta(days=7)
    date_cols = st.columns(4)
    start_day = date_cols[0].date_input("Từ ngày", value=default_start.date())
    start_time = date_cols[1].time_input("Từ giờ", value=time(hour=0, minute=0))
    end_day = date_cols[2].date_input("Đến ngày", value=default_end.date())
    end_time = date_cols[3].time_input("Đến giờ", value=time(hour=23, minute=59))
    limit = st.slider("Số bài tối đa gọi từ Graph API", min_value=5, max_value=100, value=25, step=5)

    start_dt = datetime.combine(start_day, start_time)
    end_dt = datetime.combine(end_day, end_time)
    active_keywords = get_active_keywords()

    if not access_token:
        st.warning("Bạn cần đăng nhập/liên kết Facebook trước khi thử quét group qua Graph API.")
    if not active_keywords:
        st.warning("Chưa có keyword đang bật.")
    if not group_id:
        st.warning("Chưa xác định được Group ID từ URL.")

    if st.button("Quét group bằng Facebook Graph API", type="primary", use_container_width=True):
        if not access_token or not active_keywords or not group_id:
            st.error("Thiếu Facebook token, keyword đang bật hoặc Group ID.")
            return

        with st.spinner("Đang gọi Graph API và lọc keyword..."):
            try:
                posts = fetch_facebook_group_posts(
                    group_id=group_id,
                    access_token=access_token,
                    graph_version=facebook_config["graph_version"],
                    limit=limit,
                )
                results = filter_posts_by_keywords(posts, active_keywords, start_dt, end_dt)
            except (requests.RequestException, RuntimeError) as exc:
                st.session_state["group_scan"]["last_status"] = "blocked/error"
                st.session_state["group_scan"]["last_error"] = str(exc)
                st.session_state["group_scan"]["last_scan_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                update_keyword_scan_stats(active_keywords, [], start_dt, end_dt)
                st.error(f"Không quét được group qua Graph API: {exc}")
                st.info(
                    "Nếu lỗi là thiếu quyền, bạn cần scope/permission group phù hợp, app review/advanced access, "
                    "và trong nhiều trường hợp group admin phải cho phép app. Nếu không có quyền, dùng CSV/JSON import."
                )
            else:
                st.session_state["group_scan"]["last_status"] = "success"
                st.session_state["group_scan"]["last_error"] = None
                st.session_state["group_scan"]["last_scan_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                st.session_state["group_scan"]["last_results"] = results
                update_keyword_scan_stats(active_keywords, results, start_dt, end_dt)
                st.success(f"Đã gọi {len(posts)} bài từ Graph API, match keyword: {len(results)} bài.")
                st.rerun()

    last_error = st.session_state["group_scan"].get("last_error")
    if last_error:
        st.error(last_error)

    results = st.session_state["group_scan"].get("last_results", [])
    if results:
        st.markdown("### Kết quả match gần nhất")
        result_frame = pd.DataFrame(results)
        st.dataframe(result_frame, use_container_width=True, hide_index=True)
    else:
        st.info("Chưa có bài match keyword trong lần quét gần nhất.")


def render_account_settings() -> None:
    init_account_state()
    st.subheader("Cài đặt tài khoản")
    st.caption(
        "Sau khi đăng nhập/đăng ký ở góc trái, người dùng có thể liên kết Facebook, TikTok, "
        "Threads giống flow của các app phổ biến."
    )

    account = st.session_state["account"]
    if account is None:
        st.info("Hãy dùng nút `Đăng nhập` hoặc `Đăng ký` ở góc trên bên trái để vào phần cài đặt.")
        return

    profile_col, safety_col = st.columns([1, 2])
    with profile_col:
        st.container(border=True).markdown(
            f"""
### Hồ sơ app

- **Tên:** {account['name']}
- **Email:** {account['email']}
- **Vai trò:** {account['role']}
"""
        )
        if st.button("Đăng xuất"):
            st.session_state["account"] = None
            st.session_state["auth_mode"] = None
            st.session_state.pop("facebook_oauth_state", None)
            st.rerun()

    with safety_col:
        st.warning(
            "Không nên làm kiểu app lưu mật khẩu/cookie Facebook rồi tự dùng nick cá nhân để vào group lấy dữ liệu. "
            "Bản này chỉ thiết kế hướng OAuth/API chính thức: người dùng consent, token có scope rõ ràng, "
            "và connector chỉ chạy với nguồn đã được cấp quyền."
        )
        st.markdown(
            f"Tham khảo hướng triển khai chính thức: [Facebook Login]({FACEBOOK_DOCS_URL}) và "
            f"[Meta Graph API]({FACEBOOK_GRAPH_DOCS_URL})."
        )

    st.markdown("## Liên kết nền tảng")
    facebook_config = get_facebook_oauth_config()
    facebook_connection = st.session_state["connections"]["facebook"]

    with st.container(border=True):
        st.markdown("### Facebook")
        st.caption(
            "Bấm nút bên dưới sẽ chuyển thẳng sang Facebook Login. Nếu trình duyệt đang đăng nhập "
            "Facebook, Facebook sẽ dùng phiên đó để hỏi quyền liên kết app."
        )

        config_cols = st.columns(4)
        config_cols[0].metric("App ID", "Đã có" if facebook_config["app_id"] else "Thiếu")
        config_cols[1].metric("App Secret", "Đã có" if facebook_config["app_secret"] else "Thiếu")
        config_cols[2].metric("Graph version", facebook_config["graph_version"])
        config_cols[3].metric("Trạng thái", facebook_connection["status"])

        st.code(
            "\n".join(
                [
                    f"FACEBOOK_REDIRECT_URI={facebook_config['redirect_uri']}",
                    f"FACEBOOK_SCOPES={facebook_config['scopes']}",
                ]
            ),
            language="text",
        )
        st.caption(
            "Trong Meta dashboard, Valid OAuth Redirect URI phải khớp y nguyên dòng "
            "`FACEBOOK_REDIRECT_URI` ở trên, bao gồm cả dấu `/` cuối."
        )

        if not facebook_config["app_id"]:
            st.markdown("**Chế độ không cấu hình App ID:** mở Facebook trong tab ngoài để đăng nhập thủ công.")
            st.link_button("Mở Facebook để đăng nhập ngoài", FACEBOOK_LOGIN_URL, use_container_width=True)
            st.link_button("Mở group Facebook đã cấu hình", DEFAULT_PUBLIC_GROUP_URL, use_container_width=True)
            st.warning(
                "Bạn có thể đăng nhập Facebook trong tab ngoài, nhưng Talent Radar không thể lấy token/quyền "
                "từ phiên đăng nhập đó nếu không có Facebook Login/OAuth App ID. Trình duyệt cố tình không cho "
                "website khác đọc cookie hoặc session của facebook.com."
            )
            st.info(
                "Vì vậy trạng thái connector vẫn là `Chưa liên kết`. Nút này hữu ích để người dùng mở Facebook "
                "và kiểm tra thủ công; chưa đủ để app tự thu thập dữ liệu."
            )
        else:
            auth_url = build_facebook_oauth_url(facebook_config)
            st.link_button("Đăng nhập / liên kết bằng Facebook", auth_url, use_container_width=True)

        if facebook_connection["profile"]:
            st.success(f"Facebook profile: {facebook_connection['profile']}")

        with st.expander("Facebook connector thật sẽ lấy dữ liệu như thế nào?"):
            st.write(
                "- App chỉ dùng access token được cấp qua OAuth/API chính thức.\n"
                "- Không lưu password, cookie, session cá nhân hoặc chạy browser automation để né login.\n"
                "- Với group Facebook, nếu API/permission không cho phép đọc posts thì connector phải báo `blocked`, "
                "không tự chuyển sang scrape bằng nick người dùng.\n"
                "- Khi chưa có quyền phù hợp, đường fallback đúng là CSV/JSON import hoặc nguồn export được cấp quyền."
            )

    platform_cols = st.columns(2)
    with platform_cols[0]:
        render_connector_card(
            "TikTok",
            st.session_state["connections"]["tiktok"]["status"],
            "UI placeholder. Sẽ nối TikTok API/OAuth khi xác nhận use case và quyền truy cập.",
            disabled=True,
        )
    with platform_cols[1]:
        render_connector_card(
            "Threads",
            st.session_state["connections"]["threads"]["status"],
            "UI placeholder. Sẽ nối Threads API/OAuth khi xác nhận tài khoản, scope và app review.",
            disabled=True,
        )


def render_public_crawler() -> None:
    st.subheader("Crawl thử nguồn công khai")
    st.caption(
        "Luồng này chỉ fetch HTML công khai bằng request thường. Không đăng nhập, không vượt CAPTCHA, "
        "không né giới hạn, không thu dữ liệu private. Nếu Facebook chỉ trả màn hình đăng nhập/chặn, "
        "đó là kết quả thật của lần thử."
    )

    url = st.text_input("Link group/public page", value=DEFAULT_PUBLIC_GROUP_URL)
    crawl_clicked = st.button("🚀 Crawl và tóm tắt kết quả thật", type="primary")

    if not crawl_clicked:
        st.info("Bấm nút crawl để kiểm tra nội dung public mà server hiện có thể đọc được.")
        return

    with st.spinner("Đang gọi URL công khai và tóm tắt nội dung trả về..."):
        result = crawl_public_url(url)

    if not result["ok"]:
        st.error(result["reason"])
        return

    meta = result["meta"]
    metric_cols = st.columns(5)
    metric_cols[0].metric("HTTP status", result["status_code"])
    metric_cols[1].metric("HTML bytes", f"{result['html_length']:,}")
    metric_cols[2].metric("Text chars", f"{result['text_length']:,}")
    metric_cols[3].metric("Post URL đọc được", result["post_url_count"])
    metric_cols[4].metric("Có vẻ bị chặn/login", "Có" if result["likely_blocked"] else "Không")

    if result["post_url_count"] == 0:
        st.error(
            "Kết luận test public: nút crawl đã gọi thật vào group, nhưng request không đăng nhập "
            "không đọc được bài viết nào trong group. Hiện chỉ đọc được metadata công khai của group."
        )
    else:
        st.success(f"Đọc được {result['post_url_count']} URL bài viết public từ HTML trả về.")

    st.markdown("**URL cuối cùng**")
    st.code(result["final_url"], language=None)

    if meta.get("title") or meta.get("og_title") or meta.get("description"):
        st.markdown("**Metadata đọc được**")
        st.json(meta)

    if result["likely_blocked"]:
        st.warning(
            "Facebook có thể không trả nội dung bài viết công khai cho request không đăng nhập. "
            "Bước MVP đúng hướng là dùng export/API/nguồn đã được cấp quyền, hoặc importer CSV/JSON."
        )

    st.markdown("**Tóm tắt trích xuất**")
    if result["summary"]:
        for sentence in result["summary"]:
            st.write(f"- {sentence}")
    else:
        st.write(
            "- Không có đủ câu có nghĩa để tóm tắt. Có thể trang chỉ trả shell HTML, login wall, "
            "hoặc nội dung render bằng JavaScript."
        )

    st.markdown("**Từ khóa nổi bật trong HTML/text trả về**")
    if result["keywords"]:
        keyword_frame = pd.DataFrame(result["keywords"], columns=["Từ khóa", "Tần suất"])
        st.dataframe(keyword_frame, use_container_width=True, hide_index=True)
    else:
        st.write("Không trích được từ khóa đáng kể.")

    with st.expander("Xem text preview đã trích xuất"):
        st.text(result["text_preview"] or "(Không có text preview)")


def render_crawler_shortcut() -> None:
    st.container(border=True).markdown(
        """
### ✅ Bản mới đã được load

Nếu bạn thấy khung này thì đang ở đúng dashboard mới. Chức năng crawl public nằm ngay bên dưới,
không cần tìm tab nữa.
"""
    )
    with st.container(border=True):
        st.markdown("### 🚀 Crawl nhanh link Facebook public")
        render_public_crawler()


def main() -> None:
    init_account_state()
    complete_facebook_login_if_present()
    data = load_mock_data()
    posts, sources, digests, reviews = prepare_frames(data)
    render_auth_controls()
    filtered = apply_sidebar_filters(posts)

    pages = [
        "Cài đặt",
        "Quét group & từ khóa",
        "Tổng quan",
        "Dòng nội dung VSF",
        "Tóm tắt ngày",
        "Hàng chờ rà soát",
        "Sức khỏe nguồn",
        "Crawl công khai",
    ]
    if st.session_state.get("nav_page") not in pages:
        st.session_state["nav_page"] = "Cài đặt"

    page = st.sidebar.radio(
        "Đi tới",
        pages,
        key="nav_page",
    )

    st.title("🎯 Talent Radar — Dashboard VSF-first")
    st.caption(
        "Prototype giao diện social listening cho VSF. Phần dữ liệu chính vẫn là mẫu; "
        "tab crawl công khai giúp thử một nguồn public theo cách tối giản và có kiểm soát."
    )

    generated_at = datetime.fromisoformat(data["generated_at"]).strftime("%d/%m/%Y %H:%M")
    st.info(
        f"Bộ dữ liệu mẫu tạo lúc {generated_at}. Không dùng cho báo cáo thật. "
        f"Phiên bản giao diện: `{APP_VERSION}`."
    )
    if st.session_state.get("facebook_login_success"):
        st.success(st.session_state.pop("facebook_login_success"))
    if st.session_state.get("facebook_login_error"):
        st.error(st.session_state.pop("facebook_login_error"))

    if page == "Cài đặt":
        render_account_settings()
    elif page == "Quét group & từ khóa":
        render_group_keyword_scanner()
    elif page == "Tổng quan":
        render_crawler_shortcut()
        render_overview(posts, filtered, sources)
    elif page == "Dòng nội dung VSF":
        render_feed(filtered)
    elif page == "Tóm tắt ngày":
        render_digest(digests, posts)
    elif page == "Hàng chờ rà soát":
        render_review_queue(reviews, posts)
    elif page == "Sức khỏe nguồn":
        render_source_health(sources)
    elif page == "Crawl công khai":
        render_public_crawler()


if __name__ == "__main__":
    main()
