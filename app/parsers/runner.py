"""
Парсер-воркер: периодически проходит по всем товарам в БД и собирает
актуальные цены конкурентов согласно настройке PARSER_MODE.

Запускается контейнером worker из docker-compose. Может быть запущен и
локально командой `python -m app.parsers.runner` (полезно для отладки).
"""
from __future__ import annotations
import logging
import time
from datetime import datetime

from sqlalchemy import select

from ..config import settings
from ..db import SessionLocal
from ..models import CompetitorPrice, Product, Shop, ShopWebsite
from . import wildberries, ozon, demo  # noqa: F401 — регистрация парсеров
from .base import get_parser

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("parser.runner")


def _collect_for_product(session, product: Product, shops_by_parser: dict[str, Shop]) -> int:
    """Собирает цены по одному товару у всех включённых парсеров. Возвращает
    число добавленных записей."""
    query = product.search_query or product.name
    if not query:
        return 0

    # Выбираем парсеры согласно настройке
    if settings.parser_mode == "demo":
        codes = ["demo"]
    elif settings.parser_mode == "real":
        codes = ["wildberries", "ozon"]
    else:
        codes = [settings.parser_mode]

    added = 0
    for code in codes:
        parser = get_parser(code)
        if parser is None:
            log.warning("Парсер %r не зарегистрирован", code)
            continue
        shop = shops_by_parser.get(code)
        if shop is None:
            log.warning("Магазин для парсера %r не найден в БД", code)
            continue
        try:
            items = parser.search(query, limit=10)
        except Exception:  # pragma: no cover
            log.exception("Ошибка парсера %s для %r", code, query)
            continue
        for it in items:
            session.add(CompetitorPrice(
                id_product=product.id_product,
                id_shop=shop.id_shop,
                price=it.price,
                url=it.url,
            ))
            added += 1
    return added


def run_once() -> None:
    with SessionLocal() as session:
        shops_by_parser: dict[str, Shop] = {}
        sites = session.execute(select(ShopWebsite, Shop).join(Shop,
                                ShopWebsite.id_shop == Shop.id_shop)).all()
        for sw, shop in sites:
            shops_by_parser[sw.parser_code] = shop

        products = session.execute(select(Product)).scalars().all()
        total = 0
        for p in products:
            total += _collect_for_product(session, p, shops_by_parser)
        session.commit()
        log.info("Цикл парсинга: товаров=%d, записей цен=%d", len(products), total)


def loop() -> None:
    log.info("Парсер-воркер запущен (mode=%s, interval=%ds)",
             settings.parser_mode, settings.parser_interval_sec)
    while True:
        try:
            run_once()
        except Exception:
            log.exception("Ошибка в цикле парсера")
        time.sleep(settings.parser_interval_sec)


if __name__ == "__main__":
    loop()
