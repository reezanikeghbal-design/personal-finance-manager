"""Reports page with CSV / Excel export."""
from __future__ import annotations

from datetime import date

import streamlit as st

from components import charts
from components.ui import empty_state
from config import CURRENCIES
from services import categories as cat_svc
from services import reports
from services.transactions import list_transactions
from utils import exporters
from utils.helpers import format_currency, format_percent


def render_reports(currency: str, theme: str) -> None:
    st.title("Reports")
    fmt = lambda v: format_currency(v, currency)  # noqa: E731
    all_tx = list_transactions()
    if all_tx.empty:
        empty_state("No data to report on", "Add transactions or load sample data from **Settings**.")
        return

    first = min(all_tx["date"])
    c1, c2 = st.columns([2, 3])
    picked = c1.date_input("Date range", value=(first, max(date.today(), max(all_tx["date"]))), key="rep_range")
    cats = cat_svc.list_categories()
    cat_ids = c2.multiselect("Categories (optional)", [c["id"] for c in cats],
                             format_func={c["id"]: f"{c['name']} ({c['type']})" for c in cats}.get, key="rep_cats")
    if not isinstance(picked, (list, tuple)) or len(picked) != 2:
        st.info("Select both a start and an end date.")
        return
    start, end = picked
    tx = list_transactions(start=start, end=end, category_ids=[int(i) for i in cat_ids] or None,
                           sort_by="date", ascending=True)
    if tx.empty:
        st.warning("No transactions match the selected filters.")
        return

    report = reports.build_report(tx)
    s = report["summary"]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Income", fmt(s["total_income"]))
    m2.metric("Expenses", fmt(s["total_expenses"]))
    m3.metric("Net", fmt(s["net_balance"]))
    m4.metric("Savings Rate", format_percent(s["savings_rate"]))

    money = st.column_config.NumberColumn(format=f"{CURRENCIES[currency]}%.2f")
    pct = st.column_config.NumberColumn(format="%.1f%%")
    t1, t2, t3, t4 = st.tabs(["Category breakdown", "Monthly comparison", "Savings analysis", "Transactions"])
    with t1:
        a, b = st.columns(2)
        with a:
            st.subheader("Expenses")
            st.dataframe(report["expenses_by_category"], hide_index=True, use_container_width=True,
                         column_config={"amount": money, "share_pct": pct})
        with b:
            st.subheader("Income")
            st.dataframe(report["income_by_category"], hide_index=True, use_container_width=True,
                         column_config={"amount": money, "share_pct": pct})
        fig = charts.expenses_by_category(report["expenses_by_category"], theme)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    with t2:
        st.dataframe(report["monthly_comparison"], hide_index=True, use_container_width=True,
                     column_config={"income": money, "expenses": money,
                                    "income_change_pct": pct, "expenses_change_pct": pct})
        st.plotly_chart(charts.monthly_overview(report["monthly"], theme), use_container_width=True)
    with t3:
        st.dataframe(reports.savings_analysis(report["monthly"]), hide_index=True, use_container_width=True,
                     column_config={"income": money, "expenses": money, "saved": money, "savings_rate": pct})
        fig = charts.savings_rate_trend(report["monthly"], theme)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Savings rate is undefined for months without income.")
    with t4:
        st.dataframe(exporters.transactions_for_export(tx), hide_index=True, use_container_width=True)

    st.subheader("Export")
    st.caption("Exports contain the transactions and summaries for the filters selected above.")
    tables = reports.export_tables(report, tx)
    stamp = f"{start}_{end}"
    e1, e2, e3 = st.columns(3)
    e1.download_button("⬇️ Transactions (CSV)", exporters.to_csv_bytes(tables["Transactions"]),
                       file_name=f"transactions_{stamp}.csv", mime="text/csv")
    e2.download_button("⬇️ Monthly summary (CSV)", exporters.to_csv_bytes(tables["Monthly"]),
                       file_name=f"monthly_summary_{stamp}.csv", mime="text/csv")
    e3.download_button("⬇️ Full report (Excel)", exporters.to_excel_bytes(tables),
                       file_name=f"report_{stamp}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
