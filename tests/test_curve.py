from pathlib import Path

import numpy as np
import pytest

from bond_math import discount_factors, forward_rates, load_par_curve, zero_rates_from_par

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample_par_curve.csv"


def test_flat_par_curve_gives_flat_zero_and_forward_rates():
    par = [0.05] * 6
    np.testing.assert_allclose(zero_rates_from_par(par), 0.05, rtol=1e-12)
    np.testing.assert_allclose(forward_rates(par), 0.05, rtol=1e-12)


def test_bootstrapped_discount_factors_reprice_the_par_bonds():
    par = np.array([0.02, 0.025, 0.03, 0.035, 0.04])
    df = discount_factors(par)
    for n, c in enumerate(par, start=1):
        pv = c * df[: n - 1].sum() + (1 + c) * df[n - 1]
        assert pv == pytest.approx(1.0, abs=1e-12)


def test_zero_rates_match_discount_factors():
    par = np.array([0.02, 0.025, 0.03])
    df = discount_factors(par)
    z = zero_rates_from_par(par)
    np.testing.assert_allclose((1 + z) ** np.arange(1, 4), 1 / df, rtol=1e-12)


def test_forward_rates_compound_back_to_discount_factors():
    par = np.array([0.02, 0.025, 0.03, 0.035])
    df = discount_factors(par)
    f = forward_rates(par)
    np.testing.assert_allclose(np.cumprod(1 / (1 + f)), df, rtol=1e-12)


def test_upward_sloping_curve_has_rising_forwards():
    f = forward_rates([0.02, 0.025, 0.03, 0.035])
    assert np.all(np.diff(f) > 0)


def test_negative_par_rates_are_allowed_and_reprice():
    par = np.array([-0.005, -0.004, -0.002, 0.0, 0.003])
    df = discount_factors(par)
    assert np.all(df > 0)
    assert df[0] > 1.0  # a negative rate gives a discount factor above one
    for n, c in enumerate(par, start=1):
        pv = c * df[: n - 1].sum() + (1 + c) * df[n - 1]
        assert pv == pytest.approx(1.0, abs=1e-12)


def test_curve_validation():
    with pytest.raises(ValueError):
        discount_factors([])
    with pytest.raises(ValueError):
        discount_factors([0.02, np.nan])
    with pytest.raises(ValueError, match="decimals"):
        discount_factors([5.0, 5.5])  # percentages instead of decimals
    with pytest.raises(ValueError, match="above -100%"):
        discount_factors([-1.0])


def test_curve_prices_a_coupon_bond_consistently():
    # A 3-year 4% annual bond valued with the curve's discount factors equals its price
    # computed from the curve's own zero rates, with annual compounding.
    par = [0.02, 0.025, 0.03]
    df = discount_factors(par)
    cf = [4.0, 4.0, 104.0]
    pv_curve = float(np.dot(cf, df))
    z = zero_rates_from_par(par)
    pv_zero = sum(c / (1 + zi) ** (k + 1) for k, (c, zi) in enumerate(zip(cf, z)))
    assert pv_curve == pytest.approx(pv_zero, rel=1e-12)


def test_load_par_curve_reads_a_valid_file(tmp_path):
    path = tmp_path / "curve.csv"
    path.write_text("maturity,par_rate\n1,0.02\n2,0.025\n3,0.03\n", encoding="utf-8")
    np.testing.assert_allclose(load_par_curve(path), [0.02, 0.025, 0.03])


def test_load_par_curve_rejects_bad_files(tmp_path):
    path = tmp_path / "curve.csv"
    cases = [
        ("", "empty"),
        ("tenor,rate\n1,0.02\n", "needs the columns"),
        ("maturity,par_rate\n", "no data rows"),
        ("maturity,par_rate\n1,0.02\n3,0.03\n", "in order"),
        ("maturity,par_rate\n1,0.02\n2,abc\n", "must be numbers"),
    ]
    for text, message in cases:
        path.write_text(text, encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            load_par_curve(path)


def test_load_par_curve_reports_the_line_of_a_bad_maturity(tmp_path):
    path = tmp_path / "curve.csv"
    path.write_text("maturity,par_rate\n1,0.02\n3,0.03\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 3"):
        load_par_curve(path)


def test_sample_curve_file_loads_and_prices():
    par = load_par_curve(SAMPLE)
    assert par.size == 10
    assert np.all(np.diff(par) > 0)  # the sample is upward sloping
    assert np.all(discount_factors(par) > 0)
