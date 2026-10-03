# Failure log

Failures observed while building and running the 50-case suite, with the fix or handling.

| # | Failure | Where seen | Handling |
|---|---|---|---|
| 1 | Model wraps JSON in markdown fences | v1+small, ~20% of runs | `validate.py` strips fences; recorded as `repaired`, not `raw_valid` |
| 2 | Chatty prose around the JSON | v1+small, ~10% | Extract first `{` to last `}` |
| 3 | Required field missing | v1+small ~15%, v2+small ~4% | Schema error text appended to the prompt, retry succeeds |
| 4 | Truncated / malformed JSON (`[[MALFORMED]]`, tc41, tc42) | all models | Not repairable, so retry with `invalid JSON ... at char N` feedback; recovered in 2nd attempt |
| 5 | Naive prompt ignores constraints (4 hashtags -> 3, long body) | v1 on both models, 11-12 failing cases | Prompt v2 states constraints; instruction following 75% -> 98% on small |
| 6 | Small model times out (`[[TIMEOUT]]`, tc45) | v2+small without fallback = 1 failing case | Fallback chain to large; router config passes |
| 7 | All models time out (tc46) | by design | Clean `ok:false` with `all models failed ... timeout`, no exception |
| 8 | Stream drops mid-response (tc47) | by design | Warning + non-streaming retry; result still valid |
| 9 | Contradictory instructions (tc43, tc44) | by design | Warning surfaced; first constraint wins |
| 10 | Empty input (tc49) | by design | Rejected before any model call; no cost |

Build-time mistakes: (a) shell brace expansion in `mkdir` created a literal directory and the first batch of files failed to write; re-created directories and rewrote files. (b) `scripts/seed_prompts.py` failed with `ModuleNotFoundError`; fixed by adding the repo root to `sys.path`.
Known remaining gap: `schedule` on small model is only "enough" with fallback enabled; the plain small model fails the timeout case.
