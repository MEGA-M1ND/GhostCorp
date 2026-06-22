"""
Scenario 3: Crisis — the DEMO HERO.

Q3 of a company under siege: ARR has stagnated, the competitor just closed a
$15M Series A, runway is down to ~9 months, churn is creeping up, and the rival
already holds more market share than GhostCorp. The CEO must pivot or die — and
the deterministic guards make a cost_cut/pivot decision land within a quarter.
"""

from core.state import new_state

INITIAL_STATE = new_state(
    quarter=3,
    scenario="crisis",
    simulation_status="paused",
    arr=1_500_000,
    mrr=125_000,
    burn_rate=180_000,
    cash_balance=1_700_000,   # 1.7M / 180K = ~9.4 months runway
    runway_months=9.4,
    cac=2_400,
    customers=300,
    churn_rate=7.0,
    nps_score=28,
    market_share=22.5,
    competitor_market_share=28.0,
    features_shipped=1,
    product_score=6.0,
    competitor_move="funding_round: Competitor raised $15M Series A — now has 18-month runway advantage",
)
