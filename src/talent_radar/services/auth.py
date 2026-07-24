from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from talent_radar.models import AuthSession, User


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


class AuthenticationError(ValueError):
    pass


def normalize_email(email: str) -> str:
    normalized = email.strip().casefold()
    if not EMAIL_PATTERN.fullmatch(normalized):
        raise AuthenticationError("Email khong hop le.")
    return normalized


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise AuthenticationError("Mat khau phai co it nhat 8 ky tu.")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, expected_hex = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
        )
        return hmac.compare_digest(actual, bytes.fromhex(expected_hex))
    except (ValueError, TypeError):
        return False


def register_user(db: Session, email: str, password: str) -> User:
    normalized = normalize_email(email)
    if db.scalar(select(User).where(User.email == normalized)) is not None:
        raise AuthenticationError("Email nay da duoc dang ky.")
    user = User(id=f"user_{uuid4().hex}", email=normalized, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    normalized = normalize_email(email)
    user = db.scalar(select(User).where(User.email == normalized))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise AuthenticationError("Email hoac mat khau khong dung.")
    return user


def create_session(db: Session, user: User, session_hours: int) -> tuple[str, AuthSession]:
    token = secrets.token_urlsafe(48)
    now = datetime.now(UTC)
    auth_session = AuthSession(
        id=f"session_{uuid4().hex}",
        user_id=user.id,
        token_hash=_token_hash(token),
        expires_at=now + timedelta(hours=session_hours),
    )
    db.add(auth_session)
    db.commit()
    db.refresh(auth_session)
    return token, auth_session


def authenticate_token(db: Session, token: str) -> tuple[User, AuthSession]:
    auth_session = db.scalar(
        select(AuthSession).where(AuthSession.token_hash == _token_hash(token))
    )
    if auth_session is None or auth_session.revoked_at is not None:
        raise AuthenticationError("Phien dang nhap khong hop le.")
    expires_at = auth_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        raise AuthenticationError("Phien dang nhap da het han.")
    user = db.get(User, auth_session.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Tai khoan khong hoat dong.")
    return user, auth_session


def revoke_session(db: Session, auth_session: AuthSession) -> None:
    auth_session.revoked_at = datetime.now(UTC)
    db.commit()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

