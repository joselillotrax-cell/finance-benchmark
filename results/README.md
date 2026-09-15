# Results log

`log.csv` is a hand-kept record of real grading runs — a model was asked a
problem's `prompt` verbatim, its answer was graded with `finance-benchmark
grade`, and the row records what happened. Not a controlled study: model
versions, prompting, and sampling all vary, and each row is a single run, not
an average over several. Treat it as a growing set of documented incidents,
not a leaderboard, until there are enough rows per model to say anything
statistical.

## Columns

| Column | Meaning |
|---|---|
| `date` | When the model was asked, ISO format. |
| `model` | Model name as reported by the interface used, as precisely as known. |
| `problem_id` | The problem graded, e.g. `fi-010`. |
| `candidate_answer` | What was graded — the numeric value, or the audit JSON. |
| `status` | `correct`, `near_miss`, or `wrong` — see below. |
| `correct` | `True` only when `status` is `correct`. Kept for simple pass/fail filtering. |
| `expected` | The reference value at grading time. |
| `detail` | What actually went wrong (or right), in enough detail that the row is useful without re-running anything. |

## Why three statuses, not two

An answer within a problem's `tolerance` is `correct`. Further off but within
a wider `loose_tolerance` (10x `tolerance` by default) is `near_miss`: close
enough that the method was probably sound and the gap is precision, not
concept. Anything past that is `wrong`.

This exists because a genuinely close miss and a wrong-method failure are not
the same finding, and folding them into one pass/fail bit throws that away.
`gpt-5.6-luna` landing on 4.6867% and `claude` landing on 4.6918% (0.51 bp
off, and the same value an earlier Haiku 4.5 session produced for this exact
bond) are different results worth keeping different. `gemini-3.6-flash`
landing on 4.7174% (3.07 bp off, in two independent runs) is not a near miss
by comparison — it's outside the wider band too, and the repetition across
runs suggests a systematic bias rather than a rounding difference.

A wrong verdict on an `audit` problem is never a near miss, even if a nearby
number was also supplied — misjudging whether a claim is plausible is a
conceptual failure, not an imprecision.

## Adding a row

1. `finance-benchmark show <id>` for the exact prompt, paste it to the model.
2. `finance-benchmark grade <id> <answer>` to get the verdict.
3. Append a row to `log.csv` with the detail column explaining *why*, not
   just restating pass/fail — that's the part worth keeping.
