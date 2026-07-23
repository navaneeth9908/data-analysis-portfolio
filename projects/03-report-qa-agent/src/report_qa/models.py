"""Shared data models for the report Q&A workflow."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentChunk:
    """A citation-ready slice of a source report."""

    source: str
    heading: str
    text: str
    start_line: int
    end_line: int

    @property
    def citation_label(self) -> str:
        """Return a compact source label suitable for portfolio demos."""
        return f"{self.source}#{self.heading}:L{self.start_line}-L{self.end_line}"


@dataclass(frozen=True)
class SearchHit:
    """A scored retrieval result."""

    chunk: DocumentChunk
    score: float
    matched_terms: tuple[str, ...]


@dataclass(frozen=True)
class Citation:
    """A cited source span used by the answer layer."""

    source: str
    heading: str
    start_line: int
    end_line: int

    @property
    def label(self) -> str:
        """Return the human-readable citation label."""
        return f"{self.source}#{self.heading}:L{self.start_line}-L{self.end_line}"


@dataclass(frozen=True)
class Answer:
    """Deterministic answer with supporting citations."""

    question: str
    answer: str
    citations: tuple[Citation, ...]
    hits: tuple[SearchHit, ...]
