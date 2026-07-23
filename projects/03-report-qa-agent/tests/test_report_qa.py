"""Behavior tests for the offline report Q&A workflow."""

from __future__ import annotations

from pathlib import Path

from report_qa.answer import answer_question
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
