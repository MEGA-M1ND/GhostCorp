"""
core/tick.py — the simulation tick engine. One tick == one business quarter.

Stage 2 implements the core money loop:

    CEO (strategy)  ->  Finance (KPIs)  ->  Sales (ARR delta)

Later stages slot the Competitor agent in front of the CEO, run the simplified
agents (product/marketing/customer) in parallel, and add SQLite persistence.
Those insertion points are marked below.
"""

from __future__ import annotations

import asyncio

from core.state import SimCorpState, snapshot, NUMERIC_FIELDS
from agents.ceo_agent import ceo_agent
from agents.finance_agent import finance_agent
from agents.sales_agent import sales_agent


async def run_tick(state: SimCorpState) -> SimCorpState:
    """Advance the simulation by exactly one quarter, in place + returned."""
    state["simulation_status"] = "running"

    # Step 1 (Stage 3): Competitor agent moves first to set the context.
    # state = await competitor_agent(state)

    # Step 2: CEO responds to the current state (Nemotron-70B, sequential).
    state = await ceo_agent(state)

    # Step 3 (Stage 4): simplified agents (product/marketing/customer) run here
    # in parallel via asyncio.gather.

    # Steps 4 & 5: Finance then Sales — order matters (Sales reads new burn).
    state = await finance_agent(state)
    state = await sales_agent(state)

    # Step 6: Housekeeping. Snapshot the quarter that just ran, then advance.
    state["history"].append(snapshot(state))
    state["quarter"] += 1
    # persist_to_sqlite(state)  # Stage 4

    return state


async def run_quarters(state: SimCorpState, n: int) -> SimCorpState:
    """Run `n` consecutive quarter ticks on a state."""
    for _ in range(n):
        state = await run_tick(state)
    return state


def diff_numeric(before: SimCorpState, after: SimCorpState) -> dict:
    """Return {field: (before, after)} for numeric KPIs that changed."""
    out = {}
    for field in NUMERIC_FIELDS:
        b, a = before.get(field), after.get(field)
        if b != a:
            out[field] = (b, a)
    return out


def print_state_diff(before: SimCorpState, after: SimCorpState) -> None:
    """Pretty-print the KPI delta produced by a tick (used by the demo)."""
    print(f"\n=== Quarter {before['quarter']} -> {after['quarter']} ===")
    print(f"CEO strategy : {after['ceo_strategy']}")
    print(f"CEO reasoning: {after['ceo_reasoning']}")
    print("--- KPI changes ---")
    for field, (b, a) in diff_numeric(before, after).items():
        print(f"  {field:<26} {b:>14,.1f}  ->  {a:>14,.1f}")
    print(f"Finance: {after['finance_report']}")
    print(f"Sales  : {after['sales_report']}")


if __name__ == "__main__":
    # Stage 2 smoke test: run one quarter on the MVP launch scenario and print
    # the KPI diff. Requires NVIDIA_API_KEY in the environment.
    import copy
    from simulation.scenarios.mvp_launch import INITIAL_STATE

    start = copy.deepcopy(INITIAL_STATE)
    result = asyncio.run(run_tick(copy.deepcopy(start)))
    print_state_diff(start, result)
