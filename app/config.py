"""Конфигурация приложения, загружается из переменных окружения."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(override=False)


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://pricing:pricing_pwd@localhost:5432/pricing",
    )
    parser_mode: str = os.getenv("PARSER_MODE", "demo")
    parser_interval_sec: int = int(os.getenv("PARSER_INTERVAL_SEC", "600"))
    default_user: str = os.getenv("DEFAULT_USER", "manager")
    default_password: str = os.getenv("DEFAULT_PASSWORD", "manager123")


settings = Settings()
