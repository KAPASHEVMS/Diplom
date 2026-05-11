"""Аутентификация пользователей."""
from __future__ import annotations
import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AppUser


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def authenticate(session: Session, login: str, password: str) -> AppUser | None:
    user = session.execute(
        select(AppUser).where(AppUser.login == login, AppUser.is_active.is_(True))
    ).scalar_one_or_none()
    if user and verify_password(password, user.password_hash):
        return user
    return None
