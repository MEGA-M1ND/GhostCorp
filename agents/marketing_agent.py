"""
agents/marketing_agent.py — simplified Marketing Agent. Nemotron-nano-8B.

Minimal prompt, runs in parallel. Produces a CAC adjustment multiplier for the
quarter (higher marketing budget -> lower CAC). The Sales Agent consumes it via
state["cac_adjustment"]. Read-only on state; returns a result dict.
"""

from __future__ import annotations

from core.config import fast_llm
from core.state import SimCorpState
from agents._common import ainvoke, clamp, parse_json

SYSTEM_PROMPT = "You are SimCorp's Marketing Agent. Output JSON only."


async def marketing_agent(state: SimCorpState) -> dict:
    decision = state.get("ceo_decision", {})
    strategy = state["ceo_strategy"] or "defensive_hold"
    budget = float(decision.get("budget_allocation", {}).get("marketing", 0.30)) if isinstance(decision, dict) else 0.30

    # Deterministic fallback: more marketing spend lowers CAC (multiplier < 1).
    fb_adj = clamp(1.2 - budget, 0.7, 1.5)
    fallback = {"cac_adjustment": round(fb_adj, 2)}

    user = (
        f"Marketing budget: {budget:.0%}, strategy: '{strategy}'. "
        "Output cac_adjustment (float 0.7-1.5; higher budget = lower CAC). JSON only."
    )
    try:
        out = parse_json(await ainvoke(fast_llm, SYSTEM_PROMPT, user), fallback)
    except Exception:
        out = fallback

    adj = round(clamp(out.get("cac_adjustment", fb_adj), 0.7, 1.5), 2)
    return {
        "agent": "Marketing",
        "action": f"CAC adjustment x{adj} on {budget:.0%} budget",
        "updates": {"cac_adjustment": adj},
    }
