"""Tests for the problem suite.

Two layers, deliberately different in what they guard:

* `test_every_problem_is_self_consistent` runs every problem's own solver and
  checks the answer it would compute grades as correct against itself. This
  catches typos in `inputs`, `answer_field`, or `tolerance` — the kind of
  mistake that would silently make a problem ungradable or wrong for every
  candidate, not just a model's.

* The pinned tests below check specific numeric values against the figures
  already verified independently this week (bond-desk's verify.py, the MCP
  server's own test suite, and — for fi-003 — a live tool call). If a future
  `bondmath` release ever changes these numbers, these tests are the ones
  that should explain why, not silently drift.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from benchmark.grade import grade
from benchmark.problem import load_all_problems, load_problem
from benchmark.solvers import SOLVERS

ROOT = Path(__file__).resolve().parents[1] / "problems"


def _all_problems():
    return load_all_problems(ROOT)


@pytest.mark.parametrize("problem", _all_problems(), ids=lambda p: p.id)
def test_every_problem_is_self_consistent(problem):
    outputs = SOLVERS[problem.solver](problem.inputs)

    if problem.kind == "compute":
        candidate = outputs[problem.answer_field]
        result = grade(problem, candidate)
        assert result.correct, f"{problem.id} does not grade its own answer as correct"
    else:
        candidate = {
            "is_correct": outputs["is_correct"],
            "corrected_ytm_pct": outputs["correct_ytm_pct"],
        }
        result = grade(problem, candidate)
        assert result.correct, f"{problem.id} does not grade its own answer as correct"


@pytest.mark.parametrize("problem", _all_problems(), ids=lambda p: p.id)
def test_every_problem_has_a_nonempty_prompt(problem):
    assert len(problem.prompt) > 20


def test_suite_has_no_duplicate_ids():
    ids = [p.id for p in _all_problems()]
    assert len(ids) == len(set(ids))


# --- pinned regression values, cross-checked against this week's work -----


def test_fi001_ytm_matches_verified_reference():
    p = load_problem(ROOT / "fixed_income" / "fi-001-ytm-actact.yaml")
    outputs = SOLVERS[p.solver](p.inputs)
    assert outputs["ytm_pct"] == pytest.approx(4.6867, abs=1e-3)


def test_fi002_modified_duration_matches_verified_reference():
    p = load_problem(ROOT / "fixed_income" / "fi-002-modified-duration.yaml")
    outputs = SOLVERS[p.solver](p.inputs)
    assert outputs["modified_duration_years"] == pytest.approx(3.1686, abs=1e-4)
    assert outputs["naive_modified_duration_years"] == pytest.approx(3.0976, abs=1e-4)


def test_fi003_audit_flags_the_known_bad_yield():
    p = load_problem(ROOT / "fixed_income" / "fi-003-audit-below-par.yaml")
    outputs = SOLVERS[p.solver](p.inputs)
    assert outputs["is_correct"] is False
    assert outputs["correct_ytm_pct"] == pytest.approx(4.6867, abs=1e-3)
    assert outputs["error_bp"] == pytest.approx(-67.67, abs=1.0)


def test_fi005_scenario_matches_verified_reference():
    p = load_problem(ROOT / "fixed_income" / "fi-005-scenario-shock.yaml")
    outputs = SOLVERS[p.solver](p.inputs)
    assert outputs["exact_repricing"] == pytest.approx(974.196555, abs=1e-3)


def test_fi007_bond_b_duration_exceeds_bond_a():
    """Regression for the two-bond comparison: B (long, low coupon) must
    have materially higher duration than A did in the earlier session."""
    p = load_problem(ROOT / "fixed_income" / "fi-007-duration-low-coupon-long.yaml")
    outputs = SOLVERS[p.solver](p.inputs)
    assert outputs["modified_duration_years"] == pytest.approx(7.4272, abs=1e-3)


def test_fi010_residual_is_a_fraction_of_a_basis_point():
    p = load_problem(ROOT / "fixed_income" / "fi-010-third-order-residual.yaml")
    outputs = SOLVERS[p.solver](p.inputs)
    assert abs(outputs["residual_bp"]) < 1.0


def test_fi012_audit_above_par_is_also_flagged():
    p = load_problem(ROOT / "fixed_income" / "fi-012-audit-above-par.yaml")
    outputs = SOLVERS[p.solver](p.inputs)
    assert outputs["is_correct"] is False


# --- grading behaviour itself -----------------------------------------------


def test_naive_duration_answer_is_flagged_by_name_not_just_wrong():
    """The whole point of known_failure_modes: a wrong answer that matches a
    named mistake should say so, not just fail silently."""
    p = load_problem(ROOT / "fixed_income" / "fi-002-modified-duration.yaml")
    result = grade(p, 3.0976)  # the naive-divisor answer
    assert result.correct is False
    assert result.matched_known_failure_mode == "naive_annualisation"


def test_a_genuinely_wrong_answer_matches_no_known_pattern():
    p = load_problem(ROOT / "fixed_income" / "fi-002-modified-duration.yaml")
    result = grade(p, 1.0)
    assert result.correct is False
    assert result.matched_known_failure_mode is None


def test_audit_wrong_verdict_is_caught_even_with_right_number_nearby():
    p = load_problem(ROOT / "fixed_income" / "fi-003-audit-below-par.yaml")
    result = grade(p, {"is_correct": True, "corrected_ytm_pct": 4.01})
    assert result.correct is False


# --- near-miss tier ----------------------------------------------------


def test_a_close_answer_is_a_near_miss_not_a_pass_or_a_fail():
    """The regression for the tolerance-policy decision this came from:
    4.6918% on fi-001 (0.51 bp off, well within the default 10x loose band)
    should read as distinct from both a clean pass and a genuinely wrong
    method — this is the exact value an earlier session produced."""
    p = load_problem(ROOT / "fixed_income" / "fi-001-ytm-actact.yaml")
    result = grade(p, 4.6918)
    assert result.status == "near_miss"
    assert result.correct is False  # near miss is never "correct"


def test_a_genuinely_distant_answer_is_still_wrong_not_a_near_miss():
    p = load_problem(ROOT / "fixed_income" / "fi-001-ytm-actact.yaml")
    result = grade(p, 4.7174)  # 3.07 bp off — outside the 1 bp loose band
    assert result.status == "wrong"


def test_default_loose_tolerance_is_ten_times_strict_tolerance():
    p = load_problem(ROOT / "fixed_income" / "fi-001-ytm-actact.yaml")
    assert p.loose_tolerance is None
    assert p.effective_loose_tolerance == pytest.approx(p.tolerance * 10)


def test_audit_near_miss_on_the_corrected_value_does_not_count_as_correct():
    p = load_problem(ROOT / "fixed_income" / "fi-003-audit-below-par.yaml")
    # right verdict, corrected figure close but outside tight tolerance
    result = grade(p, {"is_correct": False, "corrected_ytm_pct": 4.6918})
    assert result.status == "near_miss"


def test_audit_wrong_verdict_is_never_a_near_miss_even_if_the_number_is_close():
    """A wrong verdict is a conceptual failure, not a precision issue — it
    should never be softened into near_miss just because a nearby number was
    also supplied."""
    p = load_problem(ROOT / "fixed_income" / "fi-003-audit-below-par.yaml")
    result = grade(p, {"is_correct": True, "corrected_ytm_pct": 4.6867})
    assert result.status == "wrong"
