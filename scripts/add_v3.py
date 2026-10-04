import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from promptops.registry import Registry

reg = Registry(pathlib.Path(__file__).resolve().parent.parent / "prompts")
RULE = "Include one entry for every activity or action in the input; never merge or drop entries. Copy names and places exactly as written.\n"
for task in reg.tasks():
    template = reg.get(task, "v2").template.replace("INPUT:\n", RULE + "INPUT:\n")
    reg.add_version(task, template, "Add tie-break rule for ambiguous instructions.",
                    {"style": "strict+literal"}, activate=False)
    pv = reg.add_version(task, template, "Add tie-break rule for ambiguous instructions.",
                         {"style": "strict+literal"}, activate=False)
    print("added", pv.version, "to", task)