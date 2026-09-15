# finance-benchmark

Finance problems whose correct answer is computed, not typed in by hand.

## Why this is possible without human annotators

Most benchmarks need people to write or check every answer, which is slow
and expensive. In quantitative finance the ground truth is *calculable*: a
bond's yield to maturity, duration, or DV01 all follow from a formula. So
instead of storing a number in each problem file, this suite stores the
inputs and which reference function computes the answer — the number itself
is derived fresh every time a problem is graded, from
[`bondmath`](https://pypi.org/project/bondmath/), the same library behind
[fixed-income-mcp](https://github.com/joselillotrax-cell/fixed-income-mcp).

That also means the suite cannot silently drift from its own reference
implementation. If `bondmath` is ever fixed or improved, every problem here
re-validates against the new version for free.

## What's here

Twelve fixed-income problems, all drawn from real testing sessions rather
than invented: the exact bond and figures that motivated `bondmath` in the
first place, plus variants covering a different day-count convention, a
bond above par, a long low-coupon bond, and the higher-order residual that a
model attributed to "Taylor series terms" when the real cause was a wrong
duration.

Two problem kinds:

- **compute** — grade a single numeric field within a tolerance.
- **audit** — grade whether a claimed figure was correctly judged right or
  wrong, and, if wrong, whether the corrected figure is close to the truth.

Wrong `compute` answers are also checked against named failure patterns —
right now, the naive annualisation divisor that started this whole project.
A grading report that says *"matches the naive_annualisation pattern"*
carries a lot more information than *"wrong."*

## Use

```bash
pip install -e ".[dev]"

finance-benchmark list
finance-benchmark show fi-003
finance-benchmark grade fi-001 4.6867
finance-benchmark grade fi-003 '{"is_correct": false, "corrected_ytm_pct": 4.6867}'
```

There is no model-calling built in yet — grading takes a candidate answer
you already have. Ask a model the `prompt` from `finance-benchmark show`,
paste its answer into `grade`, done. Automating "ask N models via API and
grade all their answers" is the natural next step once there's a budget to
run it against.

## Tests

```bash
python -m pytest -v
```

Every problem is checked for internal consistency (its own reference answer
grades as correct), and several pin the exact figures already verified
independently elsewhere this week.

## Scope

Fixed income only, for now. The design — inputs plus a reference solver, no
hand-typed answers — extends to any domain where the correct answer can be
computed: derivatives pricing, loan amortisation, portfolio return
attribution. Each of those needs its own verified core first, the way
`bondmath` came before this.

## License

MIT.
