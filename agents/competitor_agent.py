"""
agents/competitor_agent.py — the adversarial Competitor. Nemotron-nano-8B.

Runs FIRST each quarter to set the drama before the CEO decides. The LLM acts as
a rival strategist: it reads SimCorp's state, picks the move from the pool that
best exploits SimCorp's weakness, and writes a short taunt. Hard selection rules
(dominant SimCorp -> aggressive; fragile runway -> funding_round) are enforced
deterministically so the adversary is reliably threatening on demo day.
"""

from __future__ import annotations

from core.config import fast_llm
from core.state import SimCorpState
from agents._common import ainvoke, log_agent, parse_json
from simulation.market_engine import (
    COMPETITOR_MOVES,
    apply_competitor_effects,
    describe_move,
    select_competitor_move,
)

SYSTEM_PROMPT = (
    "You are the rival CEO competing against SimCorp. Each quarter you pick ONE "
    "move from the allowed list that best exploits SimCorp's current weakness "
    "(low runway, high churn, big market share, weak product). Output JSON only: "
    '{"move": "<one move key>", "taunt": "one short sentence"}'
)


async def competitor_agent(state: SimCorpState) -> SimCorpState:
    move_keys = ", ".join(COMPETITOR_MOVES.keys())
    # Deterministic recommendation based on the selection rules; used as the
    # fallback and to override the LLM when a hard rule applies.
    forced = select_competitor_move(state)

    fallback = {"move": forced, "taunt": ""}
    user = (
        f"SimCorp state — market_share: {state['market_share']:.1f}%, "
        f"runway: {state['runway_months']:.1f}mo, churn: {state['churn_rate']:.1f}%, "
        f"NPS: {state['nps_score']:.0f}, product_score: {state['product_score']:.1f}\n"
        f"Allowed moves: {move_keys}\n"
        "Pick the most damaging move. JSON only."
    )

    try:
        raw = await ainvoke(fast_llm, SYSTEM_PROMPT, user)
        out = parse_json(raw, fallback)
    except Exception:
        out = dict(fallback)

    move = out.get("move")
    if move not in COMPETITOR_MOVES:
        move = forced

    # Enforce the two hard rules regardless of what the model chose.
    if state["runway_months"] < 9:
        move = "funding_round"
    elif state["market_share"] > 30 and move == "hold":
        move = forced

    # Record the move as a "key: description" string so both the CEO context and
    # the guards (which look for substrings like "price_undercut") work.
    state["competitor_move"] = f"{move}: {describe_move(move)}"
    apply_competitor_effects(state, move)

    taunt = out.get("taunt") or describe_move(move)
    log_agent(state, "Competitor", f"{move} — {taunt}")
    return state
