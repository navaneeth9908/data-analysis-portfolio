# Report Q&A Agent

A deterministic, offline report question-answering workflow for portfolio demos. The first milestone focuses on Markdown reports: ingest heading-scoped sections, retrieve relevant chunks with a transparent keyword fallback, and return extractive answers with line-level citations.

## Why this project matters

Analytics and data-engineering roles often require turning long business reports into fast, cited answers. This project demonstrates the core mechanics behind a report Q&A assistant without relying on private documents or paid APIs:

- citation-preserving document ingestion
- deterministic retrieval that can be tested locally
- concise answer generation from source evidence
- CLI output that is easy to explain in interviews

## Project layout

```text
projects/03-report-qa-agent/
  examples/sample_board_report.md
  src/report_qa/
    ingest.py       # Markdown chunking with heading + line spans
    retrieval.py    # deterministic keyword retrieval fallback
    answer.py       # extractive answer selection with citations
    cli.py          # local smoke-test CLI
  tests/test_report_qa.py
```

## Quick start

From this project directory:

```bash
python -m venv .venv
source .venv/Scripts/activate  # Git Bash on Windows
pip install -r requirements.txt
PYTHONPATH=src pytest tests/ -q
PYTHONPATH=src python -m report_qa.cli "Why were enterprise renewals delayed?" examples/sample_board_report.md --top-k 2
```

Expected answer excerpt:

```text
Question: Why were enterprise renewals delayed?

Answer:
Enterprise renewal approvals were delayed because a security review cycle took longer than planned.

Citations:
- sample_board_report.md#Risk watch:L9-L10
```

## Current capabilities

- Parses Markdown headings into citation-ready chunks.
- Preserves source filename, heading, and line ranges for each chunk.
- Ranks chunks using normalized question-term overlap with heading boosts.
- Produces a deterministic extractive answer from the best evidence chunk.
- Handles no-evidence questions with a safe fallback answer.

## Example questions

Try these against `examples/sample_board_report.md`:

1. Why were enterprise renewals delayed?
2. What improved data pipeline reliability?
3. Which region contributed the largest incremental revenue?

## Planned next milestones

- Add plain-text and PDF extraction adapters.
- Store evaluation questions and expected citations.
- Add a lightweight local vector index option while keeping keyword fallback.
- Generate a Markdown answer brief with supporting snippets.
