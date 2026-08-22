"""Deterministic CSV profiling used by the Auto EDA Analyst demo."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import date
from html import escape
from math import sqrt
from pathlib import Path
from statistics import mean, median


@dataclass(frozen=True)
class ColumnProfile:
    """A compact profile for one CSV column."""

    name: str
    inferred_type: str
    missing_count: int
    non_null_count: int
    mean: float | None
    minimum: float | None
    maximum: float | None
    first_quartile: float | None = None
    median: float | None = None
    third_quartile: float | None = None
    outlier_values: tuple[float, ...] = ()
    earliest_date: date | None = None
    latest_date: date | None = None
    unique_count: int | None = None
    top_value: str | None = None
    top_value_count: int | None = None
    categorical_values: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class NumericCorrelation:
    """A Pearson correlation calculated from pairwise populated numeric rows."""

    first_column: str
    second_column: str
    paired_row_count: int
    pearson_r: float


@dataclass(frozen=True)
class DatasetProfile:
    """A deterministic profile for a delimited input dataset."""

    source_name: str
    row_count: int
    duplicate_row_count: int
    complete_row_count: int
    schema_warnings: tuple[str, ...]
    columns: tuple[ColumnProfile, ...]
    numeric_correlations: tuple[NumericCorrelation, ...] = ()


def profile_csv(path: str | Path, delimiter: str = ",") -> DatasetProfile:
    """Profile missingness and numeric ranges for a headered CSV file."""
    source_path = Path(path)
    with source_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        fieldnames = next(reader, None)
        if not fieldnames:
            raise ValueError("CSV input must include a header row")
        schema_warnings = [
            f"Empty header name at column {index}."
            for index, name in enumerate(fieldnames, start=1)
            if not name.strip()
        ]
        rows = []
        for row_number, values in enumerate(reader, start=2):
            if len(values) != len(fieldnames):
                noun = "value" if len(values) == 1 else "values"
                schema_warnings.append(
                    f"Row {row_number} has {len(values)} {noun}; expected {len(fieldnames)}."
                )
            rows.append(
                {
                    name: values[index] if index < len(values) else None
                    for index, name in enumerate(fieldnames)
                }
            )
    schema_warnings = tuple(schema_warnings)
    duplicate_row_count = sum(
        count - 1
        for count in Counter(
            tuple(str(row.get(name) or "").strip() for name in fieldnames)
            for row in rows
        ).values()
    )
    complete_row_count = sum(
        all(str(row.get(name) or "").strip() for name in fieldnames)
        for row in rows
    )

    columns: list[ColumnProfile] = []
    for name in fieldnames:
        values = [str(row.get(name) or "").strip() for row in rows]
        non_null_values = [value for value in values if value]
        numeric_values = _as_numeric_values(non_null_values)
        sorted_numeric_values = sorted(numeric_values) if numeric_values is not None else None
        is_numeric = bool(non_null_values) and numeric_values is not None
        date_values = _as_iso_dates(non_null_values) if not is_numeric else None
        is_date = bool(non_null_values) and date_values is not None
        first_quartile = (
            _linear_percentile(sorted_numeric_values, 0.25)
            if sorted_numeric_values
            else None
        )
        third_quartile = (
            _linear_percentile(sorted_numeric_values, 0.75)
            if sorted_numeric_values
            else None
        )
        outlier_values = (
            _iqr_outliers(sorted_numeric_values, first_quartile, third_quartile)
            if sorted_numeric_values
            and first_quartile is not None
            and third_quartile is not None
            else ()
        )
        value_counts = Counter(non_null_values) if not is_numeric and not is_date else Counter()
        top_value = (
            min(value_counts, key=lambda value: (-value_counts[value], value))
            if value_counts
            else None
        )
        columns.append(
            ColumnProfile(
                name=name,
                inferred_type=(
                    "numeric" if is_numeric else "date" if is_date else "text"
                ),
                missing_count=len(values) - len(non_null_values),
                non_null_count=len(non_null_values),
                mean=mean(numeric_values) if numeric_values else None,
                minimum=min(numeric_values) if numeric_values else None,
                maximum=max(numeric_values) if numeric_values else None,
                first_quartile=first_quartile,
                median=median(sorted_numeric_values) if sorted_numeric_values else None,
                third_quartile=third_quartile,
                outlier_values=outlier_values,
                earliest_date=min(date_values) if date_values else None,
                latest_date=max(date_values) if date_values else None,
                unique_count=len(value_counts) if not is_numeric and not is_date else None,
                top_value=top_value,
                top_value_count=value_counts[top_value] if top_value is not None else None,
                categorical_values=tuple(
                    sorted(value_counts.items(), key=lambda item: (-item[1], item[0]))
                ),
            )
        )

    numeric_column_names = [
        column.name for column in columns if column.inferred_type == "numeric"
    ]
    return DatasetProfile(
        source_name=source_path.name,
        row_count=len(rows),
        duplicate_row_count=duplicate_row_count,
        complete_row_count=complete_row_count,
        schema_warnings=schema_warnings,
        columns=tuple(columns),
        numeric_correlations=_numeric_correlations(rows, numeric_column_names),
    )


def _as_numeric_values(values: list[str]) -> list[float] | None:
    """Return parsed values only when every non-missing value is numeric."""
    parsed: list[float] = []
    try:
        for value in values:
            parsed.append(float(value))
    except ValueError:
        return None
    return parsed


def _as_iso_dates(values: list[str]) -> list[date] | None:
    """Return parsed dates only when every value uses extended YYYY-MM-DD form."""
    parsed: list[date] = []
    try:
        for value in values:
            if (
                len(value) != 10
                or value[4] != "-"
                or value[7] != "-"
                or not value[:4].isdigit()
                or not value[5:7].isdigit()
                or not value[8:].isdigit()
            ):
                return None
            parsed.append(date.fromisoformat(value))
    except ValueError:
        return None
    return parsed


def _linear_percentile(sorted_values: list[float], percentile: float) -> float:
    """Calculate a percentile with deterministic linear interpolation."""
    position = (len(sorted_values) - 1) * percentile
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    fraction = position - lower_index
    return sorted_values[lower_index] + fraction * (
        sorted_values[upper_index] - sorted_values[lower_index]
    )


def _iqr_outliers(
    sorted_values: list[float], first_quartile: float, third_quartile: float
) -> tuple[float, ...]:
    """Return values outside Tukey's 1.5-IQR fences in sorted order."""
    interquartile_range = third_quartile - first_quartile
    lower_fence = first_quartile - 1.5 * interquartile_range
    upper_fence = third_quartile + 1.5 * interquartile_range
    return tuple(
        value for value in sorted_values if value < lower_fence or value > upper_fence
    )


def _numeric_correlations(
    rows: list[dict[str, str | None]], numeric_column_names: list[str]
) -> tuple[NumericCorrelation, ...]:
    """Calculate Pearson r for variable numeric-column pairs with usable data."""
    correlations: list[NumericCorrelation] = []
    for first_index, first_column in enumerate(numeric_column_names):
        for second_column in numeric_column_names[first_index + 1 :]:
            paired_values = [
                (float(first_value), float(second_value))
                for row in rows
                if (first_value := str(row.get(first_column) or "").strip())
                and (second_value := str(row.get(second_column) or "").strip())
            ]
            if len(paired_values) < 2:
                continue
            first_values, second_values = zip(*paired_values)
            first_mean = mean(first_values)
            second_mean = mean(second_values)
            first_sum_squares = sum(
                (value - first_mean) ** 2 for value in first_values
            )
            second_sum_squares = sum(
                (value - second_mean) ** 2 for value in second_values
            )
            if first_sum_squares == 0 or second_sum_squares == 0:
                continue
            covariance = sum(
                (first_value - first_mean) * (second_value - second_mean)
                for first_value, second_value in paired_values
            )
            correlations.append(
                NumericCorrelation(
                    first_column=first_column,
                    second_column=second_column,
                    paired_row_count=len(paired_values),
                    pearson_r=covariance / sqrt(first_sum_squares * second_sum_squares),
                )
            )
    return tuple(correlations)


def render_missingness_chart(dataset: DatasetProfile) -> str:
    """Render a deterministic, standalone SVG chart of missing values by column."""
    width = 720
    left_margin = 190
    bar_width = 340
    row_height = 44
    height = max(140, 88 + row_height * len(dataset.columns))
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" role="img">'
        ),
        "<title>Missing values by column</title>",
        "<desc>Each bar shows the percentage of missing values in a CSV column.</desc>",
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        (
            '<text x="24" y="34" fill="#111827" font-family="Arial, sans-serif" '
            'font-size="20" font-weight="700">Missing values by column</text>'
        ),
        (
            '<text x="24" y="58" fill="#4b5563" font-family="Arial, sans-serif" '
            'font-size="12">Percent of dataset rows with blank values</text>'
        ),
    ]
    for index, column in enumerate(dataset.columns):
        y_position = 94 + index * row_height
        percentage = column.missing_count / dataset.row_count if dataset.row_count else 0.0
        label = escape(column.name)
        summary = f"{column.missing_count} missing ({percentage:.1%})"
        lines.extend(
            [
                (
                    f'<text x="24" y="{y_position}" fill="#111827" '
                    'font-family="Arial, sans-serif" font-size="14">'
                    f"{label}</text>"
                ),
                (
                    f'<rect x="{left_margin}" y="{y_position - 15}" '
                    f'width="{bar_width}" height="20" rx="3" fill="#e5e7eb"/>'
                ),
                (
                    f'<rect x="{left_margin}" y="{y_position - 15}" '
                    f'width="{bar_width * percentage:.2f}" height="20" rx="3" '
                    f'fill="{"#dc2626" if column.missing_count else "#16a34a"}"/>'
                ),
                (
                    f'<text x="{left_margin + bar_width + 16}" y="{y_position}" '
                    'fill="#374151" font-family="Arial, sans-serif" font-size="13">'
                    f"{summary}</text>"
                ),
            ]
        )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def _constant_column_value(column: ColumnProfile) -> str | None:
    """Return a display value when a populated column has one distinct value."""
    if column.inferred_type == "numeric":
        if column.minimum is not None and column.minimum == column.maximum:
            return f"{column.minimum:.2f}"
        return None
    if len(column.categorical_values) == 1:
        return column.categorical_values[0][0]
    return None


def _strongest_numeric_correlation(
    correlations: tuple[NumericCorrelation, ...],
) -> NumericCorrelation | None:
    """Return the strongest absolute numeric relationship with stable tie-breaks."""
    if not correlations:
        return None
    return sorted(
        correlations,
        key=lambda correlation: (
            -abs(correlation.pearson_r),
            correlation.first_column,
            correlation.second_column,
        ),
    )[0]


def render_markdown_report(dataset: DatasetProfile, categorical_limit: int = 5) -> str:
    """Render a stable Markdown profile suitable for review and version control."""
    numeric_columns = [
        column for column in dataset.columns if column.first_quartile is not None
    ]
    text_column_count = len(dataset.columns) - len(numeric_columns)
    missing_value_count = sum(column.missing_count for column in dataset.columns)
    missing_column_count = sum(
        column.missing_count > 0 for column in dataset.columns
    )
    missing_columns = sorted(
        (column for column in dataset.columns if column.missing_count > 0),
        key=lambda column: (-column.missing_count, column.name),
    )
    empty_columns = sorted(
        (
            column
            for column in dataset.columns
            if dataset.row_count and column.non_null_count == 0
        ),
        key=lambda column: column.name,
    )
    complete_row_rate = (
        dataset.complete_row_count / dataset.row_count if dataset.row_count else 0.0
    )
    outlier_columns = [column for column in numeric_columns if column.outlier_values]
    constant_columns = [
        (column, value)
        for column in dataset.columns
        if (value := _constant_column_value(column)) is not None
    ]
    high_cardinality_columns = [
        column
        for column in dataset.columns
        if column.unique_count is not None
        and column.non_null_count >= 4
        and column.unique_count / column.non_null_count >= 0.8
    ]
    strongest_correlation = _strongest_numeric_correlation(dataset.numeric_correlations)
    analyst_summary = [
        "## Analyst summary",
        "",
        (
            f"- {dataset.row_count} {'row' if dataset.row_count == 1 else 'rows'} "
            f"across {len(dataset.columns)} "
            f"{'column' if len(dataset.columns) == 1 else 'columns'}: "
            f"{len(numeric_columns)} numeric and {text_column_count} text."
        ),
        (
            f"- Data quality: {missing_value_count} "
            f"{'missing value' if missing_value_count == 1 else 'missing values'} "
            f"across {missing_column_count} "
            f"{'column' if missing_column_count == 1 else 'columns'}; "
            f"{dataset.duplicate_row_count} "
            f"{'duplicate row' if dataset.duplicate_row_count == 1 else 'duplicate rows'}; "
            f"{dataset.complete_row_count} complete "
            f"{'row' if dataset.complete_row_count == 1 else 'rows'} "
            f"({complete_row_rate:.1%})."
        ),
    ]
    if numeric_columns:
        numeric_ranges = "; ".join(
            f"{column.name} spans {column.minimum:.2f} to {column.maximum:.2f}"
            for column in numeric_columns
        )
        analyst_summary.append(
            f"- Numeric {'range' if len(numeric_columns) == 1 else 'ranges'}: "
            f"{numeric_ranges}."
        )
    if outlier_columns:
        outlier_watchlist = "; ".join(
            f"{column.name} ({len(column.outlier_values)} "
            f"{'value' if len(column.outlier_values) == 1 else 'values'})"
            for column in outlier_columns
        )
        analyst_summary.append(f"- Outlier watchlist: {outlier_watchlist}.")
    if strongest_correlation:
        row_label = "row" if strongest_correlation.paired_row_count == 1 else "rows"
        analyst_summary.append(
            "- Strongest numeric relationship: "
            f"{strongest_correlation.first_column} and "
            f"{strongest_correlation.second_column} have Pearson r "
            f"{strongest_correlation.pearson_r:.2f} over "
            f"{strongest_correlation.paired_row_count} paired {row_label}."
        )
    lines = [
        "# Automated EDA Report",
        "",
        f"Source: {dataset.source_name}",
        "",
        f"Rows: {dataset.row_count}",
        "",
        *analyst_summary,
        "",
        "## Data quality",
        "",
        f"Duplicate rows: {dataset.duplicate_row_count}",
        f"Complete rows: {dataset.complete_row_count} ({complete_row_rate:.1%})",
        "",
    ]
    if missing_columns:
        lines.extend(
            [
                "## Missingness details",
                "",
                "| Column | Missing values | Missing rate |",
                "| --- | ---: | ---: |",
                *[
                    f"| {column.name} | {column.missing_count} | "
                    f"{(column.missing_count / dataset.row_count):.1%} |"
                    for column in missing_columns
                ],
                "",
            ]
        )
    if empty_columns:
        lines.extend(
            [
                "## Empty columns",
                "",
                "| Column | Missing values | Missing rate |",
                "| --- | ---: | ---: |",
                *[
                    f"| {column.name} | {column.missing_count} | "
                    f"{(column.missing_count / dataset.row_count):.1%} |"
                    for column in empty_columns
                ],
                "",
            ]
        )
    if constant_columns:
        lines.extend(
            [
                "## Constant columns",
                "",
                "| Column | Inferred type | Constant value | Non-null rows |",
                "| --- | --- | --- | ---: |",
                *[
                    f"| {column.name} | {column.inferred_type} | {value} | "
                    f"{column.non_null_count} |"
                    for column, value in constant_columns
                ],
                "",
            ]
        )
    if dataset.schema_warnings:
        lines.extend(
            [
                "Schema warnings:",
                *[f"- {warning}" for warning in dataset.schema_warnings],
                "",
            ]
        )
    lines.extend(
        [
            "## Column profile",
            "",
            "| Column | Inferred type | Missing | Non-null | Mean | Minimum | Maximum |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for column in dataset.columns:
        numeric_values = (
            f"{column.mean:.2f} | {column.minimum:.2f} | {column.maximum:.2f}"
            if column.mean is not None
            else "— | — | —"
        )
        lines.append(
            f"| {column.name} | {column.inferred_type} | {column.missing_count} | "
            f"{column.non_null_count} | {numeric_values} |"
        )
    date_columns = [
        column for column in dataset.columns if column.earliest_date is not None
    ]
    if date_columns:
        lines.extend(
            [
                "",
                "## Date ranges",
                "",
                "| Column | Earliest date | Latest date | Non-null rows |",
                "| --- | --- | --- | ---: |",
            ]
        )
        for column in date_columns:
            lines.append(
                f"| {column.name} | {column.earliest_date} | "
                f"{column.latest_date} | {column.non_null_count} |"
            )
    if numeric_columns:
        lines.extend(
            [
                "",
                "## Numeric distribution",
                "",
                "| Column | 25th percentile | Median | 75th percentile |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for column in numeric_columns:
            lines.append(
                f"| {column.name} | {column.first_quartile:.2f} | "
                f"{column.median:.2f} | {column.third_quartile:.2f} |"
            )
    if dataset.numeric_correlations:
        lines.extend(
            [
                "",
                "## Numeric correlations",
                "",
                "| First column | Second column | Pairwise rows | Pearson r |",
                "| --- | --- | ---: | ---: |",
            ]
        )
        for correlation in dataset.numeric_correlations:
            lines.append(
                f"| {correlation.first_column} | {correlation.second_column} | "
                f"{correlation.paired_row_count} | {correlation.pearson_r:.2f} |"
            )
    if outlier_columns:
        lines.extend(
            [
                "",
                "## IQR outliers",
                "",
                "| Column | Outlier count | Values outside 1.5-IQR fences |",
                "| --- | ---: | --- |",
            ]
        )
        for column in outlier_columns:
            values = ", ".join(f"{value:.2f}" for value in column.outlier_values)
            lines.append(f"| {column.name} | {len(column.outlier_values)} | {values} |")
    if high_cardinality_columns:
        lines.extend(
            [
                "",
                "## High-cardinality text columns",
                "",
                "| Column | Unique values | Non-null rows | Unique rate |",
                "| --- | ---: | ---: | ---: |",
                *[
                    f"| {column.name} | {column.unique_count} | "
                    f"{column.non_null_count} | "
                    f"{(column.unique_count / column.non_null_count):.1%} |"
                    for column in high_cardinality_columns
                ],
            ]
        )
    categorical_columns = [
        column for column in dataset.columns if column.unique_count is not None
    ]
    if categorical_columns:
        lines.extend(
            [
                "",
                "## Categorical summary",
                "",
                "| Column | Unique values | Top value | Top value count |",
                "| --- | ---: | --- | ---: |",
            ]
        )
        for column in categorical_columns:
            top_value = column.top_value or "—"
            top_value_count = (
                str(column.top_value_count)
                if column.top_value_count is not None
                else "—"
            )
            lines.append(
                f"| {column.name} | {column.unique_count} | {top_value} | "
                f"{top_value_count} |"
            )
        displayed_categorical_columns = [
            column for column in categorical_columns if column.categorical_values
        ]
        if displayed_categorical_columns and categorical_limit:
            lines.extend(
                [
                    "",
                    f"## Categorical values (top {categorical_limit} per column)",
                    "",
                    "| Column | Rank | Value | Count |",
                    "| --- | ---: | --- | ---: |",
                ]
            )
            for column in displayed_categorical_columns:
                for rank, (value, count) in enumerate(
                    column.categorical_values[:categorical_limit], start=1
                ):
                    lines.append(f"| {column.name} | {rank} | {value} | {count} |")
    return "\n".join(lines) + "\n"
