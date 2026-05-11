"""
Парсер цен Wildberries через публичный JSON-API поиска.

Endpoint:
  https://search.wb.ru/exactmatch/ru/common/v5/search?query={q}&resultset=catalog

Возвращает JSON со списком товаров; цена — в копейках в поле sizes[0].price.product
либо salePriceU. Делим на 100 для получения рублей.
"""
from __future__ import annotations
import logging
from decimal import Decimal
from typing import Sequence

import requests

from .base import BaseParser, ParsedItem, register

log = logging.getLogger(__name__)

WB_SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v5/search"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/120.0 Safari/537.36")


@register
class WildberriesParser(BaseParser):
    code = "wildberries"
    shop_name = "Wildberries"

    def search(self, query: str, *, limit: int = 10) -> Sequence[ParsedItem]:
        params = {
            "appType": "1",
            "curr": "rub",
            "dest": "-1257786",       # дефолтный регион (Москва)
            "query": query,
            "resultset": "catalog",
            "sort": "popular",
            "spp": "30",
        }
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        try:
            r = requests.get(WB_SEARCH_URL, params=params, headers=headers,
                             timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            log.warning("WB request failed for %r: %s", query, e)
            return []

        items: list[ParsedItem] = []
        products = (data.get("data") or {}).get("products") or []
        for p in products[:limit]:
            # Цена может лежать в разных полях. v5 чаще всего возвращает
            # sizes[0].price.product (в копейках).
            price_kopeks = None
            sizes = p.get("sizes") or []
            if sizes:
                pr = (sizes[0].get("price") or {})
                price_kopeks = pr.get("product") or pr.get("total")
            if price_kopeks is None:
                price_kopeks = p.get("salePriceU") or p.get("priceU")
            if not price_kopeks:
                continue
            wb_id = p.get("id")
            url = f"https://www.wildberries.ru/catalog/{wb_id}/detail.aspx" if wb_id else None
            brand = p.get("brand") or ""
            name = p.get("name") or ""
            title = f"{brand} {name}".strip()
            items.append(ParsedItem(
                title=title,
                price=Decimal(price_kopeks) / Decimal("100"),
                url=url,
            ))
        log.info("WB query %r -> %d items", query, len(items))
        return items
