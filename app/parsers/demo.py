"""
Demo-парсер: синтезирует правдоподобные цены конкурентов для тестирования
без сетевых запросов. Использует деTERMINISTIC random на основе search_query
для воспроизводимости.
"""
from __future__ import annotations
import hashlib
import random
from decimal import Decimal
from typing import Sequence

from .base import BaseParser, ParsedItem, register


@register
class DemoParser(BaseParser):
    code = "demo"
    shop_name = "Demo-конкурент"

    def search(self, query: str, *, limit: int = 10) -> Sequence[ParsedItem]:
        # Стабильный seed по запросу
        seed = int(hashlib.md5(query.encode("utf-8")).hexdigest(), 16) & 0xFFFFFFFF
        rng = random.Random(seed)
        # Базовая «рыночная цена»: 5 000 — 35 000 ₽
        base = rng.randint(5000, 35000)
        items: list[ParsedItem] = []
        for i in range(min(limit, 8)):
            # Разброс ±20 % вокруг базовой
            delta = rng.uniform(-0.20, 0.20)
            price = Decimal(int(base * (1 + delta)))
            items.append(ParsedItem(
                title=f"{query} — конкурент {i+1}",
                price=price,
                url=f"https://demo.local/p?q={query}&i={i+1}",
            ))
        return items
