"""Подключение к БД и фабрика сессий SQLAlchemy."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from .config import settings

# connect_timeout=5 — не висим, если контейнер БД не поднят
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
    connect_args={"connect_timeout": 5},
)
SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False,
                                           autoflush=False, expire_on_commit=False))


def check_connection() -> tuple[bool, str]:
    """Возвращает (ok, message). Используется GUI перед логином."""
    from sqlalchemy import text
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True, "OK"
    except UnicodeDecodeError:
        # На Windows локальные сообщения psycopg2 могут приходить в cp1251
        return False, "сервер БД недоступен (connection refused / timeout)"
    except Exception as e:
        msg = str(e)
        if "Connection refused" in msg or "could not connect" in msg.lower():
            return False, "сервер БД недоступен — поднимите docker compose"
        if "timeout" in msg.lower():
            return False, "истёк таймаут подключения к БД"
        return False, msg.splitlines()[0][:200]


def get_session():
    """Контекстный менеджер сессии для GUI/CLI кода."""
    return SessionLocal()
