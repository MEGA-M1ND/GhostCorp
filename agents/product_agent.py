"""
agents/product_agent.py — simplified Product Agent. Nemotron-nano-8B.

Minimal prompt, runs in parallel with Marketing + Customer. It is read-only on
state and returns a result dict (merged after gather) so the parallel agents
never mutate shared state concurrently.
"""

from __future__ import annotations

from core.config import fast_llm
from core.state import GhostCorpState
from agents._common import ainvoke, clamp, parse_json

SYSTEM_PROMPT = "You are GhostCorp's Product Agent. Output JSON only."


async def product_agent(state: GhostCorpState) -> dict:
    decision = state.get("ceo_decision", {})
    directive = decision.get("key_directive", "") if isinstance(decision, dict) else ""
    budget = float(decision.get("budget_allocation", {}).get("product", 0.30)) if isinstance(decision, dict) else 0.30

    # Deterministic fallback: more product budget -> more/better shipping.
    fb_features = int(clamp(round(1 + budget * 8), 1, 5))
    fb_score = clamp(state["product_score"] + (budget - 0.25) * 4, 0, 10)
    fallback = {"features_shipped": fb_features, "product_score": round(fb_score, 1)}

    user = (
        f"CEO directive: '{directive}'. Product budget: {budget:.0%}. "
        "Output features_shipped (int 1-5) and product_score (float 0-10). JSON only."
    )
    try:
        out = parse_json(await ainvoke(fast_llm, SYSTEM_PROMPT, user), fallback)
    except Exception:
        out = fallback

    features = int(clamp(out.get("features_shipped", fb_features), 1, 5))
    score = round(clamp(out.get("product_score", fb_score), 0, 10), 1)

    return {
        "agent": "Product",
        "action": f"shipped {features} feature(s), product_score {score}",
        "updates": {"features_shipped": features, "product_score": score},
    }
