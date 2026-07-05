"""Lightweight, deterministic explanations for executed NL2SQL results."""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Number
from typing import Any

from .runner import QueryResult


@dataclass(frozen=True)
class ResultInsight:
    """Short business-facing interpretation of a query result."""

    headline: str
    details: list[str]

    def to_markdown(self) -> str:
        """Render the insight as compact Markdown for CLI and README examples."""
        lines = [f"**{self.headline}**"]
        lines.extend(f"- {detail}" for detail in self.details)
        return "\n".join(lines)


def explain_result(question: str, result: QueryResult) -> ResultInsight:
    """Create a deterministic answer summary from the first result rows.

    This is intentionally not an LLM summary. It keeps the offline portfolio demo
    reproducible while still giving interviewers a business-readable answer above
    the raw SQL table.
    """
    if not result.rows:
        return ResultInsight(
            headline="No rows matched the question.",
            details=[_execution_detail(result)],
        )

    first_row = result.rows[0]
    if _looks_like_trend(question, result):
        return _explain_trend_result(result)

    label_key, label_value = _label_field(first_row)
    metric_key, metric_value = _metric_field(first_row, exclude=label_key)

    if label_key and metric_key:
        metric_label = _format_label(metric_key)
        headline = f"{_format_value(label_value)} leads with {metric_label} of {_format_value(metric_value)}."
    elif metric_key:
        metric_label = _format_label(metric_key)
        headline = f"Top result has {metric_label} of {_format_value(metric_value)}."
    else:
        headline = f"Top result: {_format_row(first_row)}."

    details = [
        _execution_detail(result),
        f"Top row: {_format_row(first_row)}.",
    ]
    if result.truncated:
        details.append("Results are a limited preview; rerun with a higher limit to inspect more rows.")

    return ResultInsight(headline=headline, details=details)


def _looks_like_trend(question: str, result: QueryResult) -> bool:
    question_lower = question.lower()
    return (
        ("trend" in question_lower or "monthly" in question_lower or "month" in result.columns)
        and "month" in result.columns
        and result.row_count > 1
    )


def _explain_trend_result(result: QueryResult) -> ResultInsight:
    metric_key = next(
        (
            column
            for column in result.columns
            if column != "month" and any(isinstance(row.get(column), Number) for row in result.rows)
        ),
        None,
    )
    if metric_key is None:
        return ResultInsight(
            headline=f"Trend returned {result.row_count} periods.",
            details=[_execution_detail(result), f"First period: {_format_row(result.rows[0])}."],
        )

    metric_values = [row[metric_key] for row in result.rows if isinstance(row.get(metric_key), Number)]
    low = min(metric_values)
    high = max(metric_values)
    peak_row = max(result.rows, key=lambda row: row.get(metric_key, float("-inf")))
    first_row = result.rows[0]
    details = [
        _execution_detail(result),
        f"First period: {_format_row(first_row)}.",
        f"Peak period: {_format_row(peak_row)}.",
    ]
    if result.truncated:
        details.append("Results are a limited preview; rerun with a higher limit to inspect more rows.")

    return ResultInsight(
        headline=(
            f"Monthly {_format_label(metric_key)} ranges from {_format_value(low)} "
            f"to {_format_value(high)} across {result.row_count} periods."
        ),
        details=details,
    )


def _execution_detail(result: QueryResult) -> str:
    column_word = "column" if len(result.columns) == 1 else "columns"
    row_word = "row" if result.row_count == 1 else "rows"
    return (
        f"Returned {result.row_count} {row_word} across {len(result.columns)} "
        f"{column_word} in {result.execution_time_ms:.1f}ms."
    )


def _label_field(row: dict[str, Any]) -> tuple[str | None, Any]:
    for key, value in row.items():
        if not isinstance(value, Number) and value is not None:
            return key, value
    return None, None


def _metric_field(row: dict[str, Any], exclude: str | None = None) -> tuple[str | None, Any]:
    for key, value in row.items():
        if key != exclude and isinstance(value, Number):
            return key, value
    return None, None


def _format_row(row: dict[str, Any]) -> str:
    return ", ".join(f"{key}={_format_value(value)}" for key, value in row.items())


def _format_label(label: str) -> str:
    """Convert snake_case result aliases into reader-friendly labels."""
    return label.replace("_", " ")


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    if value is None:
        return "NULL"
    return str(value)
