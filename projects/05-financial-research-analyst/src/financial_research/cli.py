"""Command-line entry point for the offline financial research analyst."""

from __future__ import annotations

import argparse
from pathlib import Path

from financial_research.metrics import (
    load_fundamental_history,
    load_price_history,
    render_research_brief,
    summarize_fundamentals,
    summarize_fundamentals_trend,
    summarize_moving_average_trend,
    summarize_benchmark_sensitivity,
    summarize_price_history,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic Markdown research brief from price history CSV data."
    )
    parser.add_argument("price_file", type=Path, help="CSV with date,ticker,close,volume columns")
    parser.add_argument("--ticker", required=True, help="Ticker to analyze")
    parser.add_argument("--benchmark", help="Optional benchmark ticker from the same CSV")
    parser.add_argument(
        "--periods-per-year",
        type=int,
        default=252,
        help="Annualization periods for the price history (default: 252 trading days)",
    )
    parser.add_argument(
        "--fundamentals-file",
        type=Path,
        help="Optional CSV with as_of_date,ticker,market_cap,revenue_ttm,net_income_ttm,total_equity",
    )
    parser.add_argument("--output", type=Path, required=True, help="Markdown output path")
    parser.add_argument(
        "--trend-short-window",
        type=int,
        default=3,
        help="Short moving-average window for the trend section (default: 3)",
    )
    parser.add_argument(
        "--trend-long-window",
        type=int,
        default=5,
        help="Long moving-average window for the trend section (default: 5)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    asset_prices = load_price_history(args.price_file, ticker=args.ticker)
    asset_summary = summarize_price_history(
        asset_prices,
        periods_per_year=args.periods_per_year,
    )
    trend = summarize_moving_average_trend(
        asset_prices,
        short_window=args.trend_short_window,
        long_window=args.trend_long_window,
    )

    benchmark_summary = None
    benchmark_sensitivity = None
    if args.benchmark:
        benchmark_prices = load_price_history(args.price_file, ticker=args.benchmark)
        benchmark_summary = summarize_price_history(
            benchmark_prices,
            periods_per_year=args.periods_per_year,
        )
        benchmark_sensitivity = summarize_benchmark_sensitivity(
            asset_prices,
            benchmark_prices,
        )

    fundamentals_summary = None
    fundamentals_trend = None
    if args.fundamentals_file:
        fundamentals_history = load_fundamental_history(
            args.fundamentals_file,
            ticker=args.ticker,
        )
        fundamentals_summary = summarize_fundamentals(fundamentals_history[-1])
        if len(fundamentals_history) >= 2:
            fundamentals_trend = summarize_fundamentals_trend(fundamentals_history)

    markdown = render_research_brief(
        asset_summary,
        benchmark=benchmark_summary,
        benchmark_sensitivity=benchmark_sensitivity,
        trend=trend,
        fundamentals=fundamentals_summary,
        fundamentals_trend=fundamentals_trend,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")
    print(f"Research brief written to {args.output}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
