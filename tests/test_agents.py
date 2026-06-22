"""
tests/test_agents.py — offline smoke tests for the SimCorp agent pipeline.

Runs WITHOUT an NVIDIA API key by stubbing every agent's LLM call with canned
JSON, so the deterministic orchestration (tick order, parallel merge, guards,
persistence) can be verified in CI. Run directly:

    python tests/test_agents.py

or via pytest:

    pytest tests/test_agents.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

# Ensure the repo root is importable when run directly (python tests/test_agents.py).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Use a throwaway DB so tests never touch a real simulation DB.
os.environ["DATABASE_URL"] = "sqlite:///./db/test_agents.db"

import agents.competitor_agent as cmp_mod
import agents.ceo_agent as ceo_mod
import agents.finance_agent as fin_mod
import agents.sales_agent as sal_mod
import agents.product_agent as prod_mod
import agents.marketing_agent as mkt_mod
import agents.customer_agent as cust_mod

from core.tick import run_tick, run_quarters
from core.persistence import load_latest_state, reset_db
from simulation.scenarios import load_scenario


def _install_stubs(strategy="aggressive_growth", move="price_undercut_20pct"):
    async def cmp_f(l, s, u): return json.dumps({"move": move, "taunt": "watch out."})
    async def ceo_f(l, s, u): return json.dumps({
        "strategy": strategy, "pricing_action": "hold",
        "budget_allocation": {"product": 0.35, "marketing": 0.30, "sales": 0.25, "ops": 0.10},
        "key_directive": "Execute the plan.", "reasoning": "Stub reasoning."})
    async def fin_f(l, s, u): return json.dumps({"growth_rate": 0.15, "headcount_growth": 0.08, "finance_report": "ok"})
    async def sal_f(l, s, u): return json.dumps({"lead_quality": 1.05, "sales_report": "ok"})
    async def prod_f(l, s, u): return json.dumps({"features_shipped": 2, "product_score": 7.1})
    async def mkt_f(l, s, u): return json.dumps({"cac_adjustment": 0.9})
    async def cust_f(l, s, u): return json.dumps({"new_nps": 45, "new_churn": 4.0})
    cmp_mod.ainvoke = cmp_f; ceo_mod.ainvoke = ceo_f; fin_mod.ainvoke = fin_f
    sal_mod.ainvoke = sal_f; prod_mod.ainvoke = prod_f; mkt_mod.ainvoke = mkt_f
    cust_mod.ainvoke = cust_f


def test_full_tick_runs_all_seven_agents():
    _install_stubs()
    reset_db()
    st = load_scenario("mvp_launch")
    st = asyncio.run(run_tick(st))
    agents_logged = {e["agent"] for e in st["agent_log"]}
    assert agents_logged == {"Competitor", "CEO", "Product", "Marketing", "Customer", "Finance", "Sales"}
    assert st["quarter"] == 2 and len(st["history"]) == 1


def test_kpis_change_logically_under_growth():
    _install_stubs(strategy="aggressive_growth")
    reset_db()
    st = load_scenario("mvp_launch")
    arr0, cust0, cac0 = st["arr"], st["customers"], st["cac"]
    st = asyncio.run(run_tick(st))
    assert st["arr"] > arr0, "ARR should grow under aggressive_growth"
    assert st["customers"] > cust0, "customers should grow"
    assert st["cac"] > cac0, "CAC should rise under aggressive_growth"


def test_competitor_undercut_forces_pricing_response():
    _install_stubs(move="price_undercut_20pct")
    reset_db()
    st = load_scenario("mvp_launch")
    st = asyncio.run(run_tick(st))
    assert st["ceo_decision"]["pricing_action"] != "hold"


def test_low_runway_forces_cost_cut():
    _install_stubs(strategy="aggressive_growth")
    reset_db()
    st = load_scenario("crisis")
    # Burn down runway over several quarters; guard must force cost_cut.
    st = asyncio.run(run_quarters(st, 4))
    strategies = [e["action"] for e in st["agent_log"] if e["agent"] == "CEO"]
    assert any("cost_cut" in s for s in strategies), "expected a forced cost_cut under crisis"


def test_persistence_survives_reload():
    _install_stubs()
    reset_db()
    st = load_scenario("mvp_launch")
    st = asyncio.run(run_tick(st))
    loaded = load_latest_state()
    assert loaded is not None and loaded["quarter"] == st["quarter"]


def test_eight_quarter_sim_completes():
    _install_stubs()
    reset_db()
    st = load_scenario("mvp_launch")
    while st["quarter"] <= 8:
        st = asyncio.run(run_tick(st))
    assert st["simulation_status"] == "completed" and len(st["history"]) == 8


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        t()
        print(f"  PASS  {t.__name__}")
        passed += 1
    # Clean up the throwaway DB.
    try:
        os.remove("db/test_agents.db")
    except OSError:
        pass
    print(f"\n{passed}/{len(tests)} tests passed.")


if __name__ == "__main__":
    _run_all()
