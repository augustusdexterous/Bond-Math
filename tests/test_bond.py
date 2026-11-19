"""Bond analytics checked against closed forms, an independent Decimal calculation, numerical
derivatives, round trips and seeded random bonds."""

from __future__ import annotations

import random
from decimal import Decimal, localcontext

import pytest

from bond_math import (
    Bond,
    convexity,
    dv01,
    macaulay_duration,
    modified_duration,
    price,
    yield_to_maturity,
)


def _annuity_price(bond: Bond, y: float) -> float:
    """Textbook closed form: coupon annuity plus discounted face value."""
    r = y / bond.freq
    n = bond.n_periods
    c = bond.face * bond.coupon / bond.freq
    if r == 0:
        return c * n + bond.face
    return c * (1 - (1 + r) ** -n) / r + bond.face * (1 + r) ** -n


def _decimal_price(bond: Bond, y: float) -> float:
    """Independent price: an explicit loop in 50-digit decimal arithmetic, no numpy."""
    with localcontext() as ctx:
        ctx.prec = 50
        base = 1 + Decimal(repr(y)) / Decimal(bond.freq)
        face = Decimal(repr(bond.face))
        coupon = face * Decimal(repr(bond.coupon)) / Decimal(bond.freq)
        total = Decimal(0)
        for k in range(1, bond.n_periods + 1):
            cash = coupon + face if k == bond.n_periods else coupon
            total += cash / base**k
        return float(total)


def _random_bond(rng: random.Random) -> Bond:
    freq = rng.choice([1, 2, 4, 12])
    periods = rng.randint(1, 240)
    return Bond(
        face=rng.choice([100.0, 250.0, 1000.0]),
        coupon=rng.uniform(0.0, 0.15),
        years=periods / freq,
        freq=freq,
    )


def test_par_bond_prices_at_par():
    assert price(Bond(coupon=0.05, years=10, freq=1), 0.05) == pytest.approx(100.0, abs=1e-10)
    assert price(Bond(coupon=0.05, years=10, freq=2), 0.05) == pytest.approx(100.0, abs=1e-10)


def test_price_matches_closed_form_for_a_three_year_annual_bond():
    b = Bond(face=100, coupon=0.06, years=3, freq=1)
    expected = 6 / 1.04 + 6 / 1.04**2 + 106 / 1.04**3
    assert price(b, 0.04) == pytest.approx(expected, rel=1e-12)


@pytest.mark.parametrize("freq", [1, 2, 4, 12])
def test_price_matches_the_textbook_annuity_formula(freq):
    b = Bond(face=1000, coupon=0.0625, years=15 / freq, freq=freq)
    for y in (0.0, 0.01, 0.045, 0.11):
        assert price(b, y) == pytest.approx(_annuity_price(b, y), rel=1e-11)


@pytest.mark.parametrize("freq", [1, 2, 4, 12])
def test_price_matches_independent_decimal_calculation(freq):
    rng = random.Random(7 + freq)
    for _ in range(5):
        b = _random_bond(rng)
        y = rng.uniform(-0.01, 0.15)
        assert price(b, y) == pytest.approx(_decimal_price(b, y), rel=1e-12)


def test_zero_coupon_price_and_duration_and_convexity_closed_forms():
    b = Bond(face=100, coupon=0.0, years=5, freq=1)
    y = 0.04
    assert price(b, y) == pytest.approx(100 / 1.04**5, rel=1e-12)
    assert macaulay_duration(b, y) == pytest.approx(5.0, rel=1e-12)
    assert modified_duration(b, y) == pytest.approx(5.0 / 1.04, rel=1e-12)
    assert convexity(b, y) == pytest.approx(5 * 6 / 1.04**2, rel=1e-12)


@pytest.mark.parametrize("freq", [1, 2, 4, 12])
def test_yield_to_maturity_round_trip(freq):
    b = Bond(face=100, coupon=0.045, years=7, freq=freq)
    for y in (0.001, 0.03, 0.12):
        assert yield_to_maturity(b, price(b, y)) == pytest.approx(y, abs=1e-10)


def test_yield_round_trip_for_random_bonds_including_negative_yields():
    rng = random.Random(11)
    for _ in range(200):
        b = _random_bond(rng)
        y = rng.uniform(-0.02, 0.25)
        assert yield_to_maturity(b, price(b, y)) == pytest.approx(y, abs=1e-9)


def test_yield_to_maturity_explains_when_no_yield_fits():
    b = Bond(coupon=0.05, years=10, freq=2)
    with pytest.raises(ValueError, match="no yield fits"):
        yield_to_maturity(b, 1e300)  # above the price at a -50% per-period yield
    with pytest.raises(ValueError, match="no yield fits"):
        yield_to_maturity(b, 1e-300)  # below the price at any yield up to the search cap


@pytest.mark.parametrize(("freq", "years", "coupon"), [(2, 8, 0.05), (12, 3, 0.0), (1, 30, 0.02)])
def test_modified_duration_matches_numerical_derivative(freq, years, coupon):
    b = Bond(face=100, coupon=coupon, years=years, freq=freq)
    y, h = 0.04, 1e-6
    numeric = -(price(b, y + h) - price(b, y - h)) / (2 * h) / price(b, y)
    assert modified_duration(b, y) == pytest.approx(numeric, rel=1e-6)


def test_convexity_matches_numerical_second_derivative():
    b = Bond(face=100, coupon=0.05, years=8, freq=2)
    y, h = 0.04, 1e-4
    p = price(b, y)
    numeric = (price(b, y + h) + price(b, y - h) - 2 * p) / (h * h) / p
    assert convexity(b, y) == pytest.approx(numeric, rel=1e-5)


def test_dv01_is_the_first_order_change_and_its_error_is_the_convexity_term():
    b = Bond(face=100, coupon=0.05, years=10, freq=2)
    y, bp = 0.05, 1e-4
    exact = price(b, y + bp) - price(b, y)
    bound = 0.5 * convexity(b, y) * price(b, y) * bp**2  # second-order term of the Taylor expansion
    assert dv01(b, y) < 0
    assert exact - dv01(b, y) == pytest.approx(bound, rel=1e-3)


def test_price_falls_when_yield_rises():
    b = Bond(coupon=0.03, years=5, freq=2)
    assert price(b, 0.02) > price(b, 0.03) > price(b, 0.04)


def test_price_decreases_with_yield_for_random_bonds():
    rng = random.Random(5)
    for _ in range(100):
        b = _random_bond(rng)
        ys = sorted(rng.uniform(-0.01, 0.2) for _ in range(5))
        prices = [price(b, y) for y in ys]
        assert all(a > c for a, c in zip(prices, prices[1:]))


def test_bond_validation():
    with pytest.raises(ValueError):
        Bond(years=0)
    with pytest.raises(ValueError):
        Bond(face=0)
    with pytest.raises(ValueError):
        Bond(coupon=-0.01)
    with pytest.raises(ValueError):
        Bond(years=float("inf"))
    with pytest.raises(ValueError):
        Bond(freq=3)
    with pytest.raises(ValueError, match="whole number"):
        Bond(years=2.3, freq=2)
    with pytest.raises(ValueError):
        price(Bond(), float("nan"))
    with pytest.raises(ValueError, match="above"):
        price(Bond(freq=2), -2.0)
    with pytest.raises(ValueError):
        yield_to_maturity(Bond(), 0.0)
    with pytest.raises(ValueError):
        yield_to_maturity(Bond(), float("inf"))
