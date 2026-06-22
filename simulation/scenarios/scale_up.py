"""
Scenario 2: Scale Up.

ARR ~$1.8M, a healthy customer base, ~18 months of runway, and SimCorp is
winning: it leads the competitor on market share. The competitor is active but
on the back foot. The growth-mode counterpoint to the Crisis scenario.
"""

from core.state import new_state

INITIAL_STATE = new_state(
    quarter=4,
    scenario="scale_up",
    simulation_status="paused",
    arr=1_800_000,
    mrr=150_000,
    burn_rate=140_000,
    cash_balance=2_520_000,   # 2.52M / 140K = ~18 months runway
    runway_months=18.0,
    cac=1_800,
    customers=340,
    churn_rate=3.5,
    nps_score=51,
    market_share=25.5,
    competitor_market_share=19.0,
    features_shipped=2,
    product_score=7.8,
    competitor_move="hold: Competitor made no significant moves this quarter — focus on internal execution",
)
