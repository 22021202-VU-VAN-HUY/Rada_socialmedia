from sqlalchemy import select
from sqlalchemy.orm import Session

from talent_radar.models import AuthSession
from talent_radar.services.auth import (
    AuthenticationError,
    authenticate_token,
    authenticate_user,
    create_session,
    register_user,
    revoke_session,
)


def test_password_and_session_token_are_not_stored_in_plaintext(db: Session) -> None:
    password = "correct-horse-2026"
    user = register_user(db, "Huy@Example.com", password)
    token, auth_session = create_session(db, user, 24)

    stored_session = db.scalar(select(AuthSession).where(AuthSession.id == auth_session.id))
    assert user.email == "huy@example.com"
    assert password not in user.password_hash
    assert stored_session is not None
    assert token != stored_session.token_hash
    assert len(stored_session.token_hash) == 64
    assert authenticate_user(db, "huy@example.com", password).id == user.id
    assert authenticate_token(db, token)[0].id == user.id


def test_revoked_session_is_rejected_immediately(db: Session) -> None:
    user = register_user(db, "huy@example.com", "correct-horse-2026")
    token, auth_session = create_session(db, user, 24)

    revoke_session(db, auth_session)

    try:
        authenticate_token(db, token)
    except AuthenticationError as exc:
        assert "khong hop le" in str(exc)
    else:
        raise AssertionError("Revoked session was accepted")

