"""
ghostcorp/server.py — GhostCorp Mission Control (dashboard + control-plane API).

Holds the live company state in memory and exposes:
  GET  /                  the dashboard UI
  GET  /api/state         full company state (+ running flag, preview url)
  POST /api/sprint/run    kick off N autonomous sprints (background, non-blocking)
  POST /api/reset         re-seed a fresh company / workspace
  POST /api/preview/restart  restart the live product preview

Run:  uvicorn ghostcorp.server:app --port 8000
The product preview runs as a separate process on GHOSTCORP_PRODUCT_PORT (8100).
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from ghostcorp.product_server import ProductServer
from ghostcorp.sprint import MAX_BUILD_ATTEMPTS, init_company, run_sprint

_DASHBOARD = Path(__file__).resolve().parent / "dashboard.html"
_NO_PREVIEW = os.getenv("GHOSTCORP_NO_PREVIEW") == "1"

# Allow a separately-hosted frontend (e.g. an Emergent-built dashboard) to call
# the API cross-origin. Defaults to "*"; set GHOSTCORP_CORS_ORIGINS to a
# comma-separated allowlist (e.g. "http://localhost:5173,https://my.app") to lock
# it down.
_CORS_ORIGINS = [o.strip() for o in os.getenv("GHOSTCORP_CORS_ORIGINS", "*").split(",") if o.strip()]

app = FastAPI(title="GhostCorp Mission Control")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single in-memory company. Reset re-seeds it.
_state = init_company(force=True)
_running = False
_product = ProductServer()


@app.on_event("startup")
async def _startup() -> None:
    if not _NO_PREVIEW:
        try:
            await asyncio.to_thread(_product.start)
        except Exception:
            pass


@app.on_event("shutdown")
async def _shutdown() -> None:
    if not _NO_PREVIEW:
        await asyncio.to_thread(_product.stop)


def _serialize() -> dict:
    """JSON-safe snapshot of the company for the dashboard."""
    snap = json.loads(json.dumps(_state, default=str))
    cf = snap.get("current_feature")
    if isinstance(cf, dict):
        cf.pop("_files", None)  # internal Engineer bookkeeping
    snap["running"] = _running
    snap["preview_url"] = _product.url if not _NO_PREVIEW else ""
    snap["preview_live"] = _product.is_running() if not _NO_PREVIEW else False
    snap["max_build_attempts"] = MAX_BUILD_ATTEMPTS
    return snap


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return _DASHBOARD.read_text(encoding="utf-8")


@app.get("/api/state")
def get_state() -> JSONResponse:
    return JSONResponse(_serialize())


async def _drive(n: int) -> None:
    """Run n sprints back-to-back, refreshing the preview after each ship."""
    global _running
    try:
        for _ in range(n):
            await run_sprint(_state)
            if not _NO_PREVIEW:
                try:
                    await asyncio.to_thread(_product.restart)
                except Exception:
                    pass
    finally:
        _running = False


@app.post("/api/sprint/run")
async def run_sprints_endpoint(n: int = Query(1, ge=1, le=12)) -> dict:
    global _running
    if _running:
        return {"started": False, "reason": "a sprint is already running"}
    _running = True
    asyncio.create_task(_drive(n))
    return {"started": True, "sprints": n}


@app.post("/api/reset")
async def reset() -> dict:
    global _state, _running
    if _running:
        return {"ok": False, "reason": "cannot reset while a sprint is running"}
    _state = init_company(force=True)
    if not _NO_PREVIEW:
        try:
            await asyncio.to_thread(_product.restart)
        except Exception:
            pass
    return {"ok": True}


@app.post("/api/preview/restart")
async def restart_preview() -> dict:
    if _NO_PREVIEW:
        return {"ok": False, "reason": "preview disabled"}
    ok = await asyncio.to_thread(_product.restart)
    return {"ok": ok, "url": _product.url}


def main() -> None:
    import uvicorn

    uvicorn.run(
        app,
        host=os.getenv("GHOSTCORP_HOST", "0.0.0.0"),
        port=int(os.getenv("GHOSTCORP_PORT", "8000")),
    )


if __name__ == "__main__":
    main()
