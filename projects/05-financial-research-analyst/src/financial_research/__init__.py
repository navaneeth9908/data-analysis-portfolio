"""Offline financial research analyst demo package."""

from financial_research.metrics import (
    MovingAverageTrend,
    PerformanceSummary,
    PricePoint,
    build_risk_notes,
    load_price_history,
    render_research_brief,
    summarize_moving_average_trend,
    summarize_price_history,
)

__all__ = [
    "MovingAverageTrend",
    "PerformanceSummary",
    "PricePoint",
    "build_risk_notes",
    "load_price_history",
    "render_research_brief",
    "summarize_moving_average_trend",
    "summarize_price_history",
]
