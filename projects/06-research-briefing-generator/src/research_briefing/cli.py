"""Command-line entry point for deterministic research briefings."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from research_briefing.briefing import (
    build_briefing,
    render_html_briefing,
    render_markdown_briefing,
)


def _reporting_date(value: str) -> date:
    """Parse the reporting date used to score source freshness."""
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("--as-of must use YYYY-MM-DD format") from error


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for local JSON source notes."""
    parser = argparse.ArgumentParser(
        description="Generate a deterministic ranked Markdown research briefing."
    )
    parser.add_argument("source_file", type=Path, help="JSON source-note file")
    parser.add_argument(
        "--as-of",
        required=True,
        type=_reporting_date,
        help="Reporting date used to calculate freshness (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "html"),
        default="markdown",
        help="Briefing output format (default: markdown)",
    )
    parser.add_argument("--output", required=True, type=Path, help="Briefing output path")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Rank sources and write a reviewable briefing document."""
    args = build_parser().parse_args(argv)
    briefing = build_briefing(args.source_file, args.as_of)
    renderer = render_html_briefing if args.format == "html" else render_markdown_briefing
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(renderer(briefing), encoding="utf-8")
    print(f"Briefing written to {args.output}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
