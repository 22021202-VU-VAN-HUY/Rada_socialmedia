from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st

from talent_radar.core.config import get_settings


settings = get_settings()
API_URL = settings.backend_url.rstrip("/")
EXPORT_DIR = settings.crawl_output_directory
PLATFORM_LABELS = {
    "facebook": "Facebook",
    "threads": "Threads",
    "tiktok": "TikTok",
}
STATUS_LABELS = {
    "disconnected": "Chua ket noi",
    "pending_login": "Cho xac nhan",
    "connected": "Da ket noi",
    "reauth_required": "Can dang nhap lai",
    "error": "Co loi",
}

st.set_page_config(
    page_title="Talent Radar",
    page_icon=":material/radar:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background: #f7f8fa; color: #1c2530; }
    [data-testid="stSidebar"] { background: #17212b; }
    [data-testid="stSidebar"] * { color: #f5f7f9; }
    [data-testid="stMetric"] {
        background: #ffffff; border: 1px solid #dfe4ea; border-radius: 6px; padding: 14px;
    }
    .block-container { max-width: 1440px; padding-top: 1.5rem; }
    h1, h2, h3 { letter-spacing: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)


class ApiError(RuntimeError):
    pass


def api_request(method: str, path: str, *, auth: bool = True, **kwargs: Any) -> Any:
    headers = kwargs.pop("headers", {})
    token = st.session_state.get("access_token")
    if auth and token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(
            method,
            f"{API_URL}{path}",
            headers=headers,
            timeout=20,
            **kwargs,
        )
    except requests.RequestException as exc:
        raise ApiError(f"Khong ket noi duoc API tai {API_URL}.") from exc
    if response.status_code == 401 and auth:
        st.session_state.pop("access_token", None)
        st.session_state.pop("user", None)
        raise ApiError("Phien dang nhap da het han.")
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise ApiError(str(detail))
    if response.status_code == 204:
        return None
    return response.json()


@st.cache_data(show_spinner=False)
def load_export(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def export_files() -> list[Path]:
    patterns = ("facebook_coccoc_*.json", "facebook_playwright_*.json")
    files = {path for pattern in patterns for path in EXPORT_DIR.glob(pattern)}
    return sorted(files, reverse=True)


def post_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in payload.get("posts", []):
        post = item.get("post", {})
        rows.append(
            {
                "post_id": post.get("external_id"),
                "author": post.get("author"),
                "group": post.get("group"),
                "content": post.get("content"),
                "reactions": post.get("reaction_count", 0),
                "comments": post.get("collected_comment_count", 0),
                "permalink": post.get("url"),
                "collected_at": item.get("collected_at"),
            }
        )
    return rows


def comment_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for item in payload.get("posts", []):
        post = item.get("post", {})
        for comment in item.get("comments", []):
            rows.append(
                {
                    "comment_id": comment.get("external_id"),
                    "parent_comment_id": comment.get("parent_external_id"),
                    "post_id": post.get("external_id"),
                    "author": comment.get("author"),
                    "published": comment.get("published_label"),
                    "content": comment.get("content"),
                    "is_reply": bool(comment.get("is_reply")),
                    "permalink": comment.get("permalink"),
                }
            )
    return rows


def render_auth() -> None:
    left, center, right = st.columns([1, 1.1, 1])
    with center:
        st.title("Talent Radar")
        st.caption("Dang nhap de quan ly ket noi va lich thu thap.")
        mode = st.segmented_control(
            "Tai khoan",
            ["Dang nhap", "Tao tai khoan"],
            default="Dang nhap",
            label_visibility="collapsed",
        )
        with st.form("auth_form"):
            email = st.text_input("Email", placeholder="huy@example.com")
            password = st.text_input("Mat khau", type="password")
            submitted = st.form_submit_button(
                "Dang nhap" if mode == "Dang nhap" else "Tao tai khoan",
                type="primary",
                width="stretch",
            )
        if submitted:
            endpoint = "/auth/login" if mode == "Dang nhap" else "/auth/register"
            try:
                result = api_request(
                    "POST",
                    endpoint,
                    auth=False,
                    json={"email": email, "password": password},
                )
                st.session_state.access_token = result["access_token"]
                st.session_state.user = result["user"]
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))


def selected_export() -> tuple[dict[str, Any] | None, Path | None]:
    files = export_files()
    if not files:
        return None, None
    selected = st.selectbox(
        "Lan thu thap",
        files,
        format_func=lambda path: path.stem,
        label_visibility="collapsed",
    )
    return load_export(selected), selected


def render_overview() -> None:
    st.title("Tong quan")
    try:
        jobs = api_request("GET", "/jobs")
        schedules = api_request("GET", "/schedules")
        connections = api_request("GET", "/connections")
    except ApiError as exc:
        st.error(str(exc))
        return
    payload, _ = selected_export()
    posts = post_rows(payload or {})
    comments = comment_rows(payload or {})
    metrics = st.columns(4)
    metrics[0].metric("Bai viet", len(posts))
    metrics[1].metric("Binh luan", len(comments))
    metrics[2].metric("Lich dang bat", sum(1 for item in schedules if item["enabled"]))
    metrics[3].metric(
        "Ket noi",
        sum(1 for item in connections if item["status"] == "connected"),
    )
    st.subheader("Hoat dong gan day")
    if jobs:
        st.dataframe(
            pd.DataFrame(jobs)[
                [
                    "status",
                    "trigger",
                    "source_id",
                    "posts_collected",
                    "comments_collected",
                    "created_at",
                    "error_summary",
                ]
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("Chua co job thu thap.")


def render_data(view: str) -> None:
    st.title("Bai viet" if view == "Posts" else "Binh luan")
    payload, _ = selected_export()
    if payload is None:
        st.info("Chua co export Facebook trong data/exports.")
        return
    rows = post_rows(payload) if view == "Posts" else comment_rows(payload)
    if not rows:
        st.info("Lan thu thap nay khong co du lieu.")
        return
    frame = pd.DataFrame(rows)
    if view == "Comments":
        post_ids = ["Tat ca"] + sorted(frame["post_id"].dropna().unique().tolist())
        selected_post = st.selectbox("Bai viet", post_ids)
        if selected_post != "Tat ca":
            frame = frame[frame["post_id"] == selected_post]
    st.dataframe(
        frame,
        width="stretch",
        hide_index=True,
        column_config={
            "permalink": st.column_config.LinkColumn("permalink"),
            "content": st.column_config.TextColumn("content", width="large"),
        },
    )


def render_runs() -> None:
    st.title("Lan thu thap")
    try:
        jobs = api_request("GET", "/jobs")
    except ApiError as exc:
        st.error(str(exc))
        return
    if not jobs:
        st.info("Chua co job nao.")
        return
    st.dataframe(
        pd.DataFrame(jobs),
        width="stretch",
        hide_index=True,
        column_config={"output_path": st.column_config.TextColumn("output_path", width="large")},
    )


def platform_actions(connection: dict[str, Any]) -> None:
    platform = connection["platform"]
    status = connection["status"]
    label = PLATFORM_LABELS.get(platform, platform.title())
    with st.container(border=True):
        info, action = st.columns([3, 2], vertical_alignment="center")
        with info:
            st.subheader(label)
            st.caption(STATUS_LABELS.get(status, status))
            if connection.get("profile_account_name"):
                st.caption(
                    f"Coc Coc: {connection['profile_account_name']} "
                    f"({connection.get('profile_directory')})"
                )
            if connection.get("last_error"):
                st.error(connection["last_error"])
            if platform != "facebook":
                st.caption("Collector bai viet/comment chua co trong ban nay.")
        with action:
            if status in {"disconnected", "reauth_required", "error"}:
                if st.button(
                    "Lien ket",
                    key=f"connect_{platform}",
                    icon=":material/open_in_new:",
                    width="stretch",
                ):
                    run_connection_action(platform, "connect")
            elif status == "pending_login":
                if st.button(
                    "Xac nhan",
                    key=f"confirm_{platform}",
                    type="primary",
                    icon=":material/check:",
                    width="stretch",
                ):
                    run_connection_action(platform, "confirm")
            if status in {"connected", "pending_login"}:
                if st.button(
                    "Ngat ket noi",
                    key=f"disconnect_{platform}",
                    icon=":material/link_off:",
                    width="stretch",
                ):
                    run_connection_action(platform, "disconnect")


def run_connection_action(platform: str, action: str) -> None:
    try:
        result = api_request("POST", f"/connections/{platform}/{action}")
        st.toast(result["message"])
        st.rerun()
    except ApiError as exc:
        st.error(str(exc))


def render_schedule_form(
    connections: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> None:
    facebook_connections = [
        item for item in connections if item["platform"] == "facebook" and item["status"] == "connected"
    ]
    facebook_sources = [item for item in sources if item["platform"] == "facebook"]
    if not facebook_connections:
        st.info("Lien ket Facebook truoc khi tao lich.")
        return
    if not facebook_sources:
        st.info("Chua co Facebook source. Chay sync source registry truoc.")
        return
    with st.form("new_schedule"):
        source_id = st.selectbox(
            "Nguon",
            [item["id"] for item in facebook_sources],
            format_func=lambda item_id: next(
                item["source_name"] for item in facebook_sources if item["id"] == item_id
            ),
        )
        interval = st.number_input("Lap lai (phut)", min_value=5, max_value=10080, value=60)
        max_posts = st.number_input("So bai toi da", min_value=1, max_value=200, value=5)
        enabled = st.toggle("Bat lich ngay", value=True)
        submitted = st.form_submit_button(
            "Tao lich",
            type="primary",
            icon=":material/add:",
        )
    if submitted:
        try:
            api_request(
                "POST",
                "/schedules",
                json={
                    "connection_id": facebook_connections[0]["id"],
                    "source_id": source_id,
                    "interval_minutes": interval,
                    "max_posts": max_posts,
                    "enabled": enabled,
                },
            )
            st.toast("Da tao lich thu thap.")
            st.rerun()
        except ApiError as exc:
            st.error(str(exc))


def render_schedules(schedules: list[dict[str, Any]]) -> None:
    if not schedules:
        st.caption("Chua co lich.")
        return
    for schedule in schedules:
        with st.container(border=True):
            info, controls = st.columns([4, 3], vertical_alignment="center")
            with info:
                st.write(f"**{schedule['source_id']}**")
                state = "Dang bat" if schedule["enabled"] else "Da tat"
                st.caption(
                    f"{state} | {schedule['interval_minutes']} phut | "
                    f"toi da {schedule['max_posts']} bai | {schedule['last_status']}"
                )
                if schedule.get("last_error"):
                    st.error(schedule["last_error"])
            with controls:
                cols = st.columns(3)
                toggle_label = "Tat" if schedule["enabled"] else "Bat"
                if cols[0].button(
                    toggle_label,
                    key=f"toggle_{schedule['id']}",
                    icon=":material/power_settings_new:",
                    width="stretch",
                ):
                    update_schedule_state(schedule["id"], not schedule["enabled"])
                if cols[1].button(
                    "Chay",
                    key=f"run_{schedule['id']}",
                    icon=":material/play_arrow:",
                    width="stretch",
                ):
                    run_schedule(schedule["id"])
                if cols[2].button(
                    "Xoa",
                    key=f"delete_{schedule['id']}",
                    icon=":material/delete:",
                    width="stretch",
                ):
                    delete_schedule(schedule["id"])


def update_schedule_state(schedule_id: str, enabled: bool) -> None:
    try:
        api_request("PATCH", f"/schedules/{schedule_id}", json={"enabled": enabled})
        st.rerun()
    except ApiError as exc:
        st.error(str(exc))


def run_schedule(schedule_id: str) -> None:
    try:
        api_request("POST", f"/schedules/{schedule_id}/run-now")
        st.toast("Job da vao hang doi.")
        st.rerun()
    except ApiError as exc:
        st.error(str(exc))


def delete_schedule(schedule_id: str) -> None:
    try:
        api_request("DELETE", f"/schedules/{schedule_id}")
        st.rerun()
    except ApiError as exc:
        st.error(str(exc))


def render_settings() -> None:
    st.title("Cai dat")
    try:
        connections = api_request("GET", "/connections")
        schedules = api_request("GET", "/schedules")
        sources = api_request("GET", "/sources")
    except ApiError as exc:
        st.error(str(exc))
        return
    st.subheader("Nen tang")
    st.caption(
        "Mo app bang Open Talent Radar.cmd de localhost va Facebook dung chung Coc Coc "
        "Huy (Default). Co the giu trinh duyet mo khi Lien ket va chay collector."
    )
    for connection in connections:
        platform_actions(connection)
    st.divider()
    schedule_column, list_column = st.columns([2, 3])
    with schedule_column:
        st.subheader("Tao lich")
        render_schedule_form(connections, sources)
    with list_column:
        st.subheader("Lich dang co")
        render_schedules(schedules)


def main() -> None:
    if not st.session_state.get("access_token"):
        render_auth()
        return
    try:
        user = api_request("GET", "/auth/me")
    except ApiError as exc:
        st.warning(str(exc))
        render_auth()
        return

    st.sidebar.title("Talent Radar")
    st.sidebar.caption(user["email"])
    page = st.sidebar.radio(
        "Dieu huong",
        ["Overview", "Posts", "Comments", "Runs", "Settings"],
        format_func={
            "Overview": "Tong quan",
            "Posts": "Bai viet",
            "Comments": "Binh luan",
            "Runs": "Lan thu thap",
            "Settings": "Cai dat",
        }.get,
        label_visibility="collapsed",
    )
    if st.sidebar.button(
        "Dang xuat",
        icon=":material/logout:",
        width="stretch",
    ):
        try:
            api_request("POST", "/auth/logout")
        except ApiError:
            pass
        st.session_state.clear()
        st.rerun()

    if page == "Overview":
        render_overview()
    elif page in {"Posts", "Comments"}:
        render_data(page)
    elif page == "Runs":
        render_runs()
    else:
        render_settings()


if __name__ == "__main__":
    main()
