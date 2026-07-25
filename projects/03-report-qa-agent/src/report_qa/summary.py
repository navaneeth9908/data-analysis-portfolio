"""Markdown summaries for deterministic report Q&A evaluation runs."""

from __future__ import annotations

from collections.abc import Sequence

from .evaluation import EvaluationResult


def render_evaluation_summary(
    results: Sequence[EvaluationResult],
    *,
    title: str = "Report Q&A Evaluation Summary",
) -> str:
    """Render a multi-question evaluation summary in portable Markdown."""
    result_rows = tuple(results)
    passed = sum(result.passed for result in result_rows)

    lines = [
        f"# {title}",
        "",
        f"Overall: {passed}/{len(result_rows)} questions passed",
        "",
        "| Question ID | Status | Question | Expected citation |",
        "| --- | --- | --- | --- |",
    ]
    for result in result_rows:
        status = "PASS" if result.passed else "FAIL"
        lines.append(
            "| "
            + " | ".join(
                [
                    _table_cell(result.question.id),
                    status,
                    _table_cell(result.question.question),
                    _table_cell(result.question.expected_citation),
                ]
            )
            + " |"
        )

    for result in result_rows:
        lines.extend(
            [
                "",
                f"## {result.question.id}",
                "",
                f"**Question:** {result.question.question}",
                "",
                f"**Answer:** {result.answer.answer}",
                "",
                "Citations:",
            ]
        )
        if result.answer.citations:
            lines.extend(f"- {citation.label}" for citation in result.answer.citations)
        else:
            lines.append("- No supporting citation found")

        matched_terms = ", ".join(result.matched_answer_terms) or "None"
        lines.extend(["", f"Matched expected terms: {matched_terms}"])
        if result.failure_reasons:
            lines.append("Issues:")
            lines.extend(f"- {reason}" for reason in result.failure_reasons)

    return "\n".join(lines).rstrip() + "\n"


def _table_cell(value: str) -> str:
    """Keep Markdown summary table cells on one line."""
    return value.replace("\n", " ").replace("|", "\\|")
