# Findings so far

A read of what `log.csv` actually shows, as of 28 graded runs across four
model labels and eight of the twelve fixed-income problems. This is not a
leaderboard — see [Scope](#scope) before drawing conclusions from it.

## The tally

| Model | Correct | Near miss | Wrong | Runs |
|---|---|---|---|---|
| chatgpt | 6 | 0 | 0 | 6 |
| gpt-5.6-luna | 2 | 0 | 0 | 2 |
| gemini-3.6-flash | 0 | 3 | 5 | 8 |
| claude-haiku-4.5-automated | 2 | 3 | 4 | 9 |
| claude (manual) | 1 | 1 | 0 | 2 |
| claude-haiku-4.5-low-effort | 1 | 0 | 0 | 1 |

Two things jump out before anything else does. `chatgpt` and `gpt-5.6-luna`
have not produced a single wrong or near-miss answer between them, across
eight runs covering seven different problems. `gemini-3.6-flash` has not
produced a single fully correct answer, across eight runs — every result is
either a near miss or a clean failure. Neither streak is long enough to
call definitive (see [Scope](#scope)), but they're long enough to be worth
naming rather than averaging away.

## Four distinct behaviors, not two

A benchmark that only records right/wrong would have missed everything
below except the headline tally. What actually happened is four
qualitatively different things, and they don't reduce to "some models are
better than others."

### 1. A reproducible, bond-specific bias

`gemini-3.6-flash` solved the reference bond's yield to maturity as
**4.7174%** — instead of the correct 4.6867% — in five independent runs,
across four different problems: `fi-001` (the YTM directly), `fi-002`
(feeding into duration), `fi-003` (an audit's corrected figure), `fi-010`
(feeding a scenario residual), and `fi-005` (stated explicitly as the
baseline in a shock scenario). The exact same six-decimal-adjacent number,
five times, is not sampling noise — it's a recognizable convergence point
for however this model solves this particular pricing equation. It's now
encoded directly in the problem files as
[`known_failure_modes: gemini_yield_bias`](../problems/fixed_income/fi-001-ytm-actact.yaml),
so any future run landing on it is named automatically rather than just
marked wrong.

**The same bias does not appear on other bonds.** On `fi-006` (annual
coupon, above par) and `fi-007` (long maturity, low coupon), the same model
produced near-misses with *different*, non-repeating wrong yields
(4.2018%, 4.2694%) — ordinary imprecision, not the reference-bond pattern.
Generalizing "this model's YTM solver is broken" from the first five runs
would have been wrong. The finding is narrower and more specific than that:
*this model converges to a specific wrong answer on this specific bond*,
which is a more useful thing to know than a vague reliability score, and a
good demonstration of why the schema tracks failure patterns by name
instead of only by pass/fail.

### 2. The same upstream error, different downstream damage

Because the reference bond gets asked about from several angles, the
`gemini_yield_bias` error can be tracked through the pipeline:

| Downstream quantity | Correct | Gemini's answer | Verdict |
|---|---|---|---|
| YTM itself (`fi-001`) | 4.6867% | 4.7174% | wrong |
| Modified duration (`fi-002`) | 3.1686 y | 3.1878 y | near miss |
| Scenario residual (`fi-010`) | 0.087 bp | 27.85 bp | wrong by ~320x |

The identical +3 bp yield error is nearly invisible in duration (which
isn't very sensitive to a small yield shift) and catastrophic in the
third-order residual (which is *supposed* to be a fraction of a basis
point, so a fixed absolute error dominates it completely). A benchmark that
asked only one question per model would have reported this error as
"roughly fine" or "badly broken" depending entirely on which one question
it happened to ask. Asking several turns "is this model reliable" into "for
which downstream use is this model's error tolerable," which is the more
useful question in practice.

### 3. Self-correction and its mirror image

Two runs show a model catching its own mistake mid-answer — in opposite
directions.

`claude-haiku-4.5-low-effort` on `fi-010` started with a modified duration
of 1.5825 years — the *inverse* of this whole project's original bug,
dividing by an annual-compounding factor on a semi-annual bond — producing
a 158.41 bp gap. It then noticed the inconsistency unprompted, named the
actual mechanism ("this is treating the bond as if it compounds
annually"), recalculated with the correct periodic-yield divisor, and
landed at 0.09 bp — within tolerance of the true 0.087 bp.

`gemini-3.6-flash` on `fi-004` did the reverse: computed the correct
164/180-day accrual and the correct $972.3333 dirty price mid-response,
then appended an unprompted second calculation ("if using exact 30/360
rounding... 5.5 months"), miscounted the period as 165 days, and
overwrote its own right answer with the wrong $972.50 as the final boxed
result.

Both are the same underlying behavior — a model revisiting its own work —
with opposite outcomes. Neither would show up in a benchmark that only
grades a model's *final* stated answer without anyone reading the
reasoning that produced it, since in isolation the final numbers alone
(0.09 correct, 972.50 wrong) look like an ordinary pass and an ordinary
fail rather than a self-correction and a self-sabotage.

### 4. Estimate instead of converge

The nine-problem `claude-haiku-4.5-automated` batch — isolated subagents,
no tools, no memory of this project, run in parallel against every problem
that didn't yet have a result — produced a clean pattern once laid out
side by side:

| Problem | Needs a YTM solve? | Result |
|---|---|---|
| `fi-004` (dirty price, no yield needed) | No | correct |
| `fi-008` (accrued interest only) | No | correct |
| `fi-003`, `fi-005`, `fi-006`, `fi-007`, `fi-009`, `fi-011`, `fi-012` | Yes | 1 near miss, 4 wrong, 2 near miss (see log) |

Both exact passes are the two problems solvable by pure day-count
arithmetic, with no iterative equation to solve. On every problem that
needed a yield resolved by iteration, the batch's answers show the same
shortcut: stating something like "approximately 4.1% annual" rather than
converging, then carrying that rough figure through duration, DV01, or
convexity. The one exception, `fi-007`, drifted for a different reason — a
16-term manual summation with small per-term arithmetic slips — showing
that "estimate instead of converge" isn't the *only* way this
configuration goes wrong, just the dominant one in this batch.

## Scope

Read this page as a set of documented incidents, not a controlled
comparison, for reasons worth being explicit about:

- **Single runs.** Almost every cell above is one run, not an average over
  several. A model that got one problem wrong might get it right on a
  second try, and vice versa — sampling variance is real and unmeasured
  here.
- **Inconsistent testing conditions.** The `claude-haiku-4.5-automated`
  batch ran through isolated, tool-free subagents with a fixed
  final-answer-format instruction. Every other row was pasted by hand from
  whatever chat interface was used, with whatever system prompt, prior
  context, and formatting instructions that interface's default state
  carried — none of which is recorded here. Comparing a `chatgpt` row to a
  `claude-haiku-4.5-automated` row is not an apples-to-apples comparison of
  model capability; it's a comparison of two different situations that
  happen to involve different models.
- **Uncertain model identity.** `chatgpt` and `gpt-5.6-luna` are logged as
  separate labels because that's what was reported at the time, not
  because they're known to be different models — nor are they known to be
  the same one. Treat their strong combined record as two data points
  under two names, not confirmed evidence about one model.
- **Coverage imbalance.** The Claude family has more rows than any other,
  because it's the only one this project can query automatically without
  the user paying for API access per call. That makes the dataset better
  at characterizing Claude's behavior in detail than at ranking providers
  against each other.

None of this makes the individual findings above less real — the
`gemini_yield_bias` pattern, in particular, is about as solid as a
five-repetition finding can be. It means the conclusion to draw is "here
is what happened in these specific runs, and here is a plausible
mechanism," not "here is how model X performs at yield-to-maturity in
general."

## Where this comes from

Every problem's ground truth is computed by
[`bondmath`](https://pypi.org/project/bondmath/), the library built after
finding that a language model solving this exact bond's modified duration
returned 3.0942 years — the wrong divisor for a semi-annual bond — and
then explained a resulting inconsistency as "third-order Taylor terms"
rather than tracing it to that error. See
[joselillotrax-cell/bond-desk](https://github.com/joselillotrax-cell/bond-desk)
for the original write-up. This benchmark exists to find out whether that
was a one-off or a pattern — and the `gemini_yield_bias` and
"estimate instead of converge" findings above suggest it's neither: it's a
family of related failure shapes, each specific to a model and sometimes to
a bond, that only volume of testing surfaces.
