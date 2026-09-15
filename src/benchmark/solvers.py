"""Reference solvers: each one turns a problem's raw inputs into every derived
quantity a grader might need to check, by calling `bondmath` directly.

A solver never hand-computes anything — that would reintroduce exactly the
risk this project exists to catch. It builds a `Bond`, calls the matching
`bondmath` function, and flattens the result into a plain dict of
JSON-friendly values so problem files can name a single field to grade
against without caring about the underlying dataclasses.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Callable

from bondmath import (
    Bond,
    DayCount,
    analytics,
    check_consistency,
    price_from_yield,
    scenario,
    yield_from_price,
)

__all__ = ["SOLVERS", "build_bond", "parse_date"]

_BASIS = {
    "ACT/ACT ICMA": DayCount.ACT_ACT_ICMA,
    "30/360": DayCount.THIRTY_360,
    "ACT/365": DayCount.ACT_365,
    "ACT/360": DayCount.ACT_360,
}


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def build_bond(inputs: dict[str, Any]) -> Bond:
    return Bond(
        face=inputs["face_value"],
        coupon_rate=inputs["coupon_rate_pct"] / 100,
        frequency=inputs["payments_per_year"],
        issue=parse_date(inputs["issue_date"]),
        maturity=parse_date(inputs["maturity_date"]),
        basis=_BASIS[inputs.get("day_count", "ACT/ACT ICMA")],
    )


def _quote_and_analytics(inputs: dict[str, Any]) -> dict[str, Any]:
    """Shared core for the compute solvers: resolve price/yield, then derive
    every sensitivity measure from the resolved yield."""
    bond = build_bond(inputs)
    settle = parse_date(inputs["settlement_date"])

    if "clean_price_pct_of_face" in inputs:
        clean = inputs["clean_price_pct_of_face"] / 100 * bond.face
        quote = yield_from_price(bond, settle, clean)
    else:
        quote = price_from_yield(bond, settle, inputs["ytm_pct"] / 100)

    metrics = analytics(bond, settle, quote.ytm)
    current_yield_pct = bond.annual_coupon / quote.clean * 100

    return {
        "clean_price": quote.clean,
        "clean_price_pct_of_face": quote.clean_pct,
        "accrued_interest": quote.accrued,
        "dirty_price": quote.dirty,
        "dirty_price_pct_of_face": quote.dirty_pct,
        "ytm_pct": quote.ytm * 100,
        "effective_annual_yield_pct": quote.effective_annual_yield * 100,
        "current_yield_pct": current_yield_pct,
        "macaulay_duration_years": metrics.macaulay,
        "modified_duration_years": metrics.modified,
        "effective_duration_years": metrics.effective,
        "naive_modified_duration_years": metrics.naive_modified,
        "dv01": metrics.dv01,
        "convexity_years_squared": metrics.convexity,
        "_bond": bond,
        "_settle": settle,
        "_quote": quote,
        "_metrics": metrics,
    }


def solve_price_yield(inputs: dict[str, Any]) -> dict[str, Any]:
    """Dirty/clean price, YTM, and every sensitivity measure in one call."""
    result = _quote_and_analytics(inputs)
    return {k: v for k, v in result.items() if not k.startswith("_")}


def solve_scenario(inputs: dict[str, Any]) -> dict[str, Any]:
    """Adds a rate-shock scenario on top of the base valuation."""
    base = _quote_and_analytics(inputs)
    bond, settle, quote = base["_bond"], base["_settle"], base["_quote"]
    s = scenario(bond, settle, quote.ytm, inputs["shock_bp"])
    out = {k: v for k, v in base.items() if not k.startswith("_")}
    out.update(
        {
            "shock_bp": s.shock_bp,
            "exact_repricing": s.exact,
            "duration_only_estimate": s.duration_only,
            "duration_plus_convexity_estimate": s.duration_convexity,
            "residual_bp": s.residual_bp,
            "convexity_contribution_bp": s.convexity_contribution_bp,
            "price_change_pct": (s.exact - quote.dirty) / quote.dirty * 100,
        }
    )
    return out


def solve_audit(inputs: dict[str, Any]) -> dict[str, Any]:
    """Resolves the true yield and checks a claimed figure against it —
    the reference implementation behind every 'does this number make sense'
    problem, mirroring `check_consistency_tool`."""
    bond = build_bond(inputs)
    settle = parse_date(inputs["settlement_date"])
    clean = inputs["clean_price_pct_of_face"] / 100 * bond.face

    solved = yield_from_price(bond, settle, clean)
    claimed_pct = inputs["claimed_ytm_pct"]

    # Build a Quote carrying the claimed yield so check_consistency can test
    # it against the same bounds the MCP tool uses.
    from bondmath.pricing import Quote

    claimed_quote = Quote(
        clean=solved.clean,
        dirty=solved.dirty,
        accrued=solved.accrued,
        clean_pct=solved.clean_pct,
        dirty_pct=solved.dirty_pct,
        ytm=claimed_pct / 100,
        effective_annual_yield=(1 + claimed_pct / 100 / bond.frequency) ** bond.frequency - 1,
    )
    report = check_consistency(bond, settle, claimed_quote)

    return {
        "claimed_ytm_pct": claimed_pct,
        "correct_ytm_pct": solved.ytm * 100,
        "error_bp": (claimed_pct - solved.ytm * 100) * 100,
        "is_correct": report.passed,
        "current_yield_pct": bond.annual_coupon / solved.clean * 100,
    }


SOLVERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "price_yield": solve_price_yield,
    "scenario": solve_scenario,
    "audit": solve_audit,
}
