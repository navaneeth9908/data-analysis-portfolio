"""Document ingestion and citation-preserving chunking for local reports."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .models import DocumentChunk

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_PDF_STREAM_RE = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.DOTALL)
_PDF_TEXT_COMMAND_RE = re.compile(
    r"\((?P<tj>(?:\\.|[^\\)])*)\)\s*Tj|\[(?P<array>.*?)\]\s*TJ",
    re.DOTALL,
)
_PDF_STRING_RE = re.compile(r"\((?:\\.|[^\\)])*\)")


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
    return _load_text_like_chunks(
        source=report_path.name,
        default_heading=_default_heading(report_path),
        lines=lines,
        max_chars=max_chars,
    )


def load_pdf_chunks(path: str | Path, max_chars: int = 900) -> list[DocumentChunk]:
    """Load an uncompressed text-layer PDF report into citation-ready chunks.

    This lightweight adapter is intentionally dependency-free for offline demos.
    It supports simple report exports with extractable text commands; scanned or
    compressed PDFs should be converted to text first or handled by a heavier PDF
    extraction dependency in a production system.
    """
    if max_chars < 120:
        raise ValueError("max_chars must be at least 120 so chunks keep useful context")

    report_path = Path(path)
    lines = _extract_pdf_text_lines(report_path)
    if not any(line.strip() for line in lines):
        raise ValueError(f"no extractable text layer found in {report_path.name}")
    return _load_text_like_chunks(
        source=report_path.name,
        default_heading=_default_heading(report_path),
        lines=lines,
        max_chars=max_chars,
    )


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
    if suffix == ".pdf":
        return load_pdf_chunks(report_path, max_chars=max_chars)
    raise ValueError(f"unsupported report format: {report_path.suffix or '(no suffix)'}")


def load_many_documents(paths: Iterable[str | Path], max_chars: int = 900) -> list[DocumentChunk]:
    """Load supported report files in deterministic path order."""
    chunks: list[DocumentChunk] = []
    for path in sorted(Path(p) for p in paths):
        chunks.extend(load_document_chunks(path, max_chars=max_chars))
    return chunks


def _load_text_like_chunks(
    *,
    source: str,
    default_heading: str,
    lines: list[str],
    max_chars: int,
) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    heading = default_heading
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
                source=source,
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


def _extract_pdf_text_lines(path: Path) -> list[str]:
    raw = path.read_bytes()
    lines: list[str] = []
    for stream_match in _PDF_STREAM_RE.finditer(raw):
        stream_header = raw[max(0, stream_match.start() - 300) : stream_match.start()]
        if b"/FlateDecode" in stream_header:
            continue
        stream_text = stream_match.group(1).decode("latin-1", errors="ignore")
        for text_match in _PDF_TEXT_COMMAND_RE.finditer(stream_text):
            if text_match.group("tj") is not None:
                lines.extend(_split_pdf_text_line(_decode_pdf_literal(text_match.group("tj"))))
                continue
            array_payload = text_match.group("array") or ""
            line = "".join(
                _decode_pdf_literal(string_match.group(0)[1:-1])
                for string_match in _PDF_STRING_RE.finditer(array_payload)
            )
            lines.extend(_split_pdf_text_line(line))
    return lines


def _split_pdf_text_line(text: str) -> list[str]:
    return text.splitlines() or [""]


def _decode_pdf_literal(value: str) -> str:
    characters: list[str] = []
    index = 0
    escapes = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f"}
    while index < len(value):
        character = value[index]
        if character != "\\":
            characters.append(character)
            index += 1
            continue

        index += 1
        if index >= len(value):
            break
        escaped = value[index]
        if escaped in escapes:
            characters.append(escapes[escaped])
            index += 1
        elif escaped in "()\\":
            characters.append(escaped)
            index += 1
        elif escaped in "\r\n":
            index += 1
            if escaped == "\r" and index < len(value) and value[index] == "\n":
                index += 1
        elif escaped.isdigit():
            start = index
            while index < len(value) and index - start < 3 and value[index].isdigit():
                index += 1
            characters.append(chr(int(value[start:index], 8)))
        else:
            characters.append(escaped)
            index += 1
    return "".join(characters)


def _default_heading(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").title()


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
