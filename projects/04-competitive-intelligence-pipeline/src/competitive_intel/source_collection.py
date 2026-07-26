"""Competitive intelligence source collection utilities."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceSignal:
    """A normalized strategic signal extracted from a public source note."""

    theme: str
    sentiment: str
    detail: str
    confidence: int


@dataclass(frozen=True)
class SourceNote:
    """A public-source observation about one competitor."""

    id: str
    company: str
    source_type: str
    source: str
    published_date: str
    summary: str
    signals: tuple[SourceSignal, ...]


@dataclass(frozen=True)
class CompetitorProfile:
    """Aggregated public-source view of one competitor."""

    company: str
    note_count: int
    signal_count: int
    strength_score: int
    gap_score: int
    risk_score: int
    latest_source_date: str
    source_types: tuple[str, ...]
    top_themes: tuple[str, ...]


def _clean_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return " ".join(value.strip().split())


def _normalize_key(value: object, field_name: str) -> str:
    return _clean_text(value, field_name).lower()


def _load_signal(raw_signal: dict[str, object], note_id: str) -> SourceSignal:
    confidence = raw_signal.get("confidence")
    if not isinstance(confidence, int) or not 1 <= confidence <= 5:
        raise ValueError(f"signal confidence for {note_id} must be an integer from 1 to 5")
    return SourceSignal(
        theme=_normalize_key(raw_signal.get("theme"), f"signal theme for {note_id}"),
        sentiment=_normalize_key(
            raw_signal.get("sentiment"), f"signal sentiment for {note_id}"
        ),
        detail=_clean_text(raw_signal.get("detail"), f"signal detail for {note_id}"),
        confidence=confidence,
    )


def load_source_notes(path: Path) -> tuple[SourceNote, ...]:
    """Load and normalize competitive source notes from a JSON file."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    raw_notes = payload.get("notes", [])
    if not isinstance(raw_notes, list):
        raise ValueError("source note file must contain a notes list")

    notes: list[SourceNote] = []
    for raw_note in raw_notes:
        if not isinstance(raw_note, dict):
            raise ValueError("each source note must be an object")
        note_id = _clean_text(raw_note.get("id"), "note id")
        raw_signals = raw_note.get("signals", [])
        if not isinstance(raw_signals, list) or not raw_signals:
            raise ValueError(f"source note {note_id} must include at least one signal")
        notes.append(
            SourceNote(
                id=note_id,
                company=_clean_text(raw_note.get("company"), f"company for {note_id}"),
                source_type=_normalize_key(
                    raw_note.get("source_type"), f"source_type for {note_id}"
                ),
                source=_clean_text(raw_note.get("source"), f"source for {note_id}"),
                published_date=_clean_text(
                    raw_note.get("published_date"), f"published_date for {note_id}"
                ),
                summary=_clean_text(raw_note.get("summary"), f"summary for {note_id}"),
                signals=tuple(_load_signal(signal, note_id) for signal in raw_signals),
            )
        )
    return tuple(notes)


def build_competitor_profiles(notes: tuple[SourceNote, ...]) -> tuple[CompetitorProfile, ...]:
    """Aggregate source notes into competitor profiles."""
    grouped: dict[str, list[SourceNote]] = defaultdict(list)
    for note in notes:
        grouped[note.company].append(note)

    profiles: list[CompetitorProfile] = []
    for company, company_notes in grouped.items():
        sentiment_scores = {"strength": 0, "gap": 0, "risk": 0}
        theme_scores: dict[str, int] = defaultdict(int)
        signal_count = 0
        source_types: set[str] = set()
        latest_source_date = ""

        for note in company_notes:
            source_types.add(note.source_type)
            latest_source_date = max(latest_source_date, note.published_date)
            for signal in note.signals:
                signal_count += 1
                theme_scores[signal.theme] += signal.confidence
                if signal.sentiment in sentiment_scores:
                    sentiment_scores[signal.sentiment] += signal.confidence

        top_themes = tuple(
            theme
            for theme, _score in sorted(
                theme_scores.items(), key=lambda item: (-item[1], item[0])
            )
        )
        profiles.append(
            CompetitorProfile(
                company=company,
                note_count=len(company_notes),
                signal_count=signal_count,
                strength_score=sentiment_scores["strength"],
                gap_score=sentiment_scores["gap"],
                risk_score=sentiment_scores["risk"],
                latest_source_date=latest_source_date,
                source_types=tuple(sorted(source_types)),
                top_themes=top_themes,
            )
        )
    return tuple(sorted(profiles, key=lambda profile: profile.company))


def render_landscape_markdown(
    profiles: tuple[CompetitorProfile, ...],
    *,
    title: str = "Competitive Intelligence Landscape",
) -> str:
    """Render competitor profiles as a concise Markdown landscape table."""
    lines = [
        f"# {title}",
        "",
        "Scores are confidence-weighted rollups from public-source notes.",
        "",
        "| Company | Notes | Signals | Strength | Gap | Risk | Top themes | Sources |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for profile in profiles:
        lines.append(
            "| "
            f"{profile.company} | {profile.note_count} | {profile.signal_count} | "
            f"{profile.strength_score} | {profile.gap_score} | {profile.risk_score} | "
            f"{', '.join(profile.top_themes)} | {', '.join(profile.source_types)} |"
        )
    return "\n".join(lines) + "\n"
