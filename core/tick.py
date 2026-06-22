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

from core.state import GhostCorpState, snapshot, NUMERIC_FIELDS
from core.persistence import persist_to_sqlite
from agents._common import log_agent
from agents.competitor_agent import competitor_agent
from agents.ceo_agent import ceo_agent
from agents.finance_agent import finance_agent
from agents.sales_agent import sales_agent
from agents.product_agent import product_agent
from agents.marketing_agent import marketing_agent
from agents.customer_agent import customer_agent

MAX_QUARTERS = 8


def merge_agent_results(state: GhostCorpState, results: list[dict]) -> GhostCorpState:
    """Apply the parallel agents' result dicts to state and log each.

    The simplified agents are read-only on state and return
    {agent, action, updates}; merging here keeps all mutation single-threaded.
    """
    for result in results:
        state.update(result.get("updates", {}))  # type: ignore[arg-type]
        log_agent(state, result["agent"], result["action"])
    return state


async def run_tick(state: GhostCorpState) -> GhostCorpState:
    """Advance the simulation by exactly one quarter, in place + returned."""
    state["simulation_status"] = "running"

    # Step 1: Competitor agent moves first to set the context (drama).
    state = await competitor_agent(state)

    # Step 2: CEO responds to the competitor + current state (Nemotron-70B).
    state = await ceo_agent(state)

    # Step 3: simplified agents run in PARALLEL (nano-8B, fast, read-only).
    results = await asyncio.gather(
        product_agent(state),
        marketing_agent(state),
        customer_agent(state),
    )
    state = merge_agent_results(state, results)

    # Steps 4 & 5: Finance then Sales — order matters (Sales reads new burn +
    # the Customer agent's fresh churn).
    state = await finance_agent(state)
    state = await sales_agent(state)

    # Step 6: Housekeeping. Snapshot the quarter that just ran, then advance.
    state["history"].append(snapshot(state))
    state["quarter"] += 1
    if state["quarter"] > MAX_QUARTERS:
        state["simulation_status"] = "completed"
    persist_to_sqlite(state)

    return state


async def run_quarters(state: GhostCorpState, n: int) -> GhostCorpState:
    """Run `n` consecutive quarter ticks on a state."""
    for _ in range(n):
        state = await run_tick(state)
    return state


async def run_4_quarters(scenario: str = "crisis") -> GhostCorpState:
    """Load a scenario and run 4 quarters, narrating the adversarial loop.

    Prints, per quarter: the competitor's move and the CEO's strategy +
    reasoning — so you can see the CEO visibly react to competitor pressure.
    This backs the Stage 3 approval gate.
    """
    from simulation.scenarios import load_scenario

    state = load_scenario(scenario)
    print(f"\n########## SCENARIO: {scenario} (starting Q{state['quarter']}) ##########")
    for _ in range(4):
        q = state["quarter"]
        before_runway = state["runway_months"]
        state = await run_tick(state)
        print(f"\n----- Q{q} -----")
        print(f"  Competitor : {state['competitor_move']}")
        print(f"  CEO strategy: {state['ceo_strategy']}  (pricing: "
              f"{state['ceo_decision'].get('pricing_action')})")
        print(f"  CEO reasoning: {state['ceo_reasoning']}")
        print(f"  Runway: {before_runway:.1f}mo -> {state['runway_months']:.1f}mo | "
              f"ARR ${state['arr']:,.0f} | churn {state['churn_rate']:.1f}% | "
              f"share {state['market_share']:.1f}% vs {state['competitor_market_share']:.1f}%")
    return state


def diff_numeric(before: GhostCorpState, after: GhostCorpState) -> dict:
    """Return {field: (before, after)} for numeric KPIs that changed."""
    out = {}
    for field in NUMERIC_FIELDS:
        b, a = before.get(field), after.get(field)
        if b != a:
            out[field] = (b, a)
    return out


def print_state_diff(before: GhostCorpState, after: GhostCorpState) -> None:
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
