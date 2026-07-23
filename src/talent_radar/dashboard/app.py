from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


EXPORT_DIR = Path("data/exports")

st.set_page_config(
    page_title="Talent Radar | Facebook Collector",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def load_export(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def export_files() -> list[Path]:
    return sorted(EXPORT_DIR.glob("facebook_coccoc_*.json"), reverse=True)


def post_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in payload.get("posts", []):
        post = item.get("post", {})
        rows.append(
            {
                "post_id": post.get("external_id"),
                "author": post.get("author"),
                "group": post.get("group"),
                "content": post.get("content"),
                "reactions": post.get("reaction_count", 0),
                "comments_reported": post.get("reported_comment_count", 0),
                "comments_collected": post.get("collected_comment_count", 0),
                "permalink": post.get("url"),
                "collected_at": item.get("collected_at"),
            }
        )
    return rows


def comment_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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
                    "parent_author": comment.get("parent_author"),
                    "permalink": comment.get("permalink"),
                }
            )
    return rows


def render_empty_state() -> None:
    st.header("Talent Radar")
    st.info("Chua co file crawl Facebook trong data/exports.")


def main() -> None:
    files = export_files()
    if not files:
        render_empty_state()
        return

    selected = st.sidebar.selectbox(
        "Lan crawl",
        options=files,
        format_func=lambda path: path.stem.replace("facebook_coccoc_", ""),
    )
    payload = load_export(selected)
    posts = pd.DataFrame(post_rows(payload))
    comments = pd.DataFrame(comment_rows(payload))

    st.header("Talent Radar")
    st.caption("Facebook posts and comments collected from the Coc Coc session")

    metrics_top = st.columns(2)
    metrics_bottom = st.columns(2)
    metrics_top[0].metric("Bai viet", len(posts))
    metrics_top[1].metric("Binh luan", len(comments))
    metrics_bottom[0].metric(
        "Phan hoi",
        int(comments["is_reply"].sum()) if not comments.empty else 0,
    )
    metrics_bottom[1].metric(
        "Luot tuong tac",
        int(posts["reactions"].fillna(0).sum()) if not posts.empty else 0,
    )

    posts_tab, comments_tab, run_tab = st.tabs(["Bai viet", "Binh luan", "Lan crawl"])
    with posts_tab:
        st.dataframe(
            posts,
            width="stretch",
            hide_index=True,
            column_config={
                "permalink": st.column_config.LinkColumn("permalink"),
                "content": st.column_config.TextColumn("content", width="large"),
            },
        )

    with comments_tab:
        post_ids = ["Tat ca"] + sorted(comments["post_id"].dropna().unique().tolist())
        selected_post = st.selectbox("Post ID", post_ids)
        visible = comments if selected_post == "Tat ca" else comments[comments["post_id"] == selected_post]
        st.dataframe(
            visible,
            width="stretch",
            hide_index=True,
            column_config={
                "permalink": st.column_config.LinkColumn("permalink"),
                "content": st.column_config.TextColumn("content", width="large"),
            },
        )

    with run_tab:
        st.json(
            {
                "crawler": payload.get("crawler"),
                "collected_at": payload.get("collected_at"),
                "source_group_url": payload.get("source_group_url"),
                "source_post_url": payload.get("source_post_url"),
                "json_file": str(selected),
                "post_count": len(posts),
                "comment_count": len(comments),
            }
        )


if __name__ == "__main__":
    main()
