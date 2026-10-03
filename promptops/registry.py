"""Versioned prompt registry: one JSON file per task under prompts/, with variables, metadata and history."""
from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

VAR_RE = re.compile(r"\{\{(\w+)\}\}")


@dataclass
class PromptVersion:
    task: str
    version: str
    template: str
    metadata: dict
    changelog: str
    created: str

    @property
    def variables(self) -> list[str]:
        return sorted(set(VAR_RE.findall(self.template)))


class Registry:
    def __init__(self, root: str | Path = "prompts"):
        self.root = Path(root)
        self.root.mkdir(exist_ok=True)

    def _path(self, task: str) -> Path:
        return self.root / f"{task}.json"

    def _load(self, task: str) -> dict:
        p = self._path(task)
        if not p.exists():
            raise KeyError(f"no prompts registered for task '{task}'")
        return json.loads(p.read_text())

    def tasks(self) -> list[str]:
        return sorted(p.stem for p in self.root.glob("*.json"))

    def versions(self, task: str) -> list[PromptVersion]:
        return [PromptVersion(task=task, **v) for v in self._load(task)["versions"]]

    def active(self, task: str) -> str:
        return self._load(task)["active"]

    def get(self, task: str, version: str | None = None) -> PromptVersion:
        version = version or self.active(task)
        for v in self.versions(task):
            if v.version == version:
                return v
        raise KeyError(f"task '{task}' has no version '{version}'")

    def add_version(self, task: str, template: str, changelog: str, metadata: dict | None = None,
                    activate: bool = True) -> PromptVersion:
        doc = self._load(task) if self._path(task).exists() else {"active": None, "versions": []}
        n = len(doc["versions"]) + 1
        entry = {"version": f"v{n}", "template": template, "metadata": metadata or {}, "changelog": changelog,
                 "created": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        doc["versions"].append(entry)
        if activate or not doc["active"]:
            doc["active"] = entry["version"]
        self._path(task).write_text(json.dumps(doc, indent=2))
        return PromptVersion(task=task, **entry)

    def set_active(self, task: str, version: str) -> None:
        self.get(task, version)
        doc = self._load(task)
        doc["active"] = version
        self._path(task).write_text(json.dumps(doc, indent=2))

    def render(self, task: str, version: str | None, variables: dict) -> tuple[str, PromptVersion]:
        pv = self.get(task, version)
        missing = [v for v in pv.variables if v not in variables]
        if missing:
            raise KeyError(f"missing prompt variables: {missing}")
        return VAR_RE.sub(lambda m: str(variables[m.group(1)]), pv.template), pv

    def diff(self, task: str, a: str, b: str) -> str:
        ta, tb = self.get(task, a).template.splitlines(), self.get(task, b).template.splitlines()
        return "\n".join(difflib.unified_diff(ta, tb, a, b, lineterm=""))
