"""Focused behavior tests for Auto EDA dataset profiling."""

from __future__ import annotations

from pathlib import Path

from auto_eda.profile import profile_csv, render_markdown_report


def test_rendered_report_counts_exact_duplicate_data_rows(tmp_path: Path) -> None:
    source_file = tmp_path / "duplicate_customers.csv"
    source_file.write_text(
        "customer,spend,segment\n"
        "Aster,10.5,enterprise\n"
        "Aster,10.5,enterprise\n"
        "Birch,19.5,midmarket\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "## Data quality\n\nDuplicate rows: 1\n" in report
