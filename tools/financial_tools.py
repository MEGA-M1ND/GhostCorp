"""
tools/financial_tools.py — P&L, burn rate, and runway calculators.

Pure, deterministic functions used by the Finance Agent (and available to the
API for a P&L view). Keeping the arithmetic here means the numbers are testable
in isolation and identical everywhere they're used.
"""

from __future__ import annotations

MONTHS_PER_QUARTER = 3


def project_mrr(mrr: float, growth_rate: float, churn_rate_pct: float) -> float:
    """New MRR = old MRR * (1 + growth) * (1 - churn). churn is a percent."""
    return mrr * (1 + growth_rate) * (1 - churn_rate_pct / 100)


def mrr_to_arr(mrr: float) -> float:
    return mrr * 12


def project_burn(burn_rate: float, headcount_growth: float) -> float:
    """Burn scales with headcount/cost growth; never negative."""
    return max(0.0, burn_rate * (1 + headcount_growth))


def cash_after_quarter(cash_balance: float, mrr: float, burn_rate: float) -> float:
    """Net cash after a quarter of earning MRR and paying burn."""
    return cash_balance + (mrr - burn_rate) * MONTHS_PER_QUARTER


def runway_months(cash_balance: float, burn_rate: float) -> float:
    """Months of runway. Returns a large sentinel when burn is ~zero."""
    return (cash_balance / burn_rate) if burn_rate > 1 else 999.0


def build_pnl(mrr: float, burn_rate: float) -> dict:
    """A simple quarterly P&L snapshot for reporting."""
    revenue = mrr * MONTHS_PER_QUARTER
    costs = burn_rate * MONTHS_PER_QUARTER
    return {
        "quarterly_revenue": round(revenue, 2),
        "quarterly_costs": round(costs, 2),
        "quarterly_net": round(revenue - costs, 2),
        "gross_margin_pct": round((revenue - costs) / revenue * 100, 1) if revenue else 0.0,
    }
