"""Behavior tests for the offline report Q&A workflow."""

from __future__ import annotations

from pathlib import Path

import report_qa.ingest as ingest_module
from report_qa.answer import answer_question
from report_qa.brief import render_answer_brief
from report_qa.cli import main
from report_qa.evaluation import (
    EvaluationQuestion,
    evaluate_questions,
    load_evaluation_questions,
)
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


def write_plain_text_customer_memo(tmp_path: Path) -> Path:
    """Create a plain-text report fixture with analyst-style section labels."""
    report_path = tmp_path / "customer_success_memo.txt"
    report_path.write_text(
        "Customer Success Memo\n"
        "\n"
        "Executive Summary\n"
        "West-region expansion accounts increased dashboard adoption among healthcare teams.\n"
        "\n"
        "Risk Watch\n"
        "Enterprise renewal approvals were delayed because the customer's legal team needed a fresh data-processing addendum.\n"
        "A renewal owner will escalate unresolved security questions every Friday.\n"
        "\n"
        "Next Actions\n"
        "Sales operations will circulate a procurement checklist before the next steering committee.\n",
        encoding="utf-8",
    )
    return report_path


def write_pdf_partner_memo(tmp_path: Path) -> Path:
    """Create a small text-layer PDF fixture without external dependencies."""
    report_path = tmp_path / "partner_launch_memo.pdf"
    lines = [
        "Partner Launch Memo",
        "",
        "Recommendation",
        "Launch timing slipped because partner security sign-off moved into the next compliance window.",
        "Sales engineering will complete connector certification before the public announcement.",
        "",
        "Next Actions",
        "Publish a revised enablement calendar with owner, dependency, and sign-off date.",
    ]
    report_path.write_bytes(_build_simple_pdf(lines))
    return report_path


def _build_simple_pdf(lines: list[str]) -> bytes:
    def escape_pdf_text(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    text_commands = ["BT", "/F1 12 Tf", "72 720 Td", "14 TL"]
    for line in lines:
        text_commands.append(f"({escape_pdf_text(line)}) Tj")
        text_commands.append("T*")
    text_commands.append("ET")
    content = "\n".join(text_commands).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"\nendstream",
    ]
    chunks = [b"%PDF-1.4\n"]
    offsets = [0]
    for object_id, payload in enumerate(objects, start=1):
        offsets.append(sum(len(chunk) for chunk in chunks))
        chunks.append(f"{object_id} 0 obj\n".encode("ascii") + payload + b"\nendobj\n")
    xref_offset = sum(len(chunk) for chunk in chunks)
    chunks.append(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    chunks.append(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        chunks.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    chunks.append(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return b"".join(chunks)


def test_load_text_chunks_preserves_section_citations(tmp_path: Path) -> None:
    report_path = write_plain_text_customer_memo(tmp_path)

    chunks = ingest_module.load_text_chunks(report_path, max_chars=280)

    risk = next(chunk for chunk in chunks if chunk.heading == "Risk Watch")
    assert risk.source == "customer_success_memo.txt"
    assert risk.start_line == 6
    assert risk.end_line == 8
    assert "data-processing addendum" in risk.text


def test_answer_question_supports_plain_text_reports_with_citations(tmp_path: Path) -> None:
    report_path = write_plain_text_customer_memo(tmp_path)

    answer = answer_question(
        "Why were enterprise renewals delayed?",
        [report_path],
        top_k=2,
    )

    assert answer.answer == (
        "Enterprise renewal approvals were delayed because the customer's legal "
        "team needed a fresh data-processing addendum."
    )
    assert answer.citations[0].label == "customer_success_memo.txt#Risk Watch:L6-L8"


def test_answer_question_supports_text_layer_pdf_reports_with_citations(tmp_path: Path) -> None:
    report_path = write_pdf_partner_memo(tmp_path)

    answer = answer_question(
        "Why did the partner launch timing slip?",
        [report_path],
        top_k=2,
    )

    assert answer.answer == (
        "Launch timing slipped because partner security sign-off moved into "
        "the next compliance window."
    )
    assert answer.citations[0].label == "partner_launch_memo.pdf#Recommendation:L3-L5"
    assert answer.hits[0].chunk.text.startswith("Launch timing slipped")


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


def test_render_answer_brief_includes_citations_and_supporting_snippets(tmp_path: Path) -> None:
    report_path = write_board_report(tmp_path)
    answer = answer_question(
        "Why were enterprise renewals delayed?",
        [report_path],
        top_k=2,
    )

    brief = render_answer_brief(answer)

    assert brief.startswith("# Report Q&A Brief\n")
    assert "## Question\nWhy were enterprise renewals delayed?" in brief
    assert "## Answer\nEnterprise renewal approvals were delayed" in brief
    assert "- board_report.md#Risk watch:L7-L9" in brief
    assert "### Evidence 1: board_report.md#Risk watch:L7-L9" in brief
    assert "Matched terms: `delayed`, `enterprise`, `renewal`" in brief
    assert "security review cycle took longer than planned" in brief


def test_cli_writes_markdown_answer_brief(tmp_path: Path) -> None:
    report_path = write_board_report(tmp_path)
    brief_path = tmp_path / "renewal_brief.md"

    exit_code = main(
        [
            "Why were enterprise renewals delayed?",
            str(report_path),
            "--top-k",
            "2",
            "--brief-output",
            str(brief_path),
        ]
    )

    assert exit_code == 0
    brief = brief_path.read_text(encoding="utf-8")
    assert "# Report Q&A Brief" in brief
    assert "board_report.md#Risk watch:L7-L9" in brief
    assert "security review cycle took longer than planned" in brief


def test_evaluate_questions_marks_answer_and_citation_matches(tmp_path: Path) -> None:
    report_path = write_board_report(tmp_path)
    questions = (
        EvaluationQuestion(
            id="renewal_delay",
            question="Why were enterprise renewals delayed?",
            expected_answer_terms=("security review cycle",),
            expected_citation="board_report.md#Risk watch:L7-L9",
        ),
    )

    results = evaluate_questions(questions, [report_path], top_k=2)

    assert len(results) == 1
    result = results[0]
    assert result.passed is True
    assert result.matched_answer_terms == ("security review cycle",)
    assert result.expected_citation_found is True
    assert result.failure_reasons == ()


def test_load_evaluation_questions_reads_json_question_set(tmp_path: Path) -> None:
    eval_path = tmp_path / "questions.json"
    eval_path.write_text(
        """
        {
          "questions": [
            {
              "id": "pipeline_reliability",
              "question": "What improved data pipeline reliability?",
              "expected_answer_terms": ["data-quality gates", "weekly load"],
              "expected_citation": "sample_board_report.md#Data operations:L12-L13"
            }
          ]
        }
        """.strip(),
        encoding="utf-8",
    )

    questions = load_evaluation_questions(eval_path)

    assert questions == (
        EvaluationQuestion(
            id="pipeline_reliability",
            question="What improved data pipeline reliability?",
            expected_answer_terms=("data-quality gates", "weekly load"),
            expected_citation="sample_board_report.md#Data operations:L12-L13",
        ),
    )


def test_render_evaluation_summary_includes_status_answers_and_citations(tmp_path: Path) -> None:
    from report_qa.summary import render_evaluation_summary

    report_path = write_board_report(tmp_path)
    questions = (
        EvaluationQuestion(
            id="renewal_delay",
            question="Why were enterprise renewals delayed?",
            expected_answer_terms=("security review cycle",),
            expected_citation="board_report.md#Risk watch:L7-L9",
        ),
    )
    results = evaluate_questions(questions, [report_path], top_k=2)

    summary = render_evaluation_summary(results, title="Board Q&A Evaluation Summary")

    assert summary.startswith("# Board Q&A Evaluation Summary\n")
    assert "Overall: 1/1 questions passed" in summary
    assert (
        "| renewal_delay | PASS | Why were enterprise renewals delayed? | "
        "board_report.md#Risk watch:L7-L9 |"
    ) in summary
    assert "## renewal_delay" in summary
    assert "**Answer:** Enterprise renewal approvals were delayed" in summary
    assert "- board_report.md#Risk watch:L7-L9" in summary
    assert "Matched expected terms: security review cycle" in summary


def test_cli_evaluation_mode_prints_pass_summary(tmp_path: Path, capsys) -> None:
    report_path = write_board_report(tmp_path)
    eval_path = tmp_path / "questions.json"
    eval_path.write_text(
        """
        {
          "questions": [
            {
              "id": "renewal_delay",
              "question": "Why were enterprise renewals delayed?",
              "expected_answer_terms": ["security review cycle"],
              "expected_citation": "board_report.md#Risk watch:L7-L9"
            }
          ]
        }
        """.strip(),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--eval-file",
            str(eval_path),
            "--report",
            str(report_path),
            "--top-k",
            "2",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Evaluation: 1/1 passed" in output
    assert "PASS renewal_delay" in output
    assert "board_report.md#Risk watch:L7-L9" in output


def test_cli_evaluation_mode_writes_markdown_summary(tmp_path: Path, capsys) -> None:
    report_path = write_board_report(tmp_path)
    eval_path = tmp_path / "questions.json"
    summary_path = tmp_path / "evaluation_summary.md"
    eval_path.write_text(
        """
        {
          "questions": [
            {
              "id": "renewal_delay",
              "question": "Why were enterprise renewals delayed?",
              "expected_answer_terms": ["security review cycle"],
              "expected_citation": "board_report.md#Risk watch:L7-L9"
            }
          ]
        }
        """.strip(),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--eval-file",
            str(eval_path),
            "--report",
            str(report_path),
            "--top-k",
            "2",
            "--summary-output",
            str(summary_path),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert f"Summary written to {summary_path}" in output
    summary = summary_path.read_text(encoding="utf-8")
    assert summary.startswith("# Report Q&A Evaluation Summary\n")
    assert "Overall: 1/1 questions passed" in summary
    assert "| renewal_delay | PASS | Why were enterprise renewals delayed? |" in summary


def test_example_evaluation_questions_pass_against_sample_report() -> None:
    project_dir = Path(__file__).resolve().parents[1]
    questions = load_evaluation_questions(project_dir / "examples/evaluation_questions.json")

    results = evaluate_questions(
        questions,
        [project_dir / "examples/sample_board_report.md"],
        top_k=2,
    )

    assert [result.question.id for result in results] == [
        "renewal_delay",
        "pipeline_reliability",
        "incremental_revenue_region",
        "segment_label_validation",
    ]
    assert all(result.passed for result in results), [
        (result.question.id, result.failure_reasons) for result in results
    ]
