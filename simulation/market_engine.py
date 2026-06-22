"""
simulation/market_engine.py — deterministic market simulation helpers.

Two responsibilities:
  1. The competitor move pool and weighted selection logic (exploit SimCorp's
     weaknesses).
  2. Applying a chosen competitor move's *effects* on the shared state — both
     the competitor's own market share and the adversarial pressure it puts on
     SimCorp (churn, NPS, product). Running this BEFORE the CEO each quarter is
     what makes the CEO visibly react.

Everything here is deterministic given its inputs (the only randomness is the
weighted move selection), so KPI evolution stays legible for the demo.
"""

from __future__ import annotations

import random

from agents._common import clamp
from core.state import SimCorpState

COMPETITOR_MOVES = {
    "price_undercut_20pct": "Competitor slashed prices by 20% — targeting your mid-market segment",
    "feature_launch_ai": "Competitor launched AI-powered analytics — matching your core differentiator",
    "talent_poach": "Competitor hired your VP of Engineering and 3 senior developers",
    "enterprise_deal": "Competitor signed a 500-seat enterprise deal in your target vertical",
    "free_tier_launch": "Competitor launched a free tier — directly targeting your trial pipeline",
    "funding_round": "Competitor raised $15M Series A — now has 18-month runway advantage",
    "hold": "Competitor made no significant moves this quarter — focus on internal execution",
}

# Moves considered "aggressive" — used when SimCorp is winning (share > 30%).
AGGRESSIVE_MOVES = [
    "price_undercut_20pct",
    "feature_launch_ai",
    "talent_poach",
    "enterprise_deal",
    "free_tier_launch",
]

# Default selection weights when SimCorp is neither dominant nor fragile.
_DEFAULT_WEIGHTS = {
    "price_undercut_20pct": 3,
    "feature_launch_ai": 3,
    "talent_poach": 2,
    "enterprise_deal": 2,
    "free_tier_launch": 2,
    "funding_round": 2,
    "hold": 3,
}


def select_competitor_move(state: SimCorpState, rng: random.Random | None = None) -> str:
    """Pick a competitor move key based on SimCorp's current weaknesses.

    Rules (per spec):
      - SimCorp market_share > 30%  -> aggressive moves only.
      - SimCorp runway_months < 9   -> exploit with funding_round.
      - otherwise                   -> weighted random selection.
    """
    rng = rng or random

    if state["runway_months"] < 9:
        return "funding_round"

    if state["market_share"] > 30:
        return rng.choice(AGGRESSIVE_MOVES)

    moves = list(_DEFAULT_WEIGHTS.keys())
    weights = list(_DEFAULT_WEIGHTS.values())
    return rng.choices(moves, weights=weights, k=1)[0]


def apply_competitor_effects(state: SimCorpState, move: str) -> None:
    """Mutate state to reflect a competitor move's market impact (in place).

    Effects are intentionally modest and bounded so several quarters of pressure
    accumulate into a believable crisis rather than an instant collapse.
    """
    comp = state["competitor_market_share"]

    if move == "price_undercut_20pct":
        state["competitor_market_share"] = clamp(comp + 2.0, 0, 100)
        state["churn_rate"] = clamp(state["churn_rate"] + 1.5, 0, 15)
    elif move == "feature_launch_ai":
        state["competitor_market_share"] = clamp(comp + 1.5, 0, 100)
        state["nps_score"] = clamp(state["nps_score"] - 4, -100, 100)
    elif move == "talent_poach":
        state["product_score"] = clamp(state["product_score"] - 1.0, 0, 10)
        state["competitor_market_share"] = clamp(comp + 0.5, 0, 100)
    elif move == "enterprise_deal":
        state["competitor_market_share"] = clamp(comp + 3.0, 0, 100)
    elif move == "free_tier_launch":
        state["competitor_market_share"] = clamp(comp + 1.0, 0, 100)
        state["churn_rate"] = clamp(state["churn_rate"] + 1.0, 0, 15)
    elif move == "funding_round":
        # War chest, not immediate share — pressure compounds over time.
        state["competitor_market_share"] = clamp(comp + 2.0, 0, 100)
    # "hold" -> no effect.


def describe_move(move: str) -> str:
    """Human-readable description for the activity feed / CEO context."""
    return COMPETITOR_MOVES.get(move, COMPETITOR_MOVES["hold"])
