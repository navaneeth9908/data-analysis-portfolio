"""Offline financial research analyst demo package."""

from financial_research.metrics import (
    PerformanceSummary,
    PricePoint,
    load_price_history,
    render_research_brief,
    summarize_price_history,
)

__all__ = [
    "PerformanceSummary",
    "PricePoint",
    "load_price_history",
    "render_research_brief",
    "summarize_price_history",
]
