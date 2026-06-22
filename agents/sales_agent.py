"""
agents/sales_agent.py — Sales Agent. Nemotron-nano-8B via NVIDIA NIM.

Converts the CEO strategy + marketing budget into customer acquisition: new
customers, an updated CAC, and market share. As with Finance, the LLM writes the
narrative and may nudge a bounded lead-quality knob; the acquisition math is
deterministic.
"""

from __future__ import annotations

from core.config import fast_llm
from core.state import SimCorpState
from agents._common import ainvoke, clamp, log_agent, parse_json

# Total addressable customers for the simulated market. Chosen so the scenarios'
# starting market-share figures are self-consistent (e.g. 28 customers ~= 2.1%).
TOTAL_ADDRESSABLE_CUSTOMERS = 1_333

# How aggressively each strategy converts marketing spend into customers.
CONVERSION_MULTIPLIER = {
    "aggressive_growth": 1.3,
    "defensive_hold": 0.8,
    "cost_cut": 0.5,
    "pivot": 1.0,
    "acquisition_mode": 1.1,
}

# How each strategy moves CAC (a multiplier applied this quarter).
CAC_ADJUSTMENT = {
    "aggressive_growth": 1.20,   # paying up for growth
    "defensive_hold": 1.00,
    "cost_cut": 0.85,            # cheaper, slower acquisition
    "pivot": 1.05,
    "acquisition_mode": 1.10,
}

MONTHS_PER_QUARTER = 3

SYSTEM_PROMPT = (
    "You are the Sales Agent of SimCorp. Given the CEO strategy and budget, "
    "estimate a lead_quality multiplier between 0.8 and 1.2 reflecting pipeline "
    "health, and write a 2-3 sentence sales_report. Output JSON only: "
    '{"lead_quality": float, "sales_report": "..."}'
)


async def sales_agent(state: SimCorpState) -> SimCorpState:
    strategy = state["ceo_strategy"] or "defensive_hold"
    decision = state.get("ceo_decision", {})
    alloc = decision.get("budget_allocation", {}) if isinstance(decision, dict) else {}
    marketing_fraction = float(alloc.get("marketing", 0.30))

    fallback = {"lead_quality": 1.0, "sales_report": ""}
    user = (
        f"CEO strategy: {strategy}\n"
        f"Marketing budget fraction: {marketing_fraction:.0%}\n"
        f"Current customers: {state['customers']}, CAC: ${state['cac']:,.0f}, "
        f"churn: {state['churn_rate']:.1f}%\n"
        "Estimate lead_quality (0.8-1.2) and explain. JSON only."
    )

    try:
        raw = await ainvoke(fast_llm, SYSTEM_PROMPT, user)
        out = parse_json(raw, fallback)
    except Exception as exc:
        out = dict(fallback)
        out["sales_report"] = f"Sales fallback (error: {exc})."

    lead_quality = clamp(out.get("lead_quality", 1.0), 0.8, 1.2)

    # --- Deterministic acquisition math ---
    # Marketing spend this quarter is a slice of total quarterly opex (burn).
    marketing_spend = state["burn_rate"] * MONTHS_PER_QUARTER * marketing_fraction
    cac = max(1.0, state["cac"])  # avoid div-by-zero
    conversion = CONVERSION_MULTIPLIER.get(strategy, 1.0)

    gross_new = (marketing_spend / cac) * conversion * lead_quality
    churned = state["customers"] * (state["churn_rate"] / 100)
    new_customers = max(0, round(state["customers"] - churned + gross_new))

    new_cac = round(cac * CAC_ADJUSTMENT.get(strategy, 1.0), 2)
    market_share = round(new_customers / TOTAL_ADDRESSABLE_CUSTOMERS * 100, 1)

    net_added = new_customers - state["customers"]
    state["customers"] = new_customers
    state["cac"] = new_cac
    state["market_share"] = market_share

    report = out.get("sales_report") or (
        f"Acquired ~{max(0, round(gross_new))} customers (net {net_added:+d}) at "
        f"CAC ${new_cac:,.0f}; market share now {market_share:.1f}%."
    )
    state["sales_report"] = report

    log_agent(
        state,
        "Sales",
        f"{net_added:+d} net customers -> {new_customers} total, CAC ${new_cac:,.0f}, "
        f"share {market_share:.1f}%",
    )
    return state
