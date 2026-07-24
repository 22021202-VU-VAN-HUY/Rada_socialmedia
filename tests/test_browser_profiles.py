import json
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import Session

from talent_radar.core.config import Settings
from talent_radar.models import PlatformConnection
from talent_radar.services.browser_profiles import (
    BrowserProfileError,
    launch_login_browser,
    selected_coccoc_profile,
    verify_platform_login,
)


def fake_coccoc_settings(tmp_path: Path) -> Settings:
    executable = tmp_path / "browser.exe"
    executable.touch()
    user_data = tmp_path / "User Data"
    profile = user_data / "Default"
    profile.mkdir(parents=True)
    (profile / "Preferences").write_text(
        json.dumps(
            {
                "profile": {"name": "Ca nhan 1"},
                "account_info": [{"full_name": "Vu Van Huy"}],
            }
        ),
        encoding="utf-8",
    )
    return Settings(
        _env_file=None,
        coccoc_executable_path=executable,
        coccoc_user_data_directory=user_data,
        coccoc_control_user_data_directory=user_data,
        coccoc_profile_directory="Default",
        coccoc_profile_account_name="Vu Van Huy",
    )


def test_selected_profile_resolves_huy_account(tmp_path: Path) -> None:
    profile = selected_coccoc_profile(fake_coccoc_settings(tmp_path))

    assert profile.directory == "Default"
    assert profile.profile_name == "Ca nhan 1"
    assert profile.account_name == "Vu Van Huy"


def test_login_browser_uses_existing_huy_profile(
    db: Session,
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = fake_coccoc_settings(tmp_path)
    connection = PlatformConnection(
        id="connection_test",
        user_id="user_123",
        platform="facebook",
        status="disconnected",
        profile_dir=str(settings.coccoc_user_data_directory),
        login_url="https://www.facebook.com/",
        connection_metadata={"profile_directory": "Default"},
    )
    db.add(connection)
    db.commit()
    process = Mock(pid=4321)
    popen = Mock(return_value=process)
    monkeypatch.setattr("talent_radar.services.browser_profiles.subprocess.Popen", popen)
    monkeypatch.setattr(
        "talent_radar.services.browser_profiles.coccoc_is_running",
        lambda: False,
    )
    monkeypatch.setattr(
        "talent_radar.services.browser_profiles._debug_port_available",
        lambda _port: False,
    )
    monkeypatch.setattr(
        "talent_radar.services.browser_profiles._wait_for_debug_port",
        lambda _port: True,
    )

    updated = launch_login_browser(db, settings, connection)

    arguments = popen.call_args.args[0]
    assert f"--user-data-dir={settings.coccoc_user_data_directory.resolve()}" in arguments
    assert "--profile-directory=Default" in arguments
    assert "https://www.facebook.com/" in arguments
    assert updated.status == "pending_login"
    assert updated.connection_metadata["debug_port"] == 9223


def test_login_browser_reuses_controlled_coccoc(
    db: Session,
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = fake_coccoc_settings(tmp_path)
    connection = PlatformConnection(
        id="connection_reuse",
        user_id="user_123",
        platform="facebook",
        status="disconnected",
        profile_dir=str(settings.coccoc_user_data_directory),
        login_url="https://www.facebook.com/",
        connection_metadata={"profile_directory": "Default"},
    )
    db.add(connection)
    db.commit()
    open_url = Mock()
    popen = Mock()
    monkeypatch.setattr(
        "talent_radar.services.browser_profiles._debug_port_available",
        lambda port: port == 9223,
    )
    monkeypatch.setattr(
        "talent_radar.services.browser_profiles._open_url_in_controlled_browser",
        open_url,
    )
    monkeypatch.setattr("talent_radar.services.browser_profiles.subprocess.Popen", popen)

    updated = launch_login_browser(db, settings, connection)

    open_url.assert_called_once_with(9223, "https://www.facebook.com/")
    popen.assert_not_called()
    assert updated.status == "pending_login"
    assert updated.connection_metadata["debug_port"] == 9223


def test_login_browser_rejects_uncontrolled_coccoc(
    db: Session,
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings = fake_coccoc_settings(tmp_path)
    connection = PlatformConnection(
        id="connection_uncontrolled",
        user_id="user_123",
        platform="facebook",
        status="disconnected",
        profile_dir=str(settings.coccoc_user_data_directory),
        login_url="https://www.facebook.com/",
        connection_metadata={"profile_directory": "Default"},
    )
    db.add(connection)
    db.commit()
    monkeypatch.setattr(
        "talent_radar.services.browser_profiles._debug_port_available",
        lambda _port: False,
    )
    monkeypatch.setattr(
        "talent_radar.services.browser_profiles.coccoc_is_running",
        lambda: True,
    )

    with pytest.raises(BrowserProfileError, match="ngoai che do Talent Radar"):
        launch_login_browser(db, settings, connection)


class FakeLocator:
    def __init__(self, *, count: int, visible: bool = False) -> None:
        self._count = count
        self._visible = visible

    def count(self) -> int:
        return self._count

    def nth(self, _index: int):
        return self

    def is_visible(self) -> bool:
        return self._visible


class FakePage:
    def __init__(self, *, logged_in: bool) -> None:
        self.logged_in = logged_in
        self.url = "https://www.facebook.com/profile.php?id=123" if logged_in else (
            "https://www.facebook.com/login/?next=%2Fme"
        )

    def goto(self, *_args, **_kwargs) -> None:
        return None

    def wait_for_timeout(self, _milliseconds: int) -> None:
        return None

    def locator(self, selector: str) -> FakeLocator:
        if "input[name='email']" in selector:
            return FakeLocator(count=0 if self.logged_in else 1, visible=not self.logged_in)
        return FakeLocator(count=1 if self.logged_in else 0)

    def close(self) -> None:
        return None


def fake_playwright(logged_in: bool):
    page = FakePage(logged_in=logged_in)
    context = Mock()
    context.new_page.return_value = page
    browser = Mock(contexts=[context])
    chromium = Mock()
    chromium.connect_over_cdp.return_value = browser
    playwright = Mock(chromium=chromium)
    return nullcontext(playwright)


def verify_connection(tmp_path: Path) -> tuple[Settings, PlatformConnection]:
    settings = fake_coccoc_settings(tmp_path)
    connection = PlatformConnection(
        id="connection_test",
        user_id="user_123",
        platform="facebook",
        status="pending_login",
        profile_dir=str(settings.coccoc_user_data_directory),
        login_url="https://www.facebook.com/",
        connection_metadata={"profile_directory": "Default", "debug_port": 9222},
    )
    return settings, connection


def test_confirmation_rejects_visible_facebook_login(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings, connection = verify_connection(tmp_path)
    monkeypatch.setattr(
        "talent_radar.services.browser_profiles._debug_port_available",
        lambda _port: True,
    )
    monkeypatch.setattr(
        "talent_radar.services.browser_profiles.sync_playwright",
        lambda: fake_playwright(logged_in=False),
    )

    assert verify_platform_login(settings, connection) is False


def test_confirmation_accepts_authenticated_facebook_profile(
    tmp_path: Path,
    monkeypatch,
) -> None:
    settings, connection = verify_connection(tmp_path)
    monkeypatch.setattr(
        "talent_radar.services.browser_profiles._debug_port_available",
        lambda _port: True,
    )
    monkeypatch.setattr(
        "talent_radar.services.browser_profiles.sync_playwright",
        lambda: fake_playwright(logged_in=True),
    )

    assert verify_platform_login(settings, connection) is True
