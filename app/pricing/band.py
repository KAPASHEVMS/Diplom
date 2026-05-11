"""
Алгоритм 2.4.2 из ВКР — формирование "вилки" цен.

Три модели:
  - cost     (затратная)     — на основе себестоимости и маржи
  - market   (рыночная)      — на основе цен конкурентов (min..max)
  - combined (комбинированная) — себестоимость + квантили рыночных цен
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from statistics import quantiles
from typing import Sequence


class PricingModel(str, Enum):
    COST     = "cost"
    MARKET   = "market"
    COMBINED = "combined"


@dataclass(frozen=True)
class BandParams:
    margin_low:  Decimal = Decimal("0.20")  # m_low  — для затратной (нижний +20%)
    margin_high: Decimal = Decimal("0.55")  # m_high — для затратной (верхний +55%)
    k_low:       Decimal = Decimal("1.20")  # k — комбин. множитель снизу
    k_high:      Decimal = Decimal("1.55")  # K — комбин. множитель сверху
    q_low:       float   = 0.25             # квантиль нижний
    q_high:      float   = 0.75             # квантиль верхний
    tolerance:   Decimal = Decimal("0.60")  # допуск при коллапсе диапазона


_2 = Decimal("0.01")


def _quantile(values: Sequence[Decimal], q: float) -> Decimal:
    """Простая аппроксимация квантиля (linear interpolation)."""
    if not values:
        raise ValueError("Empty competitor prices")
    if len(values) == 1:
        return values[0]
    nums = sorted(float(v) for v in values)
    # statistics.quantiles делит на n равных интервалов; используем n=100 для гибкости
    cuts = quantiles(nums, n=100, method="inclusive")
    idx = int(round(q * 100)) - 1
    idx = max(0, min(idx, len(cuts) - 1))
    return Decimal(str(cuts[idx])).quantize(_2, rounding=ROUND_HALF_UP)


def build_band(
    cost: Decimal,
    market_prices: Sequence[Decimal],
    model: PricingModel,
    params: BandParams,
) -> tuple[Decimal, Decimal]:
    """Возвращает (P_min, P_max) — рекомендуемую вилку цен."""
    if cost is None or cost <= 0:
        raise ValueError("Cost must be positive")

    if model is PricingModel.COST:
        pmin = cost * (Decimal("1") + params.margin_low)
        pmax = cost * (Decimal("1") + params.margin_high)

    elif model is PricingModel.MARKET:
        if not market_prices:
            raise ValueError("Market model requires competitor prices")
        pmin = min(market_prices)
        pmax = max(market_prices)

    elif model is PricingModel.COMBINED:
        if not market_prices:
            # деградация до затратной
            pmin = cost * params.k_low
            pmax = cost * params.k_high
        else:
            q_lo = _quantile(market_prices, params.q_low)
            q_hi = _quantile(market_prices, params.q_high)
            pmin = max(cost * params.k_low,  q_lo)
            pmax = min(cost * params.k_high, q_hi)
    else:
        raise ValueError(f"Unknown pricing model: {model}")

    # Защита от схлопывания / инверсии диапазона
    if pmin > pmax:
        center = (pmin + pmax) / Decimal("2")
        delta  = (pmin - pmax).copy_abs() * params.tolerance
        pmin = center - delta
        pmax = center + delta

    # Защита: цена не должна быть ниже себестоимости
    if pmin < cost:
        pmin = cost
    if pmax < pmin:
        pmax = pmin * (Decimal("1") + params.margin_high)

    return (pmin.quantize(_2, rounding=ROUND_HALF_UP),
            pmax.quantize(_2, rounding=ROUND_HALF_UP))
