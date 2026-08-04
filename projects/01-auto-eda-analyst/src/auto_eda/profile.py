"""Deterministic CSV profiling used by the Auto EDA Analyst demo."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
import csv


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
    unique_count: int | None = None
    top_value: str | None = None
    top_value_count: int | None = None


@dataclass(frozen=True)
class DatasetProfile:
    """A deterministic profile for a delimited input dataset."""

    source_name: str
    row_count: int
    duplicate_row_count: int
    columns: tuple[ColumnProfile, ...]


def profile_csv(path: str | Path) -> DatasetProfile:
    """Profile missingness and numeric ranges for a headered CSV file."""
    source_path = Path(path)
    with source_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise ValueError("CSV input must include a header row")
        rows = list(reader)
    duplicate_row_count = sum(
        count - 1
        for count in Counter(
            tuple(str(row.get(name) or "").strip() for name in fieldnames)
            for row in rows
        ).values()
    )

    columns: list[ColumnProfile] = []
    for name in fieldnames:
        values = [str(row.get(name) or "").strip() for row in rows]
        non_null_values = [value for value in values if value]
        numeric_values = _as_numeric_values(non_null_values)
        is_numeric = bool(non_null_values) and numeric_values is not None
        value_counts = Counter(non_null_values) if not is_numeric else Counter()
        top_value = (
            min(value_counts, key=lambda value: (-value_counts[value], value))
            if value_counts
            else None
        )
        columns.append(
            ColumnProfile(
                name=name,
                inferred_type="numeric" if is_numeric else "text",
                missing_count=len(values) - len(non_null_values),
                non_null_count=len(non_null_values),
                mean=mean(numeric_values) if numeric_values is not None else None,
                minimum=min(numeric_values) if numeric_values is not None else None,
                maximum=max(numeric_values) if numeric_values is not None else None,
                unique_count=len(value_counts) if not is_numeric else None,
                top_value=top_value,
                top_value_count=value_counts[top_value] if top_value is not None else None,
            )
        )

    return DatasetProfile(
        source_name=source_path.name,
        row_count=len(rows),
        duplicate_row_count=duplicate_row_count,
        columns=tuple(columns),
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


def render_markdown_report(dataset: DatasetProfile) -> str:
    """Render a stable Markdown profile suitable for review and version control."""
    lines = [
        "# Automated EDA Report",
        "",
        f"Source: {dataset.source_name}",
        "",
        f"Rows: {dataset.row_count}",
        "",
        "## Data quality",
        "",
        f"Duplicate rows: {dataset.duplicate_row_count}",
        "",
        "## Column profile",
        "",
        "| Column | Inferred type | Missing | Non-null | Mean | Minimum | Maximum |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
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
    return "\n".join(lines) + "\n"
