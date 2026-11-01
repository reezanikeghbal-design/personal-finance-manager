"""Sidebar navigation."""
from __future__ import annotations

import streamlit as st

import config
from database.db import get_db_path

PAGES = {
    "Dashboard": "📊", "Transactions": "💸", "Categories": "🗂️",
    "Budgets": "🎯", "Reports": "📑", "Settings": "⚙️",
}


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown(f"## 💰 {config.APP_NAME}")
        st.caption("Local-first personal finance tracking")
        page = st.radio("Navigation", list(PAGES), format_func=lambda n: f"{PAGES[n]}  {n}",
                        label_visibility="collapsed", key="nav_page")
        st.divider()
        st.caption(f"🔒 Data stored locally in `{get_db_path().name}`")
    return page
