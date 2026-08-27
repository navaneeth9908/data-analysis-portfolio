"""Focused behavior tests for Auto EDA dataset profiling."""

from __future__ import annotations

from pathlib import Path

from auto_eda.profile import (
    profile_csv,
    render_markdown_report,
    render_missingness_chart,
)


def test_profile_csv_accepts_a_semicolon_delimiter(tmp_path: Path) -> None:
    source_file = tmp_path / "semicolon_customers.csv"
    source_file.write_text(
        "customer;spend;segment\n"
        "Aster;10.5;enterprise\n"
        "Birch;19.5;midmarket\n",
        encoding="utf-8",
    )

    dataset = profile_csv(source_file, delimiter=";")
    report = render_markdown_report(dataset)

    assert [column.name for column in dataset.columns] == ["customer", "spend", "segment"]
    assert "| spend | numeric | 0 | 2 | 15.00 | 10.50 | 19.50 |" in report
    assert "| segment | 2 | enterprise | 1 |" in report


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


def test_rendered_report_includes_complete_row_coverage(tmp_path: Path) -> None:
    source_file = tmp_path / "row_coverage.csv"
    source_file.write_text(
        "customer,spend,segment\n"
        "Aster,10.5,enterprise\n"
        "Birch,,midmarket\n"
        "Cedar,19.5,\n"
        "Dune,20.0,enterprise\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "Complete rows: 2 (50.0%)\n" in report


def test_data_quality_section_summarizes_missing_value_totals(tmp_path: Path) -> None:
    source_file = tmp_path / "missing_totals.csv"
    source_file.write_text(
        "customer,spend,region\n"
        "Aster,10.5,north\n"
        "Birch,,\n"
        "Cedar,,west\n"
        "Dune,14.0,\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "## Data quality\n\n" in report
    assert "Missing values: 4 across 2 columns\n" in report
    data_quality_section = report.split("## Data quality", 1)[1].split(
        "## Missingness details", 1
    )[0]
    assert "Complete rows: 1 (25.0%)\n" in data_quality_section


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
    assert (
        "- Data quality: 1 missing value across 1 column; 0 duplicate rows; "
        "4 complete rows (80.0%).\n"
        in report
    )
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


def test_rendered_report_flags_columns_with_no_populated_values(tmp_path: Path) -> None:
    source_file = tmp_path / "empty_columns.csv"
    source_file.write_text(
        "customer,legacy_id,notes\n"
        "Aster,,\n"
        "Birch,,\n"
        "Cedar,,Needs outreach\n"
        "Dune,,Done\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "## Empty columns\n\n" in report
    assert "| Column | Missing values | Missing rate |" in report
    assert "| legacy_id | 4 | 100.0% |" in report
    empty_columns_section = report.split("## Empty columns", 1)[1].split(
        "## Column profile", 1
    )[0]
    assert "| notes |" not in empty_columns_section


def test_rendered_report_flags_high_cardinality_text_columns(tmp_path: Path) -> None:
    source_file = tmp_path / "high_cardinality_customers.csv"
    source_file.write_text(
        "customer_id,segment\n"
        "C-001,enterprise\n"
        "C-002,enterprise\n"
        "C-003,midmarket\n"
        "C-004,midmarket\n"
        "C-005,startup\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "## High-cardinality text columns\n\n" in report
    assert "| Column | Unique values | Non-null rows | Unique rate |" in report
    assert "| customer_id | 5 | 5 | 100.0% |" in report
    high_cardinality_section = report.split(
        "## High-cardinality text columns", 1
    )[1].split("## Categorical summary", 1)[0]
    assert "| segment |" not in high_cardinality_section


def test_rendered_report_summarizes_boolean_flag_text_columns(tmp_path: Path) -> None:
    source_file = tmp_path / "boolean_flags.csv"
    source_file.write_text(
        "customer,active,renewal_ready\n"
        "Aster,yes,true\n"
        "Birch,no,false\n"
        "Cedar,yes,false\n"
        "Dune,,true\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "## Boolean flag summary\n\n" in report
    assert "| Column | True-like values | False-like values | Non-null rows |" in report
    assert "| active | 2 | 1 | 3 |" in report
    assert "| renewal_ready | 2 | 2 | 4 |" in report
    boolean_section = report.split("## Boolean flag summary", 1)[1].split(
        "## Categorical summary", 1
    )[0]
    assert "| customer |" not in boolean_section


def test_rendered_report_flags_dominant_categorical_values(tmp_path: Path) -> None:
    source_file = tmp_path / "dominant_status.csv"
    source_file.write_text(
        "customer,status,region\n"
        "Aster,active,north\n"
        "Birch,active,south\n"
        "Cedar,active,east\n"
        "Dune,active,west\n"
        "Elm,paused,north\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "## Dominant categorical values\n\n" in report
    assert "| Column | Dominant value | Count | Share | Other values |" in report
    assert "| status | active | 4 | 80.0% | 1 |" in report
    dominant_section = report.split("## Dominant categorical values", 1)[1].split(
        "## Categorical summary", 1
    )[0]
    assert "| region |" not in dominant_section
    assert "| customer |" not in dominant_section


def test_rendered_report_warns_about_an_empty_header_name(tmp_path: Path) -> None:
    source_file = tmp_path / "empty_header.csv"
    source_file.write_text(
        ",spend\n"
        "Aster,10.5\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert (
        "Schema warnings:\n- Empty header name at column 1; renamed to 'column_1'.\n"
        in report
    )


def test_profile_trims_header_names_before_rendering(tmp_path: Path) -> None:
    source_file = tmp_path / "trimmed_headers.csv"
    source_file.write_text(
        " customer , spend ,segment\n"
        "Aster,10.5,enterprise\n"
        "Birch,19.5,midmarket\n",
        encoding="utf-8",
    )

    dataset = profile_csv(source_file)
    report = render_markdown_report(dataset)

    assert [column.name for column in dataset.columns] == ["customer", "spend", "segment"]
    assert (
        "- Header name ' customer ' at column 1 was trimmed to 'customer'.\n"
        in report
    )
    assert (
        "- Header name ' spend ' at column 2 was trimmed to 'spend'.\n"
        in report
    )
    assert "| spend | numeric | 0 | 2 | 15.00 | 10.50 | 19.50 |" in report


def test_profile_renames_empty_header_names_for_report_tables(tmp_path: Path) -> None:
    source_file = tmp_path / "blank_header.csv"
    source_file.write_text(
        ",spend\n"
        "Aster,10.5\n",
        encoding="utf-8",
    )

    dataset = profile_csv(source_file)
    report = render_markdown_report(dataset)

    assert [column.name for column in dataset.columns] == ["column_1", "spend"]
    assert (
        "- Empty header name at column 1; renamed to 'column_1'.\n"
        in report
    )
    assert "| column_1 | text | 0 | 1 | — | — | — |" in report


def test_profile_renames_duplicate_header_names_and_warns(tmp_path: Path) -> None:
    source_file = tmp_path / "duplicate_headers.csv"
    source_file.write_text(
        "customer,spend,spend\n"
        "Aster,10.5,11.0\n"
        "Birch,19.5,21.0\n",
        encoding="utf-8",
    )

    dataset = profile_csv(source_file)
    report = render_markdown_report(dataset)

    assert [column.name for column in dataset.columns] == [
        "customer",
        "spend",
        "spend_2",
    ]
    assert (
        "- Duplicate header name 'spend' at column 3; renamed to 'spend_2'.\n"
        in report
    )
    assert "| spend | numeric | 0 | 2 | 15.00 | 10.50 | 19.50 |" in report
    assert "| spend_2 | numeric | 0 | 2 | 16.00 | 11.00 | 21.00 |" in report


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


def test_rendered_report_includes_iso_date_ranges(tmp_path: Path) -> None:
    source_file = tmp_path / "renewals.csv"
    source_file.write_text(
        "customer,renewal_date,spend\n"
        "Aster,2026-01-15,10\n"
        "Birch,,20\n"
        "Cedar,2026-03-30,30\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "| renewal_date | date | 1 | 2 | — | — | — |" in report
    assert "## Date ranges\n\n" in report
    assert "| renewal_date | 2026-01-15 | 2026-03-30 | 2 |" in report
    date_section = report.split("## Date ranges", 1)[1].split(
        "## Numeric distribution", 1
    )[0]
    assert "| customer |" not in date_section
    assert "| spend |" not in date_section


def test_analyst_summary_counts_date_columns_and_timeline_coverage(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "renewal_pipeline.csv"
    source_file.write_text(
        "customer,renewal_date,spend\n"
        "Aster,2026-01-15,10\n"
        "Birch,,20\n"
        "Cedar,2026-03-30,30\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "- 3 rows across 3 columns: 1 numeric, 1 date, and 1 text.\n" in report
    assert (
        "- Date coverage: renewal_date runs from 2026-01-15 to 2026-03-30 "
        "across 2 populated rows.\n"
        in report
    )

def test_iso_week_date_strings_stay_categorical_text(tmp_path: Path) -> None:
    source_file = tmp_path / "week_dates.csv"
    source_file.write_text(
        "period\n"
        "2026-W03-4\n"
        "2026-W04-5\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "| period | text | 0 | 2 | — | — | — |" in report
    assert "## Date ranges" not in report
    assert "| period | 1 | 2026-W03-4 | 1 |" in report


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


def test_analyst_summary_highlights_the_strongest_numeric_correlation(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "growth_drivers.csv"
    source_file.write_text(
        "visitors,discount_rate,revenue\n"
        "1,1,10\n"
        "2,4,20\n"
        "3,2,30\n"
        "4,3,40\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert (
        "- Strongest numeric relationship: visitors and revenue have Pearson r "
        "1.00 over 4 paired rows.\n"
        in report
    )


def test_missingness_svg_escapes_a_column_name_for_safe_rendering(tmp_path: Path) -> None:
    source_file = tmp_path / "unsafe_header.csv"
    source_file.write_text("<cost & margin>\nvalue\n", encoding="utf-8")

    chart = render_missingness_chart(profile_csv(source_file))

    assert "&lt;cost &amp; margin&gt;" in chart
    assert "<cost & margin>" not in chart


def test_profile_treats_business_formatted_numbers_as_numeric(tmp_path: Path) -> None:
    source_file = tmp_path / "currency_sales.csv"
    source_file.write_text(
        "customer,revenue\n"
        "Aster,\"$1,200.50\"\n"
        "Birch,$900.25\n"
        "Cedar,($100.75)\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "| revenue | numeric | 0 | 3 | 666.67 | -100.75 | 1200.50 |" in report


def test_rendered_report_flags_mixed_numeric_text_columns(tmp_path: Path) -> None:
    source_file = tmp_path / "mixed_amounts.csv"
    source_file.write_text(
        "customer,booked_amount\n"
        "Aster,\"$1,200.00\"\n"
        "Birch,pending\n"
        "Cedar,950\n"
        "Dune,not available\n"
        "Elm,($25.00)\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "## Mixed-type warnings\n\n" in report
    assert "| Column | Numeric-like values | Non-numeric examples |" in report
    assert "| booked_amount | 3 of 5 | not available, pending |" in report
    mixed_type_section = report.split("## Mixed-type warnings", 1)[1].split(
        "## Categorical summary", 1
    )[0]
    assert "| customer |" not in mixed_type_section


def test_profile_correlates_business_formatted_numeric_columns(tmp_path: Path) -> None:
    source_file = tmp_path / "currency_drivers.csv"
    source_file.write_text(
        "month,revenue,refunds\n"
        "January,\"$1,000.00\",($50.00)\n"
        "February,\"$2,000.00\",($100.00)\n"
        "March,\"$3,000.00\",($150.00)\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "## Numeric correlations" in report
    assert "| revenue | refunds | 3 | -1.00 |" in report


def test_profile_accepts_a_header_without_data_rows(tmp_path: Path) -> None:
    source_file = tmp_path / "header_only.csv"
    source_file.write_text("customer,spend\n", encoding="utf-8")

    dataset = profile_csv(source_file)

    assert dataset.row_count == 0
    assert [(column.name, column.inferred_type) for column in dataset.columns] == [
        ("customer", "text"),
        ("spend", "text"),
    ]


def test_rendered_report_escapes_markdown_table_cells(tmp_path: Path) -> None:
    source_file = tmp_path / "markdown_sensitive_values.csv"
    source_file.write_text(
        "customer|tier,segment\n"
        '"Aster|Enterprise\nNorth",core\n'
        "Birch,expansion\n",
        encoding="utf-8",
    )

    report = render_markdown_report(profile_csv(source_file))

    assert "| customer\\|tier | text | 0 | 2 | — | — | — |" in report
    assert "| customer\\|tier | 1 | Aster\\|Enterprise North | 1 |" in report
    assert "| customer|tier | text |" not in report
    assert "Aster|Enterprise\nNorth" not in report
