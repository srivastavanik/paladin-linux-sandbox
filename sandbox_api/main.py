# sandbox_api/main.py
from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse
import asyncio, json, os

from .settings import settings
from .screens import screenshot_png_response
from .executor import stream_process, run_capture
from .scanners.static_runner import run_all
from .scanners.sarif_merge import merge_sarif, post_findings

app = FastAPI(title="Paladin Linux Sandbox API")

@app.get("/health")
async def health(): return {"ok": True}

@app.get("/status")
async def status():
    return {"ok": True, "capabilities": {
        "vnc": True, "playwright": True, "screenshot": True, "execute": bool(settings.ALLOW_EXEC)
    }}

@app.get("/screenshot")
async def screenshot(): return screenshot_png_response()

@app.post("/execute")
async def execute(cmd: str = Body(..., embed=True), timeout: int = Query(settings.TIMEOUT_DEFAULT)):
    if not settings.ALLOW_EXEC: raise HTTPException(403, "exec disabled")
    async def eventgen():
        async for line in stream_process(cmd, timeout):
            yield {"event":"data","data": line}
        yield {"event":"end","data":"done"}
    return EventSourceResponse(eventgen())

@app.post("/playwright")
async def playwright(scenario: str = Body(...), args: dict = Body(default={})):
    """
    scenario: 'goto' | 'xss' | 'auth'
    args: dict of CLI args
    """
    cmd = ["python","-m", f"playwright_scenarios.{scenario}"] + \
          sum(([f"--{k}", str(v)] for k,v in args.items()), [])
    async def eventgen():
        async for line in stream_process(" ".join(cmd), timeout=300):
            yield {"event":"data","data": line}
        yield {"event":"end","data":"done"}
    return EventSourceResponse(eventgen())

@app.post("/scan/static")
async def scan_static(repo_path: str = Body(...), session_id: str | None = Body(None)):
    sarifs = run_all(repo_path)
    merged = merge_sarif(sarifs)
    if settings.CONTROL_PLANE_URL and session_id:
        post_findings(settings.CONTROL_PLANE_URL, settings.CONTROL_PLANE_TOKEN or "", session_id, merged)
    return JSONResponse(merged)