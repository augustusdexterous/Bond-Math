"""Fixed-income analytics: bond prices, yields, duration, convexity, DV01 and zero curves.

Conventions
-----------
* Prices are per 100 of face value unless ``face`` is given.
* Yields are annual nominal rates with ``freq`` compounding periods per year.
* Cash flows fall on whole coupon periods: settlement is on a coupon date. Accrued interest and
  day-count conventions are not modelled.
* Durations are in years. DV01 is the first-order price change for a 1 basis point rise in yield.
* Curve rates are annual decimals: 0.05 means 5%. Negative rates are allowed.
"""

from .bond import (
    Bond,
    convexity,
    dv01,
    macaulay_duration,
    modified_duration,
    price,
    yield_to_maturity,
)
from .curve import (
    discount_factors,
    forward_rates,
    load_par_curve,
    zero_rates_from_par,
)

__version__ = "0.1.0"

__all__ = [
    "Bond",
    "__version__",
    "convexity",
    "discount_factors",
    "dv01",
    "forward_rates",
    "load_par_curve",
    "macaulay_duration",
    "modified_duration",
    "price",
    "yield_to_maturity",
    "zero_rates_from_par",
]
