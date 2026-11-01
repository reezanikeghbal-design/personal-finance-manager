"""Report generation. Pure functions that build tables from a transaction DataFrame."""
from __future__ import annotations

import pandas as pd

from services import analytics


def build_report(tx_df: pd.DataFrame) -> dict:
    """Return all report tables for the given (already filtered) transactions."""
    monthly = analytics.monthly_summary(tx_df)
    return {
        "summary": analytics.summarize(tx_df),
        "monthly": monthly,
        "income_by_category": analytics.category_breakdown(tx_df, "Income"),
        "expenses_by_category": analytics.category_breakdown(tx_df, "Expense"),
        "monthly_comparison": monthly_comparison(monthly),
    }


def monthly_comparison(monthly: pd.DataFrame) -> pd.DataFrame:
    """Month-over-month change in income and expenses (None for the first month)."""
    cols = ["month", "income", "expenses", "income_change_pct", "expenses_change_pct"]
    if monthly is None or monthly.empty:
        return pd.DataFrame(columns=cols)
    m = monthly.sort_values("month").reset_index(drop=True)
    rows = []
    for i, r in m.iterrows():
        def change(col):
            if i == 0:
                return None
            prev = float(m.loc[i - 1, col])
            return None if prev == 0 else round((float(r[col]) - prev) / prev * 100, 2)
        rows.append({"month": r["month"], "income": r["income"], "expenses": r["expenses"],
                     "income_change_pct": change("income"), "expenses_change_pct": change("expenses")})
    return pd.DataFrame(rows, columns=cols)


def savings_analysis(monthly: pd.DataFrame) -> pd.DataFrame:
    cols = ["month", "income", "expenses", "saved", "savings_rate"]
    if monthly is None or monthly.empty:
        return pd.DataFrame(columns=cols)
    out = monthly.rename(columns={"net": "saved"})[cols]
    return out.reset_index(drop=True)


def export_tables(report: dict, tx_df: pd.DataFrame) -> dict:
    """Map of sheet name -> DataFrame with human-readable column names."""
    s = report["summary"]
    summary = pd.DataFrame([
        {"Metric": "Total Income", "Value": s["total_income"]},
        {"Metric": "Total Expenses", "Value": s["total_expenses"]},
        {"Metric": "Net Balance", "Value": s["net_balance"]},
        {"Metric": "Savings Rate (%)", "Value": s["savings_rate"]},
    ])
    monthly = report["monthly"].rename(columns={
        "month": "Month", "income": "Income", "expenses": "Expenses",
        "net": "Net", "savings_rate": "Savings Rate (%)"})
    exp = report["expenses_by_category"].rename(columns={
        "category": "Category", "amount": "Amount", "share_pct": "Share (%)"})
    inc = report["income_by_category"].rename(columns={
        "category": "Category", "amount": "Amount", "share_pct": "Share (%)"})
    from utils.exporters import transactions_for_export
    return {
        "Summary": summary, "Monthly": monthly,
        "Expenses by Category": exp, "Income by Category": inc,
        "Transactions": transactions_for_export(tx_df),
    }
