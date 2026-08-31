"""Focused behavior tests for briefing source-note validation."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from research_briefing.briefing import build_briefing


def test_build_briefing_rejects_sources_published_after_reporting_date(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "future_source.json"
    source_file.write_text(
        json.dumps(
            {
                "briefing_title": "AI policy weekly briefing",
                "sources": [
                    {
                        "title": "Regulator publishes implementation timetable",
                        "publisher": "National AI Office",
                        "published_on": "2026-08-11",
                        "url": "https://example.com/timetable",
                        "key_point": "The first reporting deadline is scheduled for October.",
                        "follow_up_question": "Which internal teams own the October reporting deadline?",
                        "theme": "Compliance operations",
                        "relevance": 5,
                        "source_quality": 4,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="published_on cannot be after the --as-of reporting date",
    ):
        build_briefing(source_file, as_of=date(2026, 8, 10))
