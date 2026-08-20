"""End-to-end behavior tests for the Research Briefing Generator CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def test_cli_writes_a_ranked_source_backed_briefing(tmp_path: Path) -> None:
    source_file = tmp_path / "ai_policy_sources.json"
    source_file.write_text(
        json.dumps(
            {
                "briefing_title": "AI policy weekly briefing",
                "sources": [
                    {
                        "title": "Regulator publishes implementation timetable",
                        "publisher": "National AI Office",
                        "published_on": "2026-08-08",
                        "url": "https://example.com/timetable",
                        "key_point": "The first reporting deadline is scheduled for October.",
                        "follow_up_question": "Which internal teams own the October reporting deadline?",
                        "relevance": 5,
                        "source_quality": 4,
                    },
                    {
                        "title": "Industry group maps compliance costs",
                        "publisher": "Policy Forum",
                        "published_on": "2026-07-20",
                        "url": "https://example.com/costs",
                        "key_point": "Smaller vendors expect the largest documentation burden.",
                        "follow_up_question": "Which vendor contracts need updated documentation clauses?",
                        "relevance": 4,
                        "source_quality": 5,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    output_file = tmp_path / "briefing.md"
    environment = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "research_briefing.cli",
            str(source_file),
            "--as-of",
            "2026-08-10",
            "--output",
            str(output_file),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"Briefing written to {output_file}\n"
    report = output_file.read_text(encoding="utf-8")
    assert "# AI policy weekly briefing" in report
    assert "As of: 2026-08-10" in report
    assert "Sources reviewed: 2" in report
    assert "Publishers covered: 2" in report
    assert "## Source mix" in report
    assert "| National AI Office | 1 |" in report
    assert "| Policy Forum | 1 |" in report
    assert "## Freshness mix" in report
    assert "| Fresh (0-7 days) | 1 |" in report
    assert "| Recent (8-30 days) | 1 |" in report
    assert "## Ranked digest" in report
    assert "1. **Regulator publishes implementation timetable** — National AI Office (2026-08-08)" in report
    assert "Score: 17/18 | Relevance 5/5 | Source quality 4/5 | Freshness 3/3" in report
    assert "2. **Industry group maps compliance costs** — Policy Forum (2026-07-20)" in report
    assert "Score: 15/18 | Relevance 4/5 | Source quality 5/5 | Freshness 2/3" in report
    assert "- The first reporting deadline is scheduled for October." in report
    assert "## Follow-up questions" in report
    assert "- Which internal teams own the October reporting deadline?" in report
    assert "[Read source](https://example.com/timetable)" in report


def test_cli_writes_an_html_briefing_with_ranked_source_evidence(tmp_path: Path) -> None:
    source_file = tmp_path / "source_notes.json"
    source_file.write_text(
        json.dumps(
            {
                "briefing_title": "AI policy weekly briefing",
                "sources": [
                    {
                        "title": "Regulator publishes implementation timetable",
                        "publisher": "National AI Office",
                        "published_on": "2026-08-08",
                        "url": "https://example.com/timetable",
                        "key_point": "The first reporting deadline is scheduled for October.",
                        "follow_up_question": "Which internal teams own the October reporting deadline?",
                        "relevance": 5,
                        "source_quality": 4,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output_file = tmp_path / "briefing.html"
    environment = {**os.environ, "PYTHONPATH": str(Path.cwd() / "src")}

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "research_briefing.cli",
            str(source_file),
            "--as-of",
            "2026-08-10",
            "--format",
            "html",
            "--output",
            str(output_file),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"Briefing written to {output_file}\n"
    report = output_file.read_text(encoding="utf-8")
    assert "<!doctype html>" in report
    assert "<title>AI policy weekly briefing</title>" in report
    assert "<h1>AI policy weekly briefing</h1>" in report
    assert "Sources reviewed: 1" in report
    assert "Publishers covered: 1" in report
    assert "<h2>Source mix</h2>" in report
    assert "<td>National AI Office</td>" in report
    assert "<h2>Freshness mix</h2>" in report
    assert "<td>Fresh (0-7 days)</td>" in report
    assert "Regulator publishes implementation timetable" in report
    assert "17/18" in report
    assert 'href="https://example.com/timetable"' in report
    assert "Which internal teams own the October reporting deadline?" in report
