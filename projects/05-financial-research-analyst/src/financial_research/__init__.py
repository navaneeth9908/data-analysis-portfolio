"""Offline financial research analyst demo package."""

from financial_research.metrics import (
    FundamentalSnapshot,
    FundamentalsSummary,
    MovingAverageTrend,
    PerformanceSummary,
    PricePoint,
    build_risk_notes,
    load_fundamental_snapshot,
    load_price_history,
    render_research_brief,
    summarize_fundamentals,
    summarize_moving_average_trend,
    summarize_price_history,
)

__all__ = [
    "FundamentalSnapshot",
    "FundamentalsSummary",
    "MovingAverageTrend",
    "PerformanceSummary",
    "PricePoint",
    "build_risk_notes",
    "load_fundamental_snapshot",
    "load_price_history",
    "render_research_brief",
    "summarize_fundamentals",
    "summarize_moving_average_trend",
    "summarize_price_history",
]
