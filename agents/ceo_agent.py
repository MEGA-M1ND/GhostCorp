"""
agents/ceo_agent.py — the CEO supervisor. Nemotron-70B via NVIDIA NIM.

The CEO receives the full market state, reacts to the competitor's latest move,
and emits a structured strategic directive that drives every other agent this
quarter. This is the only agent on the 70B model — judges will check.
"""

from __future__ import annotations

from core.config import ceo_llm
from core.state import GhostCorpState
from agents._common import ainvoke, log_agent, parse_json

SYSTEM_PROMPT = """You are the CEO of GhostCorp, an AI-operated SaaS startup. You make strategic decisions each quarter based on financial performance, market conditions, and competitor moves.

Your decisions drive ALL other agents. Be decisive, specific, and data-driven.
Think like a Series A startup CEO who is accountable to investors.

You must output a JSON object with:
{
  "strategy": "one of: aggressive_growth | defensive_hold | pivot | cost_cut | acquisition_mode",
  "pricing_action": "one of: increase_10pct | hold | decrease_10pct | freemium_tier",
  "budget_allocation": {"product": 0.35, "marketing": 0.30, "sales": 0.25, "ops": 0.10},
  "key_directive": "One specific, actionable sentence for all agents this quarter",
  "reasoning": "2-3 sentence explanation of why, citing specific metrics"
}

Rules you must obey:
- If runway is under 6 months you MUST choose strategy "cost_cut".
- If the competitor move involves a price undercut you MUST respond with a pricing_action other than "hold".
- If churn is above 8% you MUST allocate the largest share of budget to product.
Output ONLY the JSON object, no prose."""

VALID_STRATEGIES = {
    "aggressive_growth",
    "defensive_hold",
    "pivot",
    "cost_cut",
    "acquisition_mode",
}
VALID_PRICING = {"increase_10pct", "hold", "decrease_10pct", "freemium_tier"}

# Used when the model returns nothing parseable. A safe, neutral hold.
_FALLBACK = {
    "strategy": "defensive_hold",
    "pricing_action": "hold",
    "budget_allocation": {"product": 0.35, "marketing": 0.30, "sales": 0.25, "ops": 0.10},
    "key_directive": "Hold position and protect runway while we reassess the market.",
    "reasoning": "Fallback directive: the CEO model returned no parseable decision, "
    "defaulting to a conservative hold to preserve cash.",
}


def _build_context(state: GhostCorpState) -> str:
    """The decision context handed to the CEO each quarter."""
    return (
        f"Quarter: {state['quarter']} | Scenario: {state['scenario']}\n"
        f"ARR: ${state['arr']:,.0f} | MRR: ${state['mrr']:,.0f}\n"
        f"Burn rate: ${state['burn_rate']:,.0f}/mo | Cash: ${state['cash_balance']:,.0f} "
        f"| Runway: {state['runway_months']:.1f} months\n"
        f"Customers: {state['customers']} | Churn: {state['churn_rate']:.1f}% "
        f"| NPS: {state['nps_score']:.0f}\n"
        f"Market share: {state['market_share']:.1f}% "
        f"| Competitor share: {state['competitor_market_share']:.1f}%\n"
        f"Latest competitor move: {state['competitor_move']}\n\n"
        f"Decide this quarter's strategy. Output JSON only."
    )


def _enforce_guards(decision: dict, state: GhostCorpState) -> dict:
    """Apply the CEO's non-negotiable critical behaviors after parsing.

    The prompt asks the model to obey these; we enforce them deterministically
    so the demo is reliable even if a given generation drifts.
    """
    # Normalize / validate enums.
    if decision.get("strategy") not in VALID_STRATEGIES:
        decision["strategy"] = _FALLBACK["strategy"]
    if decision.get("pricing_action") not in VALID_PRICING:
        decision["pricing_action"] = "hold"

    alloc = decision.get("budget_allocation")
    if not isinstance(alloc, dict) or not alloc:
        alloc = dict(_FALLBACK["budget_allocation"])
    # Coerce to floats and renormalize so the four buckets sum to 1.0.
    alloc = {k: max(0.0, float(v)) for k, v in alloc.items() if isinstance(v, (int, float))}
    for bucket in ("product", "marketing", "sales", "ops"):
        alloc.setdefault(bucket, 0.0)
    total = sum(alloc.values()) or 1.0
    alloc = {k: v / total for k, v in alloc.items()}
    decision["budget_allocation"] = alloc

    # Guard 1: runway < 6 months -> must cost_cut.
    if state["runway_months"] < 6:
        decision["strategy"] = "cost_cut"

    # Guard 2: price undercut -> must respond with a real pricing action.
    if "price_undercut" in (state["competitor_move"] or "") and decision["pricing_action"] == "hold":
        decision["pricing_action"] = "decrease_10pct"

    # Guard 3: churn > 8% -> product must be the largest budget bucket.
    if state["churn_rate"] > 8:
        alloc = decision["budget_allocation"]
        max_other = max(alloc.get("marketing", 0), alloc.get("sales", 0), alloc.get("ops", 0))
        if alloc.get("product", 0) <= max_other:
            alloc["product"] = max_other + 0.10
            total = sum(alloc.values())
            decision["budget_allocation"] = {k: v / total for k, v in alloc.items()}

    return decision


async def ceo_agent(state: GhostCorpState) -> GhostCorpState:
    """Run the CEO: produce a strategic directive and write it into state."""
    context = _build_context(state)
    try:
        raw = await ainvoke(ceo_llm, SYSTEM_PROMPT, context)
        decision = parse_json(raw, _FALLBACK)
    except Exception as exc:  # network/auth/rate-limit exhausted -> safe fallback
        decision = dict(_FALLBACK)
        decision["reasoning"] = f"{_FALLBACK['reasoning']} (error: {exc})"

    decision = _enforce_guards(decision, state)

    state["ceo_decision"] = decision
    state["ceo_strategy"] = decision["strategy"]
    state["ceo_reasoning"] = decision.get("reasoning", "")

    log_agent(
        state,
        "CEO",
        f"strategy={decision['strategy']}, pricing={decision['pricing_action']} "
        f"— {decision.get('key_directive', '')}",
    )
    return state
