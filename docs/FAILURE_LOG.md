# Failure log

Failures seen while building and running the 50-case suite, what caused them, and how the system handles them.
Rates come from `results/report.md`. Llama 3.2 3B (via Ollama) is the real backend; the mock backends are simulated.

## A. Real-model failures (Llama 3.2 3B)

| # | Failure | Where seen | Cause | Handling / outcome |
|---|---|---|---|---|
| 1 | Invented field names (`properties`, `location`, `events`, `preparer`, `orders`) and missing required fields | v1 + Llama: 0% valid on first try and at the end, 4% pass rate | The naive prompt does not show the schema, so the model guesses a structure | Prompt v2 puts the JSON Schema in the prompt: 90% valid on first try, 96% final |
| 2 | Dropped schedule items (tc01: 3 of 5, tc05: 3 of 5, tc17: 4 of 5, tc21 and tc25: 4 of 6) | v2, v3, v4 + Llama | The model merges or summarises agenda items | Prompt v4 ("one entry per input item") did not fix it; not resolved |
| 3 | Paraphrased keywords (tc03 "venue", tc07 "cake", tc11 "wifi", tc15 "dashboard", tc19 "sweets") | v2, v3, v4 + Llama | The model rewrites the task in its own words. The check uses exact substring matching, so a correct paraphrase counts as a failure | Left as is and reported as a limitation of the check |
| 4 | Invalid enum values: `priority` set to "urgent" or "no priority specified" | tc07 on v4 + Llama | The model does not stick to high, medium or low | Schema validation catches it and the pipeline retries with the exact error; after 3 attempts the case still failed |
| 5 | Wrong JSON type inside a list (`'{' is not of type 'object'`) | tc07 on v2 + Llama | Malformed list item | Same retry path; failed after 3 attempts |
| 6 | Timeout on one case (tc12 content_pack) | v4 + Llama | The model took longer than the timeout set for the run | Reported as a clean failure with a timeout message; no exception |
| 7 | Constraint checks fail even when the JSON is valid | v2 + Llama: 69% instruction following | The model ignores word limits and hashtag counts more often than the large mock | Not fixed; reported in the README |
| 8 | Prompts v3 and v4 did not beat v2 | pass rates of 64% (v3), 68% (v4) and 68% (v2) | Differences are within run-to-run noise | v2 stays the active prompt |
| 9 | Router sends simple tasks to the free local model first | router row: 74% pass rate | The router ranks models by price only, and Llama costs $0 | Retries and fallback give 100% final validity, but quality drops. A per-model quality rating would fix it; future work |
| 10 | Failure-injection tags (`[[TIMEOUT_ALL]]`, `[[INTERRUPT]]`) have no effect | Cases tc46 and tc47 with a real model | Only the mock backends understand these tags | Expected, not individually checked. These two cases cannot pass with Llama |

## B. Mock-backend failures (simulated, deterministic)

| # | Failure | Where seen | Handling |
|---|---|---|---|
| 11 | JSON wrapped in markdown fences | v1 + mock-small, about 20% of runs | `validate.py` strips the fences; recorded as `repaired` |
| 12 | Chatty text around the JSON | v1 + mock-small, about 10% | Extract from the first `{` to the last `}` |
| 13 | Required field missing | v1 + mock-small about 15%, v2 about 4% | Schema error text is appended to the prompt and the retry succeeds |
| 14 | Truncated or malformed JSON (tc41, tc42) | all mock models | Not repairable; retry with `invalid JSON ... at char N` feedback recovers it |
| 15 | Naive prompt ignores constraints (4 hashtags becomes 3, long bodies) | v1 on both mock models | Prompt v2 states the constraints: instruction following 75% to 98% on the small mock |
| 16 | Small mock times out (tc45) | v2 + mock-small, no fallback: 1 failing case | The fallback chain moves to mock-large and the case passes |
| 17 | Every model times out (tc46) | by design | Clean `ok: false` with `all models failed ... timeout`, no exception |
| 18 | Stream drops mid-response (tc47) | by design | Warning plus a non-streaming retry; result stays valid |
| 19 | Contradictory instructions (tc43, tc44) | by design | Warning is attached; the first stated constraint wins |
| 20 | Empty input (tc49) | by design | Rejected before any model call, so no cost |

## C. Build and workflow mistakes

| # | Mistake | Fix |
|---|---|---|
| 21 | Shell brace expansion in `mkdir` made a literal folder and the first batch of files failed to write | Created the directories one by one and rewrote the files |
| 22 | `scripts/seed_prompts.py` failed with `ModuleNotFoundError` | Added the repo root to `sys.path` |
| 23 | `pip install` reported an opentelemetry version conflict with other packages on my machine | Not caused by this project; moved to a fresh virtual environment |
| 24 | `uvicorn` was not on PATH | Ran it as `python -m uvicorn app:app` |
| 25 | Pasted a line of Python code into PowerShell | Made the edit in `pipeline.py` instead |
| 26 | `scripts/add_v3.py` printed "added v3" on every run but created a new version each time, leaving duplicate versions v3 to v6 | Wrote `scripts/dedupe_versions.py` to keep four distinct versions; the script now prints the real version number |
| 27 | Git remote was set to the placeholder `YOUR_USERNAME` | Corrected with `git remote set-url` |
| 28 | `git push` rejected because the README was edited on github.com | `git pull --rebase`, then pushed |

## Known remaining gaps

- Llama still drops schedule items and paraphrases keywords; the prompts tried so far do not fix this.
- Routing uses price only, with no quality score.
- Keyword checks are exact substring matches.
- Llama results change from run to run, so small gaps between prompt versions are not reliable.