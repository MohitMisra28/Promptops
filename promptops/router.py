"""Routing rule: task complexity x caller priority -> ordered model chain (first = primary, rest = fallbacks)."""
from __future__ import annotations

from .config import MODELS

COMPLEXITY = {"announcement": 1, "task_list": 2, "schedule": 2, "content_pack": 3}
PRIORITIES = ("quality", "speed", "cost", "balanced")


def route(task: str, priority: str = "balanced", models=None) -> list[str]:
    models = models or MODELS
    if priority not in PRIORITIES:
        raise ValueError(f"priority must be one of {PRIORITIES}")
    cheap_first = sorted(models.values(), key=lambda m: (m.price_out, m.name))
    if priority == "quality" or (priority == "balanced" and COMPLEXITY.get(task, 3) >= 3):
        order = list(reversed(cheap_first))  # premium first
    else:  # speed, cost, or a simple/medium task under balanced
        order = cheap_first
    return [m.name for m in order]
