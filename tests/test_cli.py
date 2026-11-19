import json
import re
from pathlib import Path

import pytest

from bond_math.cli import main

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample_par_curve.csv"


def _reject_constant(token: str):
    raise ValueError(f"non-standard JSON token {token}")


def test_bond_prints_analytics_for_a_yield(capsys):
    assert main(["bond", "--coupon", "0.05", "--years", "10", "--yield", "0.05"]) == 0
    out = capsys.readouterr().out
    assert re.search(r"price\s+: 100\.0000", out)
    assert "DV01" in out


def test_bond_solves_yield_from_price(capsys):
    assert main(["bond", "--coupon", "0.05", "--years", "10", "--price", "95"]) == 0
    out = capsys.readouterr().out
    assert re.search(r"yield \(annual nominal\): 5\.6\d+%", out)


def test_bond_json_output_is_strict_json(capsys):
    assert main(["bond", "--coupon", "0.05", "--years", "10", "--price", "95", "--json"]) == 0
    data = json.loads(capsys.readouterr().out, parse_constant=_reject_constant)
    assert 0.055 < data["yield"] < 0.058
    assert data["price"] == 95
    assert data["dv01"] < 0


def test_bond_reports_invalid_input(capsys):
    assert main(["bond", "--coupon", "0.05", "--years", "10.3", "--yield", "0.05", "--freq", "2"]) == 2
    assert "whole number" in capsys.readouterr().err


def test_bond_reports_an_unsolvable_price(capsys):
    assert main(["bond", "--coupon", "0.05", "--years", "10", "--price", "1e-300"]) == 2
    assert "no yield fits" in capsys.readouterr().err


def test_curve_prints_a_table_for_the_sample_file(capsys):
    assert main(["curve", str(SAMPLE)]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines[0].split()[0] == "maturity"
    assert len(lines) == 11  # header plus ten maturities


def test_curve_json_output_is_strict_json(capsys):
    assert main(["curve", str(SAMPLE), "--json"]) == 0
    rows = json.loads(capsys.readouterr().out, parse_constant=_reject_constant)
    assert [row["maturity_years"] for row in rows] == list(range(1, 11))
    assert set(rows[0]) == {"maturity_years", "par_rate", "zero_rate", "discount_factor", "forward_rate"}


def test_curve_reports_a_missing_file(tmp_path, capsys):
    assert main(["curve", str(tmp_path / "missing.csv")]) == 2
    assert "error" in capsys.readouterr().err


def test_missing_subcommand_is_a_usage_error(capsys):
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
