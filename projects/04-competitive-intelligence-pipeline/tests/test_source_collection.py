"""Behavior tests for the competitive intelligence source pipeline."""

from __future__ import annotations

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
