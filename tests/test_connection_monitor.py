from unittest.mock import Mock

from talent_radar.services import connection_monitor


def test_facebook_url_classifier_rejects_login_and_checkpoint() -> None:
    assert connection_monitor._is_authenticated_facebook_url(
        "https://www.facebook.com/login/?next=%2Fme"
    ) is False
    assert connection_monitor._is_authenticated_facebook_url(
        "https://www.facebook.com/checkpoint/123/"
    ) is False
    assert connection_monitor._is_authenticated_facebook_url(
        "https://www.facebook.com/me"
    ) is False


def test_facebook_url_classifier_accepts_profile_redirect() -> None:
    assert connection_monitor._is_authenticated_facebook_url(
        "https://www.facebook.com/profile.php?id=123"
    ) is True
    assert connection_monitor._is_authenticated_facebook_url(
        "https://www.facebook.com/huy.example"
    ) is True


def test_monitor_marks_connection_after_profile_redirect(monkeypatch) -> None:
    connected = Mock()
    monkeypatch.setattr(
        connection_monitor,
        "active_coccoc_urls",
        lambda: ["https://www.facebook.com/profile.php?id=123"],
    )
    monkeypatch.setattr(connection_monitor, "_set_connected", connected)

    connection_monitor._monitor_facebook_connection("connection_1", 1, 0)

    connected.assert_called_once_with("connection_1")
