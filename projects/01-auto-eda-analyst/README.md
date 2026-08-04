# Auto EDA Analyst

A deterministic, offline CSV profiling project that turns a small tabular dataset into a reviewable Markdown exploratory-data-analysis report. It intentionally uses only the Python standard library, so the example can be run without API keys, databases, or data-science platform credentials.

## Why this project matters

Exploratory analysis is often the first step in a reliable data workflow. This project demonstrates a compact analytics-engineering slice that:

- loads a headered CSV file from disk
- counts rows and missing values by column
- flags redundant duplicate data rows
- infers whether every populated value in a column is numeric
- calculates mean, minimum, and maximum for numeric columns
- writes a deterministic Markdown report that can be reviewed and versioned

## Quick start

From this project directory:

```bash
python -m pytest tests/ -q
PYTHONPATH=src python -m auto_eda.cli examples/sample_customers.csv \
  --output /tmp/auto_eda_report.md

# Inspect the duplicate-row quality signal with a second bundled example.
PYTHONPATH=src python -m auto_eda.cli examples/sample_duplicate_rows.csv \
  --output /tmp/auto_eda_duplicates.md
```

Expected CLI message:

```text
EDA report written to /tmp/auto_eda_report.md
```

Expected report:

```markdown
# Automated EDA Report

Source: sample_customers.csv

Rows: 3

## Data quality

Duplicate rows: 0

## Column profile

| Column | Inferred type | Missing | Non-null | Mean | Minimum | Maximum |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| customer | text | 0 | 3 | — | — | — |
| spend | numeric | 1 | 2 | 15.00 | 10.50 | 19.50 |
| segment | text | 0 | 3 | — | — | — |

## Categorical summary

| Column | Unique values | Top value | Top value count |
| --- | ---: | --- | ---: |
| customer | 3 | Aster | 1 |
| segment | 2 | enterprise | 2 |
```

The `sample_duplicate_rows.csv` example produces `Duplicate rows: 1`.

## Input contract

- Inputs must be UTF-8 CSV files with a header row.
- Blank cells count as missing values.
- Duplicate rows count redundant data records; a repeated row counts once after its first instance.
- A column is inferred as `numeric` only when it has at least one populated value and every populated value can be parsed as a number.
- Numeric results are formatted to two decimals for deterministic report diffs.
- Text columns include their count of distinct non-blank values plus the most frequent value and its frequency.

## Project layout

```text
projects/01-auto-eda-analyst/
  examples/sample_customers.csv
  examples/sample_duplicate_rows.csv
  src/auto_eda/profile.py
  src/auto_eda/cli.py
  tests/test_cli.py
  tests/test_profile.py
```

## Current capabilities

- Local CSV profiling with row counts and per-column missingness.
- Duplicate-row data-quality signal in the generated report.
- Conservative numeric-type inference and summary statistics.
- Categorical cardinality and top-value summaries for text columns.
- A standalone CLI that generates a Markdown EDA report.

## Planned next milestones

- Add schema warnings for empty header names and inconsistent row widths.
