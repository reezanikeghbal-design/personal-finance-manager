"""Categories page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import config
from components.ui import empty_state, flash
from services import categories as svc
from utils.validators import ValidationError


def render_categories() -> None:
    st.title("Categories")
    cats = svc.list_categories()
    if not cats:
        empty_state("No categories", "Create your first category below.")
    left, right = st.columns(2)
    for col, tx_type in ((left, "Income"), (right, "Expense")):
        with col:
            st.subheader(f"{tx_type} categories")
            rows = [{"Name": c["name"], "Default": "Yes" if c["is_default"] else "",
                     "Transactions": c["usage"]} for c in cats if c["type"] == tx_type]
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.caption("None yet.")

    with st.expander("➕ Create category"):
        with st.form("create_cat", clear_on_submit=True):
            name = st.text_input("Name", max_chars=config.MAX_NAME_LENGTH)
            tx_type = st.radio("Type", config.TRANSACTION_TYPES, horizontal=True)
            if st.form_submit_button("Create", type="primary"):
                try:
                    svc.create_category(name, tx_type)
                    flash(f"Category '{name.strip()}' created.")
                    st.rerun()
                except ValidationError as exc:
                    st.error(str(exc))
    if not cats:
        return

    names = {c["id"]: f"{c['name']} ({c['type']})" for c in cats}
    with st.expander("✏️ Rename category"):
        with st.form("rename_cat"):
            cid = st.selectbox("Category", list(names), format_func=names.get, key="rename_pick")
            new_name = st.text_input("New name", max_chars=config.MAX_NAME_LENGTH)
            if st.form_submit_button("Rename", type="primary"):
                try:
                    svc.rename_category(int(cid), new_name)
                    flash("Category renamed.")
                    st.rerun()
                except ValidationError as exc:
                    st.error(str(exc))

    with st.expander("🗑️ Delete category"):
        cid = st.selectbox("Category to delete", list(names), format_func=names.get, key="delete_pick")
        chosen = next(c for c in cats if c["id"] == cid)
        reassign = None
        if chosen["usage"]:
            st.warning(f"This category is used by {chosen['usage']} transaction(s). "
                       "Choose a category to move them to before deleting.")
            options = [c["id"] for c in cats if c["type"] == chosen["type"] and c["id"] != cid]
            if options:
                reassign = st.selectbox("Reassign transactions to", options,
                                        format_func=lambda i: next(c["name"] for c in cats if c["id"] == i),
                                        key="reassign_pick")
            else:
                st.error("There is no other category of the same type to reassign to. Create one first.")
        confirm = st.checkbox("I understand this cannot be undone", key=f"confirm_cat_{cid}")
        blocked = (chosen["usage"] and reassign is None) or not confirm
        if st.button("Delete category", disabled=bool(blocked), key=f"del_cat_{cid}"):
            try:
                moved = svc.delete_category(int(cid), int(reassign) if reassign is not None else None)
                flash(f"Category '{chosen['name']}' deleted." + (f" {moved} transaction(s) reassigned." if moved else ""))
                st.rerun()
            except ValidationError as exc:
                st.error(str(exc))
