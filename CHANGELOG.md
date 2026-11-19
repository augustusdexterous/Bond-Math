# Changelog

## 0.1.0

- Bond price, yield to maturity, Macaulay and modified duration, convexity and DV01 for fixed-coupon bonds with 1, 2, 4 or 12 payments a year.
- Zero curve, discount factors and one-year forward rates bootstrapped from annual par yields, with negative rates allowed.
- Command line: `bond-math bond` for one bond and `bond-math curve` for a par curve file, with text or JSON output. Input errors exit with code 2.
- Tests for closed forms, an independent decimal calculation, numerical derivatives, round trips and seeded random bonds. Continuous integration on Python 3.9 to 3.13.
