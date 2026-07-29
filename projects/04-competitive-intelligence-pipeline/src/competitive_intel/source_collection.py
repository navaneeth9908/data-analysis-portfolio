"""Competitive intelligence source collection utilities."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
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


@dataclass(frozen=True)
class BuyerFitScore:
    """Buyer-specific competitor score from weighted source-note priorities."""

    company: str
    fit_score: int
    strength_points: int
    concern_points: int
    matched_themes: tuple[str, ...]


@dataclass(frozen=True)
class SourceCoverageWarning:
    """Research coverage gap for a competitor profile."""

    company: str
    issue: str
    detail: str


@dataclass(frozen=True)
class ProfileTrendDelta:
    """Signed change between a previous and current competitor profile snapshot."""

    company: str
    status: str
    note_delta: int
    signal_delta: int
    strength_delta: int
    gap_delta: int
    risk_delta: int
    added_themes: tuple[str, ...]
    removed_themes: tuple[str, ...]


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


def build_profile_trend_deltas(
    *,
    current_profiles: tuple[CompetitorProfile, ...],
    previous_profiles: tuple[CompetitorProfile, ...],
) -> tuple[ProfileTrendDelta, ...]:
    """Compare previous and current profile snapshots with signed metric deltas."""
    current_by_company = {profile.company: profile for profile in current_profiles}
    previous_by_company = {profile.company: profile for profile in previous_profiles}

    deltas: list[ProfileTrendDelta] = []
    for company in sorted(set(current_by_company) | set(previous_by_company)):
        current = current_by_company.get(company)
        previous = previous_by_company.get(company)

        if previous is None and current is not None:
            status = "new"
        elif current is None and previous is not None:
            status = "removed"
        else:
            status = "changed"

        note_delta = (current.note_count if current else 0) - (previous.note_count if previous else 0)
        signal_delta = (current.signal_count if current else 0) - (
            previous.signal_count if previous else 0
        )
        strength_delta = (current.strength_score if current else 0) - (
            previous.strength_score if previous else 0
        )
        gap_delta = (current.gap_score if current else 0) - (previous.gap_score if previous else 0)
        risk_delta = (current.risk_score if current else 0) - (
            previous.risk_score if previous else 0
        )
        current_themes = current.top_themes if current else ()
        previous_themes = previous.top_themes if previous else ()
        added_themes = tuple(theme for theme in current_themes if theme not in previous_themes)
        removed_themes = tuple(theme for theme in previous_themes if theme not in current_themes)

        if status == "changed" and not any(
            (
                note_delta,
                signal_delta,
                strength_delta,
                gap_delta,
                risk_delta,
                added_themes,
                removed_themes,
            )
        ):
            status = "unchanged"

        deltas.append(
            ProfileTrendDelta(
                company=company,
                status=status,
                note_delta=note_delta,
                signal_delta=signal_delta,
                strength_delta=strength_delta,
                gap_delta=gap_delta,
                risk_delta=risk_delta,
                added_themes=added_themes,
                removed_themes=removed_themes,
            )
        )
    return tuple(deltas)


def _profile_to_dict(profile: CompetitorProfile) -> dict[str, object]:
    return {
        "company": profile.company,
        "note_count": profile.note_count,
        "signal_count": profile.signal_count,
        "strength_score": profile.strength_score,
        "gap_score": profile.gap_score,
        "risk_score": profile.risk_score,
        "latest_source_date": profile.latest_source_date,
        "source_types": list(profile.source_types),
        "top_themes": list(profile.top_themes),
    }


def write_profile_snapshot(
    profiles: tuple[CompetitorProfile, ...],
    path: Path,
    *,
    as_of_date: str | None = None,
) -> None:
    """Write aggregated competitor profiles as a reusable JSON snapshot."""
    payload: dict[str, object] = {
        "profiles": [_profile_to_dict(profile) for profile in profiles]
    }
    if as_of_date:
        payload["as_of_date"] = as_of_date
    snapshot_path = Path(path)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _read_int_field(raw_profile: dict[str, object], field_name: str) -> int:
    value = raw_profile.get(field_name)
    if not isinstance(value, int):
        raise ValueError(f"profile {field_name} must be an integer")
    return value


def _read_string_tuple(raw_profile: dict[str, object], field_name: str) -> tuple[str, ...]:
    raw_values = raw_profile.get(field_name, [])
    if not isinstance(raw_values, list):
        raise ValueError(f"profile {field_name} must be a list")
    return tuple(_clean_text(value, f"profile {field_name}") for value in raw_values)


def load_profile_snapshot(path: Path) -> tuple[CompetitorProfile, ...]:
    """Load profile metrics from a previous JSON snapshot."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    raw_profiles = payload.get("profiles", [])
    if not isinstance(raw_profiles, list):
        raise ValueError("profile snapshot must contain a profiles list")

    profiles: list[CompetitorProfile] = []
    for raw_profile in raw_profiles:
        if not isinstance(raw_profile, dict):
            raise ValueError("each profile snapshot row must be an object")
        profiles.append(
            CompetitorProfile(
                company=_clean_text(raw_profile.get("company"), "profile company"),
                note_count=_read_int_field(raw_profile, "note_count"),
                signal_count=_read_int_field(raw_profile, "signal_count"),
                strength_score=_read_int_field(raw_profile, "strength_score"),
                gap_score=_read_int_field(raw_profile, "gap_score"),
                risk_score=_read_int_field(raw_profile, "risk_score"),
                latest_source_date=_clean_text(
                    raw_profile.get("latest_source_date"), "profile latest_source_date"
                ),
                source_types=_read_string_tuple(raw_profile, "source_types"),
                top_themes=_read_string_tuple(raw_profile, "top_themes"),
            )
        )
    return tuple(sorted(profiles, key=lambda profile: profile.company))


def build_buyer_fit_scores(
    notes: tuple[SourceNote, ...],
    priorities: dict[str, int],
) -> tuple[BuyerFitScore, ...]:
    """Rank competitors against buyer-specific weighted priority themes."""
    normalized_priorities: dict[str, int] = {}
    for theme, weight in priorities.items():
        normalized_theme = _normalize_key(theme, "priority theme")
        if not isinstance(weight, int) or weight <= 0:
            raise ValueError(f"priority weight for {normalized_theme} must be a positive integer")
        normalized_priorities[normalized_theme] = weight
    if not normalized_priorities:
        raise ValueError("at least one buyer priority is required")

    grouped: dict[str, list[SourceNote]] = defaultdict(list)
    for note in notes:
        grouped[note.company].append(note)

    scores: list[BuyerFitScore] = []
    for company, company_notes in grouped.items():
        strength_points = 0
        concern_points = 0
        theme_points: dict[str, int] = defaultdict(int)
        for note in company_notes:
            for signal in note.signals:
                if signal.theme not in normalized_priorities:
                    continue
                weighted_points = signal.confidence * normalized_priorities[signal.theme]
                theme_points[signal.theme] += weighted_points
                if signal.sentiment == "strength":
                    strength_points += weighted_points
                elif signal.sentiment in {"gap", "risk"}:
                    concern_points += weighted_points
        matched_themes = tuple(
            theme
            for theme, _points in sorted(
                theme_points.items(), key=lambda item: (-item[1], item[0])
            )
        )
        scores.append(
            BuyerFitScore(
                company=company,
                fit_score=strength_points - concern_points,
                strength_points=strength_points,
                concern_points=concern_points,
                matched_themes=matched_themes,
            )
        )
    return tuple(
        sorted(
            scores,
            key=lambda score: (
                -score.fit_score,
                -score.strength_points,
                score.concern_points,
                score.company,
            ),
        )
    )


def build_source_coverage_warnings(
    notes: tuple[SourceNote, ...],
    *,
    as_of_date: str,
    max_note_age_days: int = 30,
    min_note_count: int = 2,
    min_source_types: int = 2,
) -> tuple[SourceCoverageWarning, ...]:
    """Flag competitor profiles that need more recent or diverse source coverage."""
    as_of = date.fromisoformat(as_of_date)
    grouped: dict[str, list[SourceNote]] = defaultdict(list)
    for note in notes:
        grouped[note.company].append(note)

    warnings: list[SourceCoverageWarning] = []
    for company in sorted(grouped):
        company_notes = grouped[company]
        source_types = tuple(sorted({note.source_type for note in company_notes}))
        latest_source_date = max(date.fromisoformat(note.published_date) for note in company_notes)
        note_count = len(company_notes)
        if note_count < min_note_count:
            noun = "note" if note_count == 1 else "notes"
            warnings.append(
                SourceCoverageWarning(
                    company=company,
                    issue="low-note-count",
                    detail=(
                        f"{company} has {note_count} {noun}; target is at least "
                        f"{min_note_count}."
                    ),
                )
            )
        if len(source_types) < min_source_types:
            warnings.append(
                SourceCoverageWarning(
                    company=company,
                    issue="single-source",
                    detail=(
                        f"{company} uses {len(source_types)} source type "
                        f"({', '.join(source_types)}); target is at least "
                        f"{min_source_types}."
                    ),
                )
            )
        source_age_days = (as_of - latest_source_date).days
        if source_age_days > max_note_age_days:
            warnings.append(
                SourceCoverageWarning(
                    company=company,
                    issue="stale-latest-source",
                    detail=(
                        f"{company}'s latest source is {source_age_days} days old "
                        f"as of {as_of_date}; refresh threshold is {max_note_age_days} days."
                    ),
                )
            )
    return tuple(warnings)


def render_buyer_fit_markdown(
    scores: tuple[BuyerFitScore, ...],
    *,
    title: str = "Buyer-fit priority scorecard",
) -> str:
    """Render buyer-specific weighted scores as a Markdown table."""
    lines = [
        f"## {title}",
        "",
        "Strength signals add points; gap and risk signals subtract concern points.",
        "",
        "| Company | Fit score | Strength points | Concern points | Matched themes |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for score in scores:
        themes = ", ".join(score.matched_themes) if score.matched_themes else "None"
        lines.append(
            "| "
            f"{score.company} | {score.fit_score} | {score.strength_points} | "
            f"{score.concern_points} | {themes} |"
        )
    return "\n".join(lines) + "\n"


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


def _format_signed_delta(value: int) -> str:
    if value > 0:
        return f"+{value}"
    return str(value)


def _format_theme_changes(delta: ProfileTrendDelta) -> str:
    changes: list[str] = []
    if delta.added_themes:
        changes.append(f"+ {', '.join(delta.added_themes)}")
    if delta.removed_themes:
        changes.append(f"- {', '.join(delta.removed_themes)}")
    return "; ".join(changes) if changes else "None"


def render_profile_trends_markdown(
    deltas: tuple[ProfileTrendDelta, ...],
    *,
    title: str = "Landscape trend deltas",
) -> str:
    """Render signed changes between previous and current profile snapshots."""
    lines = [
        f"## {title}",
        "",
        "Positive values show growth versus the previous profile snapshot.",
        "",
        "| Company | Status | Notes Δ | Signals Δ | Strength Δ | Gap Δ | Risk Δ | Theme changes |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for delta in deltas:
        lines.append(
            "| "
            f"{delta.company} | {delta.status} | {_format_signed_delta(delta.note_delta)} | "
            f"{_format_signed_delta(delta.signal_delta)} | "
            f"{_format_signed_delta(delta.strength_delta)} | "
            f"{_format_signed_delta(delta.gap_delta)} | "
            f"{_format_signed_delta(delta.risk_delta)} | {_format_theme_changes(delta)} |"
        )
    return "\n".join(lines) + "\n"


def render_executive_summary_markdown(
    profiles: tuple[CompetitorProfile, ...],
    *,
    buyer_fit_scores: tuple[BuyerFitScore, ...] = (),
    coverage_warnings: tuple[SourceCoverageWarning, ...] = (),
) -> str:
    """Render a concise decision-ready summary of the landscape."""
    lines = ["## Executive summary", ""]
    if not profiles:
        lines.append("- No competitor profiles are available yet.")
        return "\n".join(lines) + "\n"

    competitor_count = len(profiles)
    note_count = sum(profile.note_count for profile in profiles)
    signal_count = sum(profile.signal_count for profile in profiles)
    strongest_profile = sorted(
        profiles,
        key=lambda profile: (-profile.strength_score, profile.company),
    )[0]
    lines.append(
        f"- Tracked {competitor_count} competitors across {note_count} public notes "
        f"and {signal_count} extracted signals."
    )
    lines.append(
        f"- Highest strength signal: {strongest_profile.company} with "
        f"{strongest_profile.strength_score} confidence-weighted strength points."
    )

    if buyer_fit_scores:
        best_fit = buyer_fit_scores[0]
        matched_themes = ", ".join(best_fit.matched_themes) or "no matched priority themes"
        lines.append(
            f"- Best buyer-priority fit: {best_fit.company} with score "
            f"{best_fit.fit_score} across {matched_themes}."
        )

    if coverage_warnings:
        warning_companies = {warning.company for warning in coverage_warnings}
        lines.append(
            f"- Coverage watchlist: {len(coverage_warnings)} warnings across "
            f"{len(warning_companies)} companies before buyer recommendations."
        )
    else:
        lines.append("- Coverage watchlist: no source coverage gaps flagged.")
    return "\n".join(lines) + "\n"


def _follow_up_action(issue: str) -> str:
    actions = {
        "low-note-count": "Add more public notes before relying on this profile.",
        "single-source": "Diversify the source mix with another independent source type.",
        "stale-latest-source": "Refresh the profile with a newer public source.",
    }
    return actions.get(issue, "Investigate this coverage gap before publishing recommendations.")


def render_follow_up_research_markdown(
    warnings: tuple[SourceCoverageWarning, ...],
    *,
    title: str = "Recommended follow-up research",
) -> str:
    """Turn source coverage warnings into analyst collection tasks."""
    lines = [
        f"## {title}",
        "",
        "Use the watchlist to queue concrete analyst collection tasks.",
        "",
    ]
    if not warnings:
        lines.append("No immediate research follow-ups are required with the current thresholds.")
        return "\n".join(lines) + "\n"

    for warning in sorted(warnings, key=lambda item: (item.company, item.issue)):
        lines.append(
            f"- **{warning.company} · {warning.issue}** — "
            f"{_follow_up_action(warning.issue)} {warning.detail}"
        )
    return "\n".join(lines) + "\n"


def render_source_evidence_markdown(
    notes: tuple[SourceNote, ...],
    *,
    title: str = "Evidence highlights",
    max_notes_per_company: int = 2,
) -> str:
    """Render source-backed evidence snippets grouped by competitor."""
    if max_notes_per_company <= 0:
        raise ValueError("max_notes_per_company must be positive")

    grouped: dict[str, list[SourceNote]] = defaultdict(list)
    for note in notes:
        grouped[note.company].append(note)

    lines = [
        f"## {title}",
        "",
        "Source-backed snippets show why each competitor earned its score.",
        "",
    ]
    for company in sorted(grouped):
        lines.append(f"### {company}")
        company_notes = sorted(
            grouped[company],
            key=lambda note: (note.published_date, note.id),
            reverse=True,
        )
        for note in company_notes[:max_notes_per_company]:
            lines.append(
                f"- **{note.published_date} · {note.source_type} · {note.source}** — "
                f"{note.summary}"
            )
            for signal in note.signals:
                lines.append(
                    f"  - {signal.theme} / {signal.sentiment} / confidence "
                    f"{signal.confidence}: {signal.detail}"
                )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_source_coverage_markdown(
    warnings: tuple[SourceCoverageWarning, ...],
    *,
    title: str = "Research coverage watchlist",
) -> str:
    """Render coverage warnings that guide follow-up competitor research."""
    lines = [
        f"## {title}",
        "",
        "Use these checks before turning the landscape into buying recommendations.",
        "",
    ]
    if not warnings:
        lines.append("No source coverage gaps flagged with the current thresholds.")
    for warning in warnings:
        lines.append(f"- **{warning.company} · {warning.issue}** — {warning.detail}")
    return "\n".join(lines) + "\n"


def _join_csv_values(values: tuple[str, ...]) -> str:
    return "; ".join(values)


def _write_csv_table(
    output_dir: Path,
    filename: str,
    fieldnames: tuple[str, ...],
    rows: list[dict[str, object]],
) -> Path:
    path = output_dir / filename
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_report_tables_csv(
    output_dir: Path,
    *,
    profiles: tuple[CompetitorProfile, ...],
    buyer_fit_scores: tuple[BuyerFitScore, ...] = (),
    coverage_warnings: tuple[SourceCoverageWarning, ...] = (),
    trend_deltas: tuple[ProfileTrendDelta, ...] = (),
) -> tuple[Path, ...]:
    """Write analyst-handoff CSV tables from the rendered landscape inputs."""
    csv_dir = Path(output_dir)
    csv_dir.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []

    written_paths.append(
        _write_csv_table(
            csv_dir,
            "profile_summary.csv",
            (
                "company",
                "note_count",
                "signal_count",
                "strength_score",
                "gap_score",
                "risk_score",
                "latest_source_date",
                "top_themes",
                "source_types",
            ),
            [
                {
                    "company": profile.company,
                    "note_count": profile.note_count,
                    "signal_count": profile.signal_count,
                    "strength_score": profile.strength_score,
                    "gap_score": profile.gap_score,
                    "risk_score": profile.risk_score,
                    "latest_source_date": profile.latest_source_date,
                    "top_themes": _join_csv_values(profile.top_themes),
                    "source_types": _join_csv_values(profile.source_types),
                }
                for profile in profiles
            ],
        )
    )

    if buyer_fit_scores:
        written_paths.append(
            _write_csv_table(
                csv_dir,
                "buyer_fit_scorecard.csv",
                (
                    "company",
                    "fit_score",
                    "strength_points",
                    "concern_points",
                    "matched_themes",
                ),
                [
                    {
                        "company": score.company,
                        "fit_score": score.fit_score,
                        "strength_points": score.strength_points,
                        "concern_points": score.concern_points,
                        "matched_themes": _join_csv_values(score.matched_themes),
                    }
                    for score in buyer_fit_scores
                ],
            )
        )

    if trend_deltas:
        written_paths.append(
            _write_csv_table(
                csv_dir,
                "trend_deltas.csv",
                (
                    "company",
                    "status",
                    "note_delta",
                    "signal_delta",
                    "strength_delta",
                    "gap_delta",
                    "risk_delta",
                    "added_themes",
                    "removed_themes",
                ),
                [
                    {
                        "company": delta.company,
                        "status": delta.status,
                        "note_delta": delta.note_delta,
                        "signal_delta": delta.signal_delta,
                        "strength_delta": delta.strength_delta,
                        "gap_delta": delta.gap_delta,
                        "risk_delta": delta.risk_delta,
                        "added_themes": _join_csv_values(delta.added_themes),
                        "removed_themes": _join_csv_values(delta.removed_themes),
                    }
                    for delta in trend_deltas
                ],
            )
        )

    if coverage_warnings:
        written_paths.append(
            _write_csv_table(
                csv_dir,
                "coverage_watchlist.csv",
                ("company", "issue", "detail"),
                [
                    {
                        "company": warning.company,
                        "issue": warning.issue,
                        "detail": warning.detail,
                    }
                    for warning in coverage_warnings
                ],
            )
        )

    return tuple(written_paths)
