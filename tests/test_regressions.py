"""Regressions found in independent review: extreme inputs, solver range, file errors and precision."""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from bond_math import (
    Bond,
    convexity,
    discount_factors,
    load_par_curve,
    macaulay_duration,
    modified_duration,
    price,
    yield_to_maturity,
)
from bond_math.cli import main


def _reject_constant(token: str):
    raise ValueError(f"non-standard JSON token {token}")


def test_zero_coupon_bond_with_many_periods_solves_to_the_closed_form():
    b = Bond(face=100, coupon=0.0, years=100, freq=12)  # 1200 periods
    expected = 12 * ((100 / 50) ** (1 / 1200) - 1)
    assert yield_to_maturity(b, 50.0) == pytest.approx(expected, rel=1e-9)


def test_yield_search_reaches_yields_up_to_the_cap():
    b = Bond(face=100, coupon=0.0, years=1, freq=1)
    y = 6e5  # a root between 2**19 and the 1e6 cap
    assert yield_to_maturity(b, price(b, y)) == pytest.approx(y, rel=1e-9)


def test_duration_and_convexity_stay_finite_where_the_price_overflows():
    b = Bond(face=100, coupon=0.0, years=100, freq=12)
    y = -6.0  # per-period rate of -50%: the price overflows to infinity
    assert math.isinf(price(b, y))
    assert macaulay_duration(b, y) == pytest.approx(100.0, rel=1e-12)
    assert math.isfinite(modified_duration(b, y))
    assert math.isfinite(convexity(b, y))


def test_duration_and_convexity_do_not_depend_on_the_unit_of_face_value():
    small = Bond(face=100, coupon=0.05, years=10)
    huge = Bond(face=1e305, coupon=0.05, years=10)
    assert macaulay_duration(huge, 0.05) == pytest.approx(macaulay_duration(small, 0.05), rel=1e-12)
    assert convexity(huge, 0.05) == pytest.approx(convexity(small, 0.05), rel=1e-12)


def test_maturities_that_round_to_no_coupon_period_are_rejected():
    with pytest.raises(ValueError, match="at least one coupon period"):
        Bond(years=1e-12, freq=1)


def test_bonds_beyond_the_period_limit_are_rejected():
    with pytest.raises(ValueError, match="at most"):
        Bond(years=1e6, freq=12)


def test_bootstrap_refuses_curves_too_extreme_for_double_precision():
    with pytest.raises(ValueError, match="too extreme"):
        discount_factors([0.5] * 100)
    assert np.all(discount_factors([0.10] * 30) > 0)  # a normal curve is accepted


def test_malformed_curve_file_is_a_value_error_with_a_line_number(tmp_path):
    path = tmp_path / "curve.csv"
    path.write_bytes(b"maturity,par_rate\n1,0.02\x00\n")
    with pytest.raises(ValueError, match="line"):
        load_par_curve(path)


def test_whitespace_only_rows_are_skipped(tmp_path):
    path = tmp_path / "curve.csv"
    path.write_text("maturity,par_rate\n1,0.02\n   ,  \n2,0.025\n", encoding="utf-8")
    assert load_par_curve(path).tolist() == [0.02, 0.025]


def test_cli_refuses_non_finite_results_with_exit_code_2(capsys):
    assert main(["bond", "--coupon", "0", "--years", "100", "--freq", "12", "--yield", "-6"]) == 2
    assert "not finite" in capsys.readouterr().err


def test_cli_curve_with_a_nul_byte_exits_with_code_2(tmp_path, capsys):
    path = tmp_path / "curve.csv"
    path.write_bytes(b"maturity,par_rate\n1,0.02\x00\n")
    assert main(["curve", str(path)]) == 2
    assert "error" in capsys.readouterr().err


def test_cli_json_is_strict_for_a_zero_coupon_bond(capsys):
    assert main(["bond", "--coupon", "0", "--years", "100", "--freq", "12", "--price", "50", "--json"]) == 0
    data = json.loads(capsys.readouterr().out, parse_constant=_reject_constant)
    assert data["yield"] == pytest.approx(12 * ((100 / 50) ** (1 / 1200) - 1), rel=1e-9)
