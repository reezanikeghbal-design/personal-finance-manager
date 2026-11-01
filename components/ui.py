"""Shared Streamlit UI helpers: theme CSS, flash messages, empty states."""
from __future__ import annotations

import html

import streamlit as st

PALETTES = {
    "light": {"bg": "#F6F8FB", "card": "#FFFFFF", "text": "#1F2937", "muted": "#6B7280",
              "border": "#E5E7EB", "primary": "#4F46E5", "side": "#FFFFFF"},
    "dark": {"bg": "#0F172A", "card": "#1E293B", "text": "#E5E7EB", "muted": "#94A3B8",
             "border": "#334155", "primary": "#818CF8", "side": "#111827"},
}
GOOD, BAD, WARN = "#16A34A", "#DC2626", "#D97706"


def palette(theme: str) -> dict:
    return PALETTES.get(theme, PALETTES["light"])


def apply_theme(theme: str) -> None:
    p = palette(theme)
    st.markdown(f"""
<style>
.stApp {{ background: {p['bg']}; color: {p['text']}; }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stSidebar"] {{ background: {p['side']}; border-right: 1px solid {p['border']}; }}
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp label, .stApp li,
.stApp [data-testid="stMarkdownContainer"], [data-testid="stSidebar"] * {{ color: {p['text']}; }}
.stApp [data-testid="stCaptionContainer"], .stApp small {{ color: {p['muted']}; }}
[data-testid="stMetric"] {{ background: {p['card']}; border: 1px solid {p['border']};
  border-radius: 12px; padding: 14px 16px; box-shadow: 0 1px 2px rgba(0,0,0,.05); }}
[data-testid="stMetricLabel"] p {{ color: {p['muted']} !important; font-size: .85rem; }}
[data-testid="stMetricValue"] {{ font-weight: 650; }}
.stApp input, .stApp textarea, .stApp [data-baseweb="select"] > div {{
  background: {p['card']} !important; color: {p['text']} !important; border-color: {p['border']} !important; }}
[data-baseweb="popover"] * {{ background: {p['card']}; color: {p['text']}; }}
.stApp [data-testid="stForm"], .stApp [data-testid="stExpander"] {{
  background: {p['card']}; border: 1px solid {p['border']}; border-radius: 12px; }}
.stApp .stButton > button, .stApp .stDownloadButton > button, .stApp [data-testid="stFormSubmitButton"] > button {{
  border-radius: 8px; border: 1px solid {p['border']}; background: {p['card']}; color: {p['text']}; }}
.stApp .stButton > button[kind="primary"], .stApp [data-testid="stFormSubmitButton"] > button[kind="primaryFormSubmit"] {{
  background: {p['primary']}; color: #FFFFFF; border-color: {p['primary']}; }}
.pfm-bar {{ background: {p['border']}; border-radius: 6px; height: 10px; overflow: hidden; }}
.pfm-bar > div {{ height: 10px; border-radius: 6px; }}
.pfm-row {{ background: {p['card']}; border: 1px solid {p['border']}; border-radius: 12px;
  padding: 12px 16px; margin-bottom: 10px; }}
.pfm-row.over {{ border-color: {BAD}; }}
.pfm-head {{ display: flex; justify-content: space-between; margin-bottom: 6px; font-weight: 600; }}
.pfm-sub {{ color: {p['muted']}; font-size: .85rem; margin-top: 6px; }}
</style>""", unsafe_allow_html=True)


def flash(message: str, level: str = "success") -> None:
    """Queue a message to be shown after the next rerun."""
    st.session_state.setdefault("_flash", []).append((level, message))


def show_flash() -> None:
    for level, message in st.session_state.pop("_flash", []):
        {"success": st.success, "warning": st.warning, "error": st.error}.get(level, st.info)(message)


def empty_state(title: str, hint: str) -> None:
    st.info(f"**{title}**\n\n{hint}")


def progress_bar_html(pct: float | None, exceeded: bool) -> str:
    width = 0 if pct is None else max(0.0, min(float(pct), 100.0))
    if exceeded:
        color = BAD
    elif pct is not None and pct >= 80:
        color = WARN
    else:
        color = GOOD
    return f'<div class="pfm-bar"><div style="width:{width:.1f}%;background:{color}"></div></div>'


def esc(text) -> str:
    return html.escape(str(text))
