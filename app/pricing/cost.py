"""
Алгоритм 2.4.1 из ВКР — расчёт полной себестоимости.

C = P0 + P0·α + (P0 + P0·α)·β + (P0 + P0·α + (P0+P0·α)·β)·γ

где:
  P0 — закупочная цена,
  α  — доля транспортных расходов (CostCoefficients.transport),
  β  — доля таможенных платежей    (CostCoefficients.customs),
  γ  — доля косвенных расходов     (CostCoefficients.overhead).
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


_2 = Decimal("0.01")


@dataclass(frozen=True)
class CostCoefficients:
    transport: Decimal = Decimal("0.05")   # α — 5 % по умолчанию
    customs:   Decimal = Decimal("0.12")   # β — 12 %
    overhead:  Decimal = Decimal("0.08")   # γ — 8 %


def calculate_full_cost(p0: Decimal, k: CostCoefficients) -> Decimal:
    """Полная себестоимость товара с учётом каскадных надбавок."""
    if p0 is None or p0 <= 0:
        raise ValueError("Закупочная цена должна быть положительной")
    transport = p0 * k.transport
    customs   = (p0 + transport) * k.customs
    overhead  = (p0 + transport + customs) * k.overhead
    cost = p0 + transport + customs + overhead
    if cost <= 0:
        raise ValueError("Себестоимость должна быть положительной")
    return cost.quantize(_2, rounding=ROUND_HALF_UP)
