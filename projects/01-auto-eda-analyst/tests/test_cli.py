"""End-to-end behavior tests for the Auto EDA Analyst CLI."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_cli_accepts_a_semicolon_delimiter(tmp_path: Path) -> None:
    source_file = tmp_path / "semicolon_customers.csv"
    source_file.write_text(
        "customer;spend;segment\n"
        "Aster;10.5;enterprise\n"
        "Birch;19.5;midmarket\n",
        encoding="utf-8",
    )
    output_file = tmp_path / "eda_report.md"
    environment = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "auto_eda.cli",
            str(source_file),
            "--output",
            str(output_file),
            "--delimiter",
            ";",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    report = output_file.read_text(encoding="utf-8")
    assert "| customer | text | 0 | 2 | — | — | — |" in report
    assert "| spend | numeric | 0 | 2 | 15.00 | 10.50 | 19.50 |" in report
    assert "| segment | 2 | enterprise | 1 |" in report


def test_cli_writes_a_deterministic_profile_for_a_csv_with_missing_values(tmp_path: Path) -> None:
    source_file = tmp_path / "customers.csv"
    source_file.write_text(
        "customer,spend,segment\n"
        "Aster,10.5,enterprise\n"
        "Birch,,midmarket\n"
        "Cedar,19.5,enterprise\n",
        encoding="utf-8",
    )
    output_file = tmp_path / "eda_report.md"
    environment = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "auto_eda.cli",
            str(source_file),
            "--output",
            str(output_file),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"EDA report written to {output_file}\n"
    assert output_file.read_text(encoding="utf-8") == (
        "# Automated EDA Report\n\n"
        "Source: customers.csv\n\n"
        "Rows: 3\n\n"
        "## Analyst summary\n\n"
        "- 3 rows across 3 columns: 1 numeric and 2 text.\n"
        "- Data quality: 1 missing value across 1 column; 0 duplicate rows; "
        "2 complete rows (66.7%).\n"
        "- Numeric range: spend spans 10.50 to 19.50.\n\n"
        "## Data quality\n\n"
        "Duplicate rows: 0\n"
        "Complete rows: 2 (66.7%)\n\n"
        "## Missingness details\n\n"
        "| Column | Missing values | Missing rate |\n"
        "| --- | ---: | ---: |\n"
        "| spend | 1 | 33.3% |\n\n"
        "## Column profile\n\n"
        "| Column | Inferred type | Missing | Non-null | Mean | Minimum | Maximum |\n"
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |\n"
        "| customer | text | 0 | 3 | — | — | — |\n"
        "| spend | numeric | 1 | 2 | 15.00 | 10.50 | 19.50 |\n"
        "| segment | text | 0 | 3 | — | — | — |\n\n"
        "## Numeric distribution\n\n"
        "| Column | 25th percentile | Median | 75th percentile |\n"
        "| --- | ---: | ---: | ---: |\n"
        "| spend | 12.75 | 15.00 | 17.25 |\n\n"
        "## Categorical summary\n\n"
        "| Column | Unique values | Top value | Top value count |\n"
        "| --- | ---: | --- | ---: |\n"
        "| customer | 3 | Aster | 1 |\n"
        "| segment | 2 | enterprise | 2 |\n\n"
        "## Categorical values (top 5 per column)\n\n"
        "| Column | Rank | Value | Count |\n"
        "| --- | ---: | --- | ---: |\n"
        "| customer | 1 | Aster | 1 |\n"
        "| customer | 2 | Birch | 1 |\n"
        "| customer | 3 | Cedar | 1 |\n"
        "| segment | 1 | enterprise | 2 |\n"
        "| segment | 2 | midmarket | 1 |\n"
    )


def test_cli_renders_iso_date_ranges(tmp_path: Path) -> None:
    source_file = tmp_path / "renewals.csv"
    source_file.write_text(
        "customer,renewal_date\n"
        "Aster,2026-01-15\n"
        "Birch,\n"
        "Cedar,2026-03-30\n",
        encoding="utf-8",
    )
    output_file = tmp_path / "eda_report.md"
    environment = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "auto_eda.cli",
            str(source_file),
            "--output",
            str(output_file),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    report = output_file.read_text(encoding="utf-8")
    assert "| renewal_date | date | 1 | 2 | — | — | — |" in report
    assert "| renewal_date | 2026-01-15 | 2026-03-30 | 2 |" in report


def test_cli_writes_an_svg_missingness_chart_when_requested(tmp_path: Path) -> None:
    source_file = tmp_path / "customers.csv"
    source_file.write_text(
        "customer,spend\n"
        "Aster,10.5\n"
        "Birch,\n"
        "Cedar,19.5\n",
        encoding="utf-8",
    )
    output_file = tmp_path / "eda_report.md"
    chart_directory = tmp_path / "charts"
    environment = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "auto_eda.cli",
            str(source_file),
            "--output",
            str(output_file),
            "--chart-output",
            str(chart_directory),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    chart_file = chart_directory / "missingness.svg"
    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        f"EDA report written to {output_file}\n"
        f"Missingness chart written to {chart_file}\n"
    )
    chart = chart_file.read_text(encoding="utf-8")
    assert '<svg xmlns="http://www.w3.org/2000/svg"' in chart
    assert "<title>Missing values by column</title>" in chart
    assert "spend" in chart
    assert "1 missing (33.3%)" in chart


def test_cli_limits_displayed_categorical_values(tmp_path: Path) -> None:
    source_file = tmp_path / "customer_segments.csv"
    source_file.write_text(
        "segment\n"
        "enterprise\n"
        "enterprise\n"
        "enterprise\n"
        "midmarket\n"
        "midmarket\n"
        "startup\n",
        encoding="utf-8",
    )
    output_file = tmp_path / "eda_report.md"
    environment = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "auto_eda.cli",
            str(source_file),
            "--output",
            str(output_file),
            "--categorical-limit",
            "2",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    report = output_file.read_text(encoding="utf-8")
    assert "## Categorical values (top 2 per column)" in report
    assert "| segment | 1 | enterprise | 3 |" in report
    assert "| segment | 2 | midmarket | 2 |" in report
    assert "| segment | 3 | startup | 1 |" not in report


def test_cli_summarizes_boolean_flags_from_the_bundled_example(tmp_path: Path) -> None:
    source_file = Path("examples/sample_boolean_flags.csv")
    output_file = tmp_path / "eda_boolean_flags.md"
    environment = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "auto_eda.cli",
            str(source_file),
            "--output",
            str(output_file),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    report = output_file.read_text(encoding="utf-8")
    assert "## Boolean flag summary\n\n" in report
    assert "| active_customer | 3 | 1 | 4 |" in report
    assert "| renewal_ready | 2 | 2 | 4 |" in report


def test_cli_profiles_business_formatted_numbers_from_the_bundled_example(
    tmp_path: Path,
) -> None:
    source_file = Path("examples/sample_business_numbers.csv")
    output_file = tmp_path / "eda_business_numbers.md"
    environment = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "auto_eda.cli",
            str(source_file),
            "--output",
            str(output_file),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    report = output_file.read_text(encoding="utf-8")
    assert "| booked_revenue | numeric | 0 | 3 | 666.67 | -100.75 | 1200.50 |" in report


def test_cli_trims_header_names_from_the_bundled_example(tmp_path: Path) -> None:
    source_file = Path("examples/sample_whitespace_headers.csv")
    output_file = tmp_path / "eda_whitespace_headers.md"
    environment = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "auto_eda.cli",
            str(source_file),
            "--output",
            str(output_file),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    report = output_file.read_text(encoding="utf-8")
    assert "- Header name ' customer ' at column 1 was trimmed to 'customer'." in report
    assert "- Header name ' spend ' at column 2 was trimmed to 'spend'." in report
    assert "| spend | numeric | 0 | 3 | 17.00 | 10.50 | 25.00 |" in report


def test_cli_rejects_a_non_positive_categorical_limit(tmp_path: Path) -> None:
    source_file = tmp_path / "customers.csv"
    source_file.write_text("segment\nenterprise\n", encoding="utf-8")
    output_file = tmp_path / "eda_report.md"
    environment = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "auto_eda.cli",
            str(source_file),
            "--output",
            str(output_file),
            "--categorical-limit",
            "0",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 2
    assert "--categorical-limit must be at least 1" in result.stderr


def test_cli_rejects_a_multi_character_delimiter(tmp_path: Path) -> None:
    source_file = tmp_path / "customers.csv"
    source_file.write_text("customer||spend\nAster||10.5\n", encoding="utf-8")
    output_file = tmp_path / "eda_report.md"
    environment = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "auto_eda.cli",
            str(source_file),
            "--output",
            str(output_file),
            "--delimiter",
            "||",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 2
    assert "--delimiter must be exactly one character" in result.stderr
    assert not output_file.exists()
