"""
Scenario 1: MVP Launch — the default starting state.

A seed-stage SaaS startup with healthy runway, a small customer base, and a
mostly-idle competitor. The growth story everyone starts from.
"""

from core.state import new_state

INITIAL_STATE = new_state(
    quarter=1,
    scenario="mvp_launch",
    simulation_status="paused",
    arr=120_000,
    mrr=10_000,
    burn_rate=45_000,
    cash_balance=800_000,
    runway_months=17.8,
    cac=1_200,
    customers=28,
    churn_rate=4.2,
    nps_score=42,
    market_share=2.1,
    competitor_market_share=18.5,
    features_shipped=0,
    product_score=6.5,
    competitor_move="hold",
)
