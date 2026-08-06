# Auto EDA Analyst

A deterministic, offline CSV profiling project that turns a small tabular dataset into a reviewable Markdown exploratory-data-analysis report. It intentionally uses only the Python standard library, so the example can be run without API keys, databases, or data-science platform credentials.

## Why this project matters

Exploratory analysis is often the first step in a reliable data workflow. This project demonstrates a compact analytics-engineering slice that:

- loads a headered CSV file from disk
- counts rows and missing values by column
- flags redundant duplicate data rows
- infers whether every populated value in a column is numeric
- calculates mean, minimum, maximum, quartiles, and median for numeric columns
- flags numeric values outside deterministic 1.5-IQR Tukey fences
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

# Inspect schema warnings for an empty header and uneven data rows.
PYTHONPATH=src python -m auto_eda.cli examples/sample_schema_warnings.csv \
  --output /tmp/auto_eda_schema_warnings.md

# Inspect values outside Tukey's 1.5-IQR fences.
PYTHONPATH=src python -m auto_eda.cli examples/sample_iqr_outliers.csv \
  --output /tmp/auto_eda_outliers.md

# Show only the two most frequent values for each text column.
PYTHONPATH=src python -m auto_eda.cli examples/sample_customers.csv \
  --output /tmp/auto_eda_categories.md \
  --categorical-limit 2
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

## Numeric distribution

| Column | 25th percentile | Median | 75th percentile |
| --- | ---: | ---: | ---: |
| spend | 12.75 | 15.00 | 17.25 |

## Categorical summary

| Column | Unique values | Top value | Top value count |
| --- | ---: | --- | ---: |
| customer | 3 | Aster | 1 |
| segment | 2 | enterprise | 2 |

## Categorical values (top 5 per column)

| Column | Rank | Value | Count |
| --- | ---: | --- | ---: |
| customer | 1 | Aster | 1 |
| customer | 2 | Birch | 1 |
| customer | 3 | Cedar | 1 |
| segment | 1 | enterprise | 2 |
| segment | 2 | midmarket | 1 |
```

The `sample_duplicate_rows.csv` example produces `Duplicate rows: 1`.

The `sample_iqr_outliers.csv` example adds this section:

```markdown
## IQR outliers

| Column | Outlier count | Values outside 1.5-IQR fences |
| --- | ---: | --- |
| sales | 1 | 100.00 |
```

## Input contract

- Inputs must be UTF-8 CSV files with a header row.
- Blank cells count as missing values.
- Duplicate rows count redundant data records; a repeated row counts once after its first instance.
- Empty header names and records whose width differs from the header are surfaced as schema warnings; record numbers count the header as record 1.
- A column is inferred as `numeric` only when it has at least one populated value and every populated value can be parsed as a number.
- Numeric distributions use 25th/75th percentiles with linear interpolation between adjacent sorted values; median is reported separately.
- A numeric value is an outlier only when it is strictly outside Tukey's 1.5-IQR fences; reported values are sorted and formatted to two decimals.
- Numeric results are formatted to two decimals for deterministic report diffs.
- Text columns include their count of distinct non-blank values plus the most frequent value and its frequency. Their value distributions are ranked by descending frequency with alphabetical tie-breaking; the CLI displays the first five by default and accepts a positive `--categorical-limit` override.

## Project layout

```text
projects/01-auto-eda-analyst/
  examples/sample_customers.csv
  examples/sample_duplicate_rows.csv
  examples/sample_iqr_outliers.csv
  examples/sample_schema_warnings.csv
  src/auto_eda/profile.py
  src/auto_eda/cli.py
  tests/test_cli.py
  tests/test_profile.py
```

## Current capabilities

- Local CSV profiling with row counts and per-column missingness.
- Duplicate-row data-quality signal in the generated report.
- Schema warnings for empty column headers and data rows that do not match header width.
- Conservative numeric-type inference, distribution quartiles, and summary statistics.
- Deterministic IQR outlier reporting for numeric columns.
- Categorical cardinality, top-value, and configurable ranked-value summaries for text columns.
- A standalone CLI that generates a Markdown EDA report.
