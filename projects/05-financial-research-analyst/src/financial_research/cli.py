"""Command-line entry point for the offline financial research analyst."""

from __future__ import annotations

import argparse
from pathlib import Path

from financial_research.metrics import (
    load_price_history,
    render_research_brief,
    summarize_price_history,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic Markdown research brief from price history CSV data."
    )
    parser.add_argument("price_file", type=Path, help="CSV with date,ticker,close,volume columns")
    parser.add_argument("--ticker", required=True, help="Ticker to analyze")
    parser.add_argument("--benchmark", help="Optional benchmark ticker from the same CSV")
    parser.add_argument("--output", type=Path, required=True, help="Markdown output path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    asset_prices = load_price_history(args.price_file, ticker=args.ticker)
    asset_summary = summarize_price_history(asset_prices)

    benchmark_summary = None
    if args.benchmark:
        benchmark_prices = load_price_history(args.price_file, ticker=args.benchmark)
        benchmark_summary = summarize_price_history(benchmark_prices)

    markdown = render_research_brief(asset_summary, benchmark=benchmark_summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")
    print(f"Research brief written to {args.output}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
