"""Instruction checks: contradiction detection on inputs, and expectation checks on outputs."""
from __future__ import annotations

import json
import re

CONFLICTS = [
    (r"\b(short|brief|concise|one line)\b", r"\b(long|detailed|comprehensive|lengthy|in depth)\b", "short vs long"),
    (r"\b(formal|professional)\b", r"\b(casual|informal|slangy)\b", "formal vs casual"),
    (r"(?:under|at most|max(?:imum)?(?: of)?)\s+\d+\s+words", r"at least\s+\d+\s+words", "word limit vs word minimum"),
]


def detect_contradictions(text: str) -> list[str]:
    return [f"contradictory instructions detected ({label}); first-stated constraint takes priority"
            for a, b, label in CONFLICTS if re.search(a, text, re.I) and re.search(b, text, re.I)]


LIST_KEY = {"schedule": "items", "task_list": "tasks"}


def check_expectations(task: str, result: dict, expect: dict) -> list[str]:
    """Return a list of human-readable failures (empty list = case passed)."""
    fails: list[str] = []
    want_ok = expect.get("ok", True)
    if result["ok"] != want_ok:
        return [f"expected ok={want_ok} but got ok={result['ok']} ({result.get('error')})"]
    if not want_ok:
        if (sub := expect.get("error_contains")) and sub.lower() not in (result.get("error") or "").lower():
            fails.append(f"error should mention '{sub}'")
        return fails
    data = result["data"]
    blob = json.dumps(data, ensure_ascii=False).lower()
    for kw in expect.get("must_contain", []):
        if kw.lower() not in blob:
            fails.append(f"missing keyword '{kw}'")
    if (n := expect.get("min_items")) and len(data.get(LIST_KEY.get(task, ""), [])) < n:
        fails.append(f"expected >= {n} items, got {len(data.get(LIST_KEY.get(task, ''), []))}")
    if (n := expect.get("max_body_words")) and len(data.get("body", "").split()) > n:
        fails.append(f"body has {len(data['body'].split())} words, limit {n}")
    if (n := expect.get("hashtags")) and len(data.get("hashtags", [])) != n:
        fails.append(f"expected exactly {n} hashtags, got {len(data.get('hashtags', []))}")
    if (n := expect.get("tweet_max")) and len(data.get("tweet", "")) > n:
        fails.append(f"tweet is {len(data['tweet'])} chars, limit {n}")
    if (sub := expect.get("warning")) and not any(sub in w for w in result.get("warnings", [])):
        fails.append(f"expected a warning containing '{sub}'")
    return fails
