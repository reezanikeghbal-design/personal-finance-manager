"""Settings page."""
from __future__ import annotations

import streamlit as st

import config
from components.ui import flash
from database import db
from services import sample_data, settings
from utils.validators import ValidationError


def render_settings(currency: str, theme: str) -> None:
    st.title("Settings")

    st.subheader("Appearance & currency")
    c1, c2 = st.columns(2)
    new_currency = c1.selectbox("Currency", list(config.CURRENCIES),
                                index=list(config.CURRENCIES).index(currency),
                                format_func=lambda c: f"{c} ({config.CURRENCIES[c]})")
    new_theme = c2.radio("Theme", config.THEMES, index=config.THEMES.index(theme),
                         format_func=str.title, horizontal=True)
    c1.caption("Currency only changes how amounts are displayed. No conversion is performed.")
    c2.caption("Tables are drawn by Streamlit and follow Streamlit's own theme "
               "(⋮ menu → Settings → Choose app theme).")
    if st.button("Save preferences", type="primary"):
        try:
            settings.set_currency(new_currency)
            settings.set_theme(new_theme)
            flash("Preferences saved.")
            st.rerun()
        except ValidationError as exc:
            st.error(str(exc))

    st.divider()
    st.subheader("Sample data")
    if sample_data.is_loaded():
        st.info("Sample data has already been loaded and will not be added again.")
    else:
        st.caption("Adds about six months of example income, expenses and budgets. Optional.")
        if st.button("Load sample data"):
            try:
                n = sample_data.load_sample_data()
                flash(f"Loaded {n} sample transactions and monthly budgets.")
                st.rerun()
            except ValidationError as exc:
                st.error(str(exc))

    st.divider()
    st.subheader("Database")
    path = db.get_db_path()
    size_kb = path.stat().st_size / 1024 if path.exists() else 0
    st.markdown(f"Your data is stored locally in this SQLite file:\n\n`{path}`  \n({size_kb:,.1f} KB)")
    st.caption("The database is not encrypted. Protect the file with your operating system's "
               "disk encryption and access controls if needed.")

    st.markdown("**Backup**")
    st.download_button("⬇️ Download database backup", db.backup_bytes(), file_name=db.backup_filename(),
                       mime="application/octet-stream")

    st.markdown("**Restore**")
    st.warning("Restoring replaces all current data. A safety copy of the current database is saved "
               "in `data/backups/` first.")
    key = st.session_state.setdefault("restore_key", 0)
    upload = st.file_uploader("Backup file (.db, .sqlite, .sqlite3)", type=["db", "sqlite", "sqlite3"],
                              key=f"restore_upload_{key}")
    confirm = st.checkbox("I understand that this replaces my current data", key=f"restore_confirm_{key}")
    if st.button("Restore database", disabled=not (upload and confirm)):
        try:
            safety = db.restore_from_bytes(upload.getvalue(), upload.name)
            st.session_state["restore_key"] = key + 1
            flash(f"Database restored. Previous data saved to {safety.name}.")
            st.rerun()
        except ValidationError as exc:
            st.error(str(exc))
