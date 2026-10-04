"""The generation pipeline: render prompt -> cache -> route -> call (stream/timeout) -> repair/validate
-> retry with error feedback -> fallback to next model -> telemetry. Always returns a result dict."""
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from typing import Callable

from .cache import Cache
from .checks import detect_contradictions
from .config import MODELS, default_providers
from .providers import Completion, ProviderError, ProviderTimeout, StreamInterrupted, est_tokens
from .registry import Registry
from .router import route
from .schemas import SCHEMAS
from .telemetry import Telemetry
from .validate import parse_and_validate

Event = Callable[[str, dict], None]


@dataclass
class Attempt:
    model: str
    attempt: int
    ok: bool
    raw_valid: bool
    error: str | None
    latency_s: float
    input_tokens: int
    output_tokens: int
    cost_usd: float
    repairs: list[str]


class PromptOps:
    def __init__(self, registry: Registry | None = None, cache: Cache | None = None,
                 telemetry: Telemetry | None = None, providers=None, models=None,
                 max_retries: int = 2, timeout: float = float(os.getenv("PROMPTOPS_TIMEOUT", "10"))):
        self.registry = registry or Registry()
        self.cache = cache or Cache()
        self.telemetry = telemetry or Telemetry()
        self.providers = providers or default_providers()
        self.models = models or MODELS
        self.max_retries, self.timeout = max_retries, timeout

    # ------------------------------------------------------------------ helpers
    def _cost(self, m: str, tin: int, tout: int) -> float:
        c = self.models[m]
        return tin / 1000 * c.price_in + tout / 1000 * c.price_out

    def _call(self, model: str, prompt: str, stream: bool, on_event: Event | None, warnings: list[str]) -> Completion:
        prov = self.providers[self.models[model].provider]
        if not stream:
            return prov.complete(prompt, model, self.timeout)
        t0, chunks = time.perf_counter(), []
        try:
            for ch in prov.stream(prompt, model, self.timeout):
                chunks.append(ch)
                if on_event:
                    on_event("chunk", {"text": ch})
        except StreamInterrupted as e:
            warnings.append(f"stream interrupted ({e}); fell back to a non-streaming call")
            if on_event:
                on_event("interrupted", {"model": model})
            return prov.complete(prompt, model, self.timeout)
        text = "".join(chunks)
        return Completion(text, est_tokens(prompt), est_tokens(text), time.perf_counter() - t0, model)

    # ------------------------------------------------------------------ main entry
    def generate(self, task: str, text: str, *, prompt_version: str | None = None, model: str | None = None,
                 priority: str = "balanced", use_cache: bool = True, allow_fallback: bool = True,
                 stream: bool = False, on_event: Event | None = None) -> dict:
        res = {"ok": False, "task": task, "prompt_version": prompt_version, "data": None, "error": None,
               "model": None, "models_tried": [], "attempts": [], "input_tokens": 0, "output_tokens": 0,
               "cost_usd": 0.0, "latency_s": 0.0, "cached": False, "repaired": False, "fallback_used": False,
               "retried": False, "raw_valid_first_attempt": None, "warnings": []}
        try:
            if task not in SCHEMAS:
                raise ValueError(f"unknown task '{task}'. Supported: {sorted(SCHEMAS)}")
            if not text or not text.strip():
                raise ValueError("empty input: provide the messy instructions to convert")
            if model and model not in self.models:
                raise ValueError(f"unknown model '{model}'. Available: {sorted(self.models)}")
            res["warnings"] += detect_contradictions(text)
            prompt, pv = self.registry.render(task, prompt_version, {
                "input": text.strip(), "schema": json.dumps(SCHEMAS[task]), "task": task})
            res["prompt_version"] = pv.version
        except (ValueError, KeyError) as e:
            res["error"] = str(e.args[0]) if e.args else str(e)
            self.telemetry.record(res)
            return res

        chain = route(task, priority, self.models, len(text))
        if model:
            chain = [model] + ([m for m in chain if m != model] if allow_fallback else [])
        elif not allow_fallback:
            chain = chain[:1]
        ckey = Cache.key(chain[0], prompt)
        if use_cache and (hit := self.cache.get(ckey)):
            res.update(hit, cached=True, cost_usd=0.0, latency_s=0.0, warnings=res["warnings"] + hit.get("warnings", []))
            res["warnings"] = list(dict.fromkeys(res["warnings"]))
            self.telemetry.record(res)
            return res

        schema, last_err = SCHEMAS[task], "no model attempted"
        for mi, m in enumerate(chain):
            res["models_tried"].append(m)
            cur = prompt
            for n in range(self.max_retries + 1):
                if on_event:
                    on_event("start", {"model": m, "attempt": n + 1})
                try:
                    comp = self._call(m, cur, stream, on_event, res["warnings"])
                except ProviderTimeout as e:
                    last_err = f"timeout on {m}: {e}"
                    res["attempts"].append(asdict(Attempt(m, n + 1, False, False, last_err, self.timeout, 0, 0, 0.0, [])))
                    if res["raw_valid_first_attempt"] is None:
                        res["raw_valid_first_attempt"] = False
                    break  # timeouts are not retried on the same model; move down the fallback chain
                except ProviderError as e:
                    last_err = f"provider error on {m}: {e}"
                    res["attempts"].append(asdict(Attempt(m, n + 1, False, False, last_err, 0.0, 0, 0, 0.0, [])))
                    if res["raw_valid_first_attempt"] is None:
                        res["raw_valid_first_attempt"] = False
                    break
                pr = parse_and_validate(comp.text, schema)
                cost = self._cost(m, comp.input_tokens, comp.output_tokens)
                res["attempts"].append(asdict(Attempt(m, n + 1, pr.ok, pr.raw_valid, None if pr.ok else "; ".join(pr.errors[:3]),
                                                      round(comp.latency_s, 3), comp.input_tokens, comp.output_tokens,
                                                      round(cost, 6), pr.repairs)))
                if res["raw_valid_first_attempt"] is None:
                    res["raw_valid_first_attempt"] = pr.raw_valid
                res["input_tokens"] += comp.input_tokens
                res["output_tokens"] += comp.output_tokens
                res["cost_usd"] += cost
                res["latency_s"] += comp.latency_s
                if pr.ok:
                    res.update(ok=True, data=pr.data, model=m, error=None, repaired=bool(pr.repairs) or res["repaired"],
                               retried=n > 0 or res["retried"], fallback_used=mi > 0)
                    break
                last_err = "; ".join(pr.errors[:3])
                res["retried"] = True
                cur = f"{prompt}\n\nPREVIOUS ERROR: {last_err}\nReturn corrected JSON only."
            if res["ok"]:
                break
        if not res["ok"]:
            res["error"] = f"all models failed after {len(res['attempts'])} attempts; last error: {last_err}"
        res["cost_usd"] = round(res["cost_usd"], 6)
        res["latency_s"] = round(res["latency_s"], 3)
        if res["ok"] and use_cache:
            self.cache.put(ckey, {k: res[k] for k in ("ok", "data", "model", "models_tried", "attempts", "input_tokens",
                                                       "output_tokens", "repaired", "fallback_used", "retried",
                                                       "raw_valid_first_attempt", "warnings", "prompt_version")})
        self.telemetry.record(res)
        return res
