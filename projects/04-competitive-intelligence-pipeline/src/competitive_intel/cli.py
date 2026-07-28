"""Command-line entry point for the competitive intelligence pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from competitive_intel.source_collection import (
    build_buyer_fit_scores,
    build_competitor_profiles,
    build_profile_trend_deltas,
    build_source_coverage_warnings,
    load_profile_snapshot,
    load_source_notes,
    render_buyer_fit_markdown,
    render_executive_summary_markdown,
    render_follow_up_research_markdown,
    render_landscape_markdown,
    render_profile_trends_markdown,
    render_source_coverage_markdown,
    render_source_evidence_markdown,
    write_profile_snapshot,
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
    parser.add_argument(
        "--coverage-as-of",
        help="Optional YYYY-MM-DD date that enables source coverage freshness checks.",
    )
    parser.add_argument(
        "--max-note-age-days",
        type=int,
        default=30,
        help="Maximum acceptable age for latest competitor source notes when coverage checks run.",
    )
    parser.add_argument(
        "--min-note-count",
        type=int,
        default=2,
        help="Minimum source-note count expected per competitor in coverage checks.",
    )
    parser.add_argument(
        "--min-source-types",
        type=int,
        default=2,
        help="Minimum distinct source types expected per competitor in coverage checks.",
    )
    parser.add_argument(
        "--previous-profile-snapshot",
        type=Path,
        help="Optional prior profile snapshot JSON for rendering trend deltas.",
    )
    parser.add_argument(
        "--profile-snapshot-output",
        type=Path,
        help="Optional path for writing the current profile snapshot JSON.",
    )
    parser.add_argument(
        "--snapshot-as-of",
        help="Optional YYYY-MM-DD metadata date to include in --profile-snapshot-output.",
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
    priorities = _parse_priorities(args.priority)
    scores = ()
    if priorities:
        scores = build_buyer_fit_scores(notes, priorities)

    coverage_warnings = ()
    if args.coverage_as_of:
        coverage_warnings = build_source_coverage_warnings(
            notes,
            as_of_date=args.coverage_as_of,
            max_note_age_days=args.max_note_age_days,
            min_note_count=args.min_note_count,
            min_source_types=args.min_source_types,
        )

    trend_deltas = ()
    if args.previous_profile_snapshot:
        previous_profiles = load_profile_snapshot(args.previous_profile_snapshot)
        trend_deltas = build_profile_trend_deltas(
            current_profiles=profiles,
            previous_profiles=previous_profiles,
        )

    markdown = render_landscape_markdown(profiles, title=args.title)
    markdown += "\n" + render_executive_summary_markdown(
        profiles,
        buyer_fit_scores=scores,
        coverage_warnings=coverage_warnings,
    )
    if trend_deltas:
        markdown += "\n" + render_profile_trends_markdown(trend_deltas)
    if scores:
        markdown += "\n" + render_buyer_fit_markdown(scores)
    markdown += "\n" + render_source_evidence_markdown(notes)
    if args.coverage_as_of:
        markdown += "\n" + render_source_coverage_markdown(coverage_warnings)
        markdown += "\n" + render_follow_up_research_markdown(coverage_warnings)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")
        print(f"Landscape written to {args.output}")
    else:
        print(markdown, end="")

    if args.profile_snapshot_output:
        write_profile_snapshot(
            profiles,
            args.profile_snapshot_output,
            as_of_date=args.snapshot_as_of or args.coverage_as_of,
        )
        print(f"Profile snapshot written to {args.profile_snapshot_output}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
