from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

from sqlalchemy.orm import Session

from talent_radar.core.config import Settings
from talent_radar.models import OAuthState, PlatformConnection, User
from talent_radar.services import facebook_oauth


class FakeResponse:
    def __init__(self, payload: dict, *, is_error: bool = False) -> None:
        self.payload = payload
        self.is_error = is_error

    def json(self) -> dict:
        return self.payload


class FakeFacebookClient:
    def get(self, url: str, **_kwargs) -> FakeResponse:
        if url.endswith("/oauth/access_token"):
            return FakeResponse(
                {
                    "access_token": "facebook-token",
                    "token_type": "bearer",
                    "expires_in": 3600,
                }
            )
        if url.endswith("/me"):
            return FakeResponse({"id": "facebook-user-1", "name": "Huy Vu"})
        raise AssertionError(f"Unexpected URL: {url}")


def oauth_settings() -> Settings:
    return Settings(
        _env_file=None,
        facebook_app_id="123456789012345",
        facebook_app_secret="test-secret",
        facebook_redirect_uri=(
            "http://localhost:8000/connections/facebook/callback"
        ),
        facebook_graph_api_version="v20.0",
        facebook_scopes="public_profile",
    )


def persisted_connection(db: Session) -> PlatformConnection:
    user = User(
        id="user_1",
        email="huy@example.com",
        password_hash="not-used",
        is_active=True,
    )
    connection = PlatformConnection(
        id="connection_1",
        user_id=user.id,
        platform="facebook",
        status="disconnected",
        auth_method="facebook_oauth",
        profile_dir="Default",
        login_url="https://www.facebook.com/",
        connection_metadata={},
    )
    db.add_all([user, connection])
    db.commit()
    return connection


def test_begin_oauth_creates_single_use_state_and_authorization_url(
    db: Session,
) -> None:
    connection = persisted_connection(db)

    authorization_url = facebook_oauth.begin_facebook_oauth(
        db,
        oauth_settings(),
        connection,
    )

    query = parse_qs(urlparse(authorization_url).query)
    oauth_state = db.query(OAuthState).one()
    assert query["client_id"] == ["123456789012345"]
    assert query["redirect_uri"] == [
        "http://localhost:8000/connections/facebook/callback"
    ]
    assert query["scope"] == ["public_profile"]
    assert oauth_state.state_hash != query["state"][0]
    assert connection.status == "pending_authorization"


def test_callback_marks_connection_only_after_token_and_profile_verification(
    db: Session,
    monkeypatch,
) -> None:
    connection = persisted_connection(db)
    settings = oauth_settings()
    authorization_url = facebook_oauth.begin_facebook_oauth(db, settings, connection)
    state = parse_qs(urlparse(authorization_url).query)["state"][0]
    monkeypatch.setattr(
        facebook_oauth,
        "_protect_token",
        lambda token: f"protected:{token}",
    )

    completed = facebook_oauth.complete_facebook_oauth(
        db,
        settings,
        state=state,
        code="authorization-code",
        client=FakeFacebookClient(),
    )

    oauth_state = db.query(OAuthState).one()
    assert completed.status == "connected"
    assert completed.auth_method == "facebook_oauth"
    assert completed.connection_metadata["facebook_user_id"] == "facebook-user-1"
    assert completed.connection_metadata["facebook_user_name"] == "Huy Vu"
    assert completed.connection_metadata["facebook_token_protected"].startswith(
        "protected:"
    )
    assert oauth_state.used_at is not None
    assert oauth_state.used_at.replace(tzinfo=UTC) <= datetime.now(UTC)
