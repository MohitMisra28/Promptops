"""Create the initial prompt registry (v1 = naive baseline, v2 = strict). Safe to re-run: skips existing files."""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from pathlib import Path

from promptops.registry import Registry

V1 = "TASK: {{task}}\nConvert the following text into JSON.\nINPUT:\n{{input}}"
V2 = ("TASK: {{task}}\nYou are a precise structured-data generator.\n"
      "Return ONLY valid JSON matching this JSON Schema, with no markdown fences and no commentary:\n{{schema}}\n"
      "Respect every constraint in the input (word limits, counts, lengths) exactly.\nINPUT:\n{{input}}")

if __name__ == "__main__":
    reg = Registry(Path(__file__).resolve().parent.parent / "prompts")
    for task in ("schedule", "announcement", "task_list", "content_pack"):
        if (reg.root / f"{task}.json").exists():
            continue
        reg.add_version(task, V1, "Baseline: bare instruction, no schema in prompt.", {"owner": "platform", "style": "naive"}, activate=False)
        reg.add_version(task, V2, "Embed JSON schema, forbid fences/commentary, require constraint compliance.",
                        {"owner": "platform", "style": "strict"}, activate=True)
    print("seeded", reg.tasks())
