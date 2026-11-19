"""Price change for a parallel yield shock: exact repricing against duration and convexity.

Run from the repository root with the package installed (pip install -e .):
    python examples/rate_shock.py
"""

from bond_math import Bond, convexity, modified_duration, price

bond = Bond(face=100, coupon=0.05, years=10, freq=2)
y = 0.05
p0 = price(bond, y)
duration = modified_duration(bond, y)
conv = convexity(bond, y)

print(
    f"10-year 5% semiannual bond at {y:.2%}: price {p0:.4f}, "
    f"modified duration {duration:.4f} years, convexity {conv:.4f} years^2"
)
print()
print(f"{'shock (bp)':>10} {'exact %':>9} {'duration %':>11} {'+ convexity %':>14}")
for bp in (-200, -100, -25, 25, 100, 200):
    dy = bp / 10_000
    exact = price(bond, y + dy) / p0 - 1.0
    by_duration = -duration * dy
    by_convexity = by_duration + 0.5 * conv * dy * dy
    print(f"{bp:>10d} {exact * 100:>9.3f} {by_duration * 100:>11.3f} {by_convexity * 100:>14.3f}")
