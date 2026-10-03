"""Common model interface + two backends: a deterministic mock and a real local model (Ollama).

Every backend implements `complete()` and `stream()`. The pipeline never imports a vendor SDK,
so adding a provider means adding one class here and one entry in config.MODELS.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterator


class ProviderError(Exception): ...
class ProviderTimeout(ProviderError): ...
class StreamInterrupted(ProviderError): ...


@dataclass
class Completion:
    text: str
    input_tokens: int
    output_tokens: int
    latency_s: float
    model: str


def est_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class Provider:
    name = "base"

    def complete(self, prompt: str, model: str, timeout: float = 30.0) -> Completion:
        raise NotImplementedError

    def stream(self, prompt: str, model: str, timeout: float = 30.0) -> Iterator[str]:
        text = self.complete(prompt, model, timeout).text
        for i in range(0, len(text), 16):
            yield text[i : i + 16]


# --------------------------------------------------------------------------- mock backend
MOCK_PROFILES = {
    # fail rates are cumulative percentage buckets: (fenced json, prose around json, missing field)
    "mock-small": {"base": 0.4, "per_token": 0.004, "loose": (20, 30, 45), "strict": (4, 6, 10)},
    "mock-large": {"base": 1.2, "per_token": 0.012, "loose": (0, 0, 0), "strict": (0, 0, 0)},
}
MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
DATE_RE = re.compile(rf"\b(\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTH}|{MONTH}\s+\d{{1,2}})", re.I)
TIME_RE = re.compile(r"\b(\d{1,2}:\d{2}(?:\s?[ap]m)?|\d{1,2}\s?[ap]m)\b", re.I)
WORDS_RE = re.compile(r"(?:under|at most|max(?:imum)?(?: of)?)\s+(\d+)\s+words", re.I)
TAGS_RE = re.compile(r"exactly\s+(\d+)\s+hashtags", re.I)
LEAST_RE = re.compile(r"at least\s+\d+\s+words", re.I)


class MockProvider(Provider):
    """Deterministic fake LLM. Quality depends on model tier and on how strict the prompt is,
    so prompt/model changes are *measurable* without any paid API.

    Failure injection tags (put them in the input text): [[MALFORMED]], [[TIMEOUT]] (small model
    only), [[TIMEOUT_ALL]], [[INTERRUPT]] (streaming). A retry prompt containing PREVIOUS ERROR
    always gets a clean answer, mimicking how real models respond to error feedback.
    Latency is *simulated* (reported, then slept for scale * latency)."""

    name = "mock"

    def __init__(self, scale: float | None = None):
        self.scale = float(os.getenv("MOCK_LATENCY_SCALE", "0.01")) if scale is None else scale

    @staticmethod
    def _input(prompt: str) -> str:
        return prompt.split("INPUT:\n", 1)[1].split("\n\nPREVIOUS ERROR:")[0]

    def _good(self, task: str, inp: str, obeys: bool) -> dict:
        clean = re.sub(r"\[\[\w+\]\]", "", inp)
        segs = [p.strip(" \t-•*") for p in re.split(r"[.;\n]+", clean)]
        segs = [s for s in segs if s and not WORDS_RE.search(s) and not TAGS_RE.search(s) and not LEAST_RE.search(s)]
        title = (segs[0] if segs else "Untitled")[:80]
        body = segs[1:] or segs[:1]
        m = DATE_RE.search(clean)
        date = m.group(1) if m else "TBD"
        if task == "schedule":
            items = []
            for s in body:
                t = TIME_RE.search(s)
                items.append({"time": t.group(1) if t else "TBD", "activity": (TIME_RE.sub("", s).strip(" ,:-") or s)})
            return {"title": title, "date": date, "items": items}
        if task == "task_list":
            tasks = []
            for s in body:
                o = re.search(r"\b(?:by|owner|assigned to|with)\s+([A-Z][a-z]+)", s) or re.match(r"([A-Z][a-z]+)\s+\w+s\b", s)
                prio = "high" if re.search(r"urgent|asap|critical|deadline", s, re.I) else (
                    "low" if re.search(r"optional|nice to have", s, re.I) else "medium")
                tasks.append({"task": s, "owner": o.group(1) if o else "Unassigned", "priority": prio})
            return {"tasks": tasks}
        text = ". ".join(body) + "."
        limit = WORDS_RE.search(inp)
        if task == "announcement":
            if obeys and limit:
                text = " ".join(text.split()[: int(limit.group(1))])
            return {"headline": title, "body": text, "call_to_action": f"Save the date: {date}"}
        # content_pack
        n = int(TAGS_RE.search(inp).group(1)) if (obeys and TAGS_RE.search(inp)) else 3
        tags = ["#" + re.sub(r"\W", "", w.title()) for w in title.split() if len(w) > 3]
        tags = list(dict.fromkeys(tags + ["#Event", "#Team", "#Update", "#Plan", "#Agenda", "#News"]))[:n]
        tweet = f"{title}: {text}"
        if obeys and len(tweet) > 280:
            tweet = tweet[:277] + "..."
        return {"tweet": tweet, "email_subject": title[:60], "summary": text, "hashtags": tags}

    def complete(self, prompt: str, model: str, timeout: float = 30.0) -> Completion:
        if model not in MOCK_PROFILES:
            raise ProviderError(f"unknown mock model {model}")
        prof = MOCK_PROFILES[model]
        task = re.search(r"TASK:\s*(\w+)", prompt).group(1)
        inp = self._input(prompt)
        retry = "PREVIOUS ERROR:" in prompt
        strict = "Return ONLY valid JSON" in prompt
        obeys = "Respect every constraint" in prompt
        if "[[TIMEOUT_ALL]]" in inp or ("[[TIMEOUT]]" in inp and model == "mock-small" and not retry):
            raise ProviderTimeout(f"{model} exceeded {timeout}s")
        obj = self._good(task, inp, obeys)
        text = json.dumps(obj, ensure_ascii=False)
        if "[[MALFORMED]]" in inp and not retry:
            text = text[: len(text) // 2]
        elif not retry:
            h = int(hashlib.sha256(f"{model}|{task}|{inp}|{strict}".encode()).hexdigest()[:8], 16) % 100
            fence, prose, missing = prof["strict" if strict else "loose"]
            if h < fence:
                text = f"```json\n{text}\n```"
            elif h < prose:
                text = f"Sure! Here is the JSON you asked for:\n{text}\nLet me know if you need changes."
            elif h < missing:
                obj.pop(list(obj)[-1])
                text = json.dumps(obj, ensure_ascii=False)
        out_tok = est_tokens(text)
        latency = prof["base"] + prof["per_token"] * out_tok
        time.sleep(latency * self.scale)
        return Completion(text, est_tokens(prompt), out_tok, round(latency, 3), model)

    def stream(self, prompt: str, model: str, timeout: float = 30.0) -> Iterator[str]:
        text = self.complete(prompt, model, timeout).text
        chunks = [text[i : i + 12] for i in range(0, len(text), 12)]
        interrupt = "[[INTERRUPT]]" in prompt and "PREVIOUS ERROR:" not in prompt
        for i, ch in enumerate(chunks):
            if interrupt and i == len(chunks) // 2:
                raise StreamInterrupted("connection dropped mid-stream")
            yield ch


# --------------------------------------------------------------------------- real backend (free, local)
class OllamaProvider(Provider):
    """Real model via Ollama (https://ollama.com), free and local. Enable with PROMPTOPS_ENABLE_OLLAMA=1."""

    name = "ollama"

    def __init__(self, host: str | None = None):
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")

    def _open(self, prompt: str, model: str, stream: bool, timeout: float):
        body = json.dumps({"model": model, "prompt": prompt, "stream": stream, "format": "json"}).encode()
        req = urllib.request.Request(f"{self.host}/api/generate", body, {"Content-Type": "application/json"})
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except (socket.timeout, TimeoutError) as e:
            raise ProviderTimeout(str(e)) from e
        except urllib.error.URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise ProviderTimeout(str(e)) from e
            raise ProviderError(f"ollama unreachable: {e.reason}") from e

    def complete(self, prompt: str, model: str, timeout: float = 30.0) -> Completion:
        t0 = time.perf_counter()
        try:
            with self._open(prompt, model, False, timeout) as r:
                d = json.load(r)
        except (socket.timeout, TimeoutError) as e:
            raise ProviderTimeout(str(e)) from e
        return Completion(d.get("response", ""), d.get("prompt_eval_count", est_tokens(prompt)),
                          d.get("eval_count", est_tokens(d.get("response", ""))), time.perf_counter() - t0, model)

    def stream(self, prompt: str, model: str, timeout: float = 30.0) -> Iterator[str]:
        try:
            with self._open(prompt, model, True, timeout) as r:
                for line in r:
                    if line.strip():
                        yield json.loads(line).get("response", "")
        except (socket.timeout, TimeoutError, ConnectionError) as e:
            raise StreamInterrupted(str(e)) from e
