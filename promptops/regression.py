"""Repeatable prompt/model regression runner.
   python -m promptops.regression            # full comparison, writes results/report.{json,md}
Compares prompt versions x model configs on the fixed test set and reports schema validity,
instruction following, latency, tokens, cost and failures."""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from .cache import Cache
from .checks import check_expectations
from .pipeline import PromptOps
from .registry import Registry
from .telemetry import Telemetry

ROOT = Path(__file__).resolve().parent.parent
CONSTRAINT_KEYS = ("must_contain", "min_items", "max_body_words", "hashtags", "tweet_max")


def load_cases(path: Path | None = None) -> list[dict]:
    return json.loads((path or ROOT / "data" / "test_cases.json").read_text())


def run_config(cases: list[dict], prompt_version: str, model: str | None, label: str, registry: Registry | None = None) -> dict:
    """model=None means 'use the production router with fallback enabled'."""
    ops = PromptOps(registry=registry or Registry(ROOT / "prompts"), cache=Cache(), telemetry=Telemetry())
    rows = []
    for c in cases:
        r = ops.generate(c["task"], c["input"], prompt_version=prompt_version, model=model, use_cache=False,
                         allow_fallback=model is None, stream=c.get("stream", False))
        fails = check_expectations(c["task"], r, c["expect"])
        rows.append({"id": c["id"], "task": c["task"], "tags": c["tags"], "ok": r["ok"], "passed": not fails, "failures": fails,
                     "raw_valid": bool(r["raw_valid_first_attempt"]), "latency_s": r["latency_s"], "tokens": r["input_tokens"] + r["output_tokens"],
                     "cost_usd": r["cost_usd"], "retried": r["retried"], "fallback": r["fallback_used"], "model": r["model"],
                     "error": r["error"], "has_constraints": any(k in c["expect"] for k in CONSTRAINT_KEYS) and c["expect"].get("ok", True)})
    gen = [r for r in rows if "empty_input" not in r["tags"]]  # empty input never reaches a model
    lat = sorted(r["latency_s"] for r in gen)
    cons = [r for r in rows if r["has_constraints"]]
    n_ok = sum(r["passed"] and True for r in cons if r["ok"])
    return {
        "label": label, "prompt_version": prompt_version, "model": model or "router(balanced)+fallback", "cases": len(rows),
        "schema_valid_raw": round(sum(r["raw_valid"] for r in gen) / len(gen), 3),
        "schema_valid_final": round(sum(r["ok"] for r in rows if r["id"] in {g["id"] for g in gen}) / len(gen), 3),
        "instruction_following": round(n_ok / len(cons), 3),
        "pass_rate": round(sum(r["passed"] for r in rows) / len(rows), 3),
        "latency_mean_s": round(statistics.mean(lat), 3), "latency_p95_s": lat[int(0.95 * (len(lat) - 1))],
        "tokens": sum(r["tokens"] for r in rows), "cost_usd": round(sum(r["cost_usd"] for r in rows), 5),
        "retry_rate": round(sum(r["retried"] for r in rows) / len(rows), 3),
        "fallback_rate": round(sum(r["fallback"] for r in rows) / len(rows), 3),
        "failures": [{"id": r["id"], "task": r["task"], "why": r["failures"]} for r in rows if not r["passed"]],
        "rows": rows,
    }


def cheaper_enough(small: dict, large: dict) -> list[dict]:
    out = []
    for task in sorted({r["task"] for r in small["rows"]}):
        s = [r for r in small["rows"] if r["task"] == task]
        l = [r for r in large["rows"] if r["task"] == task]
        sp, lp = sum(r["passed"] for r in s) / len(s), sum(r["passed"] for r in l) / len(l)
        sc, lc = sum(r["cost_usd"] for r in s), sum(r["cost_usd"] for r in l)
        out.append({"task": task, "small_pass": round(sp, 3), "large_pass": round(lp, 3), "small_cost": round(sc, 5),
                    "large_cost": round(lc, 5), "verdict": "small model is enough" if sp >= lp else "small model is NOT enough",
                    "small_failed": [r["id"] for r in s if not r["passed"]]})
    return out


def markdown(report: dict) -> str:
    L = ["# PromptOps comparison report", "",
         f"{report['n_cases']} fixed test cases. Mock backends: latency is **simulated**, cost uses **hypothetical** price tables "
         "(small $0.0002/$0.0006, large $0.003/$0.015 per 1k tokens in/out).", "",
         "| config | schema valid (first try) | schema valid (final) | instruction following | pass rate | mean latency s | p95 s | tokens | cost USD | retry | fallback |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in report["configs"]:
        L.append(f"| {c['label']} | {c['schema_valid_raw']:.0%} | {c['schema_valid_final']:.0%} | {c['instruction_following']:.0%} | {c['pass_rate']:.0%} | "
                 f"{c['latency_mean_s']} | {c['latency_p95_s']} | {c['tokens']} | {c['cost_usd']} | {c['retry_rate']:.0%} | {c['fallback_rate']:.0%} |")
    L += ["", "## Is the cheaper model enough? (prompt v2, no fallback)", "", "| task | small pass | large pass | small cost | large cost | verdict |", "|---|---|---|---|---|---|"]
    for r in report["cheaper_model"]:
        L.append(f"| {r['task']} | {r['small_pass']:.0%} | {r['large_pass']:.0%} | {r['small_cost']} | {r['large_cost']} | {r['verdict']} |")
    L += ["", "## Failures by config", ""]
    for c in report["configs"]:
        L.append(f"**{c['label']}** - {len(c['failures'])} failing case(s)")
        for f in c["failures"][:8]:
            L.append(f"- `{f['id']}` ({f['task']}): {'; '.join(f['why'])}")
        if len(c["failures"]) > 8:
            L.append(f"- ... and {len(c['failures']) - 8} more (see report.json)")
        L.append("")
    return "\n".join(L)


def main(out_dir: Path | None = None) -> dict:
    cases = load_cases()
    out_dir = out_dir or ROOT / "results"
    out_dir.mkdir(exist_ok=True)
    configs = [run_config(cases, v, m, f"{v} + {m}") for v in ("v1", "v2") for m in ("mock-small", "mock-large")]
    configs.append(run_config(cases, "v2", None, "v2 + router (fallback on)"))
    from .config import MODELS
    for m in [x for x in MODELS if not x.startswith("mock-")]:
        configs += [run_config(cases, v, m, f"{v} + {m}") for v in ("v1", "v2", "v3", "v4")]
    by = {(c["prompt_version"], c["model"]): c for c in configs}
    report = {"n_cases": len(cases), "configs": [{k: v for k, v in c.items() if k != "rows"} for c in configs],
              "cheaper_model": cheaper_enough(by[("v2", "mock-small")], by[("v2", "mock-large")]),
              "rows": {c["label"]: c["rows"] for c in configs}}
    (out_dir / "report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
    (out_dir / "report.md").write_text(markdown(report))
    return report


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    rep = main()
    print((ROOT / "results" / "report.md").read_text())
