import json

from promptops import regression


def test_fixture_has_at_least_50_cases_with_expectations():
    cases = regression.load_cases()
    assert len(cases) >= 50 and len({c["id"] for c in cases}) == len(cases)
    assert all("expect" in c and c["task"] and "input" in c for c in cases)
    assert {"malformed_json", "contradictory", "timeout_fallback", "interrupted_stream"} <= {t for c in cases for t in c["tags"]}


def test_regression_gates(tmp_path):
    """The gate CI would run: the shipped configuration must not regress."""
    rep = regression.main(tmp_path)
    by = {c["label"]: c for c in rep["configs"]}
    prod = by["v2 + router (fallback on)"]
    assert prod["pass_rate"] >= 0.98 and prod["schema_valid_final"] >= 0.95
    assert by["v2 + mock-small"]["instruction_following"] > by["v1 + mock-small"]["instruction_following"]  # prompt v2 is measurably better
    assert by["v2 + mock-small"]["cost_usd"] < by["v2 + mock-large"]["cost_usd"]                           # cheaper model is cheaper
    assert prod["cost_usd"] < by["v2 + mock-large"]["cost_usd"]                                            # routing saves money
    assert (tmp_path / "report.md").exists() and json.loads((tmp_path / "report.json").read_text())["n_cases"] == 50
