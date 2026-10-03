from fastapi.testclient import TestClient

import app as appmod

c = TestClient(appmod.app)


def test_generate_and_compare_endpoints():
    r = c.post("/api/generate", json={"task": "task_list", "input": "Audit. Sam collects invoices urgent.", "use_cache": False}).json()
    assert r["ok"] and r["data"]["tasks"][0]["priority"] == "high"
    cmp = c.post("/api/compare", json={"task": "schedule", "input": "Offsite in Pune. kickoff 10am. lunch 1pm.",
                                       "variants": [{"prompt_version": "v1", "model": "mock-small"}, {"prompt_version": "v2", "model": "mock-large"}]}).json()
    assert len(cmp["results"]) == 2 and all(x["ok"] for x in cmp["results"])


def test_stream_endpoint_emits_final_event():
    text = c.get("/api/stream", params={"task": "announcement", "input": "Party in Goa. doors 6pm.", "model": "mock-small"}).text
    assert "event: chunk" in text and "event: final" in text


def test_registry_and_models_endpoints():
    assert c.get("/api/health").json() == {"status": "ok"}
    assert {m["name"] for m in c.get("/api/models").json()["models"]} >= {"mock-small", "mock-large"}
    assert c.get("/api/route", params={"task": "content_pack"}).json()["chain"][0] == "mock-large"
    assert c.get("/api/route", params={"task": "x", "priority": "nope"}).status_code == 400
    assert set(c.get("/api/prompts").json()) == {"schedule", "announcement", "task_list", "content_pack"}
