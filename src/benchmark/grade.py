"""Grading.

Two problem kinds, two grading rules:

`compute` problems check one numeric field. Three outcomes, not two: within
`tolerance` is `correct`; outside that but within `loose_tolerance` is
`near_miss` — close enough that the method was probably sound and the gap is
precision rather than concept; anything wider is `wrong`. Collapsing a near
miss into a binary pass/fail would treat "iterated one Newton step short of
convergence" the same as "used the wrong formula," which throws away exactly
the distinction this project cares about. If the answer is wrong (not
correct), grading also checks whether it matches a *known* wrong answer — the
naive annualisation divisor, for instance — so a failure report says *which*
mistake was made, not just that one was.

`audit` problems check a binary verdict (was the claimed figure plausible?)
and, when the claim was wrong, whether the model's corrected figure is close
to the true one — graded with the same three-tier tolerance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .problem import Problem
from .solvers import SOLVERS

__all__ = ["GradeResult", "Status", "grade"]

Status = Literal["correct", "near_miss", "wrong"]


@dataclass(frozen=True)
class GradeResult:
    """Outcome of grading one candidate answer.

    Attributes:
        status: "correct" (within tolerance), "near_miss" (within the wider
            loose_tolerance band but not tolerance), or "wrong".
        correct: True only when status == "correct". Kept as a plain bool
            alongside `status` so simple pass/fail checks don't need to know
            about the three-tier scheme.
        expected: The reference value(s) computed for this problem.
        candidate: What was graded.
        matched_known_failure_mode: Name of the known wrong-answer pattern
            the candidate matches, if status != "correct" and it matches one.
        detail: One-line human-readable summary.
    """

    status: Status
    expected: Any
    candidate: Any
    matched_known_failure_mode: str | None
    detail: str

    @property
    def correct(self) -> bool:
        return self.status == "correct"


def _classify(diff: float, tolerance: float, loose_tolerance: float) -> Status:
    if diff <= tolerance:
        return "correct"
    if diff <= loose_tolerance:
        return "near_miss"
    return "wrong"


def _match_known_failure_mode(
    candidate: float, problem: Problem, outputs: dict[str, Any]
) -> str | None:
    """Check a wrong candidate against every named failure pattern.

    A pattern's value is either a literal number (an empirically observed
    recurring wrong answer) or a string naming a solver output field (a value
    derived by the same formula error on this problem's own inputs).
    """
    for name, pattern in problem.known_failure_modes.items():
        target = pattern if isinstance(pattern, (int, float)) else outputs.get(pattern)
        if target is not None and abs(candidate - target) <= problem.tolerance:
            return name
    return None


def _grade_compute(problem: Problem, candidate: float) -> GradeResult:
    outputs = SOLVERS[problem.solver](problem.inputs)
    expected = outputs[problem.answer_field]
    diff = abs(candidate - expected)
    status = _classify(diff, problem.tolerance, problem.effective_loose_tolerance)

    matched = _match_known_failure_mode(candidate, problem, outputs) if status != "correct" else None

    if status == "correct":
        detail = f"within tolerance of {expected:.6g} {problem.unit}"
    elif status == "near_miss":
        detail = (
            f"near miss: expected {expected:.6g} {problem.unit}, got "
            f"{candidate:.6g} (off by {diff:.4g}, within the wider band — "
            f"method looks sound, precision is off)"
        )
    elif matched:
        pattern = problem.known_failure_modes[matched]
        pattern_value = pattern if isinstance(pattern, (int, float)) else outputs[pattern]
        detail = (
            f"expected {expected:.6g} {problem.unit}; matches the known "
            f"'{matched}' failure pattern ({pattern_value:.6g})"
        )
    else:
        detail = f"expected {expected:.6g} {problem.unit}, got {candidate:.6g}"

    return GradeResult(status, expected, candidate, matched, detail)


def _grade_audit(problem: Problem, candidate: dict[str, Any]) -> GradeResult:
    outputs = SOLVERS[problem.solver](problem.inputs)
    expected = {"is_correct": outputs["is_correct"], "correct_ytm_pct": outputs["correct_ytm_pct"]}

    verdict_ok = bool(candidate.get("is_correct")) == outputs["is_correct"]

    value_status: Status = "correct"
    corrected = candidate.get("corrected_ytm_pct")
    if not outputs["is_correct"]:
        if corrected is None:
            value_status = "wrong"
        else:
            diff = abs(corrected - outputs["correct_ytm_pct"])
            value_status = _classify(diff, problem.tolerance, problem.effective_loose_tolerance)

    if not verdict_ok:
        status: Status = "wrong"  # a wrong verdict is never a near miss
    else:
        status = value_status

    matched = None
    if status != "correct" and corrected is not None:
        matched = _match_known_failure_mode(corrected, problem, outputs)

    if status == "correct":
        detail = "verdict and corrected figure both right"
    elif not verdict_ok:
        detail = f"wrong verdict: claim is actually {'valid' if outputs['is_correct'] else 'invalid'}"
    elif matched:
        pattern = problem.known_failure_modes[matched]
        pattern_value = pattern if isinstance(pattern, (int, float)) else outputs[pattern]
        detail = (
            f"verdict right, but the corrected figure matches the known "
            f"'{matched}' failure pattern ({pattern_value:.6g}) rather than "
            f"the true {outputs['correct_ytm_pct']:.6g}"
        )
    elif status == "near_miss":
        detail = f"verdict right, corrected figure close but outside tight tolerance: expected {outputs['correct_ytm_pct']:.6g}"
    else:
        detail = f"verdict right, but corrected figure off: expected {outputs['correct_ytm_pct']:.6g}"

    return GradeResult(status, expected, candidate, matched, detail)


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
