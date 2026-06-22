"""
agents/finance_agent.py — Finance Agent. Nemotron-nano-8B via NVIDIA NIM.

Updates all financial KPIs after the CEO sets strategy. The LLM chooses two
bounded "knobs" (growth_rate and headcount_growth, within the band allowed by
the CEO's strategy) and writes the narrative finance_report; the actual KPI math
is deterministic so the demo numbers stay sane and legible.
"""

from __future__ import annotations

from core.config import fast_llm
from core.state import GhostCorpState
from agents._common import ainvoke, clamp, log_agent, parse_json
from tools.financial_tools import (
    cash_after_quarter,
    mrr_to_arr,
    project_burn,
    project_mrr,
    runway_months,
)

# Quarterly net-MRR growth bands per CEO strategy (low, high).
GROWTH_BANDS = {
    "aggressive_growth": (0.15, 0.25),
    "defensive_hold": (0.02, 0.05),
    "cost_cut": (-0.05, 0.02),
    "pivot": (-0.10, 0.30),
    "acquisition_mode": (0.05, 0.20),
}

# Headcount/cost growth bands per strategy (drives burn). Negative = shrinking.
HEADCOUNT_BANDS = {
    "aggressive_growth": (0.05, 0.20),
    "defensive_hold": (-0.02, 0.03),
    "cost_cut": (-0.25, -0.05),
    "pivot": (-0.10, 0.10),
    "acquisition_mode": (0.00, 0.15),
}

SYSTEM_PROMPT = (
    "You are the Finance Agent of GhostCorp. Given the CEO strategy and current "
    "financials, choose a quarterly growth_rate and headcount_growth within the "
    "allowed ranges, and write a 2-3 sentence finance_report. Output JSON only: "
    '{"growth_rate": float, "headcount_growth": float, "finance_report": "..."}'
)


def _band(strategy: str, bands: dict) -> tuple[float, float]:
    return bands.get(strategy, bands["defensive_hold"])


async def finance_agent(state: GhostCorpState) -> GhostCorpState:
    strategy = state["ceo_strategy"] or "defensive_hold"
    g_lo, g_hi = _band(strategy, GROWTH_BANDS)
    h_lo, h_hi = _band(strategy, HEADCOUNT_BANDS)

    g_mid, h_mid = (g_lo + g_hi) / 2, (h_lo + h_hi) / 2
    fallback = {
        "growth_rate": g_mid,
        "headcount_growth": h_mid,
        "finance_report": "",
    }

    user = (
        f"CEO strategy: {strategy}\n"
        f"Current MRR: ${state['mrr']:,.0f}, burn: ${state['burn_rate']:,.0f}/mo, "
        f"cash: ${state['cash_balance']:,.0f}, churn: {state['churn_rate']:.1f}%\n"
        f"Allowed growth_rate range: [{g_lo}, {g_hi}]\n"
        f"Allowed headcount_growth range: [{h_lo}, {h_hi}]\n"
        "Pick values in range and explain. JSON only."
    )

    try:
        raw = await ainvoke(fast_llm, SYSTEM_PROMPT, user)
        out = parse_json(raw, fallback)
    except Exception as exc:
        out = dict(fallback)
        out["finance_report"] = f"Finance fallback (error: {exc})."

    # Clamp the LLM's knobs into the strategy-allowed bands.
    growth_rate = clamp(out.get("growth_rate", g_mid), g_lo, g_hi)
    headcount_growth = clamp(out.get("headcount_growth", h_mid), h_lo, h_hi)

    # --- Deterministic KPI math (shared tools) ---
    new_mrr = project_mrr(state["mrr"], growth_rate, state["churn_rate"])
    new_arr = mrr_to_arr(new_mrr)
    new_burn = project_burn(state["burn_rate"], headcount_growth)
    new_cash = cash_after_quarter(state["cash_balance"], new_mrr, new_burn)
    runway = runway_months(new_cash, new_burn)

    state["mrr"] = round(new_mrr, 2)
    state["arr"] = round(new_arr, 2)
    state["burn_rate"] = round(new_burn, 2)
    state["cash_balance"] = round(new_cash, 2)
    state["runway_months"] = round(max(0.0, runway), 1)

    report = out.get("finance_report") or (
        f"ARR moved to ${new_arr:,.0f} on {growth_rate:+.0%} growth; "
        f"burn at ${new_burn:,.0f}/mo leaves {state['runway_months']:.1f} months runway."
    )
    state["finance_report"] = report

    log_agent(
        state,
        "Finance",
        f"ARR ${new_arr:,.0f} (growth {growth_rate:+.0%}), burn ${new_burn:,.0f}/mo, "
        f"runway {state['runway_months']:.1f}mo",
    )
    return state
