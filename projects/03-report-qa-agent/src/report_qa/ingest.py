"""Document ingestion and citation-preserving chunking for local reports."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .models import DocumentChunk

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def load_markdown_chunks(path: str | Path, max_chars: int = 900) -> list[DocumentChunk]:
    """Load a Markdown report into heading-scoped chunks.

    The chunk line span starts at the Markdown heading line and ends at the last
    non-empty content line in that section. Long sections are split by line
    groups while keeping the original source filename and heading.
    """
    if max_chars < 120:
        raise ValueError("max_chars must be at least 120 so chunks keep useful context")

    report_path = Path(path)
    lines = report_path.read_text(encoding="utf-8").splitlines()
    chunks: list[DocumentChunk] = []
    heading = report_path.stem.replace("_", " ").replace("-", " ").title()
    section_start = 1
    section_lines: list[tuple[int, str]] = []

    def flush_section() -> None:
        nonlocal section_lines
        trimmed = _trim_blank_edges(section_lines)
        if not trimmed:
            section_lines = []
            return
        chunks.extend(
            _split_section(
                source=report_path.name,
                heading=heading,
                heading_line=section_start,
                lines=trimmed,
                max_chars=max_chars,
            )
        )
        section_lines = []

    for line_no, line in enumerate(lines, start=1):
        match = _HEADING_RE.match(line)
        if match:
            flush_section()
            heading = match.group(2).strip()
            section_start = line_no
            section_lines = []
            continue
        section_lines.append((line_no, line))

    flush_section()
    return chunks


def load_text_chunks(path: str | Path, max_chars: int = 900) -> list[DocumentChunk]:
    """Load a plain-text report into citation-ready section chunks.

    Plain-text exports often keep human-readable section labels without Markdown
    markers. A line is treated as a heading when it is short, alphabetic, and
    does not end like a sentence; following lines become the cited chunk body.
    """
    if max_chars < 120:
        raise ValueError("max_chars must be at least 120 so chunks keep useful context")

    report_path = Path(path)
    lines = report_path.read_text(encoding="utf-8").splitlines()
    chunks: list[DocumentChunk] = []
    heading = report_path.stem.replace("_", " ").replace("-", " ").title()
    section_start = 1
    section_lines: list[tuple[int, str]] = []

    def flush_section() -> None:
        nonlocal section_lines
        trimmed = _trim_blank_edges(section_lines)
        if not trimmed:
            section_lines = []
            return
        chunks.extend(
            _split_section(
                source=report_path.name,
                heading=heading,
                heading_line=section_start,
                lines=trimmed,
                max_chars=max_chars,
            )
        )
        section_lines = []

    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if _looks_like_text_heading(stripped):
            flush_section()
            heading = stripped.rstrip(":")
            section_start = line_no
            section_lines = []
            continue
        section_lines.append((line_no, line))

    flush_section()
    return chunks


def load_many_markdown(paths: Iterable[str | Path], max_chars: int = 900) -> list[DocumentChunk]:
    """Load multiple Markdown files in deterministic path order."""
    chunks: list[DocumentChunk] = []
    for path in sorted(Path(p) for p in paths):
        chunks.extend(load_markdown_chunks(path, max_chars=max_chars))
    return chunks


def load_document_chunks(path: str | Path, max_chars: int = 900) -> list[DocumentChunk]:
    """Load a supported report file into citation-ready chunks."""
    report_path = Path(path)
    suffix = report_path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return load_markdown_chunks(report_path, max_chars=max_chars)
    if suffix == ".txt":
        return load_text_chunks(report_path, max_chars=max_chars)
    raise ValueError(f"unsupported report format: {report_path.suffix or '(no suffix)'}")


def load_many_documents(paths: Iterable[str | Path], max_chars: int = 900) -> list[DocumentChunk]:
    """Load supported report files in deterministic path order."""
    chunks: list[DocumentChunk] = []
    for path in sorted(Path(p) for p in paths):
        chunks.extend(load_document_chunks(path, max_chars=max_chars))
    return chunks


def _looks_like_text_heading(line: str) -> bool:
    if not line:
        return False
    if len(line) > 80 or len(line.split()) > 8:
        return False
    if not any(character.isalpha() for character in line):
        return False
    if line.startswith(("-", "*", "•")):
        return False
    return not line.endswith((".", "!", "?", ";"))


def _trim_blank_edges(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    start = 0
    end = len(lines)
    while start < end and not lines[start][1].strip():
        start += 1
    while end > start and not lines[end - 1][1].strip():
        end -= 1
    return lines[start:end]


def _split_section(
    *,
    source: str,
    heading: str,
    heading_line: int,
    lines: list[tuple[int, str]],
    max_chars: int,
) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    current: list[tuple[int, str]] = []
    current_start = heading_line

    for line_no, line in lines:
        candidate = current + [(line_no, line)]
        candidate_text = "\n".join(text for _, text in candidate).strip()
        if current and len(candidate_text) > max_chars:
            chunks.append(_make_chunk(source, heading, current_start, current))
            current = [(line_no, line)]
            current_start = line_no
        else:
            current = candidate

    if current:
        chunks.append(_make_chunk(source, heading, current_start, current))
    return chunks


def _make_chunk(
    source: str,
    heading: str,
    start_line: int,
    lines: list[tuple[int, str]],
) -> DocumentChunk:
    text = "\n".join(line for _, line in lines).strip()
    end_line = max(line_no for line_no, line in lines if line.strip())
    return DocumentChunk(
        source=source,
        heading=heading,
        text=text,
        start_line=start_line,
        end_line=end_line,
    )
