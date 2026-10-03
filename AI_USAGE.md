# AI usage

**Tools:** Claude (Anthropic) generated the first draft of the code, tests, docs and UI from the project brief.

**What I (the submitter) must do before submitting:** read every module, be able to explain it, and edit this file to reflect your own work.
The brief marks the adapter/router, the prompt registry + schema pipeline, and the regression runner as "your own work"; treat the generated versions as a starting point to understand, modify and extend.

**How output was verified**
- 25 automated tests (`python -m pytest -q`) covering repair, validation, registry, router, retry, fallback, timeout, caching, streaming, contradictions and the API.
- Ran the 50-case regression across 5 configurations and checked the numbers behave as the design predicts (v2 > v1, large >= small, router cheaper than large).
- Smoke-tested the API including SSE streaming with an injected interrupt.

**What was NOT verified:** the Ollama adapter against a live Ollama server; the UI in multiple browsers; real hosted-model pricing (mock prices are hypothetical).
