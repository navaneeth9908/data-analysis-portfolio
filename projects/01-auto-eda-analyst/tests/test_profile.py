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


def test_rendered_report_warns_about_an_empty_header_name(tmp_path: Path) -> None:
    source_file = tmp_path / "empty_header.csv"
    source_file.write_text(
        ",spend\n"
        "Aster,10.5\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "Schema warnings:\n- Empty header name at column 1.\n" in report


def test_rendered_report_warns_about_inconsistent_row_widths(tmp_path: Path) -> None:
    source_file = tmp_path / "inconsistent_rows.csv"
    source_file.write_text(
        "customer,spend\n"
        "Aster,10.5\n"
        "Birch\n"
        "Cedar,19.5,extra\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "- Row 3 has 1 value; expected 2.\n" in report
    assert "- Row 4 has 3 values; expected 2.\n" in report
