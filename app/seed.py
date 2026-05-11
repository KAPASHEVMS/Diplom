"""
Начальное заполнение БД:
  - пользователи (manager / admin)
  - справочники (бренды, виды товаров, модели ценообразования)
  - магазины-конкуренты с парсерами
  - демо-каталог из 8 товаров
"""
from __future__ import annotations
from decimal import Decimal

from sqlalchemy import select

from .config import settings
from .db import SessionLocal
from .auth import hash_password
from .models import (
    AppUser, VType, Brand, MType, Shop, ShopWebsite, Product,
)


def seed():
    with SessionLocal() as s:
        # Users
        if not s.execute(select(AppUser).where(AppUser.login == settings.default_user)).scalar_one_or_none():
            s.add(AppUser(login=settings.default_user, role="manager",
                          full_name="Менеджер по умолчанию",
                          password_hash=hash_password(settings.default_password)))
        if not s.execute(select(AppUser).where(AppUser.login == "admin")).scalar_one_or_none():
            s.add(AppUser(login="admin", role="admin",
                          full_name="Администратор",
                          password_hash=hash_password("admin123")))

        # VType
        for n in ["Шины", "Диски"]:
            if not s.execute(select(VType).where(VType.name == n)).scalar_one_or_none():
                s.add(VType(name=n))

        # Brand
        brands = [
            ("Michelin", "Франция"),
            ("Continental", "Германия"),
            ("Hankook", "Республика Корея"),
            ("Bridgestone", "Япония"),
            ("BBS", "Германия"),
            ("Brembo", "Италия"),
            ("Replica", "—"),
        ]
        for n, c in brands:
            if not s.execute(select(Brand).where(Brand.name == n)).scalar_one_or_none():
                s.add(Brand(name=n, country=c))

        # MType
        models = [
            ("cost",     "Затратная",       "m_low=0.20; m_high=0.55"),
            ("market",   "Рыночная",         "берёт min/max цен конкурентов"),
            ("combined", "Комбинированная",  "k=1.20; K=1.55; q_low=0.25; q_high=0.75"),
        ]
        for code, name, params in models:
            if not s.execute(select(MType).where(MType.code == code)).scalar_one_or_none():
                s.add(MType(code=code, name=name, params=params))

        # Shops + parsers
        shops = [
            ("Wildberries", "Москва",         "https://www.wildberries.ru", "wildberries"),
            ("Ozon",        "Москва",         "https://www.ozon.ru",        "ozon"),
            ("Demo-конкурент","—",           "https://demo.local",         "demo"),
        ]
        for name, city, url, parser in shops:
            shop = s.execute(select(Shop).where(Shop.name == name)).scalar_one_or_none()
            if not shop:
                shop = Shop(name=name, city=city); s.add(shop); s.flush()
            site = s.execute(
                select(ShopWebsite).where(ShopWebsite.id_shop == shop.id_shop)
            ).scalar_one_or_none()
            if not site:
                s.add(ShopWebsite(id_shop=shop.id_shop, url=url, parser_code=parser))

        s.flush()

        # Brand IDs
        brand_id = {b.name: b.id_brand for b in s.execute(select(Brand)).scalars()}
        vt = {v.name: v.id_v_type for v in s.execute(select(VType)).scalars()}

        # Products demo catalog
        products = [
            ("MICH-205-55-16", "Michelin Pilot Sport 4 205/55 R16",  brand_id["Michelin"],    vt["Шины"], "6200", "Michelin Pilot Sport 4 205 55 R16"),
            ("CONT-225-45-17", "Continental SportContact 6 225/45 R17", brand_id["Continental"], vt["Шины"], "7800", "Continental SportContact 6 225 45 R17"),
            ("HANK-185-65-15", "Hankook Kinergy Eco 2 K435 185/65 R15", brand_id["Hankook"],    vt["Шины"], "3250", "Hankook Kinergy Eco K435 185 65 R15"),
            ("BRDG-215-55-17", "Bridgestone Turanza T005 215/55 R17",   brand_id["Bridgestone"],vt["Шины"], "5900", "Bridgestone Turanza T005 215 55 R17"),
            ("BBS-CH-R-18",    "Диск BBS CH-R 8x18 5x112 ET32",         brand_id["BBS"],        vt["Диски"], "21400","BBS CH-R 18 5x112"),
            ("BREM-LX-17",     "Диск Brembo LX 7x17 5x114 ET40",        brand_id["Brembo"],     vt["Диски"], "14000","Brembo LX 17"),
            ("REP-VW-16",      "Диск Replica VW 6.5x16 5x112 ET33",     brand_id["Replica"],    vt["Диски"], "4200", "Replica диск Volkswagen 16"),
            ("REP-TOY-17",     "Диск Replica Toyota 7x17 5x114 ET45",   brand_id["Replica"],    vt["Диски"], "5600", "Replica Toyota 17 5x114"),
        ]
        for sku, name, br, vt_id, pp, q in products:
            if not s.execute(select(Product).where(Product.sku == sku)).scalar_one_or_none():
                s.add(Product(
                    sku=sku, name=name, id_brand=br, id_v_type=vt_id,
                    purchase_price=Decimal(pp), search_query=q,
                ))

        s.commit()
        print("Seed completed.")


if __name__ == "__main__":
    seed()
