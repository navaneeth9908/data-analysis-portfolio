"""Command line entry point for the offline report Q&A demo."""

from __future__ import annotations

import argparse
from pathlib import Path

from .answer import answer_question
from .brief import render_answer_brief
from .evaluation import evaluate_questions, load_evaluation_questions
from .summary import render_evaluation_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ask a cited question over local reports.")
    parser.add_argument("question", nargs="?", help="Business question to answer from the report corpus")
    parser.add_argument(
        "reports",
        nargs="*",
        type=Path,
        help="Markdown or plain-text report files to search",
    )
    parser.add_argument("--top-k", type=int, default=3, help="Number of chunks to retrieve")
    parser.add_argument(
        "--brief-output",
        type=Path,
        help="Write a Markdown answer brief with citations and supporting snippets",
    )
    parser.add_argument(
        "--eval-file",
        type=Path,
        help="JSON question set with expected answer terms and citations",
    )
    parser.add_argument(
        "--report",
        dest="evaluation_reports",
        action="append",
        type=Path,
        help="Report file to use in evaluation mode; repeat for multiple Markdown or plain-text reports",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        help="Write a Markdown multi-question evaluation summary in evaluation mode",
    )
    args = parser.parse_args(argv)

    default_reports = [Path("examples/sample_board_report.md")]
    if args.eval_file:
        reports = args.evaluation_reports or args.reports or default_reports
        questions = load_evaluation_questions(args.eval_file)
        results = evaluate_questions(questions, reports, top_k=args.top_k)
        passed = sum(result.passed for result in results)
        print(f"Evaluation: {passed}/{len(results)} passed")
        for result in results:
            status = "PASS" if result.passed else "FAIL"
            print(f"{status} {result.question.id} - {result.question.question}")
            print(f"  answer: {result.answer.answer}")
            print(f"  citation: {result.question.expected_citation}")
            if result.failure_reasons:
                print(f"  issues: {'; '.join(result.failure_reasons)}")
        if args.summary_output:
            args.summary_output.parent.mkdir(parents=True, exist_ok=True)
            args.summary_output.write_text(render_evaluation_summary(results), encoding="utf-8")
            print(f"Summary written to {args.summary_output}")
        return 0 if passed == len(results) else 1

    if args.question is None:
        parser.error("question is required unless --eval-file is provided")

    reports = args.reports or default_reports
    answer = answer_question(args.question, reports, top_k=args.top_k)

    print(f"Question: {answer.question}")
    print("\nAnswer:")
    print(answer.answer)
    print("\nCitations:")
    if answer.citations:
        for citation in answer.citations:
            print(f"- {citation.label}")
    else:
        print("- No supporting citation found")

    print("\nTop evidence:")
    for index, hit in enumerate(answer.hits, start=1):
        terms = ", ".join(hit.matched_terms)
        print(f"{index}. {hit.chunk.citation_label} (score={hit.score:.2f}; terms={terms})")

    if args.brief_output:
        args.brief_output.parent.mkdir(parents=True, exist_ok=True)
        args.brief_output.write_text(render_answer_brief(answer), encoding="utf-8")
        print(f"\nBrief written to {args.brief_output}")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by CLI smoke tests
    raise SystemExit(main())
