"""Problem loading.

A problem file never stores a numeric answer. It stores the inputs, which
solver turns them into every derived quantity, which field of that output is
the one being graded, and how close counts as correct. The number itself is
computed fresh every time a problem is loaded, from the same `bondmath` that
backs the MCP server — so the benchmark cannot silently drift from its own
reference implementation, and updating `bondmath` re-validates every problem
in the suite for free.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

__all__ = ["Problem", "load_problem", "load_all_problems"]

Kind = Literal["compute", "audit"]


@dataclass(frozen=True)
class Problem:
    """One benchmark item.

    Attributes:
        id: Short unique identifier, e.g. "fi-003".
        category: Top-level grouping, e.g. "fixed_income".
        kind: "compute" grades a single numeric field. "audit" grades whether
            a claimed figure was correctly judged right or wrong.
        prompt: The natural-language question, verbatim, as it should be
            given to a model under test.
        solver: Key into `benchmark.solvers.SOLVERS` — which reference
            function turns `inputs` into checkable outputs.
        inputs: Raw parameters passed to the solver.
        answer_field: For "compute", the solver-output key being graded.
            Unused for "audit", which grades `is_correct` plus, when the
            claim was wrong, `correct_ytm_pct`.
        unit: Human-readable unit of the answer, for display only.
        tolerance: Absolute tolerance in the same units as `answer_field`.
            An answer within this counts as fully correct.
        loose_tolerance: A second, wider band. An answer outside `tolerance`
            but within this counts as a "near miss" — close enough that the
            method was probably sound and the gap is precision, not concept.
            Defaults to 10x `tolerance` when not set explicitly. A near miss
            is never graded as correct; it is a separate, visible category
            rather than being folded into either "right" or "wrong".
        known_failure_modes: Name -> either an alternate solver output field
            (a string, e.g. "naive_modified_duration_years" — a value derived
            by the *same* formula error on *this* problem's own inputs), or a
            literal number (an empirically observed recurring wrong answer,
            not derived from any formula here — e.g. a specific model
            converging to the same wrong yield across several different
            problems on the same bond). If a wrong answer matches one of
            these within tolerance, grading reports which known failure
            pattern it matches, rather than just "wrong".
    """

    id: str
    category: str
    kind: Kind
    prompt: str
    solver: str
    inputs: dict[str, Any]
    answer_field: str | None = None
    unit: str = ""
    tolerance: float = 1e-6
    loose_tolerance: float | None = None
    known_failure_modes: dict[str, str | float] = field(default_factory=dict)

    @property
    def effective_loose_tolerance(self) -> float:
        return self.loose_tolerance if self.loose_tolerance is not None else self.tolerance * 10


def load_problem(path: Path) -> Problem:
    data = yaml.safe_load(path.read_text())
    return Problem(
        id=data["id"],
        category=data["category"],
        kind=data["kind"],
        prompt=data["prompt"].strip(),
        solver=data["solver"],
        inputs=data["inputs"],
        answer_field=data.get("answer_field"),
        unit=data.get("unit", ""),
        tolerance=float(data.get("tolerance", 1e-6)),
        loose_tolerance=(
            float(data["loose_tolerance"]) if "loose_tolerance" in data else None
        ),
        known_failure_modes=data.get("known_failure_modes", {}),
    )


def load_all_problems(root: Path) -> list[Problem]:
    files = sorted(root.rglob("*.yaml"))
    return [load_problem(f) for f in files]
