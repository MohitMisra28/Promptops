"""Schema validation + cheap deterministic repair. Anything repair cannot fix triggers a retry
with the validation error fed back to the model."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from jsonschema import Draft202012Validator


@dataclass
class ParseResult:
    ok: bool
    data: dict | None = None
    errors: list[str] = field(default_factory=list)
    repairs: list[str] = field(default_factory=list)
    raw_valid: bool = False  # valid with zero repair


def _errors(data, schema) -> list[str]:
    return [f"{'/'.join(map(str, e.path)) or '$'}: {e.message}" for e in Draft202012Validator(schema).iter_errors(data)]


def parse_and_validate(text: str, schema: dict) -> ParseResult:
    repairs: list[str] = []
    cand = text.strip()
    if cand.startswith("```"):
        cand = re.sub(r"^```(?:json)?\s*|\s*```$", "", cand).strip()
        repairs.append("stripped_markdown_fence")
    for attempt in range(2):
        try:
            data = json.loads(cand)
            break
        except json.JSONDecodeError as e:
            if attempt == 1:
                return ParseResult(False, None, [f"invalid JSON: {e.msg} at char {e.pos}"], repairs)
            start, end = cand.find("{"), cand.rfind("}")
            if start != -1 and end > start and (start > 0 or end < len(cand) - 1):
                cand = cand[start : end + 1]
                repairs.append("extracted_json_object")
            fixed = re.sub(r",(\s*[}\]])", r"\1", cand)
            if fixed != cand:
                cand = fixed
                repairs.append("removed_trailing_comma")
    errs = _errors(data, schema)
    return ParseResult(not errs, data if not errs else None, errs, repairs, raw_valid=(not errs and not repairs))
