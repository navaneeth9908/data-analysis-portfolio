"""Command-line entry point for the competitive intelligence pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from competitive_intel.source_collection import (
    build_buyer_fit_scores,
    build_competitor_profiles,
    load_source_notes,
    render_buyer_fit_markdown,
    render_landscape_markdown,
    render_source_evidence_markdown,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a Markdown competitor landscape from normalized source notes."
    )
    parser.add_argument("source_notes", type=Path, help="Path to source_notes.json")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional Markdown output path. Prints to stdout when omitted.",
    )
    parser.add_argument(
        "--title",
        default="Competitive Intelligence Landscape",
        help="Markdown report title.",
    )
    parser.add_argument(
        "--priority",
        action="append",
        default=[],
        metavar="THEME=WEIGHT",
        help="Buyer priority theme and positive integer weight; repeat for multiple priorities.",
    )
    return parser


def _parse_priorities(raw_priorities: list[str]) -> dict[str, int]:
    priorities: dict[str, int] = {}
    for raw_priority in raw_priorities:
        if "=" not in raw_priority:
            raise ValueError("priority must use THEME=WEIGHT format")
        theme, raw_weight = raw_priority.split("=", 1)
        try:
            weight = int(raw_weight)
        except ValueError as exc:
            raise ValueError(f"priority weight for {theme} must be an integer") from exc
        priorities[theme] = weight
    return priorities


def main(argv: list[str] | None = None) -> int:
    """Run the competitive landscape CLI."""
    args = build_parser().parse_args(argv)
    notes = load_source_notes(args.source_notes)
    profiles = build_competitor_profiles(notes)
    markdown = render_landscape_markdown(profiles, title=args.title)
    priorities = _parse_priorities(args.priority)
    if priorities:
        scores = build_buyer_fit_scores(notes, priorities)
        markdown += "\n" + render_buyer_fit_markdown(scores)
    markdown += "\n" + render_source_evidence_markdown(notes)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")
        print(f"Landscape written to {args.output}")
    else:
        print(markdown, end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
