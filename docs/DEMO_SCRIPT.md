# 6-minute demo shot list
1. (0:00) Problem: messy brief in, trustworthy JSON out. Show the repo layout.
2. (0:45) Experiment tab: same input, v1+small vs v2+large; point at validity, retries, tokens, cost.
3. (2:00) Inject `[[MALFORMED]]`, then `[[TIMEOUT]]`; show retry and fallback in the attempt log.
4. (3:00) Stream variant A with `[[INTERRUPT]]`; show the recovery message.
5. (3:45) Prompt registry tab: v1 vs v2 changelog; `registry.diff`.
6. (4:15) Terminal: `python -m promptops.regression`; walk through report.md and the "is the cheaper model enough" table.
7. (5:15) `pytest -q` green; explain the regression gate. Close with limitations (mock backends, Ollama untested).
