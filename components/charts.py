"""Plotly chart builders. Each function returns a figure (or None when there is no data)."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from components.ui import BAD, GOOD, palette

_INCOME_COLOR, _EXPENSE_COLOR, _NET_COLOR = GOOD, BAD, "#4F46E5"


def _style(fig: go.Figure, theme: str, title: str, height: int = 340) -> go.Figure:
    p = palette(theme)
    fig.update_layout(
        title={"text": title, "x": 0.01, "font": {"size": 16}}, height=height,
        paper_bgcolor=p["card"], plot_bgcolor=p["card"], font={"color": p["text"]},
        margin={"l": 20, "r": 20, "t": 50, "b": 20}, legend={"orientation": "h", "y": -0.2},
    )
    fig.update_xaxes(gridcolor=p["border"], zeroline=False)
    fig.update_yaxes(gridcolor=p["border"], zeroline=False)
    return fig


def income_vs_expenses(summary: dict, theme: str = "light"):
    if not summary or (summary["total_income"] == 0 and summary["total_expenses"] == 0):
        return None
    fig = go.Figure(go.Bar(
        x=["Income", "Expenses"], y=[summary["total_income"], summary["total_expenses"]],
        marker_color=[_INCOME_COLOR, _EXPENSE_COLOR],
        text=[f"{summary['total_income']:,.2f}", f"{summary['total_expenses']:,.2f}"],
        textposition="outside"))
    fig.update_layout(showlegend=False)
    return _style(fig, theme, "Income vs. Expenses")


def monthly_spending_trend(monthly: pd.DataFrame, theme: str = "light"):
    if monthly is None or monthly.empty:
        return None
    fig = go.Figure(go.Scatter(x=monthly["month"], y=monthly["expenses"], mode="lines+markers",
                               line={"color": _EXPENSE_COLOR, "width": 3}, name="Expenses",
                               fill="tozeroy", fillcolor="rgba(220,38,38,0.08)"))
    fig.update_xaxes(type="category")
    return _style(fig, theme, "Monthly Spending Trend")


def expenses_by_category(breakdown: pd.DataFrame, theme: str = "light"):
    if breakdown is None or breakdown.empty:
        return None
    fig = go.Figure(go.Pie(labels=breakdown["category"], values=breakdown["amount"], hole=0.55,
                           textinfo="percent", sort=False))
    return _style(fig, theme, "Expenses by Category")


def monthly_overview(monthly: pd.DataFrame, theme: str = "light"):
    if monthly is None or monthly.empty:
        return None
    fig = go.Figure()
    fig.add_bar(x=monthly["month"], y=monthly["income"], name="Income", marker_color=_INCOME_COLOR)
    fig.add_bar(x=monthly["month"], y=monthly["expenses"], name="Expenses", marker_color=_EXPENSE_COLOR)
    fig.add_scatter(x=monthly["month"], y=monthly["net"], name="Net", mode="lines+markers",
                    line={"color": _NET_COLOR, "width": 3})
    fig.update_layout(barmode="group")
    fig.update_xaxes(type="category")
    return _style(fig, theme, "Monthly Financial Overview")


def savings_rate_trend(monthly: pd.DataFrame, theme: str = "light"):
    if monthly is None or monthly.empty or monthly["savings_rate"].isna().all():
        return None
    fig = go.Figure(go.Scatter(x=monthly["month"], y=monthly["savings_rate"], mode="lines+markers",
                               line={"color": _NET_COLOR, "width": 3}, name="Savings rate"))
    fig.update_yaxes(ticksuffix="%")
    fig.update_xaxes(type="category")
    return _style(fig, theme, "Savings Rate by Month")
