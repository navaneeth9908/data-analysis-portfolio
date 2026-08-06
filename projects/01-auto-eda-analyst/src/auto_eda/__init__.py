"""Public API for the deterministic Auto EDA Analyst demo."""

from auto_eda.profile import (
    ColumnProfile,
    DatasetProfile,
    NumericCorrelation,
    profile_csv,
    render_markdown_report,
)

__all__ = [
    "ColumnProfile",
    "DatasetProfile",
    "NumericCorrelation",
    "profile_csv",
    "render_markdown_report",
]
