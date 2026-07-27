from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen
from uuid import uuid4

from playwright.sync_api import Error as PlaywrightError, sync_playwright
from sqlalchemy import select
from sqlalchemy.orm import Session

from talent_radar.core.config import Settings
from talent_radar.models import PlatformConnection, User
from talent_radar.schemas import PlatformConnectionRead


PLATFORM_LOGIN_URLS = {
    "facebook": "https://www.facebook.com/",
    "tiktok": "https://www.tiktok.com/login",
    "threads": "https://www.threads.net/login",
}


class BrowserProfileError(ValueError):
    pass


@dataclass(frozen=True)
class CocCocProfile:
    user_data_dir: Path
    directory: str
    profile_name: str
    account_name: str | None


def connection_for_platform(
    db: Session,
    settings: Settings,
    user: User,
    platform: str,
) -> PlatformConnection:
    platform = platform.casefold()
    login_url = PLATFORM_LOGIN_URLS.get(platform)
    if login_url is None:
        raise BrowserProfileError(f"Nen tang khong duoc ho tro: {platform}")

    profile = selected_coccoc_profile(settings)
    connection = db.scalar(
        select(PlatformConnection).where(
            PlatformConnection.user_id == user.id,
            PlatformConnection.platform == platform,
        )
    )
    if connection is None:
        connection = PlatformConnection(
            id=f"connection_{uuid4().hex}",
            user_id=user.id,
            platform=platform,
            status="disconnected",
            auth_method=(
                "facebook_oauth"
                if platform == "facebook"
                else "existing_browser_profile"
            ),
            profile_dir=str(profile.user_data_dir),
            login_url=login_url,
            connection_metadata=_profile_metadata(profile),
        )
        db.add(connection)
    else:
        metadata = connection.connection_metadata or {}
        profile_changed = (
            Path(connection.profile_dir).resolve() != profile.user_data_dir
            or metadata.get("profile_directory") != profile.directory
        )
        connection.profile_dir = str(profile.user_data_dir)
        if platform != "facebook":
            connection.auth_method = "existing_browser_profile"
        connection.login_url = login_url
        connection.connection_metadata = {
            **metadata,
            **_profile_metadata(profile),
        }
        if profile_changed and connection.auth_method != "facebook_oauth":
            connection.status = "disconnected"
            connection.last_connected_at = None
            connection.last_checked_at = None
            connection.last_error = "Can xac minh lai tren dung profile Coc Coc."
            connection.browser_process_id = None
    db.commit()
    db.refresh(connection)
    return connection


def launch_coccoc_url(settings: Settings, url: str) -> int | None:
    selected_coccoc_profile(settings)
    _open_url_in_default_browser(url)
    return None


def launch_login_browser(
    db: Session,
    settings: Settings,
    connection: PlatformConnection,
) -> PlatformConnection:
    profile = selected_coccoc_profile(settings)
    target_url = (
        "https://www.facebook.com/me"
        if connection.platform == "facebook"
        else connection.login_url
    )
    _open_url_in_default_browser(target_url)

    connection.status = "pending_login"
    connection.browser_process_id = None
    connection.last_error = None
    connection.connection_metadata = {
        **(connection.connection_metadata or {}),
        **_profile_metadata(profile),
        "login_verified": False,
        "login_check": "default_browser_profile",
    }
    db.commit()
    db.refresh(connection)
    return connection


def ensure_controlled_coccoc(
    settings: Settings,
    initial_url: str,
) -> tuple[int, int | None]:
    selected_coccoc_profile(settings)
    debug_port = settings.coccoc_remote_debugging_port

    if _debug_port_available(debug_port):
        _open_url_in_controlled_browser(debug_port, initial_url)
        return debug_port, None
    raise BrowserProfileError(
        "Coc Coc mac dinh chua co kenh collector noi bo. "
        "Talent Radar se khong tu mo profile hoac user moi."
    )


def verify_platform_login(
    settings: Settings,
    connection: PlatformConnection,
) -> bool:
    if connection.platform != "facebook":
        raise BrowserProfileError(
            f"Chua co bo kiem tra dang nhap cho {connection.platform}."
        )
    debug_port = (connection.connection_metadata or {}).get("debug_port")
    if not isinstance(debug_port, int) or not _debug_port_available(debug_port):
        raise BrowserProfileError(
            "Khong con ket noi voi cua so Coc Coc vua mo. "
            "Hay bam Lien ket lai, dang nhap va giu cua so mo khi bam Xac nhan."
        )

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(
                f"http://127.0.0.1:{debug_port}"
            )
            if not browser.contexts:
                return False
            page = browser.contexts[0].new_page()
            try:
                page.goto(
                    "https://www.facebook.com/me",
                    wait_until="domcontentloaded",
                    timeout=30_000,
                )
                page.wait_for_timeout(1500)
                current_url = page.url.casefold()
                login_fields = page.locator(
                    "input[name='email'], input[name='pass'], form[action*='login']"
                )
                has_visible_login = any(
                    login_fields.nth(index).is_visible()
                    for index in range(login_fields.count())
                )
                blocked = "/login" in current_url or "/checkpoint" in current_url
                has_logged_in_navigation = page.locator(
                    "[role='navigation'], [aria-label='Facebook'], "
                    "[aria-label*='Trang cá nhân'], [aria-label*='profile']"
                ).count() > 0
                return not blocked and not has_visible_login and has_logged_in_navigation
            finally:
                page.close()
    except PlaywrightError as exc:
        raise BrowserProfileError(
            "Khong the kiem tra phien Facebook tren profile Huy."
        ) from exc


def connection_read(connection: PlatformConnection) -> PlatformConnectionRead:
    metadata = connection.connection_metadata or {}
    return PlatformConnectionRead(
        id=connection.id,
        platform=connection.platform,
        status=connection.status,
        auth_method=connection.auth_method,
        last_connected_at=connection.last_connected_at,
        last_checked_at=connection.last_checked_at,
        last_error=connection.last_error,
        profile_directory=metadata.get("profile_directory"),
        profile_name=metadata.get("profile_name"),
        profile_account_name=metadata.get("profile_account_name"),
        connected_account_id=metadata.get("facebook_user_id"),
        connected_account_name=metadata.get("facebook_user_name"),
    )


def selected_coccoc_profile(settings: Settings) -> CocCocProfile:
    user_data_dir = settings.coccoc_user_data_directory.resolve()
    directory = settings.coccoc_profile_directory.strip()
    if not user_data_dir.is_dir():
        raise BrowserProfileError(f"Khong tim thay Coc Coc User Data tai {user_data_dir}")
    if not directory or Path(directory).name != directory:
        raise BrowserProfileError("COCCOC_PROFILE_DIRECTORY khong hop le.")
    profile_dir = user_data_dir / directory
    preferences_path = profile_dir / "Preferences"
    if not preferences_path.is_file():
        raise BrowserProfileError(f"Khong tim thay profile Coc Coc {directory}.")
    try:
        preferences = json.loads(preferences_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BrowserProfileError("Khong doc duoc metadata profile Coc Coc.") from exc

    account_info = preferences.get("account_info") or []
    account_name = next(
        (
            item.get("full_name")
            for item in account_info
            if isinstance(item, dict) and item.get("full_name")
        ),
        None,
    )
    profile_name = preferences.get("profile", {}).get("name") or directory
    expected_account_name = settings.coccoc_profile_account_name.strip()
    if (
        expected_account_name
        and account_name
        and account_name.casefold() != expected_account_name.casefold()
    ):
        raise BrowserProfileError(
            f"Profile {directory} khong thuoc tai khoan {expected_account_name}."
        )
    return CocCocProfile(
        user_data_dir=user_data_dir,
        directory=directory,
        profile_name=profile_name,
        account_name=account_name,
    )


def _open_url_in_default_browser(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise BrowserProfileError("URL mo trong trinh duyet khong hop le.")
    startfile = getattr(os, "startfile", None)
    if startfile is None:
        raise BrowserProfileError(
            "Chi ho tro mo trinh duyet mac dinh tren Windows."
        )
    try:
        startfile(url)
    except OSError as exc:
        raise BrowserProfileError(
            "Khong mo duoc URL trong trinh duyet mac dinh cua Windows."
        ) from exc


def _open_url_in_controlled_browser(port: int, url: str) -> None:
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(
                f"http://127.0.0.1:{port}"
            )
            if not browser.contexts:
                raise BrowserProfileError("Coc Coc khong co browser context.")
            browser.contexts[0].new_page().goto(
                url,
                wait_until="domcontentloaded",
                timeout=30_000,
            )
    except PlaywrightError as exc:
        raise BrowserProfileError(
            "Khong mo duoc tab moi trong Coc Coc cua Talent Radar."
        ) from exc


def _profile_metadata(profile: CocCocProfile) -> dict:
    return {
        "profile_source": "existing_coccoc",
        "profile_directory": profile.directory,
        "profile_name": profile.profile_name,
        "profile_account_name": profile.account_name,
    }


def _debug_port_available(port: int) -> bool:
    try:
        with urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1) as response:
            return response.status == 200
    except (OSError, URLError):
        return False
