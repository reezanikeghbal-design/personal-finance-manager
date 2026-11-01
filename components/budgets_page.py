"""Budgets page."""
from __future__ import annotations

from datetime import date

import streamlit as st

from components.ui import empty_state, esc, flash, progress_bar_html
from config import CURRENCIES
from services import analytics
from services import budgets as svc
from services import categories as cat_svc
from utils.helpers import add_months, format_currency, format_percent, month_key
from utils.validators import ValidationError


def _month_options() -> list[str]:
    base = date.today().replace(day=1)
    return [month_key(add_months(base, n)) for n in range(3, -13, -1)]


def render_budgets(currency: str) -> None:
    st.title("Budgets")
    fmt = lambda v: format_currency(v, currency)  # noqa: E731
    options = _month_options()
    month = st.selectbox("Month", options, index=options.index(month_key(date.today())), key="budget_month")
    status = svc.get_budget_status(month)
    totals = analytics.budget_totals(status)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Budget", fmt(totals["budget"]))
    m2.metric("Actual Spending", fmt(totals["spent"]))
    m3.metric("Remaining", fmt(totals["remaining"]) if totals["remaining"] is not None else "N/A")
    m4.metric("Usage", format_percent(totals["usage_pct"]))

    if status.empty:
        empty_state(f"No budgets for {month}", "Add a budget for an expense category below.")
    else:
        over = status[status["exceeded"]]
        if len(over):
            st.error(f"{len(over)} budget(s) exceeded: " + ", ".join(over["category"]))
        for r in status.itertuples():
            cls = "pfm-row over" if r.exceeded else "pfm-row"
            tag = " ⚠️ Over budget" if r.exceeded else ""
            st.markdown(
                f'<div class="{cls}"><div class="pfm-head"><span>{esc(r.category)}{tag}</span>'
                f'<span>{format_percent(r.usage_pct)}</span></div>'
                f'{progress_bar_html(r.usage_pct, r.exceeded)}'
                f'<div class="pfm-sub">Budget {fmt(r.budget)} · Spent {fmt(r.spent)} · '
                f'Remaining {fmt(r.remaining)}</div></div>', unsafe_allow_html=True)
        table = status.rename(columns={"category": "Category", "budget": "Budget Amount",
                                       "spent": "Actual Spending", "remaining": "Remaining Budget",
                                       "usage_pct": "Usage (%)", "exceeded": "Exceeded"})
        st.dataframe(table.drop(columns=["budget_id"]), use_container_width=True, hide_index=True,
                     column_config={c: st.column_config.NumberColumn(format=f"{CURRENCIES[currency]}%.2f")
                                    for c in ("Budget Amount", "Actual Spending", "Remaining Budget")})

    expense_cats = cat_svc.list_categories("Expense")
    budgeted = set(status["category"]) if not status.empty else set()
    free = [c for c in expense_cats if c["name"] not in budgeted]
    with st.expander("➕ Add budget", expanded=status.empty):
        if not free:
            st.info("Every expense category already has a budget for this month.")
        else:
            with st.form("add_budget", clear_on_submit=True):
                cid = st.selectbox("Expense category", [c["id"] for c in free],
                                   format_func={c["id"]: c["name"] for c in free}.get)
                amount = st.number_input("Budget amount", min_value=0.0, step=10.0, format="%.2f")
                if st.form_submit_button("Save budget", type="primary"):
                    try:
                        svc.create_budget(int(cid), month, amount)
                        flash("Budget created.")
                        st.rerun()
                    except ValidationError as exc:
                        st.error(str(exc))

    if status.empty:
        return
    with st.expander("✏️ Edit or delete budget"):
        ids = {int(r.budget_id): r.category for r in status.itertuples()}
        bid = st.selectbox("Budget", list(ids), format_func=ids.get, key="edit_budget_pick")
        current = float(status.loc[status["budget_id"] == bid, "budget"].iloc[0])
        amount = st.number_input("New amount", min_value=0.0, step=10.0, format="%.2f",
                                 value=current, key=f"edit_budget_amt_{bid}")
        c1, c2 = st.columns(2)
        if c1.button("Update budget", type="primary", key=f"upd_budget_{bid}"):
            try:
                svc.update_budget(int(bid), amount)
                flash("Budget updated.")
                st.rerun()
            except ValidationError as exc:
                st.error(str(exc))
        confirm = c2.checkbox("Confirm deletion", key=f"confirm_budget_{bid}")
        if c2.button("Delete budget", disabled=not confirm, key=f"del_budget_{bid}"):
            try:
                svc.delete_budget(int(bid))
                flash("Budget deleted.")
                st.rerun()
            except ValidationError as exc:
                st.error(str(exc))
