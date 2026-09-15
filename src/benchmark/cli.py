"""Command-line entry point.

    finance-benchmark list
    finance-benchmark show fi-003
    finance-benchmark grade fi-001 4.6867
    finance-benchmark grade fi-003 '{"is_correct": false, "corrected_ytm_pct": 4.6867}'

No model-calling here on purpose: grading takes a candidate answer you
already have (typed by hand, or pasted from a model's response), so this
works today without any API key or budget for running models. Automating the
"ask N models, grade their answers" loop is future work once there's budget
for it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .grade import grade
from .problem import load_all_problems, load_problem

PROBLEMS_ROOT = Path(__file__).resolve().parents[2] / "problems"


def _find(problem_id: str):
    for p in load_all_problems(PROBLEMS_ROOT):
        if p.id == problem_id:
            return p
    raise SystemExit(f"no problem with id {problem_id!r}")


def cmd_list(_args: argparse.Namespace) -> None:
    problems = load_all_problems(PROBLEMS_ROOT)
    for p in problems:
        print(f"{p.id:8} [{p.category:13}] ({p.kind:7}) {p.prompt.splitlines()[0][:70]}")
    print(f"\n{len(problems)} problems total")


def cmd_show(args: argparse.Namespace) -> None:
    p = _find(args.id)
    print(f"id:       {p.id}")
    print(f"category: {p.category}")
    print(f"kind:     {p.kind}")
    print(f"unit:     {p.unit}")
    print(f"\n{p.prompt}\n")


def cmd_grade(args: argparse.Namespace) -> None:
    p = _find(args.id)
    candidate = json.loads(args.answer) if p.kind == "audit" else float(args.answer)
    result = grade(p, candidate)
    mark = "PASS" if result.correct else "FAIL"
    print(f"[{mark}] {p.id}: {result.detail}")
    sys.exit(0 if result.correct else 1)


def main() -> None:
    parser = argparse.ArgumentParser(prog="finance-benchmark")
    sub = parser.add_subparsers(required=True)

    sub.add_parser("list").set_defaults(func=cmd_list)

    show = sub.add_parser("show")
    show.add_argument("id")
    show.set_defaults(func=cmd_show)

    g = sub.add_parser("grade")
    g.add_argument("id")
    g.add_argument("answer")
    g.set_defaults(func=cmd_grade)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
