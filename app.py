"""Personal Finance Manager - Streamlit entry point."""
import streamlit as st

import config

st.set_page_config(page_title=config.APP_NAME, page_icon="💰", layout="wide")

from components.budgets_page import render_budgets  # noqa: E402
from components.categories_page import render_categories  # noqa: E402
from components.dashboard import render_dashboard  # noqa: E402
from components.reports_page import render_reports  # noqa: E402
from components.settings_page import render_settings  # noqa: E402
from components.sidebar import render_sidebar  # noqa: E402
from components.transactions_page import render_transactions  # noqa: E402
from components.ui import apply_theme, show_flash  # noqa: E402
from database.db import init_db  # noqa: E402
from services import settings  # noqa: E402


def main() -> None:
    init_db()
    currency, theme = settings.get_currency(), settings.get_theme()
    apply_theme(theme)
    page = render_sidebar()
    show_flash()
    if page == "Dashboard":
        render_dashboard(currency, theme)
    elif page == "Transactions":
        render_transactions(currency)
    elif page == "Categories":
        render_categories()
    elif page == "Budgets":
        render_budgets(currency)
    elif page == "Reports":
        render_reports(currency, theme)
    else:
        render_settings(currency, theme)


main()
