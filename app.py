"""FastAPI server: JSON API + SSE streaming + the experiment UI (static/index.html)."""
from __future__ import annotations

import json
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from promptops.cache import Cache
from promptops.config import MODELS
from promptops.pipeline import PromptOps
from promptops.registry import Registry
from promptops.router import COMPLEXITY, route
from promptops.schemas import SCHEMAS
from promptops.telemetry import Telemetry

ROOT = Path(__file__).parent
ops = PromptOps(Registry(ROOT / "prompts"), Cache(ROOT / ".cache" / "cache.jsonl"), Telemetry(ROOT / "telemetry.jsonl"))
app = FastAPI(title="PromptOps")


class GenReq(BaseModel):
    task: str
    input: str
    prompt_version: str | None = None
    model: str | None = None
    priority: str = "balanced"
    use_cache: bool = True


class Variant(BaseModel):
    prompt_version: str | None = None
    model: str | None = None


class CmpReq(BaseModel):
    task: str
    input: str
    variants: list[Variant]
    use_cache: bool = False


class NewVersion(BaseModel):
    template: str
    changelog: str
    metadata: dict = {}


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/models")
def models():
    return {"models": [m.__dict__ for m in MODELS.values()], "tasks": {t: {"complexity": COMPLEXITY[t], "schema": SCHEMAS[t]} for t in SCHEMAS}}


@app.get("/api/route")
def route_preview(task: str, priority: str = "balanced"):
    try:
        return {"chain": route(task, priority)}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/generate")
def generate(req: GenReq):
    return ops.generate(req.task, req.input, prompt_version=req.prompt_version, model=req.model,
                        priority=req.priority, use_cache=req.use_cache)


@app.post("/api/compare")
def compare(req: CmpReq):
    with ThreadPoolExecutor(max_workers=max(1, len(req.variants))) as ex:
        futs = [ex.submit(ops.generate, req.task, req.input, prompt_version=v.prompt_version, model=v.model,
                          use_cache=req.use_cache, allow_fallback=False) for v in req.variants]
        return {"results": [f.result() for f in futs]}


@app.get("/api/stream")
def stream(task: str, input: str, prompt_version: str | None = None, model: str | None = None, priority: str = "balanced"):
    q: queue.Queue = queue.Queue()

    def work():
        r = ops.generate(task, input, prompt_version=prompt_version, model=model, priority=priority,
                         use_cache=False, stream=True, on_event=lambda k, p: q.put((k, p)))
        q.put(("final", r))
        q.put(None)

    threading.Thread(target=work, daemon=True).start()

    def gen():
        while (item := q.get()) is not None:
            yield f"event: {item[0]}\ndata: {json.dumps(item[1], ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/prompts")
def prompts():
    return {t: {"active": ops.registry.active(t), "versions": [v.__dict__ | {"variables": v.variables} for v in ops.registry.versions(t)]}
            for t in ops.registry.tasks()}


@app.post("/api/prompts/{task}")
def add_prompt(task: str, body: NewVersion):
    if task not in SCHEMAS:
        raise HTTPException(404, "unknown task")
    return ops.registry.add_version(task, body.template, body.changelog, body.metadata, activate=False).__dict__


@app.get("/api/telemetry")
def telemetry():
    return {**ops.telemetry.summary(), "cache": {"hits": ops.cache.hits, "misses": ops.cache.misses}}


@app.get("/api/report")
def report():
    p = ROOT / "results" / "report.json"
    if not p.exists():
        raise HTTPException(404, "run `python -m promptops.regression` first")
    d = json.loads(p.read_text())
    d.pop("rows", None)
    return d
