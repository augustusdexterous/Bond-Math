"""Zero curve from annual par yields by bootstrapping, with discount factors and forward rates.

Par rates are annual-pay and maturities are whole years 1, 2, ..., N, so the curve is annually
compounded. Rates are decimals: 0.05 means 5%. Negative rates are allowed, as they were in
several markets after 2014.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from numpy.typing import ArrayLike, NDArray

__all__ = [
    "discount_factors",
    "forward_rates",
    "load_par_curve",
    "zero_rates_from_par",
]

# Relative accuracy required of every discount factor. Beyond it, the bootstrap is refused.
_MAX_RELATIVE_ERROR = 1e-6


def _as_par_rates(par_rates: ArrayLike) -> NDArray[np.float64]:
    rates = np.asarray(par_rates, dtype=np.float64)
    if rates.ndim != 1 or rates.size == 0:
        raise ValueError("par_rates must be a non-empty one-dimensional array")
    if not np.all(np.isfinite(rates)):
        raise ValueError("par rates must be finite")
    if np.any(rates > 1.0):
        raise ValueError("par rates are decimals (0.05 means 5%); values above 1 are rejected")
    if np.any(rates <= -1.0):
        raise ValueError("par rates must be above -100%")
    return rates


def discount_factors(par_rates: ArrayLike) -> NDArray[np.float64]:
    """Discount factors for maturities 1..N, bootstrapped from annual par rates.

    A par bond of maturity n with coupon c has price 1:
    ``1 = c * sum_{k<n} DF_k + (1 + c) * DF_n``, so ``DF_n = (1 - c * sum) / (1 + c)``.

    Raises ValueError when the curve is so extreme that the subtraction in that formula loses
    more than ``_MAX_RELATIVE_ERROR`` of the discount factor's accuracy.
    """
    c = _as_par_rates(par_rates)
    df = np.empty(c.size)
    running = 0.0
    eps = np.finfo(np.float64).eps
    for n, rate in enumerate(c):
        df[n] = (1.0 - rate * running) / (1.0 + rate)
        if df[n] <= 0:
            raise ValueError("par rates imply a non-positive discount factor; the curve is inconsistent")
        # Rounding in 1 - rate * running is about eps * (1 + rate * running); relative to df[n]
        # that is the accuracy of this discount factor.
        rounding = 4.0 * eps * (1.0 + rate * running) / (1.0 + rate)
        if rounding > _MAX_RELATIVE_ERROR * df[n]:
            raise ValueError(
                f"maturity {n + 1}: the curve is too extreme for double precision; "
                "discount factors from this maturity on would lose accuracy"
            )
        running += df[n]
    return df


def zero_rates_from_par(par_rates: ArrayLike) -> NDArray[np.float64]:
    """Annually compounded zero rates for maturities 1..N."""
    df = discount_factors(par_rates)
    maturities = np.arange(1, df.size + 1, dtype=np.float64)
    return df ** (-1.0 / maturities) - 1.0


def forward_rates(par_rates: ArrayLike) -> NDArray[np.float64]:
    """One-year forward rates: the rate for year n, from time n-1 to time n.

    The first entry is the one-year zero rate, since it starts at time 0.
    """
    df = discount_factors(par_rates)
    previous = np.concatenate([[1.0], df[:-1]])
    return previous / df - 1.0


def load_par_curve(path: str | Path) -> NDArray[np.float64]:
    """Read annual par rates from a CSV file with the columns ``maturity`` and ``par_rate``.

    Maturities must be 1, 2, ..., N in order. Rates are decimals (0.05 means 5%). Blank rows are
    skipped.
    """
    try:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.reader(fh)
            try:
                header = next(reader, None)
                if header is None:
                    raise ValueError("par curve file is empty")
                names = [name.strip().lower() for name in header]
                if "maturity" not in names or "par_rate" not in names:
                    raise ValueError("par curve file needs the columns maturity and par_rate")
                i_mat, i_rate = names.index("maturity"), names.index("par_rate")
                rates: list[float] = []
                for row in reader:
                    if not any(cell.strip() for cell in row):
                        continue
                    line = reader.line_num
                    try:
                        maturity = float(row[i_mat])
                        rate = float(row[i_rate])
                    except (IndexError, ValueError):
                        raise ValueError(f"line {line}: maturity and par_rate must be numbers") from None
                    if maturity != len(rates) + 1:
                        raise ValueError(
                            f"line {line}: maturities must be 1, 2, 3, ... in order; got {row[i_mat].strip()!r}"
                        )
                    rates.append(rate)
            except csv.Error as exc:
                raise ValueError(f"line {reader.line_num + 1}: malformed CSV ({exc})") from None
    except UnicodeDecodeError:
        raise ValueError(f"{path} is not UTF-8 text; save it as a UTF-8 CSV file") from None
    if not rates:
        raise ValueError("par curve file has no data rows")
    return np.asarray(rates, dtype=np.float64)
