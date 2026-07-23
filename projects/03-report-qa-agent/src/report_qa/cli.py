"""Command line entry point for the offline report Q&A demo."""

from __future__ import annotations

import argparse
from pathlib import Path

from .answer import answer_question


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ask a cited question over local Markdown reports.")
    parser.add_argument("question", help="Business question to answer from the report corpus")
    parser.add_argument(
        "reports",
        nargs="*",
        type=Path,
        default=[Path("examples/sample_board_report.md")],
        help="Markdown report files to search",
    )
    parser.add_argument("--top-k", type=int, default=3, help="Number of chunks to retrieve")
    args = parser.parse_args(argv)

    answer = answer_question(args.question, args.reports, top_k=args.top_k)

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
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by CLI smoke tests
    raise SystemExit(main())
