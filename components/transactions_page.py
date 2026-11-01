"""Transactions page: add, search/filter/sort, edit, delete."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

import config
from components.ui import empty_state, flash
from config import CURRENCIES
from services import categories as cat_svc
from services import transactions as tx_svc
from utils.validators import ValidationError

SORT_OPTIONS = {"Date": "date", "Amount": "amount", "Category": "category",
                "Type": "type", "Description": "description", "Created": "created_at"}


def _add_section() -> None:
    with st.expander("➕ Add transaction", expanded=False):
        tx_type = st.radio("Type", config.TRANSACTION_TYPES, horizontal=True, key="add_type")
        cats = cat_svc.list_categories(tx_type)
        with st.form("add_tx_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            amount = c1.number_input("Amount", min_value=0.0, step=1.0, format="%.2f")
            cat_id = c2.selectbox("Category", [c["id"] for c in cats],
                                  format_func={c["id"]: c["name"] for c in cats}.get) if cats else None
            tx_date = c3.date_input("Date", value=date.today())
            desc = st.text_input("Description", max_chars=config.MAX_DESCRIPTION_LENGTH)
            if st.form_submit_button("Save transaction", type="primary"):
                try:
                    tx_svc.add_transaction(amount, tx_type, int(cat_id) if cat_id is not None else None,
                                           tx_date, desc)
                    flash("Transaction added.")
                    st.rerun()
                except ValidationError as exc:
                    st.error(str(exc))


def _edit_section(df: pd.DataFrame, symbol: str) -> None:
    st.subheader("Edit or delete")
    labels = {int(r.id): f"#{int(r.id)} · {r.date} · {r.category} · {symbol}{r.amount:,.2f}"
              for r in df.itertuples()}
    tx_id = st.selectbox("Select a transaction", list(labels), format_func=labels.get, key="edit_pick")
    tx = tx_svc.get_transaction(int(tx_id))
    if tx is None:
        st.warning("Transaction no longer exists.")
        return
    types = list(config.TRANSACTION_TYPES)
    new_type = st.radio("Type", types, index=types.index(tx["type"]), horizontal=True,
                        key=f"edit_type_{tx_id}")
    cats = cat_svc.list_categories(new_type)
    ids = [c["id"] for c in cats]
    names = {c["id"]: c["name"] for c in cats}
    with st.form(f"edit_form_{tx_id}"):
        c1, c2, c3 = st.columns(3)
        amount = c1.number_input("Amount", min_value=0.0, step=1.0, format="%.2f",
                                 value=float(tx["amount"]))
        cat_id = c2.selectbox("Category", ids, format_func=names.get,
                              index=ids.index(tx["category_id"]) if tx["category_id"] in ids else 0)
        tx_date = c3.date_input("Date", value=tx["date"])
        desc = st.text_input("Description", value=tx["description"], max_chars=config.MAX_DESCRIPTION_LENGTH)
        if st.form_submit_button("Update transaction", type="primary"):
            try:
                tx_svc.update_transaction(int(tx_id), amount, new_type, int(cat_id), tx_date, desc)
                flash(f"Transaction #{tx_id} updated.")
                st.rerun()
            except ValidationError as exc:
                st.error(str(exc))

    pending = st.session_state.get("delete_pending")
    if pending != tx_id:
        if st.button("🗑️ Delete transaction", key=f"del_{tx_id}"):
            st.session_state["delete_pending"] = tx_id
            st.rerun()
    else:
        st.warning(f"Permanently delete transaction #{tx_id}? This cannot be undone.")
        b1, b2, _ = st.columns([1, 1, 4])
        if b1.button("Yes, delete", type="primary", key=f"confirm_del_{tx_id}"):
            try:
                tx_svc.delete_transaction(int(tx_id))
                flash(f"Transaction #{tx_id} deleted.")
            except ValidationError as exc:
                flash(str(exc), "error")
            st.session_state.pop("delete_pending", None)
            st.rerun()
        if b2.button("Cancel", key=f"cancel_del_{tx_id}"):
            st.session_state.pop("delete_pending", None)
            st.rerun()


def render_transactions(currency: str) -> None:
    st.title("Transactions")
    symbol = CURRENCIES[currency]
    _add_section()

    st.subheader("History")
    all_cats = cat_svc.list_categories()
    f1, f2, f3 = st.columns([2, 1, 2])
    search = f1.text_input("Search", placeholder="Description or category…", key="tx_search")
    type_filter = f2.selectbox("Type", ["All", *config.TRANSACTION_TYPES], key="tx_type_filter")
    cat_filter = f3.multiselect("Categories", [c["id"] for c in all_cats],
                                format_func={c["id"]: c["name"] for c in all_cats}.get, key="tx_cat_filter")
    g1, g2, g3 = st.columns([2, 1, 1])
    use_range = g1.checkbox("Filter by date range", key="tx_use_range")
    start = end = None
    if use_range:
        picked = g1.date_input("Date range", value=(date.today().replace(day=1), date.today()), key="tx_range")
        if isinstance(picked, (list, tuple)) and len(picked) == 2:
            start, end = picked
        else:
            g1.info("Select both a start and an end date.")
    sort_label = g2.selectbox("Sort by", list(SORT_OPTIONS), key="tx_sort")
    ascending = g3.radio("Order", ["Descending", "Ascending"], key="tx_order") == "Ascending"

    df = tx_svc.list_transactions(start=start, end=end,
                                  tx_type=None if type_filter == "All" else type_filter,
                                  category_ids=[int(c) for c in cat_filter] or None,
                                  search=search, sort_by=SORT_OPTIONS[sort_label], ascending=ascending)
    if df.empty:
        if not (search or cat_filter or use_range or type_filter != "All"):
            empty_state("No transactions yet", "Use **Add transaction** above to record your first one.")
        else:
            st.warning("No transactions match the current filters.")
        return

    shown = df.rename(columns={"id": "ID", "date": "Date", "type": "Type", "category": "Category",
                               "amount": "Amount", "description": "Description", "created_at": "Created At"})
    st.caption(f"{len(shown)} transaction(s)")
    st.dataframe(shown, use_container_width=True, hide_index=True, column_config={
        "Amount": st.column_config.NumberColumn(format=f"{symbol}%.2f"),
        "Date": st.column_config.DateColumn(format="YYYY-MM-DD"),
        "Created At": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm"),
    })
    _edit_section(df, symbol)
