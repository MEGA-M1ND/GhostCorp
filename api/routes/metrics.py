"""
api/routes/metrics.py — read-only metrics endpoints for charts + activity feed.

  GET /api/metrics    history array (chart data)
  GET /api/agent-log  agent activity log array
"""

from __future__ import annotations

from fastapi import APIRouter

from api.sim_service import sim

router = APIRouter()


@router.get("/metrics")
def metrics() -> list[dict]:
    return sim.get_state()["history"]


@router.get("/agent-log")
def agent_log() -> list[dict]:
    return sim.get_state()["agent_log"]
