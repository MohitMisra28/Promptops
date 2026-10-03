"""Exact-match response cache keyed by sha256(model + rendered prompt). Optional JSONL persistence."""
from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path


class Cache:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self._d: dict[str, dict] = {}
        self._lock = threading.Lock()
        self.hits = self.misses = 0
        if self.path and self.path.exists():
            for line in self.path.read_text().splitlines():
                rec = json.loads(line)
                self._d[rec["k"]] = rec["v"]

    @staticmethod
    def key(model: str, prompt: str) -> str:
        return hashlib.sha256(f"{model}\x00{prompt}".encode()).hexdigest()

    def get(self, k: str):
        with self._lock:
            v = self._d.get(k)
            self.hits += v is not None
            self.misses += v is None
            return v

    def put(self, k: str, v: dict) -> None:
        with self._lock:
            self._d[k] = v
            if self.path:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a") as f:
                    f.write(json.dumps({"k": k, "v": v}) + "\n")
