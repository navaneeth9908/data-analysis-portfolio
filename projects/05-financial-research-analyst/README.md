# Financial Research Analyst

A deterministic, offline financial analytics project for turning simple price-history CSV data into risk/return metrics and a concise Markdown or self-contained HTML research brief. This project starts with a reproducible sample asset (`NOVA`) and benchmark (`MKT`) so the full path can be tested without API keys or market-data credentials.

## Why this project matters

Financial research workflows need transparent calculations before adding live data feeds or narrative layers. This project demonstrates an analytics-engineering foundation for investment-style reporting:

- ingest a tidy price-history file with dates, tickers, closes, and volume
- calculate cumulative return, average periodic return, annualized volatility, maximum drawdown, moving-average trend signals, aligned benchmark correlation/beta, TTM valuation/profitability ratios, cross-period fundamentals trends, and rule-backed risk notes with benchmark-aware drawdown context
- compare an asset against a benchmark using deterministic sample data
- generate a Markdown brief or self-contained HTML report that is easy to review, version, and share

## Project layout

```text
projects/05-financial-research-analyst/
  examples/sample_prices.csv          # deterministic asset + benchmark prices
  examples/sample_fundamentals.csv    # deterministic TTM valuation/profitability inputs
  examples/sample_research_brief.md   # generated Markdown report
  examples/sample_research_brief.html # generated standalone HTML report
  src/financial_research/
    metrics.py                        # CSV loading, calculations, report renderers
    cli.py                            # report generation CLI
  tests/
    test_metrics.py
    test_cli.py
```

## Quick start

From this project directory:

```bash
python -m venv .venv
source .venv/Scripts/activate  # Git Bash on Windows
pip install -r requirements.txt
pytest tests/ -q
PYTHONPATH=src python -m financial_research.cli examples/sample_prices.csv \
  --ticker NOVA \
  --benchmark MKT \
  --fundamentals-file examples/sample_fundamentals.csv \
  --trend-short-window 3 \
  --trend-long-window 5 \
  --output examples/sample_research_brief.md

# Render the same brief as a self-contained HTML page for browser sharing.
PYTHONPATH=src python -m financial_research.cli examples/sample_prices.csv \
  --ticker NOVA \
  --benchmark MKT \
  --fundamentals-file examples/sample_fundamentals.csv \
  --trend-short-window 3 \
  --trend-long-window 5 \
  --format html \
  --output examples/sample_research_brief.html
```

Expected CLI message:

```text
Research brief written to examples\sample_research_brief.md
```

### Output formats

`--format markdown` is the default and writes the concise analyst-review brief shown below. Pass `--format html` to create a self-contained document with the same performance, benchmark-sensitivity, fundamentals, trend, and risk-note content in semantic headings and tables; it has no external assets and can be opened directly in a browser.

Expected report excerpt:

```text
# NOVA Financial Research Brief

Coverage window: 2026-01-02 to 2026-01-07 (6 observations).

## Performance summary

Benchmark: MKT

| Metric | Asset | Benchmark | Difference |
| --- | ---: | ---: | ---: |
| Cumulative return | 10.00% | 5.00% | +5.00 pts |
| Average daily return | 1.97% | 0.99% | +0.98 pts |
| Annualized volatility | 54.36% | 19.06% | +35.29 pts |
| Maximum drawdown | -1.89% | -0.98% | -0.91 pts |

## Benchmark sensitivity

Aligned observations: 6.

| Metric | Value |
| --- | ---: |
| Return correlation | -0.37 |
| Beta vs MKT | -1.05 |

## Fundamentals snapshot

As of: 2026-01-07 (TTM inputs)

| Metric | Value |
| --- | ---: |
| Price-to-sales | 5.00x |
| Net margin | 15.00% |
| Return on equity | 20.00% |

## Fundamentals trend

Coverage: 2025-10-07 to 2026-01-07 (2 observations).

| Metric | Start | Latest | Change |
| --- | ---: | ---: | ---: |
| Price-to-sales | 4.44x | 5.00x | +0.56x |
| Net margin | 13.33% | 15.00% | +1.67 pts |
| Return on equity | 17.14% | 20.00% | +2.86 pts |

## Moving-average trend

| Metric | Value |
| --- | ---: |
| Latest close | 110.00 |
| 3-day moving average | 106.67 |
| 5-day moving average | 104.60 |
| Close vs 5-day MA | +5.16% |
| 3-day vs 5-day MA | +1.98% |

Signal: **uptrend**

## Risk notes
- Annualized volatility is elevated at 54.36%; review position sizing and scenario-test wider return swings.
- Cumulative return led MKT by 5.00 percentage points over the sample window.
- Drawdown looks asset-specific: NOVA fell 0.91 percentage points more than MKT from peak to trough.
- Moving-average signal is uptrend; latest close is 5.16% above the 5-day moving average.
- Educational portfolio demo, not investment advice.
```

## Input format

The loader expects a CSV with these columns:

```csv
date,ticker,close,volume
2026-01-02,NOVA,100,1200000
2026-01-02,MKT,100,4200000
```

- `date` uses ISO format (`YYYY-MM-DD`).
- `ticker` is normalized to uppercase.
- `close` must be positive.
- `volume` cannot be negative.

### Annualization period

Price histories are annualized with 252 periods by default, which fits daily trading data. Use `--periods-per-year` to match the sampling cadence; for example, pass `--periods-per-year 12` for a monthly series. The same setting is applied to both the selected asset and its optional benchmark.

### Benchmark sensitivity

When `--benchmark` is supplied, the report also aligns the asset and benchmark on shared dates and calculates periodic-return correlation and beta. The calculation requires at least three shared observations (two aligned return periods), and both aligned return series must vary; this makes the comparison explicit rather than inferring market exposure from separate price windows.

### Optional fundamentals format

Pass `--fundamentals-file` to add a point-in-time valuation/profitability snapshot for the selected ticker. The loader selects that ticker's newest `as_of_date` row for the snapshot. When two or more dated rows are present, it also adds a start-to-latest trend table for price-to-sales, net margin, and return on equity.

```csv
as_of_date,ticker,market_cap,revenue_ttm,net_income_ttm,total_equity
2025-10-07,NOVA,400000000,90000000,12000000,70000000
2026-01-07,NOVA,500000000,100000000,15000000,75000000
```

- `market_cap`, `revenue_ttm`, and `total_equity` must be positive because they are ratio denominators.
- `net_income_ttm` can be negative; the generated net margin and return-on-equity values retain its sign.
- The report adds price-to-sales, net margin, and return on equity from the supplied trailing-twelve-month inputs.

## Current capabilities

- Loads deterministic local price-history CSV files.
- Filters and sorts observations for one ticker at a time.
- Validates same-ticker inputs, positive closes, and non-negative volume.
- Calculates cumulative return, average return, annualized volatility, maximum drawdown, aligned benchmark-return correlation/beta, short-vs-long moving-average trend signals, trailing-twelve-month price-to-sales, net margin, return on equity, cross-period fundamentals trends, and rule-backed risk notes that label drawdowns as asset-specific or market-wide when benchmark data is available.
- Renders an asset-vs-benchmark Markdown brief or a self-contained HTML report with optional fundamentals snapshot/trend tables, reproducible technical signals, and risk sections suitable for a portfolio demo.
- Provides focused tests and a CLI smoke path.

## Milestone status

The report-output milestone is complete: the CLI produces the original Markdown brief by default and an equivalent standalone HTML document with `--format html`.

> Educational portfolio demo, not investment advice.
