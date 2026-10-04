import json
import shutil
from pathlib import Path

import pytest

from promptops.cache import Cache
from promptops.checks import check_expectations, detect_contradictions
from promptops.pipeline import PromptOps
from promptops.providers import MockProvider
from promptops.registry import Registry
from promptops.router import route
from promptops.schemas import SCHEMAS
from promptops.telemetry import Telemetry
from promptops.validate import parse_and_validate

ROOT = Path(__file__).resolve().parent.parent
GOOD = "Offsite in Pune on 3 March. kickoff 10am. lunch 1pm. Priya books venue."


@pytest.fixture
def ops(tmp_path):
    shutil.copytree(ROOT / "prompts", tmp_path / "prompts")
    return PromptOps(Registry(tmp_path / "prompts"), Cache(), Telemetry(), providers={"mock": MockProvider(scale=0)})


# ---- validation / repair
def test_valid_json_is_raw_valid():
    r = parse_and_validate('{"tasks":[{"task":"a","owner":"b","priority":"low"}]}', SCHEMAS["task_list"])
    assert r.ok and r.raw_valid and not r.repairs

def test_markdown_fence_and_trailing_comma_are_repaired():
    r = parse_and_validate('```json\n{"headline":"h","body":"b","call_to_action":"c",}\n```', SCHEMAS["announcement"])
    assert r.ok and not r.raw_valid and "stripped_markdown_fence" in r.repairs and "removed_trailing_comma" in r.repairs

def test_prose_wrapped_json_is_extracted():
    assert parse_and_validate('Sure!\n{"headline":"h","body":"b","call_to_action":"c"}\nBye', SCHEMAS["announcement"]).ok

def test_truncated_json_fails_with_message():
    r = parse_and_validate('{"headline":"h","bo', SCHEMAS["announcement"])
    assert not r.ok and "invalid JSON" in r.errors[0]

def test_schema_violation_reports_path():
    r = parse_and_validate('{"tasks":[{"task":"a","owner":"b","priority":"urgent"}]}', SCHEMAS["task_list"])
    assert not r.ok and "tasks/0/priority" in r.errors[0]

# ---- registry
def test_registry_versions_render_and_history(tmp_path):
    reg = Registry(tmp_path)
    reg.add_version("schedule", "A {{input}}", "first")
    reg.add_version("schedule", "B {{input}} {{task}}", "second", {"owner": "me"})
    assert [v.version for v in reg.versions("schedule")] == ["v1", "v2"] and reg.active("schedule") == "v2"
    assert reg.render("schedule", "v1", {"input": "x"})[0] == "A x"
    assert "-A {{input}}" in reg.diff("schedule", "v1", "v2")
    with pytest.raises(KeyError):
        reg.render("schedule", "v2", {"input": "x"})  # missing {{task}}
    reg.set_active("schedule", "v1")
    assert reg.get("schedule").version == "v1"

# ---- router
def test_router_rules():
    assert route("announcement", "cost")[0] == "mock-small"
    assert route("announcement", "quality")[0] == "mock-large"
    assert route("content_pack", "balanced")[0] == "mock-large"
    assert route("announcement", "balanced")[0] == "mock-small"
    assert set(route("schedule", "speed")) == {"mock-small", "mock-large"}
    with pytest.raises(ValueError):
        route("schedule", "bogus")

# ---- pipeline behaviour
def test_happy_path_tracks_tokens_latency_cost(ops):
    r = ops.generate("schedule", GOOD, prompt_version="v2", model="mock-large")
    assert r["ok"] and r["input_tokens"] > 0 and r["output_tokens"] > 0 and r["latency_s"] > 0 and r["cost_usd"] > 0
    assert r["data"]["items"][0]["time"] == "10am"

def test_cache_hit_is_free_and_flagged(ops):
    first = ops.generate("schedule", GOOD, model="mock-small")
    second = ops.generate("schedule", GOOD, model="mock-small")
    assert not first["cached"] and second["cached"] and second["cost_usd"] == 0 and second["data"] == first["data"]
    assert ops.cache.hits == 1

def test_malformed_json_recovers_via_retry_with_error_feedback(ops):
    r = ops.generate("schedule", "Design review on 4 May. kickoff 10am. [[MALFORMED]] wrap-up 11am.", model="mock-large", use_cache=False)
    assert r["ok"] and r["retried"] and len(r["attempts"]) == 2 and "invalid JSON" in r["attempts"][0]["error"]

def test_timeout_falls_back_to_next_model(ops):
    r = ops.generate("schedule", "Retro in Pune on 6 June. standup 9am. [[TIMEOUT]] review 11am.", model="mock-small", use_cache=False)
    assert r["ok"] and r["fallback_used"] and r["model"] == "mock-large" and "timeout" in r["attempts"][0]["error"]

def test_timeout_without_fallback_gives_clear_error(ops):
    r = ops.generate("schedule", "x [[TIMEOUT]] y 9am", model="mock-small", allow_fallback=False, use_cache=False)
    assert not r["ok"] and "timeout" in r["error"].lower()

def test_all_models_timeout_is_a_clean_failure(ops):
    r = ops.generate("announcement", "Maintenance [[TIMEOUT_ALL]] 2am", use_cache=False)
    assert not r["ok"] and r["data"] is None and "all models failed" in r["error"] and len(r["models_tried"]) == 2

def test_interrupted_stream_falls_back_to_non_streaming(ops):
    events = []
    r = ops.generate("schedule", "Webinar in Jaipur on 7 July. intro 3pm. demo 4pm. [[INTERRUPT]]", model="mock-large",
                     stream=True, on_event=lambda k, p: events.append(k), use_cache=False)
    assert r["ok"] and any("interrupted" in w for w in r["warnings"]) and "interrupted" in events and "chunk" in events

def test_streaming_without_interrupt_yields_chunks(ops):
    chunks = []
    r = ops.generate("schedule", GOOD, model="mock-large", stream=True, on_event=lambda k, p: k == "chunk" and chunks.append(p["text"]), use_cache=False)
    assert r["ok"] and json.loads("".join(chunks)) == r["data"]

def test_contradictory_instructions_are_flagged_not_fatal(ops):
    r = ops.generate("announcement", "Office move on 1 October. Be brief. Make it long and detailed. Keep the body under 20 words.", prompt_version="v2")
    assert r["ok"] and any("contradict" in w for w in r["warnings"]) and len(r["data"]["body"].split()) <= 20
    assert detect_contradictions("Be formal. Keep it casual.")

def test_bad_inputs_never_raise(ops):
    assert "empty input" in ops.generate("schedule", "   ")["error"]
    assert "unknown task" in ops.generate("poem", "hi")["error"]
    assert "unknown model" in ops.generate("schedule", "hi", model="gpt-9")["error"]
    assert "no version" in ops.generate("schedule", "hi", prompt_version="v99")["error"]

def test_telemetry_records_every_run(ops):
    ops.generate("schedule", GOOD); ops.generate("schedule", "   ")
    s = ops.telemetry.summary()
    assert s["runs"] == 2 and 0 < s["success_rate"] < 1

def test_strict_prompt_beats_naive_prompt_on_instructions(ops):
    txt = "Launch in Goa on 2 May. doors 6pm. show 7pm. Use exactly 4 hashtags."
    naive = ops.generate("content_pack", txt, prompt_version="v1", model="mock-large", use_cache=False)
    strict = ops.generate("content_pack", txt, prompt_version="v2", model="mock-large", use_cache=False)
    assert len(naive["data"]["hashtags"]) != 4 and len(strict["data"]["hashtags"]) == 4

def test_check_expectations_detects_violations():
    res = {"ok": True, "data": {"body": "a b c d"}, "warnings": []}
    assert check_expectations("announcement", res, {"max_body_words": 2})
    assert not check_expectations("announcement", res, {"max_body_words": 4})

def test_router_sends_long_inputs_to_large_model():
    assert route("announcement", "balanced", input_len=50)[0] == "mock-small"
    assert route("announcement", "balanced", input_len=900)[0] == "mock-large"
