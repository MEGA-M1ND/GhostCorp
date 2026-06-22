"""
agents/customer_agent.py — simplified Customer Agent. Nemotron-nano-8B.

Minimal prompt, runs in parallel. Reads the (competitor-shocked) NPS, churn, and
product score and settles a new NPS + churn for the quarter. Better product ->
lower churn, higher NPS. Read-only on state; returns a result dict. Its churn
output feeds Finance and Sales later in the same tick.
"""

from __future__ import annotations

from core.config import fast_llm
from core.state import SimCorpState
from agents._common import ainvoke, clamp, parse_json

SYSTEM_PROMPT = "You are SimCorp's Customer Agent. Output JSON only."


async def customer_agent(state: SimCorpState) -> dict:
    nps, churn, score = state["nps_score"], state["churn_rate"], state["product_score"]

    # Deterministic fallback: product quality above/below 6 moves the needles.
    fb_churn = clamp(churn + (6 - score) * 0.3, 0, 15)
    fb_nps = clamp(nps + (score - 6) * 2, -100, 100)
    fallback = {"new_nps": round(fb_nps, 1), "new_churn": round(fb_churn, 1)}

    user = (
        f"nps={nps:.0f}, churn={churn:.1f}, product_score={score:.1f}. "
        "Output new_nps (-100..100) and new_churn (0-15). "
        "Better product lowers churn and raises NPS. JSON only."
    )
    try:
        out = parse_json(await ainvoke(fast_llm, SYSTEM_PROMPT, user), fallback)
    except Exception:
        out = fallback

    new_nps = round(clamp(out.get("new_nps", fb_nps), -100, 100), 1)
    new_churn = round(clamp(out.get("new_churn", fb_churn), 0, 15), 1)

    return {
        "agent": "Customer",
        "action": f"NPS {new_nps}, churn {new_churn}%",
        "updates": {"nps_score": new_nps, "churn_rate": new_churn},
    }
