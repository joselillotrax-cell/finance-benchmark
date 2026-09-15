"""Grading.

Two problem kinds, two grading rules:

`compute` problems check one numeric field within a tolerance. If the answer
is wrong, grading also checks whether it matches a *known* wrong answer —
the naive annualisation divisor, for instance — so a failure report says
*which* mistake was made, not just that one was.

`audit` problems check a binary verdict (was the claimed figure plausible?)
and, when the claim was wrong, whether the model's corrected figure is close
to the true one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .problem import Problem
from .solvers import SOLVERS

__all__ = ["GradeResult", "grade"]


@dataclass(frozen=True)
class GradeResult:
    """Outcome of grading one candidate answer.

    Attributes:
        correct: Whether the answer falls within tolerance of the reference.
        expected: The reference value(s) computed for this problem.
        candidate: What was graded.
        matched_known_failure_mode: Name of the known wrong-answer pattern
            the candidate matches, if `correct` is False and it matches one.
        detail: One-line human-readable summary.
    """

    correct: bool
    expected: Any
    candidate: Any
    matched_known_failure_mode: str | None
    detail: str


def _grade_compute(problem: Problem, candidate: float) -> GradeResult:
    outputs = SOLVERS[problem.solver](problem.inputs)
    expected = outputs[problem.answer_field]
    correct = abs(candidate - expected) <= problem.tolerance

    matched = None
    if not correct:
        for name, field in problem.known_failure_modes.items():
            alt = outputs.get(field)
            if alt is not None and abs(candidate - alt) <= problem.tolerance:
                matched = name
                break

    if correct:
        detail = f"within tolerance of {expected:.6g} {problem.unit}"
    elif matched:
        detail = (
            f"expected {expected:.6g} {problem.unit}; matches the known "
            f"'{matched}' failure pattern ({outputs[problem.known_failure_modes[matched]]:.6g})"
        )
    else:
        detail = f"expected {expected:.6g} {problem.unit}, got {candidate:.6g}"

    return GradeResult(correct, expected, candidate, matched, detail)


def _grade_audit(problem: Problem, candidate: dict[str, Any]) -> GradeResult:
    outputs = SOLVERS[problem.solver](problem.inputs)
    expected = {"is_correct": outputs["is_correct"], "correct_ytm_pct": outputs["correct_ytm_pct"]}

    verdict_ok = bool(candidate.get("is_correct")) == outputs["is_correct"]
    value_ok = True
    if not outputs["is_correct"]:
        corrected = candidate.get("corrected_ytm_pct")
        value_ok = corrected is not None and abs(corrected - outputs["correct_ytm_pct"]) <= problem.tolerance

    correct = verdict_ok and value_ok

    if correct:
        detail = "verdict and corrected figure both right"
    elif not verdict_ok:
        detail = f"wrong verdict: claim is actually {'valid' if outputs['is_correct'] else 'invalid'}"
    else:
        detail = f"verdict right, but corrected figure off: expected {outputs['correct_ytm_pct']:.6g}"

    return GradeResult(correct, expected, candidate, None, detail)


def grade(problem: Problem, candidate: Any) -> GradeResult:
    """Grade one candidate answer against a problem's freshly computed reference.

    Args:
        problem: The problem being graded.
        candidate: A number for "compute" problems, or a dict with
            `is_correct` (and `corrected_ytm_pct` when False) for "audit".
    """
    if problem.kind == "compute":
        return _grade_compute(problem, float(candidate))
    if problem.kind == "audit":
        return _grade_audit(problem, dict(candidate))
    raise ValueError(f"unknown problem kind: {problem.kind!r}")
