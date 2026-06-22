"""
core/state.py — SimCorpState, the single source of truth for the simulation.

This TypedDict is the shared LangGraph state. Every agent reads from it and
writes back to it; the dashboard renders it; SQLite persists it. Keeping the
schema in one place means the graph, the API, and the UI never disagree about
what a "quarter" looks like.
"""

from __future__ import annotations

from typing import List, TypedDict


class SimCorpState(TypedDict):
    # --- Simulation metadata ---
    quarter: int                       # Current quarter (1-8)
    scenario: str                      # "mvp_launch" | "scale_up" | "crisis"
    simulation_status: str             # "running" | "paused" | "completed"

    # --- Financial KPIs ---
    arr: float                         # Annual Recurring Revenue ($)
    mrr: float                         # Monthly Recurring Revenue ($)
    burn_rate: float                   # Monthly cash burn ($)
    cash_balance: float                # Current cash on hand ($)
    runway_months: float               # cash_balance / burn_rate
    cac: float                         # Customer Acquisition Cost ($)
    cac_adjustment: float              # Transient: Marketing Agent's CAC multiplier
                                       # for this quarter, consumed by Sales.

    # --- Market KPIs ---
    customers: int                     # Total active customers
    churn_rate: float                  # Monthly churn %
    nps_score: float                   # Net Promoter Score (-100 to 100)
    market_share: float                # % of total addressable market
    competitor_market_share: float     # Competitor's market share %

    # --- Product KPIs ---
    features_shipped: int              # Features shipped this quarter
    product_score: float               # Product quality score (0-10)

    # --- Agent decisions (populated each tick) ---
    ceo_strategy: str                  # CEO's strategic directive (text)
    ceo_reasoning: str                 # CEO's full reasoning chain (for LangSmith)
    ceo_decision: dict                 # Machine-readable CEO output consumed by
                                       # downstream agents within the same tick:
                                       # {strategy, pricing_action, budget_allocation,
                                       #  key_directive}
    competitor_move: str               # Competitor's action this quarter
    finance_report: str                # Finance Agent summary
    sales_report: str                  # Sales Agent summary

    # --- Agent activity log (for dashboard feed) ---
    agent_log: List[dict]              # [{agent, action, timestamp, quarter}]

    # --- Historical snapshots (for charts) ---
    history: List[dict]                # [{quarter, arr, burn_rate, market_share, nps}]


# Canonical ordering of the numeric KPI fields — handy for diffs, persistence,
# and printing a clean state delta in the Stage 2 money-loop test.
NUMERIC_FIELDS: tuple[str, ...] = (
    "arr",
    "mrr",
    "burn_rate",
    "cash_balance",
    "runway_months",
    "cac",
    "customers",
    "churn_rate",
    "nps_score",
    "market_share",
    "competitor_market_share",
    "features_shipped",
    "product_score",
)


def snapshot(state: SimCorpState) -> dict:
    """A compact, chart-ready record of the quarter for `history`."""
    return {
        "quarter": state["quarter"],
        "arr": state["arr"],
        "mrr": state["mrr"],
        "burn_rate": state["burn_rate"],
        "cash_balance": state["cash_balance"],
        "runway_months": state["runway_months"],
        "customers": state["customers"],
        "market_share": state["market_share"],
        "competitor_market_share": state["competitor_market_share"],
        "nps": state["nps_score"],
        "churn_rate": state["churn_rate"],
        "product_score": state["product_score"],
    }


def new_state(**overrides) -> SimCorpState:
    """Build a fully-populated SimCorpState, defaulting every field.

    Scenarios call this with a handful of overrides so they never have to
    enumerate the entire schema and risk leaving a field undefined.
    """
    base: SimCorpState = {
        "quarter": 1,
        "scenario": "mvp_launch",
        "simulation_status": "paused",
        "arr": 0.0,
        "mrr": 0.0,
        "burn_rate": 0.0,
        "cash_balance": 0.0,
        "runway_months": 0.0,
        "cac": 0.0,
        "cac_adjustment": 1.0,
        "customers": 0,
        "churn_rate": 0.0,
        "nps_score": 0.0,
        "market_share": 0.0,
        "competitor_market_share": 0.0,
        "features_shipped": 0,
        "product_score": 0.0,
        "ceo_strategy": "",
        "ceo_reasoning": "",
        "ceo_decision": {},
        "competitor_move": "hold",
        "finance_report": "",
        "sales_report": "",
        "agent_log": [],
        "history": [],
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base
