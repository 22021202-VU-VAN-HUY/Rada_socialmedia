from __future__ import annotations

import base64
import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from talent_radar.core.config import Settings
from talent_radar.models import OAuthState, PlatformConnection


class FacebookOAuthError(ValueError):
    pass


def begin_facebook_oauth(
    db: Session,
    settings: Settings,
    connection: PlatformConnection,
) -> str:
    _validate_settings(settings)
    state = secrets.token_urlsafe(32)
    db.add(
        OAuthState(
            id=f"oauth_state_{uuid4().hex}",
            user_id=connection.user_id,
            connection_id=connection.id,
            provider="facebook",
            state_hash=_state_hash(state),
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        )
    )
    connection.status = "pending_authorization"
    connection.last_error = None
    connection.connection_metadata = {
        **(connection.connection_metadata or {}),
        "oauth_started_at": datetime.now(UTC).isoformat(),
    }
    db.commit()

    query = urlencode(
        {
            "client_id": settings.facebook_app_id,
            "redirect_uri": settings.facebook_redirect_uri,
            "state": state,
            "response_type": "code",
            "scope": settings.facebook_scopes,
        }
    )
    return (
        f"https://www.facebook.com/{settings.facebook_graph_api_version}"
        f"/dialog/oauth?{query}"
    )


def complete_facebook_oauth(
    db: Session,
    settings: Settings,
    *,
    state: str,
    code: str,
    client: httpx.Client | None = None,
) -> PlatformConnection:
    _validate_settings(settings)
    oauth_state = db.scalar(
        select(OAuthState).where(
            OAuthState.provider == "facebook",
            OAuthState.state_hash == _state_hash(state),
        )
    )
    if oauth_state is None or oauth_state.used_at is not None:
        raise FacebookOAuthError("Yeu cau lien ket khong hop le hoac da duoc su dung.")
    if _as_utc(oauth_state.expires_at) <= datetime.now(UTC):
        raise FacebookOAuthError("Yeu cau lien ket da het han. Hay bam Lien ket lai.")

    oauth_state.used_at = datetime.now(UTC)
    db.commit()

    owns_client = client is None
    http_client = client or httpx.Client(timeout=20)
    try:
        token_payload = _get_json(
            http_client,
            f"https://graph.facebook.com/{settings.facebook_graph_api_version}"
            "/oauth/access_token",
            params={
                "client_id": settings.facebook_app_id,
                "client_secret": settings.facebook_app_secret,
                "redirect_uri": settings.facebook_redirect_uri,
                "code": code,
            },
        )
        access_token = token_payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise FacebookOAuthError("Facebook khong tra ve access token.")
        profile = _get_json(
            http_client,
            f"https://graph.facebook.com/{settings.facebook_graph_api_version}/me",
            params={"fields": "id,name"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    finally:
        if owns_client:
            http_client.close()

    facebook_user_id = profile.get("id")
    if not isinstance(facebook_user_id, str) or not facebook_user_id:
        raise FacebookOAuthError("Khong xac minh duoc tai khoan Facebook.")

    connection = db.get(PlatformConnection, oauth_state.connection_id)
    if connection is None or connection.user_id != oauth_state.user_id:
        raise FacebookOAuthError("Khong tim thay ket noi Facebook tuong ung.")
    connection.status = "connected"
    connection.auth_method = "facebook_oauth"
    connection.last_connected_at = datetime.now(UTC)
    connection.last_checked_at = datetime.now(UTC)
    connection.last_error = None
    connection.browser_process_id = None
    connection.connection_metadata = {
        **(connection.connection_metadata or {}),
        "facebook_user_id": facebook_user_id,
        "facebook_user_name": profile.get("name"),
        "facebook_token_protected": _protect_token(access_token),
        "facebook_token_type": token_payload.get("token_type", "bearer"),
        "facebook_token_expires_in": token_payload.get("expires_in"),
        "oauth_completed_at": datetime.now(UTC).isoformat(),
    }
    db.commit()
    db.refresh(connection)
    return connection


def mark_facebook_oauth_error(
    db: Session,
    *,
    state: str,
    message: str,
) -> None:
    oauth_state = db.scalar(
        select(OAuthState).where(
            OAuthState.provider == "facebook",
            OAuthState.state_hash == _state_hash(state),
        )
    )
    if oauth_state is None:
        return
    connection = db.get(PlatformConnection, oauth_state.connection_id)
    if connection is None:
        return
    connection.status = "error"
    connection.last_error = message
    connection.last_checked_at = datetime.now(UTC)
    oauth_state.used_at = oauth_state.used_at or datetime.now(UTC)
    db.commit()


def _validate_settings(settings: Settings) -> None:
    if not settings.facebook_app_id.strip() or not settings.facebook_app_secret.strip():
        raise FacebookOAuthError(
            "Chua cau hinh FACEBOOK_APP_ID va FACEBOOK_APP_SECRET trong .env."
        )
    if not settings.facebook_redirect_uri.startswith(("http://", "https://")):
        raise FacebookOAuthError("FACEBOOK_REDIRECT_URI khong hop le.")


def _get_json(
    client: httpx.Client,
    url: str,
    **kwargs,
) -> dict:
    try:
        response = client.get(url, **kwargs)
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise FacebookOAuthError("Khong ket noi duoc Facebook OAuth.") from exc
    if response.is_error or "error" in payload:
        detail = payload.get("error", {}).get("message")
        raise FacebookOAuthError(detail or "Facebook tu choi yeu cau OAuth.")
    if not isinstance(payload, dict):
        raise FacebookOAuthError("Phan hoi OAuth cua Facebook khong hop le.")
    return payload


def _state_hash(state: str) -> str:
    return hashlib.sha256(state.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _protect_token(token: str) -> str:
    if os.name != "nt":
        raise FacebookOAuthError("Ma hoa token Facebook chi duoc ho tro tren Windows.")
    try:
        import win32crypt

        protected_result = win32crypt.CryptProtectData(
            token.encode("utf-8"),
            "Talent Radar Facebook token",
            None,
            None,
            None,
            0,
        )
        protected = (
            protected_result[1]
            if isinstance(protected_result, tuple)
            else protected_result
        )
    except Exception as exc:
        raise FacebookOAuthError("Khong ma hoa duoc token Facebook tren Windows.") from exc
    return base64.b64encode(protected).decode("ascii")
