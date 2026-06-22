"""
api/sim_service.py — the in-memory simulation service backing the REST API.

Holds the single current SimCorpState, serializes ticks behind an asyncio.Lock
(LLM ticks take seconds; we never want two overlapping), and bridges to the
scenario loader + SQLite persistence. On startup it restores the last persisted
state so the simulation survives a server restart.
"""

from __future__ import annotations

import asyncio

from core.persistence import init_db, load_latest_state, reset_db
from core.tick import run_tick
from simulation.scenarios import SCENARIO_MODULES, load_scenario


class SimService:
    def __init__(self) -> None:
        init_db()
        latest = load_latest_state()
        self.state = latest if latest is not None else load_scenario("mvp_launch")
        self._lock = asyncio.Lock()

    @property
    def busy(self) -> bool:
        return self._lock.locked()

    def get_state(self) -> dict:
        return self.state

    def start(self) -> dict:
        self.state["simulation_status"] = "running"
        return self.state

    async def next_tick(self) -> dict:
        # If a tick is already running, return current state unchanged rather
        # than queueing a second concurrent tick (which would corrupt state).
        if self._lock.locked():
            return self.state
        async with self._lock:
            self.state = await run_tick(self.state)
        return self.state

    def reset(self) -> dict:
        """Reset to the current scenario's initial conditions."""
        scenario = self.state.get("scenario", "mvp_launch")
        reset_db()
        self.state = load_scenario(scenario)
        return self.state

    def load_scenario(self, name: str) -> dict:
        if name not in SCENARIO_MODULES:
            raise KeyError(name)
        reset_db()
        self.state = load_scenario(name)
        return self.state


# Module-level singleton shared by all routes.
sim = SimService()
