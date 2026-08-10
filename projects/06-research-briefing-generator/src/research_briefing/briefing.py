"""Deterministic, source-backed briefing generation for local JSON source notes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path


@dataclass(frozen=True)
class RankedSource:
    """A validated source note with transparent ranking inputs."""

    title: str
    publisher: str
    published_on: date
    url: str
    key_point: str
    follow_up_question: str
    relevance: int
    source_quality: int
    freshness: int

    @property
    def score(self) -> int:
        """Return the deterministic 18-point source-priority score."""
        return self.relevance * 2 + self.source_quality + self.freshness


@dataclass(frozen=True)
class Briefing:
    """A ranked set of source notes for one briefing topic."""

    title: str
    as_of: date
    sources: tuple[RankedSource, ...]


def build_briefing(path: str | Path, as_of: date) -> Briefing:
    """Load, validate, and rank a JSON source-note file for a fixed reporting date."""
    source_path = Path(path)
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Briefing input must be a JSON object")
    title = _required_text(payload, "briefing_title")
    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ValueError("Briefing input must include at least one source")

    sources = tuple(_rank_source(raw_source, as_of) for raw_source in raw_sources)
    return Briefing(
        title=title,
        as_of=as_of,
        sources=tuple(
            sorted(
                sources,
                key=lambda source: (-source.score, source.title.lower(), source.publisher.lower()),
            )
        ),
    )


def render_markdown_briefing(briefing: Briefing) -> str:
    """Render a stable Markdown briefing with sources, scores, and next questions."""
    lines = [
        f"# {briefing.title}",
        "",
        f"As of: {briefing.as_of.isoformat()}",
        "",
        f"Sources reviewed: {len(briefing.sources)}",
        "",
        "## Ranked digest",
        "",
    ]
    for rank, source in enumerate(briefing.sources, start=1):
        lines.extend(
            [
                (
                    f"{rank}. **{source.title}** — {source.publisher} "
                    f"({source.published_on.isoformat()})"
                ),
                (
                    f"   - Score: {source.score}/18 | Relevance {source.relevance}/5 | "
                    f"Source quality {source.source_quality}/5 | Freshness {source.freshness}/3"
                ),
                f"   - {source.key_point}",
                f"   - Source: [Read source]({source.url})",
                "",
            ]
        )
    lines.extend(["## Follow-up questions", ""])
    lines.extend(f"- {source.follow_up_question}" for source in briefing.sources)
    return "\n".join(lines) + "\n"


def _rank_source(raw_source: object, as_of: date) -> RankedSource:
    """Validate one source object and calculate its recency score."""
    if not isinstance(raw_source, dict):
        raise ValueError("Each source must be a JSON object")
    try:
        published_on = date.fromisoformat(_required_text(raw_source, "published_on"))
    except ValueError as error:
        raise ValueError("published_on must use YYYY-MM-DD format") from error
    relevance = _rating(raw_source, "relevance")
    source_quality = _rating(raw_source, "source_quality")
    return RankedSource(
        title=_required_text(raw_source, "title"),
        publisher=_required_text(raw_source, "publisher"),
        published_on=published_on,
        url=_required_text(raw_source, "url"),
        key_point=_required_text(raw_source, "key_point"),
        follow_up_question=_required_text(raw_source, "follow_up_question"),
        relevance=relevance,
        source_quality=source_quality,
        freshness=_freshness_score(published_on, as_of),
    )


def _required_text(payload: dict[str, object], field: str) -> str:
    """Read a required non-blank string from an input object."""
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-blank string")
    return value.strip()


def _rating(payload: dict[str, object], field: str) -> int:
    """Read an integer rating on the documented one-to-five scale."""
    value = payload.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5:
        raise ValueError(f"{field} must be an integer from 1 to 5")
    return value


def _freshness_score(published_on: date, as_of: date) -> int:
    """Score source age in transparent weekly, monthly, and older bands."""
    age_in_days = (as_of - published_on).days
    if age_in_days <= 7:
        return 3
    if age_in_days <= 30:
        return 2
    return 1
