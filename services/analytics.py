"""Financial calculations on transaction DataFrames.

All functions are pure (no database access) so they are easy to test.
Expected transaction columns: id, date, type, category, amount, description, created_at.
"""
from __future__ import annotations

import pandas as pd

TX_COLUMNS = ["id", "date", "type", "category", "amount", "description", "created_at"]


def empty_transactions() -> pd.DataFrame:
    return pd.DataFrame(columns=TX_COLUMNS)


def _prep(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or len(df) == 0:
        out = empty_transactions()
        out["date"] = pd.to_datetime(out["date"])
        out["amount"] = out["amount"].astype(float)
        return out
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out["amount"] = pd.to_numeric(out["amount"]).astype(float)
    return out


def total_income(df) -> float:
    d = _prep(df)
    return round(float(d.loc[d["type"] == "Income", "amount"].sum()), 2)


def total_expenses(df) -> float:
    d = _prep(df)
    return round(float(d.loc[d["type"] == "Expense", "amount"].sum()), 2)


def net_balance(df) -> float:
    return round(total_income(df) - total_expenses(df), 2)


def savings_rate(income: float, expenses: float):
    """(Income - Expenses) / Income * 100, or None when income is zero."""
    if income is None or income <= 0:
        return None
    return round((income - expenses) / income * 100, 2)


def summarize(df) -> dict:
    income, expenses = total_income(df), total_expenses(df)
    return {
        "total_income": income,
        "total_expenses": expenses,
        "net_balance": round(income - expenses, 2),
        "savings_rate": savings_rate(income, expenses),
    }


def monthly_summary(df) -> pd.DataFrame:
    """One row per month (YYYY-MM) with income, expenses, net and savings rate."""
    cols = ["month", "income", "expenses", "net", "savings_rate"]
    d = _prep(df)
    if d.empty:
        return pd.DataFrame(columns=cols)
    d["month"] = d["date"].dt.strftime("%Y-%m")
    income = d[d["type"] == "Income"].groupby("month")["amount"].sum()
    expenses = d[d["type"] == "Expense"].groupby("month")["amount"].sum()
    months = sorted(set(d["month"]))
    rows = []
    for m in months:
        inc = round(float(income.get(m, 0.0)), 2)
        exp = round(float(expenses.get(m, 0.0)), 2)
        rows.append({"month": m, "income": inc, "expenses": exp,
                     "net": round(inc - exp, 2), "savings_rate": savings_rate(inc, exp)})
    return pd.DataFrame(rows, columns=cols)


def category_breakdown(df, tx_type: str = "Expense") -> pd.DataFrame:
    """Total per category for one type, with percentage share, largest first."""
    cols = ["category", "amount", "share_pct"]
    d = _prep(df)
    d = d[d["type"] == tx_type]
    if d.empty:
        return pd.DataFrame(columns=cols)
    grouped = d.groupby("category", as_index=False)["amount"].sum()
    total = float(grouped["amount"].sum())
    grouped["amount"] = grouped["amount"].round(2)
    grouped["share_pct"] = (grouped["amount"] / total * 100).round(2) if total > 0 else 0.0
    return grouped.sort_values(["amount", "category"], ascending=[False, True]).reset_index(drop=True)[cols]


def month_summary(df, month: str) -> dict:
    """Summary restricted to a single 'YYYY-MM' month."""
    d = _prep(df)
    if not d.empty:
        d = d[d["date"].dt.strftime("%Y-%m") == month]
    return summarize(d)


def compute_budget_status(budgets_df, tx_df, month: str) -> pd.DataFrame:
    """Budget vs actual spending for one month.

    budgets_df columns: id, category, month, amount.
    Returns: budget_id, category, budget, spent, remaining, usage_pct, exceeded.
    """
    cols = ["budget_id", "category", "budget", "spent", "remaining", "usage_pct", "exceeded"]
    if budgets_df is None or len(budgets_df) == 0:
        return pd.DataFrame(columns=cols)
    b = budgets_df[budgets_df["month"] == month]
    if b.empty:
        return pd.DataFrame(columns=cols)
    d = _prep(tx_df)
    spent_by_cat = {}
    if not d.empty:
        m = d[(d["type"] == "Expense") & (d["date"].dt.strftime("%Y-%m") == month)]
        spent_by_cat = m.groupby("category")["amount"].sum().to_dict()
    rows = []
    for _, r in b.iterrows():
        budget = round(float(r["amount"]), 2)
        spent = round(float(spent_by_cat.get(r["category"], 0.0)), 2)
        usage = round(spent / budget * 100, 2) if budget > 0 else None
        rows.append({
            "budget_id": r["id"], "category": r["category"], "budget": budget,
            "spent": spent, "remaining": round(budget - spent, 2),
            "usage_pct": usage, "exceeded": spent > budget,
        })
    return pd.DataFrame(rows, columns=cols).sort_values("category").reset_index(drop=True)


def budget_totals(status_df: pd.DataFrame) -> dict:
    """Totals over budgeted categories only (avoids mixing unbudgeted spending)."""
    if status_df is None or len(status_df) == 0:
        return {"budget": 0.0, "spent": 0.0, "remaining": None, "usage_pct": None}
    budget = round(float(status_df["budget"].sum()), 2)
    spent = round(float(status_df["spent"].sum()), 2)
    return {"budget": budget, "spent": spent, "remaining": round(budget - spent, 2),
            "usage_pct": round(spent / budget * 100, 2) if budget > 0 else None}
