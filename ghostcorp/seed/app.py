"""
GhostCorp product — seed application.

The empty-but-runnable skeleton the AI company starts from on Sprint 0. The
Engineer agent grows it by dropping self-contained feature modules into
`features/`; this app auto-discovers any module there that defines a `router`
(a FastAPI APIRouter) and mounts it — so the Engineer never has to edit app.py.

Conventions the agents rely on:
  - Feature modules live in features/<name>.py and expose `router = APIRouter()`.
  - Endpoints live under /api/... and return JSON.
  - Persistence goes through `from db import connect` (shared SQLite).
"""

from __future__ import annotations

import importlib
import os
import pkgutil
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402

from db import init_db  # noqa: E402

# Product identity — overwritten by the DevOps agent once the CEO picks a product.
PRODUCT = {
    "name": "Untitled Product",
    "vision": "The AI founders have not chosen a product yet.",
    "version": "0.0.0",
}

app = FastAPI(title="GhostCorp Product")
init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "product": PRODUCT["name"], "version": PRODUCT["version"]}


@app.get("/api/product")
def product_info() -> dict:
    return PRODUCT


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    path = os.path.join(BASE_DIR, "templates", "index.html")
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _load_features() -> None:
    """Auto-discover and mount every feature module's router."""
    features_dir = os.path.join(BASE_DIR, "features")
    if not os.path.isdir(features_dir):
        return
    import features  # noqa: F401  (ensures the package is importable)

    for _, name, _ in pkgutil.iter_modules([features_dir]):
        module = importlib.import_module(f"features.{name}")
        router = getattr(module, "router", None)
        if router is not None:
            app.include_router(router)


# A broken feature raises here -> the whole suite goes red, which is exactly the
# signal QA needs. DevOps only ships green, so the product never stays broken.
_load_features()
