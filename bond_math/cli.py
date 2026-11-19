"""Command line: ``bond-math bond ...`` for one bond, ``bond-math curve FILE`` for a par curve."""

from __future__ import annotations

import argparse
import json
import math
import sys

from .bond import (
    Bond,
    convexity,
    dv01,
    macaulay_duration,
    modified_duration,
    price,
    yield_to_maturity,
)
from .curve import discount_factors, forward_rates, load_par_curve, zero_rates_from_par


def _require_finite(report: dict) -> dict:
    bad = [name for name, value in report.items() if isinstance(value, float) and not math.isfinite(value)]
    if bad:
        raise ValueError(
            f"the result is not finite for these inputs ({', '.join(bad)}); the price may overflow"
        )
    return report


def _bond_report(args: argparse.Namespace) -> dict:
    bond = Bond(face=args.face, coupon=args.coupon, years=args.years, freq=args.freq)
    if args.price is not None:
        y = yield_to_maturity(bond, args.price)
        p = args.price
    else:
        y = args.yld
        p = price(bond, y)
    return _require_finite(
        {
            "face": bond.face,
            "coupon": bond.coupon,
            "years": bond.years,
            "freq": bond.freq,
            "price": p,
            "yield": y,
            "macaulay_duration_years": macaulay_duration(bond, y),
            "modified_duration_years": modified_duration(bond, y),
            "convexity_years_squared": convexity(bond, y),
            "dv01": dv01(bond, y),
        }
    )


def _print_bond(report: dict) -> None:
    print(f"price                : {report['price']:.4f}")
    print(f"yield (annual nominal): {report['yield'] * 100:.4f}%")
    print(f"macaulay duration    : {report['macaulay_duration_years']:.4f} years")
    print(f"modified duration    : {report['modified_duration_years']:.4f}")
    print(f"convexity            : {report['convexity_years_squared']:.4f}")
    print(f"DV01 (per 1bp)       : {report['dv01']:.4f}")


def _curve_report(path: str) -> list[dict]:
    par = load_par_curve(path)
    df = discount_factors(par)
    zero = zero_rates_from_par(par)
    fwd = forward_rates(par)
    return [
        _require_finite(
            {
                "maturity_years": n,
                "par_rate": float(par[n - 1]),
                "zero_rate": float(zero[n - 1]),
                "discount_factor": float(df[n - 1]),
                "forward_rate": float(fwd[n - 1]),
            }
        )
        for n in range(1, par.size + 1)
    ]


def _print_curve(rows: list[dict]) -> None:
    print(f"{'maturity':>8} {'par %':>8} {'zero %':>8} {'DF':>10} {'forward %':>10}")
    for row in rows:
        print(
            f"{row['maturity_years']:>8d} {row['par_rate'] * 100:>8.4f} "
            f"{row['zero_rate'] * 100:>8.4f} {row['discount_factor']:>10.6f} "
            f"{row['forward_rate'] * 100:>10.4f}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bond-math",
        description="Fixed-income analytics: bond price, yield, duration, convexity and DV01, "
        "and zero rates, discount factors and forwards from par yields.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    bond_cmd = sub.add_parser("bond", help="analytics for one fixed-rate bond")
    bond_cmd.add_argument("--face", type=float, default=100.0)
    bond_cmd.add_argument("--coupon", type=float, required=True, help="annual coupon rate, e.g. 0.05")
    bond_cmd.add_argument("--years", type=float, required=True)
    bond_cmd.add_argument("--freq", type=int, default=2, choices=(1, 2, 4, 12))
    group = bond_cmd.add_mutually_exclusive_group(required=True)
    group.add_argument("--yield", dest="yld", type=float, help="annual yield, e.g. 0.04")
    group.add_argument("--price", type=float, help="market price; the yield is solved for")
    bond_cmd.add_argument("--json", action="store_true", help="print the analytics as JSON")

    curve_cmd = sub.add_parser("curve", help="zero rates, discount factors and forwards from par yields")
    curve_cmd.add_argument("path", help="CSV with columns maturity,par_rate (decimals, maturities 1..N)")
    curve_cmd.add_argument("--json", action="store_true", help="print the curve as JSON")

    args = parser.parse_args(argv)
    try:
        if args.command == "bond":
            report = _bond_report(args)
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                _print_bond(report)
        else:
            rows = _curve_report(args.path)
            if args.json:
                print(json.dumps(rows, indent=2))
            else:
                _print_curve(rows)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
