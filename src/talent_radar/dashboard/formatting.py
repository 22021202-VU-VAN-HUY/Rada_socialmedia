from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def relative_published(post: dict[str, Any], reference: datetime) -> str | None:
    raw = post.get("published_at")
    if not isinstance(raw, str) or not raw:
        return post.get("published_label")
    try:
        published = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return post.get("published_label")
    if published.tzinfo is None:
        published = published.replace(tzinfo=UTC)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    seconds = max(
        0,
        int(
            (
                reference.astimezone(UTC)
                - published.astimezone(UTC)
            ).total_seconds()
        ),
    )
    if seconds < 60:
        return "V\u1eeba xong"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} ph\u00fat"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} gi\u1edd"
    return f"{hours // 24} ng\u00e0y"
