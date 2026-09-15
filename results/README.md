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
| `correct` | The grader's verdict. |
| `expected` | The reference value at grading time. |
| `detail` | What actually went wrong (or right), in enough detail that the row is useful without re-running anything. |

## Adding a row

1. `finance-benchmark show <id>` for the exact prompt, paste it to the model.
2. `finance-benchmark grade <id> <answer>` to get the verdict.
3. Append a row to `log.csv` with the detail column explaining *why*, not
   just restating pass/fail — that's the part worth keeping.
