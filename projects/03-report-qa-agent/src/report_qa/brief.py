"""Markdown brief rendering for report Q&A answers."""

from __future__ import annotations

from .models import Answer, SearchHit


def render_answer_brief(answer: Answer, *, max_snippet_chars: int = 360) -> str:
    """Render an answer and its evidence as a portable Markdown brief."""
    if max_snippet_chars < 80:
        raise ValueError("max_snippet_chars must be at least 80")

    lines = [
        "# Report Q&A Brief",
        "",
        "## Question",
        answer.question,
        "",
        "## Answer",
        answer.answer,
        "",
        "## Citations",
    ]

    if answer.citations:
        lines.extend(f"- {citation.label}" for citation in answer.citations)
    else:
        lines.append("- No supporting citation found")

    lines.extend(["", "## Supporting evidence"])
    if answer.hits:
        for index, hit in enumerate(answer.hits, start=1):
            lines.extend(_format_evidence_hit(index, hit, max_snippet_chars=max_snippet_chars))
    else:
        lines.append("No retrieved evidence was available for this question.")

    return "\n".join(lines).rstrip() + "\n"


def _format_evidence_hit(index: int, hit: SearchHit, *, max_snippet_chars: int) -> list[str]:
    terms = ", ".join(f"`{term}`" for term in sorted(set(hit.matched_terms)))
    snippet = _snippet(hit.chunk.text, max_chars=max_snippet_chars)
    return [
        "",
        f"### Evidence {index}: {hit.chunk.citation_label}",
        f"Score: {hit.score:.2f}",
        f"Matched terms: {terms or 'none'}",
        "",
        f"> {snippet}",
    ]


def _snippet(text: str, *, max_chars: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rstrip() + "…"
