"""
api/routes/simulation.py — simulation control endpoints.

  GET  /api/state            full SimCorpState
  POST /api/start            mark the simulation running
  POST /api/next-tick        run one quarter (async; serialized)
  POST /api/reset            reset to current scenario's initial state
  POST /api/scenario/{name}  load a pre-built scenario
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.sim_service import sim

router = APIRouter()


@router.get("/state")
def get_state() -> dict:
    return sim.get_state()


@router.post("/start")
def start() -> dict:
    return sim.start()


@router.post("/next-tick")
async def next_tick() -> dict:
    return await sim.next_tick()


@router.post("/reset")
def reset() -> dict:
    return sim.reset()


@router.post("/scenario/{name}")
def load_scenario(name: str) -> dict:
    try:
        return sim.load_scenario(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown scenario: {name}")
