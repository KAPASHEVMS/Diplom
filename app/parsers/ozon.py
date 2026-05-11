"""
Парсер Ozon — best-effort через публичный JSON-эндпоинт каталога.

Замечание: Ozon активно борется с парсингом (anti-bot, динамические токены).
Этот парсер использует publicly-known v2 endpoint api.ozon.ru/composer-api.bx/page/json/v2.
В случае блокировки возвращает пустой список — это не критично, в наличии есть
другой источник (Wildberries) и fallback на demo-парсер.
"""
from __future__ import annotations
import json
import logging
import re
from decimal import Decimal
from typing import Sequence

import requests

from .base import BaseParser, ParsedItem, register

log = logging.getLogger(__name__)

OZON_URL = "https://api.ozon.ru/composer-api.bx/page/json/v2"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/120.0 Safari/537.36")
_PRICE_RE = re.compile(r"(\d[\d\s]*\d|\d)")


def _to_decimal(price_str: str) -> Decimal | None:
    m = _PRICE_RE.search(price_str.replace("\u00a0", " "))
    if not m:
        return None
    try:
        return Decimal(m.group(1).replace(" ", ""))
    except Exception:
        return None


@register
class OzonParser(BaseParser):
    code = "ozon"
    shop_name = "Ozon"

    def search(self, query: str, *, limit: int = 10) -> Sequence[ParsedItem]:
        url = f"{OZON_URL}?url=/search/?text={requests.utils.quote(query)}"
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "x-o3-app-name": "dweb_client",
            "x-o3-app-version": "release_9-9-2023_e2",
        }
        try:
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            log.info("Ozon request failed for %r: %s", query, e)
            return []

        items: list[ParsedItem] = []
        widget_states = (data.get("widgetStates") or {})
        # Перебираем виджеты — нужный называется searchResultsV2 или tileGridDesktop
        for key, raw in widget_states.items():
            if "searchResult" not in key and "tileGrid" not in key:
                continue
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            for it in (payload.get("items") or [])[:limit]:
                price_field = None
                for tile in (it.get("mainState") or []):
                    if tile.get("type") == "priceV2":
                        p = (tile.get("priceV2") or {}).get("price") or []
                        if p:
                            price_field = p[0].get("text")
                            break
                if not price_field:
                    continue
                price = _to_decimal(price_field)
                if price is None or price <= 0:
                    continue
                title_field = ""
                for tile in (it.get("mainState") or []):
                    if tile.get("type") == "textAtom":
                        atom = tile.get("atom") or {}
                        title_field = (atom.get("text") or "").strip()
                        if title_field:
                            break
                action = (it.get("action") or {}).get("link") or ""
                items.append(ParsedItem(
                    title=title_field or "Ozon item",
                    price=price,
                    url=("https://www.ozon.ru" + action) if action.startswith("/") else None,
                ))
                if len(items) >= limit:
                    break
            if items:
                break
        log.info("Ozon query %r -> %d items", query, len(items))
        return items
