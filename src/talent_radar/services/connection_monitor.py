from __future__ import annotations

import logging
import threading
import time
from datetime import UTC, datetime
from urllib.parse import urlsplit

from talent_radar.core.database import SessionLocal
from talent_radar.models import PlatformConnection


logger = logging.getLogger(__name__)
_threads: dict[str, threading.Thread] = {}
_threads_lock = threading.Lock()


def start_connection_monitor(
    connection_id: str,
    *,
    timeout_seconds: int = 600,
    poll_seconds: float = 0.5,
) -> None:
    with _threads_lock:
        current = _threads.get(connection_id)
        if current is not None and current.is_alive():
            return
        thread = threading.Thread(
            target=_monitor_facebook_connection,
            args=(connection_id, timeout_seconds, poll_seconds),
            name=f"connection-monitor-{connection_id[-8:]}",
            daemon=True,
        )
        _threads[connection_id] = thread
        thread.start()


def facebook_login_visible() -> bool:
    return any(_is_authenticated_facebook_url(url) for url in active_coccoc_urls())


def active_coccoc_urls() -> list[str]:
    try:
        import pythoncom
        import win32gui
        from pywinauto import Desktop
    except ImportError:
        return []

    urls: list[str] = []
    pythoncom.CoInitialize()
    try:
        handle = win32gui.GetForegroundWindow()
        window = Desktop(backend="uia").window(handle=handle)
        for edit in window.descendants(control_type="Edit"):
            if edit.element_info.automation_id != "view_1012":
                continue
            value = edit.get_value().strip()
            if value:
                urls.append(_normalize_address_bar_url(value))
    except Exception:
        return []
    finally:
        pythoncom.CoUninitialize()
    return urls


def _monitor_facebook_connection(
    connection_id: str,
    timeout_seconds: int,
    poll_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    try:
        while time.monotonic() < deadline:
            urls = active_coccoc_urls()
            if any(_is_authenticated_facebook_url(url) for url in urls):
                _set_connected(connection_id)
                return
            if any(_is_checkpoint_url(url) for url in urls):
                _set_connection_error(
                    connection_id,
                    "reauth_required",
                    "Facebook dang yeu cau checkpoint hoac xac minh bo sung.",
                )
                return
            time.sleep(poll_seconds)
        _set_connection_error(
            connection_id,
            "pending_login",
            "Chua xac nhan duoc dang nhap Facebook. Bam Lien ket de mo lai tab.",
        )
    except Exception:
        logger.exception("Facebook connection monitor failed")
        _set_connection_error(
            connection_id,
            "error",
            "Khong theo doi duoc trang thai tab Facebook trong Coc Coc.",
        )
    finally:
        with _threads_lock:
            _threads.pop(connection_id, None)


def _set_connected(connection_id: str) -> None:
    now = datetime.now(UTC)
    with SessionLocal() as db:
        connection = db.get(PlatformConnection, connection_id)
        if connection is None or connection.status == "disconnected":
            return
        connection.status = "connected"
        connection.last_connected_at = now
        connection.last_checked_at = now
        connection.last_error = None
        connection.connection_metadata = {
            **(connection.connection_metadata or {}),
            "login_verified": True,
            "login_verified_at": now.isoformat(),
            "login_check": "coccoc_address_bar",
        }
        db.commit()


def _set_connection_error(connection_id: str, status: str, message: str) -> None:
    with SessionLocal() as db:
        connection = db.get(PlatformConnection, connection_id)
        if connection is None or connection.status == "disconnected":
            return
        connection.status = status
        connection.last_checked_at = datetime.now(UTC)
        connection.last_error = message
        db.commit()


def _normalize_address_bar_url(value: str) -> str:
    value = value.strip()
    if "://" not in value:
        value = "https://" + value
    return value


def _is_authenticated_facebook_url(url: str) -> bool:
    parts = urlsplit(url)
    host = (parts.hostname or "").casefold()
    path = parts.path.rstrip("/").casefold()
    if host not in {"facebook.com", "www.facebook.com", "m.facebook.com"}:
        return False
    blocked_paths = {
        "",
        "/",
        "/login",
        "/me",
        "/checkpoint",
        "/recover",
        "/reg",
    }
    return path not in blocked_paths and not any(
        marker in path for marker in ("/login/", "/checkpoint/", "/recover/")
    )


def _is_checkpoint_url(url: str) -> bool:
    parts = urlsplit(url)
    host = (parts.hostname or "").casefold()
    path = parts.path.casefold()
    return host.endswith("facebook.com") and "/checkpoint" in path
