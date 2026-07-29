"""Behavior tests for the competitive intelligence source pipeline."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import competitive_intel.source_collection as source_collection
from competitive_intel.source_collection import build_competitor_profiles, load_source_notes


def test_load_source_notes_normalizes_company_names_and_signal_fields(tmp_path: Path) -> None:
    notes_path = tmp_path / "source_notes.json"
    notes_path.write_text(
        json.dumps(
            {
                "notes": [
                    {
                        "id": "acme-q2-webinar",
                        "company": "  Acme Analytics  ",
                        "source_type": "Webinar",
                        "source": "Q2 product webinar",
                        "published_date": "2026-06-18",
                        "summary": "Acme emphasized governed self-service dashboards for finance teams.",
                        "signals": [
                            {
                                "theme": " Product ",
                                "sentiment": "Strength",
                                "detail": "Finance-ready semantic layer templates",
                                "confidence": 4,
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    notes = load_source_notes(notes_path)

    assert len(notes) == 1
    note = notes[0]
    assert note.company == "Acme Analytics"
    assert note.source_type == "webinar"
    assert note.signals[0].theme == "product"
    assert note.signals[0].sentiment == "strength"
    assert note.signals[0].confidence == 4


def test_build_competitor_profiles_rolls_up_signal_scores(tmp_path: Path) -> None:
    notes_path = tmp_path / "source_notes.json"
    notes_path.write_text(
        json.dumps(
            {
                "notes": [
                    {
                        "id": "acme-webinar",
                        "company": "Acme Analytics",
                        "source_type": "webinar",
                        "source": "Finance analytics webinar",
                        "published_date": "2026-06-18",
                        "summary": "Acme highlighted governed analytics templates.",
                        "signals": [
                            {
                                "theme": "product",
                                "sentiment": "strength",
                                "detail": "Finance-ready semantic layer templates",
                                "confidence": 4,
                            },
                            {
                                "theme": "pricing",
                                "sentiment": "risk",
                                "detail": "Enterprise packaging requires annual platform commit",
                                "confidence": 2,
                            },
                        ],
                    },
                    {
                        "id": "acme-release",
                        "company": "Acme Analytics",
                        "source_type": "press release",
                        "source": "Connector launch announcement",
                        "published_date": "2026-06-20",
                        "summary": "Acme announced a faster ERP connector rollout.",
                        "signals": [
                            {
                                "theme": "delivery",
                                "sentiment": "strength",
                                "detail": "ERP connector implementation window cut to four weeks",
                                "confidence": 3,
                            }
                        ],
                    },
                    {
                        "id": "northstar-review",
                        "company": "Northstar BI",
                        "source_type": "review",
                        "source": "Customer implementation review",
                        "published_date": "2026-06-11",
                        "summary": "Northstar BI customers praised onboarding support.",
                        "signals": [
                            {
                                "theme": "support",
                                "sentiment": "strength",
                                "detail": "Hands-on enablement reduced dashboard rollout risk",
                                "confidence": 5,
                            }
                        ],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    notes = load_source_notes(notes_path)

    profiles = build_competitor_profiles(notes)

    acme = next(profile for profile in profiles if profile.company == "Acme Analytics")
    assert acme.note_count == 2
    assert acme.signal_count == 3
    assert acme.strength_score == 7
    assert acme.risk_score == 2
    assert acme.gap_score == 0
    assert acme.latest_source_date == "2026-06-20"
    assert acme.source_types == ("press release", "webinar")
    assert acme.top_themes == ("product", "delivery", "pricing")


def test_render_landscape_markdown_summarizes_profiles(tmp_path: Path) -> None:
    notes_path = tmp_path / "source_notes.json"
    notes_path.write_text(
        json.dumps(
            {
                "notes": [
                    {
                        "id": "acme-webinar",
                        "company": "Acme Analytics",
                        "source_type": "webinar",
                        "source": "Finance analytics webinar",
                        "published_date": "2026-06-18",
                        "summary": "Acme highlighted governed analytics templates.",
                        "signals": [
                            {
                                "theme": "product",
                                "sentiment": "strength",
                                "detail": "Finance-ready semantic layer templates",
                                "confidence": 4,
                            },
                            {
                                "theme": "pricing",
                                "sentiment": "risk",
                                "detail": "Annual platform commit required",
                                "confidence": 2,
                            },
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    profiles = build_competitor_profiles(load_source_notes(notes_path))

    markdown = source_collection.render_landscape_markdown(
        profiles,
        title="Analytics Platform Competitor Landscape",
    )

    assert markdown.startswith("# Analytics Platform Competitor Landscape\n")
    assert "| Company | Notes | Signals | Strength | Gap | Risk | Top themes | Sources |" in markdown
    assert "| Acme Analytics | 1 | 2 | 4 | 0 | 2 | product, pricing | webinar |" in markdown
    assert "Scores are confidence-weighted rollups from public-source notes." in markdown


def test_build_profile_trend_deltas_compares_previous_and_current_profiles() -> None:
    previous_profiles = (
        source_collection.CompetitorProfile(
            company="Acme Analytics",
            note_count=2,
            signal_count=3,
            strength_score=7,
            gap_score=0,
            risk_score=2,
            latest_source_date="2026-06-20",
            source_types=("press release", "webinar"),
            top_themes=("product", "pricing"),
        ),
        source_collection.CompetitorProfile(
            company="Northstar BI",
            note_count=2,
            signal_count=3,
            strength_score=8,
            gap_score=3,
            risk_score=0,
            latest_source_date="2026-06-16",
            source_types=("review", "website"),
            top_themes=("support", "governance"),
        ),
    )
    current_profiles = (
        source_collection.CompetitorProfile(
            company="Acme Analytics",
            note_count=3,
            signal_count=5,
            strength_score=9,
            gap_score=1,
            risk_score=2,
            latest_source_date="2026-06-25",
            source_types=("press release", "review", "webinar"),
            top_themes=("product", "delivery"),
        ),
        source_collection.CompetitorProfile(
            company="Beacon Metrics",
            note_count=1,
            signal_count=2,
            strength_score=4,
            gap_score=0,
            risk_score=1,
            latest_source_date="2026-06-23",
            source_types=("blog",),
            top_themes=("governance", "pricing"),
        ),
    )

    deltas = source_collection.build_profile_trend_deltas(
        current_profiles=current_profiles,
        previous_profiles=previous_profiles,
    )

    assert [(delta.company, delta.status) for delta in deltas] == [
        ("Acme Analytics", "changed"),
        ("Beacon Metrics", "new"),
        ("Northstar BI", "removed"),
    ]
    acme = deltas[0]
    assert acme.note_delta == 1
    assert acme.signal_delta == 2
    assert acme.strength_delta == 2
    assert acme.gap_delta == 1
    assert acme.risk_delta == 0
    assert acme.added_themes == ("delivery",)
    assert acme.removed_themes == ("pricing",)
    beacon = deltas[1]
    assert beacon.added_themes == ("governance", "pricing")
    northstar = deltas[2]
    assert northstar.note_delta == -2
    assert northstar.removed_themes == ("support", "governance")


def test_profile_snapshot_round_trip_preserves_profile_metrics(tmp_path: Path) -> None:
    project_dir = Path(__file__).resolve().parents[1]
    profiles = build_competitor_profiles(load_source_notes(project_dir / "examples/source_notes.json"))
    snapshot_path = tmp_path / "profile_snapshot.json"

    source_collection.write_profile_snapshot(
        profiles,
        snapshot_path,
        as_of_date="2026-07-02",
    )
    loaded_profiles = source_collection.load_profile_snapshot(snapshot_path)

    assert loaded_profiles == profiles
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert payload["as_of_date"] == "2026-07-02"
    assert payload["profiles"][0] == {
        "company": "Acme Analytics",
        "note_count": 2,
        "signal_count": 3,
        "strength_score": 7,
        "gap_score": 0,
        "risk_score": 2,
        "latest_source_date": "2026-06-20",
        "source_types": ["press release", "webinar"],
        "top_themes": ["product", "delivery", "pricing"],
    }


def test_render_profile_trends_markdown_summarizes_signed_changes() -> None:
    deltas = (
        source_collection.ProfileTrendDelta(
            company="Acme Analytics",
            status="changed",
            note_delta=1,
            signal_delta=2,
            strength_delta=2,
            gap_delta=1,
            risk_delta=0,
            added_themes=("delivery",),
            removed_themes=("pricing",),
        ),
        source_collection.ProfileTrendDelta(
            company="Northstar BI",
            status="removed",
            note_delta=-2,
            signal_delta=-3,
            strength_delta=-8,
            gap_delta=-3,
            risk_delta=0,
            added_themes=(),
            removed_themes=("support", "governance"),
        ),
    )

    markdown = source_collection.render_profile_trends_markdown(deltas)

    assert markdown.startswith("## Landscape trend deltas\n")
    assert "Positive values show growth versus the previous profile snapshot." in markdown
    assert "| Company | Status | Notes Δ | Signals Δ | Strength Δ | Gap Δ | Risk Δ | Theme changes |" in markdown
    assert "| Acme Analytics | changed | +1 | +2 | +2 | +1 | 0 | + delivery; - pricing |" in markdown
    assert "| Northstar BI | removed | -2 | -3 | -8 | -3 | 0 | - support, governance |" in markdown


def test_render_source_evidence_markdown_groups_latest_notes_by_competitor() -> None:
    project_dir = Path(__file__).resolve().parents[1]
    notes = load_source_notes(project_dir / "examples/source_notes.json")

    markdown = source_collection.render_source_evidence_markdown(
        notes,
        max_notes_per_company=1,
    )

    assert markdown.startswith("## Evidence highlights\n")
    assert "Source-backed snippets show why each competitor earned its score." in markdown
    assert "### Acme Analytics" in markdown
    assert "### Northstar BI" in markdown
    assert markdown.index("### Acme Analytics") < markdown.index("### Northstar BI")
    assert (
        "- **2026-06-20 · press release · ERP connector launch announcement** — "
        "Acme announced a faster ERP connector rollout aimed at mid-market analytics teams."
        in markdown
    )
    assert (
        "  - delivery / strength / confidence 3: Implementation window for the ERP connector "
        "is marketed as four weeks with certified templates."
        in markdown
    )
    assert "Finance analytics product webinar" not in markdown


def test_cli_writes_landscape_markdown(tmp_path: Path, capsys) -> None:
    notes_path = tmp_path / "source_notes.json"
    output_path = tmp_path / "landscape.md"
    notes_path.write_text(
        json.dumps(
            {
                "notes": [
                    {
                        "id": "acme-webinar",
                        "company": "Acme Analytics",
                        "source_type": "webinar",
                        "source": "Finance analytics webinar",
                        "published_date": "2026-06-18",
                        "summary": "Acme highlighted governed analytics templates.",
                        "signals": [
                            {
                                "theme": "product",
                                "sentiment": "strength",
                                "detail": "Finance-ready semantic layer templates",
                                "confidence": 4,
                            }
                        ],
                    },
                    {
                        "id": "northstar-review",
                        "company": "Northstar BI",
                        "source_type": "review",
                        "source": "Implementation review",
                        "published_date": "2026-06-11",
                        "summary": "Northstar customers praised onboarding support.",
                        "signals": [
                            {
                                "theme": "support",
                                "sentiment": "strength",
                                "detail": "Hands-on enablement reduced rollout risk",
                                "confidence": 5,
                            }
                        ],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    from competitive_intel.cli import main

    exit_code = main(
        [
            str(notes_path),
            "--output",
            str(output_path),
            "--title",
            "Analytics Competitor Landscape",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert f"Landscape written to {output_path}" in output
    markdown = output_path.read_text(encoding="utf-8")
    assert markdown.startswith("# Analytics Competitor Landscape\n")
    assert "| Acme Analytics | 1 | 1 | 4 | 0 | 0 | product | webinar |" in markdown
    assert "| Northstar BI | 1 | 1 | 5 | 0 | 0 | support | review |" in markdown


def test_cli_adds_buyer_fit_scorecard_when_priorities_are_supplied(tmp_path: Path, capsys) -> None:
    project_dir = Path(__file__).resolve().parents[1]
    output_path = tmp_path / "landscape-with-fit.md"
    from competitive_intel.cli import main

    exit_code = main(
        [
            str(project_dir / "examples/source_notes.json"),
            "--output",
            str(output_path),
            "--title",
            "Sample Analytics Competitor Landscape",
            "--priority",
            "governance=2",
            "--priority",
            "support=2",
            "--priority",
            "delivery=1",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert f"Landscape written to {output_path}" in output
    markdown = output_path.read_text(encoding="utf-8")
    assert "## Buyer-fit priority scorecard" in markdown
    assert "| Orion Data Cloud | 8 | 8 | 0 | governance |" in markdown
    assert "| Northstar BI | 4 | 10 | 6 | support, governance |" in markdown
    assert "## Evidence highlights" in markdown
    assert "### Orion Data Cloud" in markdown
    assert (
        "- **2026-06-21 · job posting · Customer success implementation role** — "
        "Orion is hiring implementation specialists to standardize customer onboarding playbooks."
        in markdown
    )
    assert (
        "  - onboarding / neutral / confidence 2: Hiring plan suggests investment in "
        "repeatable onboarding motions for enterprise customers."
        in markdown
    )


def test_cli_adds_source_coverage_watchlist_when_as_of_date_is_supplied(
    tmp_path: Path, capsys
) -> None:
    project_dir = Path(__file__).resolve().parents[1]
    output_path = tmp_path / "landscape-with-coverage.md"
    from competitive_intel.cli import main

    exit_code = main(
        [
            str(project_dir / "examples/source_notes.json"),
            "--output",
            str(output_path),
            "--title",
            "Sample Analytics Competitor Landscape",
            "--coverage-as-of",
            "2026-07-02",
            "--max-note-age-days",
            "7",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert f"Landscape written to {output_path}" in output
    markdown = output_path.read_text(encoding="utf-8")
    assert "## Research coverage watchlist" in markdown
    assert (
        "- **Acme Analytics · stale-latest-source** — Acme Analytics's latest source "
        "is 12 days old as of 2026-07-02; refresh threshold is 7 days."
        in markdown
    )
    assert (
        "- **Northstar BI · stale-latest-source** — Northstar BI's latest source "
        "is 16 days old as of 2026-07-02; refresh threshold is 7 days."
        in markdown
    )
    assert "No source coverage gaps flagged" not in markdown


def test_example_source_notes_generate_expected_landscape() -> None:
    project_dir = Path(__file__).resolve().parents[1]
    notes = load_source_notes(project_dir / "examples/source_notes.json")

    profiles = build_competitor_profiles(notes)
    markdown = source_collection.render_landscape_markdown(
        profiles,
        title="Sample Analytics Competitor Landscape",
    )

    assert [profile.company for profile in profiles] == [
        "Acme Analytics",
        "Northstar BI",
        "Orion Data Cloud",
    ]
    assert "| Acme Analytics | 2 | 3 | 7 | 0 | 2 | product, delivery, pricing |" in markdown
    assert "| Orion Data Cloud | 2 | 3 | 4 | 3 | 0 | governance, ecosystem, onboarding |" in markdown


def test_build_buyer_fit_scores_ranks_competitors_by_weighted_priorities() -> None:
    project_dir = Path(__file__).resolve().parents[1]
    notes = load_source_notes(project_dir / "examples/source_notes.json")

    scores = source_collection.build_buyer_fit_scores(
        notes,
        priorities={"governance": 2, "support": 2, "delivery": 1},
    )

    assert [score.company for score in scores] == [
        "Orion Data Cloud",
        "Northstar BI",
        "Acme Analytics",
    ]
    orion = scores[0]
    assert orion.fit_score == 8
    assert orion.strength_points == 8
    assert orion.concern_points == 0
    assert orion.matched_themes == ("governance",)
    northstar = scores[1]
    assert northstar.fit_score == 4
    assert northstar.strength_points == 10
    assert northstar.concern_points == 6
    assert northstar.matched_themes == ("support", "governance")


def test_render_buyer_fit_markdown_formats_priority_scorecard() -> None:
    project_dir = Path(__file__).resolve().parents[1]
    notes = load_source_notes(project_dir / "examples/source_notes.json")
    scores = source_collection.build_buyer_fit_scores(
        notes,
        priorities={"governance": 2, "support": 2, "delivery": 1},
    )

    markdown = source_collection.render_buyer_fit_markdown(
        scores,
        title="Healthcare analytics buyer fit",
    )

    assert markdown.startswith("## Healthcare analytics buyer fit\n")
    assert "| Company | Fit score | Strength points | Concern points | Matched themes |" in markdown
    assert "| Orion Data Cloud | 8 | 8 | 0 | governance |" in markdown
    assert "| Northstar BI | 4 | 10 | 6 | support, governance |" in markdown


def test_build_source_coverage_warnings_flags_stale_and_thin_profiles() -> None:
    notes = (
        source_collection.SourceNote(
            id="beacon-single-blog",
            company="Beacon Metrics",
            source_type="blog",
            source="Founder roadmap post",
            published_date="2026-06-01",
            summary="Beacon described a planned analytics governance launch.",
            signals=(
                source_collection.SourceSignal(
                    theme="governance",
                    sentiment="neutral",
                    detail="Roadmap mentions a governed metrics workspace.",
                    confidence=3,
                ),
            ),
        ),
        source_collection.SourceNote(
            id="northstar-review",
            company="Northstar BI",
            source_type="review",
            source="Public implementation review",
            published_date="2026-06-18",
            summary="Northstar customers praised implementation support.",
            signals=(
                source_collection.SourceSignal(
                    theme="support",
                    sentiment="strength",
                    detail="Hands-on enablement reduced rollout risk.",
                    confidence=5,
                ),
            ),
        ),
        source_collection.SourceNote(
            id="northstar-website",
            company="Northstar BI",
            source_type="website",
            source="Partner solutions page",
            published_date="2026-06-16",
            summary="Northstar promotes implementation partners.",
            signals=(
                source_collection.SourceSignal(
                    theme="ecosystem",
                    sentiment="strength",
                    detail="Partner network supports regulated rollouts.",
                    confidence=3,
                ),
            ),
        ),
    )

    warnings = source_collection.build_source_coverage_warnings(
        notes,
        as_of_date="2026-06-20",
        max_note_age_days=10,
        min_note_count=2,
        min_source_types=2,
    )

    assert [(warning.company, warning.issue) for warning in warnings] == [
        ("Beacon Metrics", "low-note-count"),
        ("Beacon Metrics", "single-source"),
        ("Beacon Metrics", "stale-latest-source"),
    ]
    assert "1 note" in warnings[0].detail
    assert "blog" in warnings[1].detail
    assert "19 days old" in warnings[2].detail


def test_render_source_coverage_markdown_lists_watchlist_warnings() -> None:
    warnings = (
        source_collection.SourceCoverageWarning(
            company="Beacon Metrics",
            issue="low-note-count",
            detail="Beacon Metrics has 1 note; target is at least 2.",
        ),
        source_collection.SourceCoverageWarning(
            company="Beacon Metrics",
            issue="stale-latest-source",
            detail="Beacon Metrics's latest source is 19 days old as of 2026-06-20.",
        ),
    )

    markdown = source_collection.render_source_coverage_markdown(warnings)

    assert markdown.startswith("## Research coverage watchlist\n")
    assert "Use these checks before turning the landscape into buying recommendations." in markdown
    assert "- **Beacon Metrics · low-note-count** — Beacon Metrics has 1 note; target is at least 2." in markdown
    assert "- **Beacon Metrics · stale-latest-source** — Beacon Metrics's latest source is 19 days old as of 2026-06-20." in markdown


def test_render_executive_summary_highlights_key_portfolio_findings() -> None:
    project_dir = Path(__file__).resolve().parents[1]
    notes = load_source_notes(project_dir / "examples/source_notes.json")
    profiles = build_competitor_profiles(notes)
    buyer_scores = source_collection.build_buyer_fit_scores(
        notes,
        priorities={"governance": 2, "support": 2, "delivery": 1},
    )
    warnings = source_collection.build_source_coverage_warnings(
        notes,
        as_of_date="2026-07-02",
        max_note_age_days=7,
    )

    markdown = source_collection.render_executive_summary_markdown(
        profiles,
        buyer_fit_scores=buyer_scores,
        coverage_warnings=warnings,
    )

    assert markdown.startswith("## Executive summary\n")
    assert "- Tracked 3 competitors across 6 public notes and 9 extracted signals." in markdown
    assert "- Highest strength signal: Northstar BI with 8 confidence-weighted strength points." in markdown
    assert "- Best buyer-priority fit: Orion Data Cloud with score 8 across governance." in markdown
    assert "- Coverage watchlist: 3 warnings across 3 companies before buyer recommendations." in markdown


def test_render_follow_up_research_markdown_turns_coverage_gaps_into_actions() -> None:
    warnings = (
        source_collection.SourceCoverageWarning(
            company="Beacon Metrics",
            issue="low-note-count",
            detail="Beacon Metrics has 1 note; target is at least 2.",
        ),
        source_collection.SourceCoverageWarning(
            company="Beacon Metrics",
            issue="single-source",
            detail="Beacon Metrics uses 1 source type (blog); target is at least 2.",
        ),
        source_collection.SourceCoverageWarning(
            company="Acme Analytics",
            issue="stale-latest-source",
            detail="Acme Analytics's latest source is 12 days old as of 2026-07-02.",
        ),
    )

    markdown = source_collection.render_follow_up_research_markdown(warnings)

    assert markdown.startswith("## Recommended follow-up research\n")
    assert "Use the watchlist to queue concrete analyst collection tasks." in markdown
    assert (
        "- **Acme Analytics · stale-latest-source** — Refresh the profile with a newer public source. "
        "Acme Analytics's latest source is 12 days old as of 2026-07-02."
        in markdown
    )
    assert (
        "- **Beacon Metrics · low-note-count** — Add more public notes before relying on this profile. "
        "Beacon Metrics has 1 note; target is at least 2."
        in markdown
    )
    assert (
        "- **Beacon Metrics · single-source** — Diversify the source mix with another independent source type. "
        "Beacon Metrics uses 1 source type (blog); target is at least 2."
        in markdown
    )


def test_cli_adds_trend_deltas_and_writes_profile_snapshot(tmp_path: Path, capsys) -> None:
    project_dir = Path(__file__).resolve().parents[1]
    previous_snapshot = tmp_path / "previous_profile_snapshot.json"
    output_path = tmp_path / "landscape-with-trends.md"
    current_snapshot = tmp_path / "current_profile_snapshot.json"
    previous_snapshot.write_text(
        json.dumps(
            {
                "as_of_date": "2026-06-18",
                "profiles": [
                    {
                        "company": "Acme Analytics",
                        "note_count": 1,
                        "signal_count": 2,
                        "strength_score": 4,
                        "gap_score": 0,
                        "risk_score": 2,
                        "latest_source_date": "2026-06-18",
                        "source_types": ["webinar"],
                        "top_themes": ["product", "pricing"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    from competitive_intel.cli import main

    exit_code = main(
        [
            str(project_dir / "examples/source_notes.json"),
            "--output",
            str(output_path),
            "--title",
            "Sample Analytics Competitor Landscape",
            "--previous-profile-snapshot",
            str(previous_snapshot),
            "--profile-snapshot-output",
            str(current_snapshot),
            "--snapshot-as-of",
            "2026-07-02",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert f"Landscape written to {output_path}" in output
    assert f"Profile snapshot written to {current_snapshot}" in output
    markdown = output_path.read_text(encoding="utf-8")
    assert "## Landscape trend deltas" in markdown
    assert "| Acme Analytics | changed | +1 | +1 | +3 | 0 | 0 | + delivery |" in markdown
    assert "| Orion Data Cloud | new | +2 | +3 | +4 | +3 | 0 | + governance, ecosystem, onboarding |" in markdown
    current_profiles = source_collection.load_profile_snapshot(current_snapshot)
    assert [profile.company for profile in current_profiles] == [
        "Acme Analytics",
        "Northstar BI",
        "Orion Data Cloud",
    ]


def test_cli_adds_executive_summary_and_follow_up_research(tmp_path: Path, capsys) -> None:
    project_dir = Path(__file__).resolve().parents[1]
    output_path = tmp_path / "landscape-with-summary.md"
    from competitive_intel.cli import main

    exit_code = main(
        [
            str(project_dir / "examples/source_notes.json"),
            "--output",
            str(output_path),
            "--title",
            "Sample Analytics Competitor Landscape",
            "--priority",
            "governance=2",
            "--priority",
            "support=2",
            "--priority",
            "delivery=1",
            "--coverage-as-of",
            "2026-07-02",
            "--max-note-age-days",
            "7",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert f"Landscape written to {output_path}" in output
    markdown = output_path.read_text(encoding="utf-8")
    assert "## Executive summary" in markdown
    assert "- Best buyer-priority fit: Orion Data Cloud with score 8 across governance." in markdown
    assert "## Recommended follow-up research" in markdown
    assert "- **Acme Analytics · stale-latest-source** — Refresh the profile with a newer public source." in markdown


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_write_report_tables_csv_exports_analyst_handoff_tables(tmp_path: Path) -> None:
    project_dir = Path(__file__).resolve().parents[1]
    notes = load_source_notes(project_dir / "examples/source_notes.json")
    profiles = build_competitor_profiles(notes)
    scores = source_collection.build_buyer_fit_scores(
        notes,
        priorities={"governance": 2, "support": 2, "delivery": 1},
    )
    warnings = source_collection.build_source_coverage_warnings(
        notes,
        as_of_date="2026-07-02",
        max_note_age_days=7,
    )
    previous_profiles = source_collection.load_profile_snapshot(
        project_dir / "examples/previous_profile_snapshot.json"
    )
    trend_deltas = source_collection.build_profile_trend_deltas(
        current_profiles=profiles,
        previous_profiles=previous_profiles,
    )

    written_paths = source_collection.write_report_tables_csv(
        tmp_path / "report_tables",
        profiles=profiles,
        buyer_fit_scores=scores,
        coverage_warnings=warnings,
        trend_deltas=trend_deltas,
    )

    assert [path.name for path in written_paths] == [
        "profile_summary.csv",
        "buyer_fit_scorecard.csv",
        "trend_deltas.csv",
        "coverage_watchlist.csv",
    ]
    profile_rows = _read_csv_rows(tmp_path / "report_tables/profile_summary.csv")
    assert profile_rows[0] == {
        "company": "Acme Analytics",
        "note_count": "2",
        "signal_count": "3",
        "strength_score": "7",
        "gap_score": "0",
        "risk_score": "2",
        "latest_source_date": "2026-06-20",
        "top_themes": "product; delivery; pricing",
        "source_types": "press release; webinar",
    }
    buyer_fit_rows = _read_csv_rows(tmp_path / "report_tables/buyer_fit_scorecard.csv")
    assert buyer_fit_rows[0] == {
        "company": "Orion Data Cloud",
        "fit_score": "8",
        "strength_points": "8",
        "concern_points": "0",
        "matched_themes": "governance",
    }
    trend_rows = _read_csv_rows(tmp_path / "report_tables/trend_deltas.csv")
    assert trend_rows[0]["company"] == "Acme Analytics"
    assert trend_rows[0]["note_delta"] == "1"
    assert trend_rows[0]["added_themes"] == "delivery"
    coverage_rows = _read_csv_rows(tmp_path / "report_tables/coverage_watchlist.csv")
    assert coverage_rows[0] == {
        "company": "Acme Analytics",
        "issue": "stale-latest-source",
        "detail": "Acme Analytics's latest source is 12 days old as of 2026-07-02; refresh threshold is 7 days.",
    }


def test_cli_writes_csv_report_tables_for_analyst_handoff(tmp_path: Path, capsys) -> None:
    project_dir = Path(__file__).resolve().parents[1]
    output_path = tmp_path / "landscape.md"
    csv_dir = tmp_path / "report_tables"
    from competitive_intel.cli import main

    exit_code = main(
        [
            str(project_dir / "examples/source_notes.json"),
            "--output",
            str(output_path),
            "--title",
            "Sample Analytics Competitor Landscape",
            "--priority",
            "governance=2",
            "--priority",
            "support=2",
            "--priority",
            "delivery=1",
            "--coverage-as-of",
            "2026-07-02",
            "--max-note-age-days",
            "7",
            "--previous-profile-snapshot",
            str(project_dir / "examples/previous_profile_snapshot.json"),
            "--csv-output-dir",
            str(csv_dir),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert f"Landscape written to {output_path}" in output
    assert f"CSV tables written to {csv_dir}" in output
    assert (csv_dir / "profile_summary.csv").exists()
    assert (csv_dir / "buyer_fit_scorecard.csv").exists()
    assert (csv_dir / "trend_deltas.csv").exists()
    assert (csv_dir / "coverage_watchlist.csv").exists()
    assert _read_csv_rows(csv_dir / "buyer_fit_scorecard.csv")[0]["company"] == "Orion Data Cloud"
