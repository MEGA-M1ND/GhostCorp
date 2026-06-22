"""
GhostCorp product — seed application.

This is the empty-but-runnable skeleton the AI company starts from on Sprint 0.
The agents grow it feature by feature: new routes, models, validation, and UI.
It is a real FastAPI + SQLite app — every feature the Engineer adds is testable
with real pytest, and the whole thing serves a live UI for the demo preview.

Conventions the agents follow (keep these stable so codegen stays tractable):
  - All persistence goes through a single SQLite database (see `db_path()`).
  - Feature endpoints live under `/api/...` and return JSON.
  - `PRODUCT` metadata (name/vision) is set once the CEO picks the product.
"""

from __future__ import annotations

import os
import sqlite3

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Product identity — overwritten by DevOps once the CEO names the product.
PRODUCT = {
    "name": "Untitled Product",
    "vision": "The AI founders have not chosen a product yet.",
    "version": "0.0.0",
}

app = FastAPI(title="GhostCorp Product")


def db_path() -> str:
    """Single source of truth for the product database location."""
    return os.path.join(BASE_DIR, "product.db")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create baseline tables. Agents add their own tables alongside these."""
    with connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)"
        )
        conn.commit()


# Initialize on import so `TestClient(app)` and `uvicorn` both have a ready DB.
init_db()


@app.get("/health")
def health() -> dict:
    """Liveness probe used by the executor and DevOps agent."""
    return {"status": "ok", "product": PRODUCT["name"], "version": PRODUCT["version"]}


@app.get("/api/product")
def product_info() -> dict:
    """The product's identity — rendered in the live preview header."""
    return PRODUCT


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Serve the product's single-page UI (grown by the agents)."""
    path = os.path.join(BASE_DIR, "templates", "index.html")
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()
