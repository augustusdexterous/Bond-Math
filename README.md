# bond-math

[![CI](https://github.com/augustusdexterous/Bond-Math/actions/workflows/ci.yml/badge.svg)](https://github.com/augustusdexterous/Bond-Math/actions/workflows/ci.yml)
![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)

Fixed-income analytics in Python: the price, yield, duration, convexity and DV01 of a fixed-rate bond, and zero rates, discount factors and one-year forward rates bootstrapped from annual par yields. It comes with a command line and a Python API. The only dependencies are NumPy and SciPy.

```console
$ bond-math bond --coupon 0.05 --years 10 --yield 0.05
price                : 100.0000
yield (annual nominal): 5.0000%
macaulay duration    : 7.9894 years
modified duration    : 7.7946
convexity            : 73.6287
DV01 (per 1bp)       : -0.0779

$ bond-math bond --coupon 0.05 --years 10 --price 95
price                : 95.0000
yield (annual nominal): 5.6617%
...

$ bond-math curve examples/sample_par_curve.csv
maturity    par %   zero %         DF  forward %
       1   3.0000   3.0000   0.970874     3.0000
       2   3.2000   3.2032   0.938888     3.4068
       3   3.4000   3.4092   0.904321     3.8224
...
      10   4.2000   4.2666   0.658491     4.7674
```

The curve file is **synthetic** and ships for testing the output format. It is not market data.

## Install

```bash
pip install git+https://github.com/augustusdexterous/Bond-Math.git
```

Requires Python 3.9 or newer.

## Command line

```console
$ bond-math bond --coupon 0.05 --years 10 --freq 2 --yield 0.04        # analytics at a yield
$ bond-math bond --coupon 0.05 --years 10 --freq 2 --price 95 --json   # solve the yield, JSON output
$ bond-math curve par_curve.csv --json                                  # zero curve from par yields
```

The curve file has two columns, `maturity` and `par_rate`. Maturities are 1, 2, ..., N in order, and rates are decimals (0.05 means 5%).

```csv
maturity,par_rate
1,0.0300
2,0.0320
3,0.0340
```

Input errors print a message on standard error and exit with code 2. So do results that are not finite, such as a price that overflows at an extreme yield.

## Python

```python
from bond_math import Bond, convexity, dv01, modified_duration, price, yield_to_maturity
from bond_math import load_par_curve, zero_rates_from_par, forward_rates

bond = Bond(face=100, coupon=0.05, years=10, freq=2)
y = yield_to_maturity(bond, 95.0)  # 0.056617...
price(bond, y)  # 95.0
modified_duration(bond, y), convexity(bond, y), dv01(bond, y)

par = load_par_curve("examples/sample_par_curve.csv")
zero = zero_rates_from_par(par)  # annually compounded zero rates, maturities 1..N
fwd = forward_rates(par)  # one-year forward rates
```

## What it computes

| Area | Functions |
|---|---|
| Bond price | `price` |
| Yield | `yield_to_maturity` (Brent's method; raises a clear error when no yield fits the price) |
| Duration and convexity | `macaulay_duration`, `modified_duration`, `convexity` |
| Price sensitivity | `dv01` (first-order estimate for a 1 bp rise) |
| Curve | `discount_factors`, `zero_rates_from_par`, `forward_rates`, `load_par_curve` |

## Conventions

- Yields are annual nominal rates, compounded `freq` times a year (1, 2, 4 or 12).
- Cash flows fall on whole coupon periods. Settlement is on a coupon date.
- Prices are per 100 of face value unless `face` is given.
- Durations and convexity are in years and years squared.
- DV01 is negative for a normal bond: the price falls when yield rises.
- Curve rates are annual decimals. Negative rates are allowed. A value above 1 (100%) is rejected, which catches percentages written as 5 instead of 0.05.

## How it is checked

The test suite has 58 tests. They pass locally on Python 3.9 and 3.13, and continuous integration runs them on 3.9 to 3.13.

- Closed forms: the annuity formula, zero-coupon price, duration and convexity, and bootstrapped curves that reprice their own par bonds.
- An independent calculation: 50-digit `Decimal` arithmetic in a plain loop, compared with the NumPy implementation on random bonds at four frequencies.
- Numerical derivatives: modified duration and convexity against finite differences of `price`.
- Round trips: `yield_to_maturity(price(y)) == y` on 200 random bonds, including negative yields.
- Properties: price falls as yield rises, and forwards compound back to the discount factors.
- The DV01 error is checked to equal the convexity term.
- Ten deliberately broken variants were tried during development (a wrong convexity term, a missing duration divisor, a wrong bootstrap denominator, a wrong forward rate, a removed yield bracket check, a lowered yield-search cap, a removed zero-cash-flow mask, and others). The tests failed for each.
- Regression tests cover the bugs an independent review found: zero-coupon bonds with 1200 periods, yields up to the search cap, duration and convexity where the price overflows, very large face values, CSV errors, and blank rows in curve files.

The rate-shock example checks the duration and convexity approximations against exact repricing:

```console
$ python examples/rate_shock.py
10-year 5% semiannual bond at 5.00%: price 100.0000, modified duration 7.7946 years, convexity 73.6287 years^2

shock (bp)   exact %  duration %  + convexity %
      -200    17.169      15.589         17.062
      -100     8.176       7.795          8.163
       -25     1.972       1.949          1.972
        25    -1.926      -1.949         -1.926
       100    -7.439      -7.795         -7.426
       200   -14.212     -15.589        -14.117
```

Duration alone misses the curvature of the price. Adding convexity closes most of the gap.

## Limits

- No day-count conventions (ACT/360, 30/360), accrued interest, business-day adjustments or stub periods. Settlement must fall on a coupon date.
- Plain fixed-coupon bonds only. Callable, puttable, floating-rate, inflation-linked and amortising bonds are not modelled.
- The curve bootstraps from annual par rates with maturities 1..N. There is no interpolation and no semiannual or market-convention input.
- DV01 is first order. Use `price` at two yields for an exact change.
- No credit spread, liquidity premium, taxes, fees or embedded options.
- At most 100,000 coupon periods. Curves that are too extreme for double precision are refused, where the relative accuracy of a discount factor would fall below one part in a million.
- No market data is included. The sample curve is synthetic. Check the results against your own data before relying on them.

This is a calculator for learning and prototyping. It is not investment advice.

## Development

```bash
git clone https://github.com/augustusdexterous/Bond-Math.git
cd bond-math
pip install -e ".[dev]"
python -m pytest -q
ruff check . && ruff format --check .
```

The formulas are written out in [docs/method.md](docs/method.md).

## References

- Macaulay, F. R. (1938). *Some Theoretical Problems Suggested by the Movements of Interest Rates, Bond Yields and Stock Prices in the United States since 1856*. National Bureau of Economic Research.
- Tuckman, B., & Serrat, A. (2011). *Fixed Income Securities: Tools for Today's Markets* (3rd ed.). Wiley.

## License

MIT. See [LICENSE](LICENSE).
