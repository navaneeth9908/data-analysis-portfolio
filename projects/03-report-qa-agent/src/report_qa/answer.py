"""Extractive answering over retrieved report chunks."""

from __future__ import annotations

import re
from pathlib import Path
from collections.abc import Sequence

from .ingest import load_many_markdown
from .models import Answer, Citation, DocumentChunk, SearchHit
from .retrieval import search_chunks, tokenize

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def answer_question(
    question: str,
    paths: Sequence[str | Path],
    *,
    top_k: int = 3,
    max_chars: int = 900,
) -> Answer:
    """Answer a question using deterministic retrieval and source citations."""
    chunks = load_many_markdown(paths, max_chars=max_chars)
    hits = tuple(search_chunks(chunks, question, top_k=top_k))
    if not hits:
        return Answer(
            question=question,
            answer="I could not find enough evidence in the provided reports to answer that question.",
            citations=(),
            hits=(),
        )

    best_hit = hits[0]
    best_sentence = _best_sentence(question, best_hit)
    citation = _citation_for(best_hit.chunk)
    return Answer(
        question=question,
        answer=best_sentence,
        citations=(citation,),
        hits=hits,
    )


def _best_sentence(question: str, hit: SearchHit) -> str:
    question_terms = set(tokenize(question))
    sentences = [sentence.strip() for sentence in _SENTENCE_RE.split(hit.chunk.text) if sentence.strip()]
    if not sentences:
        return hit.chunk.text.strip()

    def score(sentence: str) -> tuple[int, int]:
        sentence_terms = set(tokenize(sentence))
        return (len(question_terms & sentence_terms), -len(sentence))

    return max(sentences, key=score)


def _citation_for(chunk: DocumentChunk) -> Citation:
    return Citation(
        source=chunk.source,
        heading=chunk.heading,
        start_line=chunk.start_line,
        end_line=chunk.end_line,
    )
