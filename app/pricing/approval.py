"""
Алгоритм 2.4.3 — утверждение цены P* пользователем.
"""
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from ..models import ProductShop, AuditLog


class PriceOutOfBandError(ValueError):
    """P* не попала в вилку [Pmin; Pmax]."""


def approve_price(session: Session, *, product_shop_id: int, p_star: Decimal,
                  user_id: int) -> ProductShop:
    ps = session.get(ProductShop, product_shop_id)
    if ps is None:
        raise ValueError(f"ProductShop {product_shop_id} not found")
    if ps.price_min is None or ps.price_max is None:
        raise ValueError("Вилка цен не рассчитана — выполните расчёт")
    if not (ps.price_min <= p_star <= ps.price_max):
        raise PriceOutOfBandError(
            f"Цена {p_star} вне вилки [{ps.price_min}; {ps.price_max}]"
        )
    ps.approved_price = p_star
    ps.approved_at = datetime.utcnow()
    ps.approved_by = user_id
    session.add(AuditLog(
        id_user=user_id,
        action="approve_price",
        target_id=ps.id_ps,
        payload=f"price={p_star}",
    ))
    session.commit()
    return ps
