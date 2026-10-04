import json, pathlib

root = pathlib.Path(__file__).resolve().parent.parent / "prompts"
for p in sorted(root.glob("*.json")):
    doc = json.loads(p.read_text())
    keep = {v["version"]: v for v in doc["versions"]}
    if "v6" not in keep:
        print("skip", p.name, "(already cleaned)")
        continue
    v5 = keep["v5"]
    v5["version"] = "v4"
    v5["changelog"] = "Require one entry per input item and exact copying of names and places (added after real-model failures)."
    v5["metadata"] = {"style": "strict+complete"}
    doc["versions"] = [keep["v1"], keep["v2"], keep["v3"], v5]
    p.write_text(json.dumps(doc, indent=2))
    print("cleaned", p.name)