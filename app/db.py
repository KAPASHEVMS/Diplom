"""Подключение к БД и фабрика сессий SQLAlchemy."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False,
                                           autoflush=False, expire_on_commit=False))


def get_session():
    """Контекстный менеджер сессии для GUI/CLI кода."""
    return SessionLocal()
