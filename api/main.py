"""
api/main.py — the SimCorp FastAPI application.

Run with:  uvicorn api.main:app --reload

Serves the single-file dashboard at "/" and the REST API under "/api". CORS is
wide open — this is a hackathon MVP with no auth.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.routes import metrics, simulation

app = FastAPI(title="SimCorp", description="AI-operated SaaS startup simulation")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulation.router, prefix="/api", tags=["simulation"])
app.include_router(metrics.router, prefix="/api", tags=["metrics"])

_DASHBOARD = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "dashboard", "index.html")
)


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    """Serve the single-file React dashboard."""
    return FileResponse(_DASHBOARD)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok"}
