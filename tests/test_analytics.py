import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import analytics, reports  # noqa: E402


def make_df():
    rows = [
        (1, date(2026, 1, 5), "Income", "Salary", 3000.0, "", None),
        (2, date(2026, 1, 10), "Expense", "Food", 400.0, "", None),
        (3, date(2026, 1, 12), "Expense", "Housing", 1000.0, "", None),
        (4, date(2026, 2, 5), "Income", "Salary", 3000.0, "", None),
        (5, date(2026, 2, 20), "Expense", "Food", 600.0, "", None),
        (6, date(2026, 2, 21), "Income", "Freelance", 500.0, "", None),
    ]
    return pd.DataFrame(rows, columns=analytics.TX_COLUMNS)


def close(a, b):
    return abs(a - b) < 1e-9


def test_totals_and_net_balance():
    df = make_df()
    assert analytics.total_income(df) == 6500.0
    assert analytics.total_expenses(df) == 2000.0
    assert analytics.net_balance(df) == 4500.0


def test_savings_rate_formula_and_zero_income():
    assert analytics.savings_rate(1000, 250) == 75.0
    assert analytics.savings_rate(1000, 1500) == -50.0
    assert analytics.savings_rate(0, 100) is None


def test_empty_dataframe_is_safe():
    for df in (analytics.empty_transactions(), None):
        s = analytics.summarize(df)
        assert s == {"total_income": 0.0, "total_expenses": 0.0, "net_balance": 0.0, "savings_rate": None}
        assert analytics.monthly_summary(df).empty
        assert analytics.category_breakdown(df).empty


def test_monthly_summary():
    m = analytics.monthly_summary(make_df())
    assert list(m["month"]) == ["2026-01", "2026-02"]
    jan, feb = m.iloc[0], m.iloc[1]
    assert jan["income"] == 3000.0 and jan["expenses"] == 1400.0 and jan["net"] == 1600.0
    assert close(jan["savings_rate"], 53.33)
    assert feb["income"] == 3500.0 and feb["expenses"] == 600.0


def test_month_summary_and_category_breakdown():
    df = make_df()
    feb = analytics.month_summary(df, "2026-02")
    assert feb["total_income"] == 3500.0 and feb["total_expenses"] == 600.0
    b = analytics.category_breakdown(df, "Expense")
    assert list(b["category"]) == ["Food", "Housing"]       # tie on amount -> alphabetical
    assert b.iloc[0]["amount"] == 1000.0 and close(b["share_pct"].sum(), 100.0)
    assert close(b.iloc[0]["share_pct"], 50.0)


def test_budget_status_spending_remaining_and_exceeded():
    df = make_df()
    budgets = pd.DataFrame([
        (1, 10, "Food", "2026-01", 500.0),
        (2, 11, "Housing", "2026-01", 900.0),
        (3, 12, "Travel", "2026-01", 200.0),
        (4, 10, "Food", "2026-02", 700.0),
    ], columns=["id", "category_id", "category", "month", "amount"])
    s = analytics.compute_budget_status(budgets, df, "2026-01").set_index("category")
    assert s.loc["Food", "spent"] == 400.0 and s.loc["Food", "remaining"] == 100.0
    assert close(s.loc["Food", "usage_pct"], 80.0) and not s.loc["Food", "exceeded"]
    assert s.loc["Housing", "spent"] == 1000.0 and s.loc["Housing", "remaining"] == -100.0
    assert bool(s.loc["Housing", "exceeded"]) and close(s.loc["Housing", "usage_pct"], 111.11)
    assert s.loc["Travel", "spent"] == 0.0 and s.loc["Travel", "usage_pct"] == 0.0
    assert "2026-02" not in set(s.index)
    totals = analytics.budget_totals(analytics.compute_budget_status(budgets, df, "2026-01"))
    assert totals["budget"] == 1600.0 and totals["spent"] == 1400.0 and totals["remaining"] == 200.0


def test_budget_status_without_budgets():
    s = analytics.compute_budget_status(pd.DataFrame(), make_df(), "2026-01")
    assert s.empty
    assert analytics.budget_totals(s)["remaining"] is None


def test_report_monthly_comparison():
    r = reports.build_report(make_df())
    comp = r["monthly_comparison"]
    assert comp.iloc[0]["income_change_pct"] is None or pd.isna(comp.iloc[0]["income_change_pct"])
    assert close(comp.iloc[1]["income_change_pct"], 16.67)
    assert close(comp.iloc[1]["expenses_change_pct"], -57.14)
