"""Dashboard page."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from components import charts
from components.ui import empty_state
from services import analytics
from services.budgets import get_budget_status
from services.transactions import list_transactions
from utils.helpers import format_currency, format_percent, month_bounds, month_key


def date_filter(df: pd.DataFrame, key: str) -> tuple[pd.DataFrame, str]:
    """Render All time / Month / Custom range filters; return filtered frame and a label."""
    mode = st.radio("Period", ["All time", "Month", "Custom range"], horizontal=True, key=f"{key}_mode")
    if mode == "Month":
        months = sorted({d.strftime("%Y-%m") for d in pd.to_datetime(df["date"])}, reverse=True) \
            if len(df) else [month_key(date.today())]
        month = st.selectbox("Month", months, key=f"{key}_month")
        first, last = month_bounds(month)
        label = month
    elif mode == "Custom range":
        today = date.today()
        picked = st.date_input("Date range", value=(today.replace(day=1), today), key=f"{key}_range")
        if not isinstance(picked, (list, tuple)) or len(picked) != 2:
            st.info("Select both a start and an end date.")
            return df.iloc[0:0], "incomplete range"
        first, last = picked
        label = f"{first} to {last}"
    else:
        return df, "all time"
    if len(df) == 0:
        return df, label
    dates = pd.to_datetime(df["date"]).dt.date
    return df[(dates >= first) & (dates <= last)], label


def render_dashboard(currency: str, theme: str) -> None:
    st.title("Dashboard")
    all_tx = list_transactions()
    if all_tx.empty:
        empty_state("No transactions yet",
                    "Add your first transaction on the **Transactions** page, or load sample data from **Settings**.")
        return

    filtered, label = date_filter(all_tx, "dash")
    fmt = lambda v: format_currency(v, currency)  # noqa: E731
    s = analytics.summarize(filtered)
    st.caption(f"Showing: {label}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Income", fmt(s["total_income"]))
    c2.metric("Total Expenses", fmt(s["total_expenses"]))
    c3.metric("Net Balance", fmt(s["net_balance"]))
    c4.metric("Savings Rate", format_percent(s["savings_rate"]),
              help="(Income − Expenses) ÷ Income × 100. Shown as N/A when income is zero.")

    current = month_key(date.today())
    cur = analytics.month_summary(all_tx, current)
    status = get_budget_status(current)
    totals = analytics.budget_totals(status)
    d1, d2, d3 = st.columns(3)
    d1.metric(f"Income ({current})", fmt(cur["total_income"]))
    d2.metric(f"Expenses ({current})", fmt(cur["total_expenses"]))
    d3.metric("Remaining Monthly Budget",
              fmt(totals["remaining"]) if totals["remaining"] is not None else "N/A",
              help="Total budget minus spending in budgeted categories for the current month. "
                   "N/A when no budgets are set.")

    if filtered.empty:
        st.warning("No transactions in the selected period.")
        return
    monthly = analytics.monthly_summary(filtered)
    left, right = st.columns(2)
    with left:
        st.plotly_chart(charts.income_vs_expenses(s, theme), use_container_width=True)
    with right:
        st.plotly_chart(charts.monthly_spending_trend(monthly, theme), use_container_width=True)
    left, right = st.columns(2)
    with left:
        fig = charts.expenses_by_category(analytics.category_breakdown(filtered, "Expense"), theme)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No expenses in this period.")
    with right:
        st.plotly_chart(charts.monthly_overview(monthly, theme), use_container_width=True)
