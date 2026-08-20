"""Focused behavior tests for Auto EDA dataset profiling."""

from __future__ import annotations

from pathlib import Path

from auto_eda.profile import (
    profile_csv,
    render_markdown_report,
    render_missingness_chart,
)


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


def test_rendered_report_flags_constant_numeric_and_text_columns(tmp_path: Path) -> None:
    source_file = tmp_path / "constant_columns.csv"
    source_file.write_text(
        "region,unit_price,status\n"
        "north,9.99,active\n"
        "south,9.99,active\n"
        "west,9.99,active\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "## Constant columns\n\n" in report
    assert "| unit_price | numeric | 9.99 | 3 |" in report
    assert "| status | text | active | 3 |" in report
    constant_section = report.split("## Constant columns", 1)[1].split(
        "## Column profile", 1
    )[0]
    assert "| region | text |" not in constant_section


def test_rendered_report_includes_an_actionable_analyst_summary(tmp_path: Path) -> None:
    source_file = tmp_path / "sales.csv"
    source_file.write_text(
        "sales,segment\n"
        "10,north\n"
        "11,south\n"
        "12,\n"
        "13,north\n"
        "100,north\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "## Analyst summary\n\n" in report
    assert "- 5 rows across 2 columns: 1 numeric and 1 text.\n" in report
    assert "- Data quality: 1 missing value across 1 column; 0 duplicate rows.\n" in report
    assert "- Numeric range: sales spans 10.00 to 100.00.\n" in report
    assert "- Outlier watchlist: sales (1 value).\n" in report


def test_rendered_report_prioritizes_columns_with_missing_values(tmp_path: Path) -> None:
    source_file = tmp_path / "missingness.csv"
    source_file.write_text(
        "customer,spend,region\n"
        "Aster,10.5,north\n"
        "Birch,,\n"
        "Cedar,,west\n"
        "Dune,14.0,\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "## Missingness details\n\n" in report
    assert "| Column | Missing values | Missing rate |" in report
    assert "| spend | 2 | 50.0% |" in report
    assert "| region | 2 | 50.0% |" in report
    missingness_section = report.split("## Missingness details", 1)[1].split(
        "## Column profile", 1
    )[0]
    assert "| customer |" not in missingness_section


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


def test_rendered_report_includes_numeric_quartiles(tmp_path: Path) -> None:
    source_file = tmp_path / "quarterly_sales.csv"
    source_file.write_text(
        "sales\n"
        "10\n"
        "20\n"
        "30\n"
        "40\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "| sales | 17.50 | 25.00 | 32.50 |" in report


def test_rendered_report_flags_values_outside_iqr_outlier_fences(tmp_path: Path) -> None:
    source_file = tmp_path / "outlier_sales.csv"
    source_file.write_text(
        "sales\n"
        "10\n"
        "11\n"
        "12\n"
        "13\n"
        "100\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "| sales | 1 | 100.00 |" in report


def test_rendered_report_includes_pairwise_numeric_correlations(tmp_path: Path) -> None:
    source_file = tmp_path / "monthly_sales.csv"
    source_file.write_text(
        "month,sales,refunds\n"
        "January,10,6\n"
        "February,20,4\n"
        "March,30,2\n"
        "April,,0\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "## Numeric correlations" in report
    assert "| sales | refunds | 3 | -1.00 |" in report


def test_missingness_svg_escapes_a_column_name_for_safe_rendering(tmp_path: Path) -> None:
    source_file = tmp_path / "unsafe_header.csv"
    source_file.write_text("<cost & margin>\nvalue\n", encoding="utf-8")

    chart = render_missingness_chart(profile_csv(source_file))

    assert "&lt;cost &amp; margin&gt;" in chart
    assert "<cost & margin>" not in chart


def test_profile_accepts_a_header_without_data_rows(tmp_path: Path) -> None:
    source_file = tmp_path / "header_only.csv"
    source_file.write_text("customer,spend\n", encoding="utf-8")

    dataset = profile_csv(source_file)

    assert dataset.row_count == 0
    assert [(column.name, column.inferred_type) for column in dataset.columns] == [
        ("customer", "text"),
        ("spend", "text"),
    ]
