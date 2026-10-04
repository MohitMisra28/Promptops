# AI usage

## Tools

- **Claude (Anthropic)**, used in the claude.ai chat interface, for the first draft of the project and for help with debugging and setup.
- **Llama 3.2 3B**, run locally through Ollama. It is a backend of the platform being built, not a coding assistant.

## What the AI produced

Claude generated the first version of the repository from the project brief:
- the provider interface, mock backends and the Ollama adapter
- the prompt registry, schemas, validation and repair, caching, telemetry and the pipeline
- the router, the 50-case generator and the regression runner
- the FastAPI app and the experiment UI
- the automated tests, the first versions of the README and the architecture notes

## What I did myself

- Installed and ran the project, ran the test suite, and fixed my environment (virtual environment, PATH and dependency problems).
- Installed Ollama, downloaded Llama 3.2 3B, and made it a real backend by setting the environment variables and adding a configurable timeout to `pipeline.py`.
- Extended the regression runner to compare prompt versions on the real model, and ran it.
- Added prompt versions v3 and v4 (the v4 rule came from reading Llama's failures), found that my script had created duplicate versions, and cleaned them up.
- Added the router rule that sends long inputs to the large model, and the test for it. The test suite went from 25 to 26 tests.
- Read the regression results and corrected an overclaim: v4 did not beat v2, so v2 stays active.
- Set up the GitHub repository, committed the work, and resolved a rejected push.


## How the output was checked

- 26 automated tests pass (`python -m pytest -q`), including a regression gate on the mock backends.
- The 50-case regression ran on five mock configurations and on four prompt versions with the real model. The results behave as the design predicts: the strict prompt helps, the large mock beats the small one, and the router lowers cost with mock backends only.
- I read the failures from the real model (see `docs/FAILURE_LOG.md`) and found that the results with Llama were less favourable than with the mocks. I reported them as they are.
- The server started and served the UI, `/api/models` and `/api/prompts` with HTTP 200.
  

## What was not verified

- Results from the mock backends use simulated latency and hypothetical prices, so absolute numbers are illustrative.
- Llama output varies between runs. I ran the regression once per prompt version, so small differences between versions are not reliable.
- The UI was not tested in several browsers, and I did not deploy the app.
- The tags that inject failures (`[[TIMEOUT_ALL]]`, `[[INTERRUPT]]`) only work on the mocks, so two edge cases cannot pass with Llama.

## Understanding

I can explain how a request moves through the system: the prompt is rendered from the registry, the cache is checked, the router picks a model order, the model is called with a timeout, the output is repaired and validated, it is retried with the error message if invalid, a fallback model is used if needed, and the result is recorded in telemetry.
