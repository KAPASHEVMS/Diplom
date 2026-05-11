"""Базовый интерфейс парсера цен конкурентов."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence


@dataclass(frozen=True)
class ParsedItem:
    title: str
    price: Decimal
    url: str | None = None


class BaseParser:
    """Базовый класс. Конкретные парсеры наследуются от него."""

    code: str = ""           # уникальный код (wildberries, ozon, demo)
    shop_name: str = ""      # имя магазина в БД (создаётся seed-ом)

    def search(self, query: str, *, limit: int = 10) -> Sequence[ParsedItem]:
        """Возвращает список найденных позиций по поисковому запросу."""
        raise NotImplementedError


_REGISTRY: dict[str, BaseParser] = {}


def register(parser_cls: type[BaseParser]) -> type[BaseParser]:
    inst = parser_cls()
    _REGISTRY[parser_cls.code] = inst
    return parser_cls


def get_parser(code: str) -> BaseParser | None:
    return _REGISTRY.get(code)


def list_parsers() -> list[BaseParser]:
    return list(_REGISTRY.values())
