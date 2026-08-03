"""End-to-end behavior tests for the Auto EDA Analyst CLI."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


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
        "## Column profile\n\n"
        "| Column | Inferred type | Missing | Non-null | Mean | Minimum | Maximum |\n"
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |\n"
        "| customer | text | 0 | 3 | — | — | — |\n"
        "| spend | numeric | 1 | 2 | 15.00 | 10.50 | 19.50 |\n"
        "| segment | text | 0 | 3 | — | — | — |\n"
    )
