"""Command-line entry point for the deterministic Auto EDA Analyst demo."""

from __future__ import annotations

import argparse
from pathlib import Path

from auto_eda.profile import profile_csv, render_markdown_report


def _positive_integer(value: str) -> int:
    """Parse a command-line integer that must be at least one."""
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("--categorical-limit must be at least 1")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for CSV profiling."""
    parser = argparse.ArgumentParser(
        description="Generate a deterministic Markdown EDA report from a CSV file."
    )
    parser.add_argument("source_file", type=Path, help="Headered CSV file to profile")
    parser.add_argument("--output", type=Path, required=True, help="Markdown output path")
    parser.add_argument(
        "--categorical-limit",
        type=_positive_integer,
        default=5,
        help="Maximum categorical values to display per text column (default: 5)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Profile the requested CSV and write its Markdown report."""
    args = build_parser().parse_args(argv)
    report = render_markdown_report(
        profile_csv(args.source_file), categorical_limit=args.categorical_limit
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"EDA report written to {args.output}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
