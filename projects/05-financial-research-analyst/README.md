# Financial Research Analyst

A deterministic, offline financial analytics project for turning simple price-history CSV data into risk/return metrics and a concise Markdown research brief. This project starts with a reproducible sample asset (`NOVA`) and benchmark (`MKT`) so the full path can be tested without API keys or market-data credentials.

## Why this project matters

Financial research workflows need transparent calculations before adding live data feeds or narrative layers. This project demonstrates an analytics-engineering foundation for investment-style reporting:

- ingest a tidy price-history file with dates, tickers, closes, and volume
- calculate cumulative return, average periodic return, annualized volatility, and maximum drawdown
- compare an asset against a benchmark using deterministic sample data
- generate a Markdown brief that is easy to review, version, and share

## Project layout

```text
projects/05-financial-research-analyst/
  examples/sample_prices.csv          # deterministic asset + benchmark prices
  examples/sample_research_brief.md   # generated Markdown report
  src/financial_research/
    metrics.py                        # CSV loading, calculations, Markdown renderer
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
  --output examples/sample_research_brief.md
```

Expected CLI message:

```text
Research brief written to examples\sample_research_brief.md
```

Expected report excerpt:

```text
# NOVA Financial Research Brief

Coverage window: 2026-01-02 to 2026-01-07 (6 observations).

| Metric | Asset | Benchmark | Difference |
| --- | ---: | ---: | ---: |
| Cumulative return | 10.00% | 5.00% | +5.00 pts |
| Annualized volatility | 54.36% | 19.06% | +35.29 pts |
| Maximum drawdown | -1.89% | -0.98% | -0.91 pts |
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

## Current capabilities

- Loads deterministic local price-history CSV files.
- Filters and sorts observations for one ticker at a time.
- Validates same-ticker inputs, positive closes, and non-negative volume.
- Calculates cumulative return, average return, annualized volatility, and maximum drawdown.
- Renders an asset-vs-benchmark Markdown brief suitable for a portfolio demo.
- Provides focused tests and a CLI smoke path.

## Planned next milestones

- Add rolling return and moving-average trend metrics.
- Add a small fundamentals-style metrics fixture for valuation and profitability ratios.
- Add richer risk notes that flag volatility, drawdown, and benchmark underperformance thresholds.
- Package a final notebook or HTML report view after the metric layer is stable.

> Educational portfolio demo, not investment advice.
