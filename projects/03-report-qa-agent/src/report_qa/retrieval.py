"""Deterministic keyword retrieval for offline report Q&A demos."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence

from .models import DocumentChunk, SearchHit

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9']+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "because",
    "by",
    "did",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "was",
    "were",
    "what",
    "which",
    "why",
    "with",
}


def tokenize(text: str) -> tuple[str, ...]:
    """Normalize text into simple retrieval tokens."""
    tokens = []
    for token in _TOKEN_RE.findall(text.lower()):
        if token in _STOPWORDS:
            continue
        tokens.append(_stem(token))
    return tuple(tokens)


def search_chunks(
    chunks: Sequence[DocumentChunk],
    question: str,
    top_k: int = 3,
) -> list[SearchHit]:
    """Rank chunks by overlap with the question terms.

    This intentionally stays offline and deterministic. It is not meant to beat
    embeddings; it provides a transparent fallback that is easy to test and
    explain in interviews.
    """
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    question_terms = tuple(dict.fromkeys(tokenize(question)))
    if not question_terms:
        return []

    hits: list[SearchHit] = []
    for chunk in chunks:
        body_counts = Counter(tokenize(chunk.text))
        heading_terms = set(tokenize(chunk.heading))
        matched_terms = tuple(
            term for term in question_terms if body_counts[term] or term in heading_terms
        )
        if not matched_terms:
            continue

        score = sum(body_counts[term] for term in matched_terms)
        score += sum(1.5 for term in matched_terms if term in heading_terms)
        score += min(len(matched_terms) * 0.25, 1.0)
        hits.append(SearchHit(chunk=chunk, score=score, matched_terms=matched_terms))

    return sorted(
        hits,
        key=lambda hit: (-hit.score, hit.chunk.source, hit.chunk.start_line, hit.chunk.heading),
    )[:top_k]


def _stem(token: str) -> str:
    """Apply light stemming for plural business terms."""
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token
