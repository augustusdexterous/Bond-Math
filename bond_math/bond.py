"""Plain-vanilla fixed-rate bonds: price, yield, duration, convexity and DV01.

Cash flows fall on whole coupon periods, so settlement is on a coupon date. Yields are annual
nominal rates, compounded ``freq`` times a year. The formulas are in docs/method.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import optimize

__all__ = [
    "Bond",
    "convexity",
    "dv01",
    "macaulay_duration",
    "modified_duration",
    "price",
    "yield_to_maturity",
]

_VALID_FREQ = (1, 2, 4, 12)
_MAX_PERIODS = 100_000  # longer bonds are rejected; they are far outside any planning case
_YIELD_SEARCH_FLOOR = 0.5  # solve yields down to -50% per period
_YIELD_SEARCH_CAP = 1e6  # give up searching above this annual yield


@dataclass(frozen=True)
class Bond:
    """A fixed-coupon bond.

    face : principal repaid at maturity.
    coupon : annual coupon rate as a decimal (0.05 = 5% per year).
    years : time to maturity in years. ``years * freq`` must be a whole number of periods.
    freq : coupon payments per year (1, 2, 4 or 12).
    """

    face: float = 100.0
    coupon: float = 0.0
    years: float = 10.0
    freq: int = 2

    def __post_init__(self) -> None:
        if not math.isfinite(self.face) or self.face <= 0:
            raise ValueError("face must be a finite positive number")
        if not math.isfinite(self.coupon) or self.coupon < 0:
            raise ValueError("coupon must be a finite, non-negative rate")
        if not math.isfinite(self.years) or self.years <= 0:
            raise ValueError("years must be a finite positive number")
        if self.freq not in _VALID_FREQ:
            raise ValueError(f"freq must be one of {_VALID_FREQ}")
        periods = self.years * self.freq
        if abs(periods - round(periods)) > 1e-9:
            raise ValueError("years * freq must be a whole number of coupon periods")
        if round(periods) < 1:
            raise ValueError("the bond must have at least one coupon period")
        if periods > _MAX_PERIODS:
            raise ValueError(f"at most {_MAX_PERIODS} coupon periods are supported")

    @property
    def n_periods(self) -> int:
        return round(self.years * self.freq)

    def cash_flows(self) -> tuple[np.ndarray, np.ndarray]:
        """Period numbers (1..N) and the cash paid in each period."""
        k = np.arange(1, self.n_periods + 1, dtype=np.float64)
        cf = np.full(k.size, self.face * self.coupon / self.freq)
        cf[-1] += self.face
        return k, cf


def _check_yield(y: float, freq: int) -> None:
    if not math.isfinite(y) or y <= -freq:
        raise ValueError("yield must be finite and above -freq (the per-period rate must exceed -100%)")


def price(bond: Bond, y: float) -> float:
    """Present value of the bond at annual nominal yield ``y``.

    Returns infinity when the value overflows a float, which happens only at extreme yields.
    """
    _check_yield(y, bond.freq)
    k, cf = bond.cash_flows()
    with np.errstate(over="ignore", invalid="ignore"):
        discount = (1.0 + y / bond.freq) ** (-k)
        # Zero cash flows contribute nothing. Multiplying them by an overflowed discount would give NaN.
        return float(np.sum(np.where(cf > 0, cf * discount, 0.0)))


def yield_to_maturity(bond: Bond, market_price: float) -> float:
    """Annual nominal yield that prices the bond at ``market_price``.

    Price falls as yield rises, so the root is bracketed and found with Brent's method.
    Raises ValueError when no yield in the search range gives that price.
    """
    if not math.isfinite(market_price) or market_price <= 0:
        raise ValueError("market_price must be a finite positive number")
    lower = -bond.freq * _YIELD_SEARCH_FLOOR

    def gap(y: float) -> float:
        return price(bond, y) - market_price

    if gap(lower) < 0:
        raise ValueError("no yield fits this price: it is above the price at a -50% per-period yield")
    upper = 1.0
    while gap(upper) > 0:
        if upper >= _YIELD_SEARCH_CAP:
            raise ValueError("no yield fits this price: it is below the price at a very high yield")
        upper = min(upper * 2.0, _YIELD_SEARCH_CAP)
    root = optimize.brentq(gap, lower, upper, xtol=1e-14, rtol=1e-14, maxiter=500)
    return float(root)


def _pv_weights(bond: Bond, y: float) -> tuple[np.ndarray, np.ndarray]:
    """Period numbers and present-value weights, scaled so the largest weight is 1.

    The weights are computed in log space, so they stay finite where the price itself overflows.
    Duration and convexity only use ratios of these weights, so the scale cancels.
    """
    _check_yield(y, bond.freq)
    k, cf = bond.cash_flows()
    log_base = math.log1p(y / bond.freq)
    log_pv = np.full(k.size, -np.inf)
    positive = cf > 0
    log_pv[positive] = np.log(cf[positive]) - k[positive] * log_base
    return k, np.exp(log_pv - np.max(log_pv))


def macaulay_duration(bond: Bond, y: float) -> float:
    """Present-value-weighted average time to the cash flows, in years."""
    k, w = _pv_weights(bond, y)
    return float(np.sum(w * (k / bond.freq)) / np.sum(w))


def modified_duration(bond: Bond, y: float) -> float:
    """Percentage price sensitivity: ``-(dP/dy) / P``, in years."""
    return macaulay_duration(bond, y) / (1.0 + y / bond.freq)


def convexity(bond: Bond, y: float) -> float:
    """Second derivative of price with respect to yield, divided by price, in years squared."""
    k, w = _pv_weights(bond, y)
    base = 1.0 + y / bond.freq
    return float(np.sum(w * k * (k + 1.0)) / (np.sum(w) * base**2 * bond.freq**2))


def dv01(bond: Bond, y: float) -> float:
    """First-order price change for a 1 basis point rise in yield: ``-ModDur * P * 0.0001``.

    The result is negative for a normal bond. It ignores convexity; the error is about
    ``0.5 * convexity * P * 1e-8``. Use ``price`` at two yields for the exact change.
    """
    p = price(bond, y)
    return -modified_duration(bond, y) * p * 1e-4
