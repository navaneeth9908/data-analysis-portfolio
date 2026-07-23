"""Behavior tests for the offline report Q&A workflow."""

from __future__ import annotations

from pathlib import Path

from report_qa.answer import answer_question
from report_qa.ingest import load_markdown_chunks
from report_qa.retrieval import search_chunks


def write_board_report(tmp_path: Path) -> Path:
    """Create a small deterministic report fixture for retrieval tests."""
    report_path = tmp_path / "board_report.md"
    report_path.write_text(
        "# Board Update\n"
        "\n"
        "## Revenue highlights\n"
        "ARR rose 18% year over year after expansion in the West region.\n"
        "Healthcare customers adopted the analytics starter package quickly.\n"
        "\n"
        "## Risk watch\n"
        "Enterprise renewal approvals were delayed because a security review cycle took longer than planned.\n"
        "The account team needs a procurement checklist before the next steering committee.\n"
        "\n"
        "## Next actions\n"
        "Sales operations will publish a weekly renewal-risk tracker with owner, blocker, and next meeting date.\n",
        encoding="utf-8",
    )
    return report_path


def test_load_markdown_chunks_preserves_headings_and_citation_lines(tmp_path: Path) -> None:
    report_path = write_board_report(tmp_path)

    chunks = load_markdown_chunks(report_path, max_chars=280)

    revenue = next(chunk for chunk in chunks if chunk.heading == "Revenue highlights")
    assert revenue.source == "board_report.md"
    assert revenue.start_line == 3
    assert revenue.end_line == 5
    assert "ARR rose 18%" in revenue.text


def test_search_chunks_ranks_relevant_chunk_and_reports_terms(tmp_path: Path) -> None:
    report_path = write_board_report(tmp_path)
    chunks = load_markdown_chunks(report_path, max_chars=280)

    hits = search_chunks(chunks, "Which risk delayed enterprise renewals?", top_k=2)

    assert hits[0].chunk.heading == "Risk watch"
    assert hits[0].score > hits[1].score
    assert {"risk", "delayed", "enterprise"}.issubset(set(hits[0].matched_terms))


def test_answer_question_returns_cited_extractive_answer(tmp_path: Path) -> None:
    report_path = write_board_report(tmp_path)

    answer = answer_question(
        "Why were enterprise renewals delayed?",
        [report_path],
        top_k=2,
    )

    assert answer.answer == (
        "Enterprise renewal approvals were delayed because a security review cycle "
        "took longer than planned."
    )
    assert len(answer.citations) == 1
    citation = answer.citations[0]
    assert citation.source == "board_report.md"
    assert citation.heading == "Risk watch"
    assert citation.start_line == 7
    assert citation.end_line == 9
    assert citation.label == "board_report.md#Risk watch:L7-L9"
