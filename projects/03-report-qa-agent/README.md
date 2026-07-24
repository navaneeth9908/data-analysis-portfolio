# Report Q&A Agent

A deterministic, offline report question-answering workflow for portfolio demos. The current milestone ingests Markdown and plain-text reports, retrieves relevant chunks with a transparent keyword fallback, returns extractive answers with line-level citations, and can export a Markdown answer brief for sharing.

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
  examples/customer_success_memo.txt
  examples/evaluation_questions.json
  examples/renewal_delay_brief.md
  src/report_qa/
    ingest.py       # Markdown/plain-text chunking with heading + line spans
    retrieval.py    # deterministic keyword retrieval fallback
    answer.py       # extractive answer selection with citations
    brief.py        # Markdown answer brief rendering
    evaluation.py   # expected-answer checks for offline evaluation
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
PYTHONPATH=src python -m report_qa.cli "Why were enterprise renewal approvals delayed?" examples/customer_success_memo.txt --top-k 2
PYTHONPATH=src python -m report_qa.cli "Why were enterprise renewals delayed?" examples/sample_board_report.md --top-k 2 --brief-output examples/renewal_delay_brief.md
PYTHONPATH=src python -m report_qa.cli --eval-file examples/evaluation_questions.json --report examples/sample_board_report.md --top-k 2
```

Expected answer excerpt:

```text
Question: Why were enterprise renewals delayed?

Answer:
Enterprise renewal approvals were delayed because a security review cycle took longer than planned.

Citations:
- sample_board_report.md#Risk watch:L9-L10
```

Plain-text memo smoke test excerpt:

```text
Question: Why were enterprise renewal approvals delayed?

Answer:
Enterprise renewal approvals were delayed because the customer's legal team needed a fresh data-processing addendum.

Citations:
- customer_success_memo.txt#Risk Watch:L6-L8
```

Markdown brief excerpt (`examples/renewal_delay_brief.md`):

```text
# Report Q&A Brief

## Question
Why were enterprise renewals delayed?

## Citations
- sample_board_report.md#Risk watch:L9-L10

## Supporting evidence
### Evidence 1: sample_board_report.md#Risk watch:L9-L10
```

Expected evaluation excerpt:

```text
Evaluation: 4/4 passed
PASS renewal_delay - Why were enterprise renewals delayed?
PASS pipeline_reliability - What improved data pipeline reliability?
PASS incremental_revenue_region - Which region contributed the largest incremental revenue?
PASS segment_label_validation - What validation rule will data engineering add?
```

## Current capabilities

- Parses Markdown and plain-text headings into citation-ready chunks.
- Preserves source filename, heading, and line ranges for each chunk.
- Ranks chunks using normalized question-term overlap with heading boosts.
- Produces a deterministic extractive answer from the best evidence chunk.
- Writes a portable Markdown answer brief with citations and ranked supporting snippets.
- Runs a local evaluation question set with expected answer terms and citations.
- Handles no-evidence questions with a safe fallback answer.

## Example questions

Try these against `examples/sample_board_report.md` and `examples/customer_success_memo.txt`:

1. Why were enterprise renewals delayed?
2. What improved data pipeline reliability?
3. Which region contributed the largest incremental revenue?
4. Why were enterprise renewal approvals delayed?

## Planned next milestones

- Add PDF extraction adapters for report exports.
- Add a lightweight local vector index option while keeping keyword fallback.
- Expand the Markdown answer brief into a multi-question report summary.
