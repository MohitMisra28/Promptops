"""Per-run telemetry: tokens, latency, cost, outcome. In-memory with optional JSONL sink."""
from __future__ import annotations

import json
import statistics
import threading
import time
from pathlib import Path


class Telemetry:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self.records: list[dict] = []
        self._lock = threading.Lock()

    def record(self, r: dict) -> None:
        row = {"ts": time.time(), **{k: r.get(k) for k in (
            "task", "prompt_version", "model", "ok", "cached", "fallback_used", "retried", "repaired",
            "input_tokens", "output_tokens", "cost_usd", "latency_s", "error")}}
        with self._lock:
            self.records.append(row)
            if self.path:
                with self.path.open("a") as f:
                    f.write(json.dumps(row) + "\n")

    def summary(self) -> dict:
        rs = self.records
        if not rs:
            return {"runs": 0}
        lat = sorted(r["latency_s"] for r in rs if not r["cached"])
        by_model: dict[str, dict] = {}
        for r in rs:
            m = by_model.setdefault(r["model"] or "none", {"runs": 0, "cost_usd": 0.0})
            m["runs"] += 1
            m["cost_usd"] = round(m["cost_usd"] + (r["cost_usd"] or 0), 6)
        return {
            "runs": len(rs), "success_rate": round(sum(r["ok"] for r in rs) / len(rs), 3),
            "cache_hit_rate": round(sum(bool(r["cached"]) for r in rs) / len(rs), 3),
            "fallback_rate": round(sum(bool(r["fallback_used"]) for r in rs) / len(rs), 3),
            "retry_rate": round(sum(bool(r["retried"]) for r in rs) / len(rs), 3),
            "input_tokens": sum(r["input_tokens"] or 0 for r in rs),
            "output_tokens": sum(r["output_tokens"] or 0 for r in rs),
            "cost_usd": round(sum(r["cost_usd"] or 0 for r in rs), 6),
            "latency_mean_s": round(statistics.mean(lat), 3) if lat else 0,
            "latency_p95_s": round(lat[min(len(lat) - 1, int(0.95 * len(lat)))], 3) if lat else 0,
            "by_model": by_model,
        }
