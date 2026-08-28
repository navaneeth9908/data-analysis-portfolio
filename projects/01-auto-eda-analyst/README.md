# Auto EDA Analyst

A deterministic, offline CSV profiling project that turns a small tabular dataset into a reviewable Markdown exploratory-data-analysis report. It intentionally uses only the Python standard library, so the example can be run without API keys, databases, or data-science platform credentials.

## Why this project matters

Exploratory analysis is often the first step in a reliable data workflow. This project demonstrates a compact analytics-engineering slice that:

- loads a headered CSV file from disk
- counts rows and missing values by column
- reports complete-row coverage for downstream analysis readiness
- flags redundant duplicate data rows
- flags columns that have no populated values before analysts build downstream assumptions
- infers whether every populated value in a column is numeric, including common business-formatted values with currency symbols or thousands separators
- calculates mean, minimum, maximum, quartiles, median, and pairwise correlations for numeric columns, including business-formatted numeric exports
- flags numeric columns with values below zero so refunds, credits, and data-entry sign issues are reviewed explicitly
- flags columns that mix numeric-like export values with non-numeric status text before analysts trust them as dimensions
- flags text columns dominated by one repeated category so low-variation fields are visible before segmentation
- identifies ISO `YYYY-MM-DD` date columns and reports their earliest/latest dates
- flags numeric values outside deterministic 1.5-IQR Tukey fences
- normalizes accidental whitespace in CSV header names while preserving schema warnings
- writes a deterministic Markdown report that can be reviewed and versioned
- escapes Markdown table-sensitive characters in headers and text values so generated reports remain valid when source data contains pipes or embedded line breaks
- distills profiling results into an analyst-ready summary of data quality, complete-row coverage, missingness priority, numeric ranges, detected outliers, and the strongest numeric relationship

## Quick start

From this project directory:

```bash
python -m pytest tests/ -q
PYTHONPATH=src python -m auto_eda.cli examples/sample_customers.csv \
  --output /tmp/auto_eda_report.md

# Write a standalone SVG showing missing values by column.
PYTHONPATH=src python -m auto_eda.cli examples/sample_customers.csv \
  --output /tmp/auto_eda_report.md \
  --chart-output /tmp/auto_eda_charts

# Inspect the duplicate-row quality signal with a second bundled example.
PYTHONPATH=src python -m auto_eda.cli examples/sample_duplicate_rows.csv \
  --output /tmp/auto_eda_duplicates.md

# Inspect schema warnings for an empty header that is renamed plus uneven data rows.
PYTHONPATH=src python -m auto_eda.cli examples/sample_schema_warnings.csv \
  --output /tmp/auto_eda_schema_warnings.md

# Inspect duplicate headers; repeated names are renamed before profiling.
PYTHONPATH=src python -m auto_eda.cli examples/sample_duplicate_headers.csv \
  --output /tmp/auto_eda_duplicate_headers.md

# Inspect headers with accidental leading/trailing spaces.
PYTHONPATH=src python -m auto_eda.cli examples/sample_whitespace_headers.csv \
  --output /tmp/auto_eda_whitespace_headers.md

# Inspect columns that contain no populated values.
PYTHONPATH=src python -m auto_eda.cli examples/sample_empty_columns.csv \
  --output /tmp/auto_eda_empty_columns.md

# Inspect values outside Tukey's 1.5-IQR fences.
PYTHONPATH=src python -m auto_eda.cli examples/sample_iqr_outliers.csv \
  --output /tmp/auto_eda_outliers.md

# Surface populated columns that repeat one distinct value.
PYTHONPATH=src python -m auto_eda.cli examples/sample_constant_columns.csv \
  --output /tmp/auto_eda_constant_columns.md

# Flag likely identifier columns with many distinct text values.
PYTHONPATH=src python -m auto_eda.cli examples/sample_high_cardinality_customers.csv \
  --output /tmp/auto_eda_high_cardinality.md

# Summarize yes/no or true/false operational flag columns.
PYTHONPATH=src python -m auto_eda.cli examples/sample_boolean_flags.csv \
  --output /tmp/auto_eda_boolean_flags.md

# Flag text dimensions where one category dominates the populated rows.
PYTHONPATH=src python -m auto_eda.cli examples/sample_dominant_categories.csv \
  --output /tmp/auto_eda_dominant_categories.md

# Parse common business-formatted revenue values as numeric.
PYTHONPATH=src python -m auto_eda.cli examples/sample_business_numbers.csv \
  --output /tmp/auto_eda_business_numbers.md

# Flag numeric columns with refunds, credits, or other negative values.
PYTHONPATH=src python -m auto_eda.cli examples/sample_negative_values.csv \
  --output /tmp/auto_eda_negative_values.md

# Flag amount columns that mix numeric-like values with status text.
PYTHONPATH=src python -m auto_eda.cli examples/sample_mixed_type_amounts.csv \
  --output /tmp/auto_eda_mixed_type_amounts.md

# Keep Markdown tables valid when headers or values contain pipes or line breaks.
PYTHONPATH=src python -m auto_eda.cli examples/sample_markdown_sensitive_values.csv \
  --output /tmp/auto_eda_markdown_sensitive_values.md

# Correlate business-formatted currency columns without preprocessing.
PYTHONPATH=src python -m auto_eda.cli examples/sample_currency_correlations.csv \
  --output /tmp/auto_eda_currency_correlations.md

# Inspect Pearson correlations using rows populated in both numeric columns.
PYTHONPATH=src python -m auto_eda.cli examples/sample_numeric_correlations.csv \
  --output /tmp/auto_eda_correlations.md

# Inspect a semicolon-delimited export without rewriting it first.
PYTHONPATH=src python -m auto_eda.cli examples/sample_semicolon_customers.csv \
  --output /tmp/auto_eda_semicolon.md \
  --delimiter ";"

# Inspect ISO date ranges for timeline-style fields.
PYTHONPATH=src python -m auto_eda.cli examples/sample_renewals.csv \
  --output /tmp/auto_eda_renewals.md

# Show only the two most frequent values for each text column.
PYTHONPATH=src python -m auto_eda.cli examples/sample_customers.csv \
  --output /tmp/auto_eda_categories.md \
  --categorical-limit 2
```

Expected CLI message:

```text
EDA report written to /tmp/auto_eda_report.md
```

With `--chart-output /tmp/auto_eda_charts`, the CLI also writes an accessible, standalone SVG artifact and reports its location:

```text
Missingness chart written to /tmp/auto_eda_charts/missingness.svg
```

The chart uses one bar per column, shows both the number and percentage of blank values, and can be opened directly in a browser or embedded in a portfolio page.

Expected report:

```markdown
# Automated EDA Report

Source: sample_customers.csv

Rows: 3

## Analyst summary

- 3 rows across 3 columns: 1 numeric and 2 text.
- Data quality: 1 missing value across 1 column; 0 duplicate rows; 2 complete rows (66.7%).
- Numeric range: spend spans 10.50 to 19.50.

## Data quality

Duplicate rows: 0
Missing values: 1 across 1 column
Complete rows: 2 (66.7%)

## Missingness details

| Column | Missing values | Missing rate |
| --- | ---: | ---: |
| spend | 1 | 33.3% |

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

The `sample_schema_warnings.csv` example renames a blank first header to a stable
placeholder before profiling, while still preserving a warning for analyst review:

```markdown
Schema warnings:
- Empty header name at column 1; renamed to 'column_1'.
```

The `sample_duplicate_headers.csv` example surfaces duplicate CSV headers before
profiling so the second copy is not silently overwritten:

```markdown
Schema warnings:
- Duplicate header name 'spend' at column 3; renamed to 'spend_2'.
```

The `sample_whitespace_headers.csv` example trims accidental export whitespace
from header names before profiling and keeps a schema warning for review:

```markdown
Schema warnings:
- Header name ' customer ' at column 1 was trimmed to 'customer'.
- Header name ' spend ' at column 2 was trimmed to 'spend'.
```

The `sample_empty_columns.csv` example adds this section so fields that are
present in the extract but unusable for analysis are easy to spot:

```markdown
## Empty columns

| Column | Missing values | Missing rate |
| --- | ---: | ---: |
| legacy_id | 4 | 100.0% |
```

The `sample_iqr_outliers.csv` example adds this section:

```markdown
## IQR outliers

| Column | Outlier count | Values outside 1.5-IQR fences |
| --- | ---: | --- |
| sales | 1 | 100.00 |
```

The `sample_constant_columns.csv` example adds this section, so fields that do not vary can be reviewed before downstream analysis:

```markdown
## Constant columns

| Column | Inferred type | Constant value | Non-null rows |
| --- | --- | --- | ---: |
| unit_price | numeric | 9.99 | 3 |
| status | text | active | 3 |
```

The `sample_high_cardinality_customers.csv` example adds this section, so likely identifier fields are separated from ordinary categorical dimensions:

```markdown
## High-cardinality text columns

| Column | Unique values | Non-null rows | Unique rate |
| --- | ---: | ---: | ---: |
| customer_id | 5 | 5 | 100.0% |
```

The `sample_boolean_flags.csv` example adds this section, so operational flags are counted consistently even when source systems use yes/no or true/false text values:

```markdown
## Boolean flag summary

| Column | True-like values | False-like values | Non-null rows |
| --- | ---: | ---: | ---: |
| active_customer | 3 | 1 | 4 |
| renewal_ready | 2 | 2 | 4 |
```

The `sample_dominant_categories.csv` example adds this section, so low-variation text fields are visible before analysts treat them as balanced dimensions:

```markdown
## Dominant categorical values

| Column | Dominant value | Count | Share | Other values |
| --- | --- | ---: | ---: | ---: |
| status | active | 4 | 80.0% | 1 |
```

The `sample_business_numbers.csv` example keeps common finance/export formatting numeric, including currency symbols, thousands separators, and parenthesized negatives:

```markdown
| booked_revenue | numeric | 0 | 3 | 666.67 | -100.75 | 1200.50 |
```

The `sample_negative_values.csv` example adds a focused review table for numeric columns containing below-zero values:

```markdown
## Negative numeric values

| Column | Negative values | Lowest value | Highest negative value |
| --- | ---: | ---: | ---: |
| refund_amount | 2 | -25.00 | -10.00 |
| net_revenue | 1 | -50.00 | -50.00 |
```

The `sample_mixed_type_amounts.csv` example keeps partially numeric status
fields visible as text while warning that some populated values look like
amounts:

```markdown
## Mixed-type warnings

| Column | Numeric-like values | Non-numeric examples |
| --- | ---: | --- |
| booked_amount | 3 of 5 | not available, pending |
```

The `sample_markdown_sensitive_values.csv` example escapes dynamic Markdown
table cells, so source pipes and embedded line breaks do not split report rows:

```markdown
| customer\|tier | text | 0 | 2 | — | — | — |
| customer\|tier | 1 | Aster\|Enterprise North | 1 |
```

The `sample_currency_correlations.csv` example applies the same parsing before calculating pairwise numeric relationships, so currency exports can be correlated without manual cleanup:

```markdown
- Strongest numeric relationship: revenue and refunds have Pearson r -1.00 over 3 paired rows.

## Numeric correlations

| First column | Second column | Pairwise rows | Pearson r |
| --- | --- | ---: | ---: |
| revenue | refunds | 3 | -1.00 |
```

The `sample_numeric_correlations.csv` example adds this section; its missing April sales value is excluded from the pairwise calculation. The analyst summary also calls out the strongest relationship so reviewers see the highest-signal numeric pair before the detailed table.

```markdown
- Strongest numeric relationship: sales and refunds have Pearson r -1.00 over 3 paired rows.

## Numeric correlations

| First column | Second column | Pairwise rows | Pearson r |
| --- | --- | ---: | ---: |
| sales | refunds | 3 | -1.00 |
```

The `sample_renewals.csv` example adds a date-range section for populated ISO date columns and summarizes the timeline coverage before the detailed tables:

```markdown
- 3 rows across 4 columns: 1 numeric, 1 date, and 2 text.
- Date coverage: renewal_date runs from 2026-01-15 to 2026-03-30 across 2 populated rows.

## Date ranges

| Column | Earliest date | Latest date | Non-null rows |
| --- | --- | --- | ---: |
| renewal_date | 2026-01-15 | 2026-03-30 | 2 |
```

## Input contract

- Inputs must be UTF-8 CSV files with a header row. A header-only file produces a zero-row report with text columns rather than failing. Use `--delimiter` for single-character delimiters such as semicolons when exported data is not comma-separated; longer delimiter values are rejected with a clear CLI validation error before report files are written.
- Blank cells count as missing values. Reports show the total missing-value count and affected column count in the data-quality summary, then rank incomplete columns by missing count and percentage in a dedicated section.
- Complete rows are records with populated values for every header column; reports show both the count and percentage so analysis-ready coverage is visible before modeling or charting.
- Duplicate rows count redundant data records; a repeated row counts once after its first instance.
- Columns with no populated values appear in an `Empty columns` table with a 100% missing rate.
- Text columns with at least four populated values and at least 80% distinct values appear in a `High-cardinality text columns` table so likely identifiers are not mistaken for low-cardinality dimensions.
- Text columns whose populated values are only yes/no, y/n, or true/false appear in a `Boolean flag summary` table with true-like and false-like counts while still remaining visible in categorical summaries.
- Non-boolean text columns where the top value is at least 80% of populated rows appear in a `Dominant categorical values` table with the dominant value, count, share, and number of remaining values.
- Empty header names, duplicate header names, header names with accidental leading/trailing whitespace, and records whose width differs from the header are surfaced as schema warnings; record numbers count the header as record 1, blank headers are renamed to stable `column_N` placeholders, trimmed headers use the stripped display name, and repeated headers are renamed with numeric suffixes before profiling.
- A column is inferred as `numeric` only when it has at least one populated value and every populated value can be parsed as a number. Common business formatting is accepted for numeric parsing: comma thousands separators, leading `$`, `€`, or `£`, and parenthesized negative values such as `($100.75)`.
- Numeric columns with one or more values below zero appear in a `Negative numeric values` table with the count, lowest value, and highest negative value.
- Text columns with at least one numeric-like value and at least one non-numeric value appear in a `Mixed-type warnings` table. The warning reports the count of numeric-like populated values and up to three sorted non-numeric examples, while keeping the column in categorical summaries for review.
- Generated Markdown table cells escape pipe characters and collapse embedded line breaks in dynamic header and text values, keeping report tables parseable without mutating the underlying source profile.
- A non-numeric column is inferred as `date` only when every populated value is an ISO `YYYY-MM-DD` date; date columns appear in a `Date ranges` table instead of categorical-value summaries.
- Numeric distributions use 25th/75th percentiles with linear interpolation between adjacent sorted values; median is reported separately.
- A numeric value is an outlier only when it is strictly outside Tukey's 1.5-IQR fences; reported values are sorted and formatted to two decimals.
- A populated numeric or text column with exactly one distinct value appears in a `Constant columns` table; all-missing columns do not appear.
- Numeric-column pairs with at least two rows populated in both columns and nonzero variation report a Pearson correlation; missing values are excluded pairwise and constant pairs are omitted.
- Passing `--chart-output DIRECTORY` writes a deterministic `missingness.svg` chart that plots each column's blank-value count and percentage. SVG label text is escaped so input header text is safe to render.
- Every report starts with an analyst summary of dataset shape, data quality, and complete-row coverage. It separates detected date columns from text columns, adds date-coverage ranges when ISO date columns are present, includes numeric ranges when numeric columns are present, an outlier watchlist only when the IQR check finds values to review, and the strongest absolute Pearson correlation when numeric-column pairs are available.
- Numeric results are formatted to two decimals for deterministic report diffs.
- Text columns include their count of distinct non-blank values plus the most frequent value and its frequency. Their value distributions are ranked by descending frequency with alphabetical tie-breaking; the CLI displays the first five by default and accepts a positive `--categorical-limit` override.

## Project layout

```text
projects/01-auto-eda-analyst/
  examples/sample_boolean_flags.csv
  examples/sample_business_numbers.csv
  examples/sample_customers.csv
  examples/sample_constant_columns.csv
  examples/sample_dominant_categories.csv
  examples/sample_duplicate_headers.csv
  examples/sample_duplicate_rows.csv
  examples/sample_empty_columns.csv
  examples/sample_high_cardinality_customers.csv
  examples/sample_iqr_outliers.csv
  examples/sample_markdown_sensitive_values.csv
  examples/sample_mixed_type_amounts.csv
  examples/sample_negative_values.csv
  examples/sample_numeric_correlations.csv
  examples/sample_renewals.csv
  examples/sample_schema_warnings.csv
  examples/sample_semicolon_customers.csv
  examples/sample_whitespace_headers.csv
  src/auto_eda/profile.py
  src/auto_eda/cli.py
  tests/test_cli.py
  tests/test_profile.py
```

## Current capabilities

- Local CSV profiling with row counts, complete-row coverage, total missing-value counts, ranked per-column missingness, and configurable one-character delimiters for non-comma exports.
- Concise analyst summary of dataset shape, missingness, duplicate rows, date coverage, numeric ranges, IQR outlier watchlists, and strongest numeric relationships.
- Duplicate-row data-quality signal in the generated report.
- Empty-column signal for fields that contain no populated values.
- Constant-column signal for populated fields with one distinct value.
- High-cardinality text-column signal for likely identifiers or sparse dimensions.
- Boolean flag summary for yes/no, y/n, or true/false text columns.
- Dominant-category warnings for low-variation text fields where one value accounts for at least 80% of populated rows.
- Mixed-type warnings for text columns that combine parseable amounts with non-numeric status values.
- Markdown-safe table rendering for source headers and text values that contain pipes or embedded line breaks.
- Schema warnings for empty, duplicate, or whitespace-padded column headers, including deterministic placeholder names for blank headers, and data rows that do not match header width.
- Conservative numeric-type inference, distribution quartiles, negative-value checks, and summary statistics, including common business-formatted numbers with currency symbols, thousands separators, or parenthesized negatives.
- ISO date-column inference with earliest/latest date range reporting.
- Pairwise-complete Pearson correlations for variable numeric-column pairs.
- Optional standalone SVG missingness chart artifacts via `--chart-output`.
- Deterministic IQR outlier reporting for numeric columns.
- Categorical cardinality, top-value, and configurable ranked-value summaries for text columns.
- A standalone CLI that generates a Markdown EDA report.
