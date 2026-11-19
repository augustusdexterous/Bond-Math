# Method

This page gives the formulas behind bond-math. Yields `y` are annual nominal rates with `f` compounding periods per year. A bond has `N = years × f` coupon periods, with coupon `c` and face value `F`.

## 1. Bond price

Cash flows in period `k = 1..N` are `CF_k = c·F/f`, plus `F` in the last period. The price is their present value:

    P(y) = Σ_{k=1..N} CF_k · (1 + y/f)^(−k)

For a par bond (`c = y`), `P = F`.

## 2. Yield to maturity

`P(y)` falls as `y` rises, so the yield that matches a market price `P*` is the root of `P(y) − P* = 0`. The solver:

1. starts the lower bracket at `y = −f/2` (a per-period rate of −50%),
2. raises the upper bracket from `y = 1` by doubling until the price falls below `P*`,
3. solves with Brent's method (SciPy `brentq`) to a tolerance of 1e-14.

If the price is above `P(−f/2)`, or no yield up to 10⁶ matches it, the function raises an error instead of returning a value.

## 3. Duration and convexity

The weights `PV_k` are computed in log space and scaled so the largest is 1. Duration and convexity only use ratios of these weights, so they stay finite where the price itself overflows, and they do not depend on the face value.

Macaulay duration is the present-value-weighted average time to the cash flows, in years:

    D_mac = Σ_k (k/f) · PV_k / P,   PV_k = CF_k · (1 + y/f)^(−k)

Modified duration is the percentage price sensitivity, `D_mod = −(dP/dy)/P = D_mac / (1 + y/f)`.

Convexity is `C = (1/P) · d²P/dy²`, in years squared:

    C = (1 / (P · f²)) · Σ_k CF_k · k(k+1) · (1 + y/f)^(−k−2)

## 4. DV01

DV01 is the first-order price change for a 1 basis point (0.0001) rise in yield:

    DV01 = −D_mod · P · 0.0001

It is negative for a normal bond. The omitted term is the convexity term, `½ · C · P · (0.0001)²`. For the 10-year example in the README it is about 0.00004 per 100 of face value.

## 5. Zero curve from par yields

Par rates `c_n` are annual-pay, with maturities `n = 1..N`. A par bond of maturity `n` has price 1, so with discount factors `DF_k`:

    1 = c_n · Σ_{k<n} DF_k + (1 + c_n) · DF_n

which gives the bootstrap:

    DF_n = (1 − c_n · Σ_{k<n} DF_k) / (1 + c_n),   DF_0 = 1

The annually compounded zero rate for maturity `n` is `z_n = DF_n^(−1/n) − 1`.

The one-year forward rate for year `n` (from time `n−1` to time `n`) is

    f_n = DF_{n−1} / DF_n − 1

so `f_1 = z_1`. Negative par rates are allowed. A non-positive discount factor, which would mean the inputs are inconsistent, raises an error.

The subtraction `1 − c_n · Σ DF_k` loses accuracy when `c_n · Σ DF_k` is close to 1, which happens for very long or very high-rate curves. The rounding error in that term, relative to `DF_n`, is bounded before each step. If the bound exceeds one part in a million, the bootstrap raises an error instead of returning inaccurate values.

## 6. What is checked

| Component | Check |
|---|---|
| Price | Closed-form annuity formula; 50-digit `Decimal` loop on random bonds at four frequencies |
| Yield | Round trip on 200 random bonds, including negative yields; error on unsolvable prices |
| Modified duration, convexity | Finite differences of `price`; zero-coupon closed forms |
| DV01 | The error against the exact 1 bp change equals the convexity term |
| Curve | Bootstrapped curve reprices its own par bonds; zero and forward rates consistent with the discount factors |

## 7. Limits

- Settlement is on a coupon date. Accrued interest and day-count conventions are not applied.
- The curve uses annual par rates only. Real curves are built from a mix of instruments with market conventions, so the zero rates here are a simplified model.
- No interpolation is done between maturities.
- The yield solver's search range is `(−f/2, 10⁶]` annual.
- Bonds are limited to 100,000 coupon periods.
