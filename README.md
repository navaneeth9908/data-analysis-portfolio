# Data Analysis Portfolio

A practical portfolio of data analysis, analytics engineering, and AI-assisted data products. Each project is designed to look and work like a small production system: documented inputs, reproducible pipelines, tests, and examples that can be explained in interviews.

## Why this repo exists

My background is in analytics and data engineering, so this portfolio focuses on projects that connect business questions to reliable data workflows:

- natural-language analytics over tabular data
- SQL generation and validation for warehouse-style datasets
- document/report Q&A with retrieval-augmented generation
- market and competitive intelligence workflows
- financial research and metrics analysis
- automated research briefings and summarization

The projects are inspired by open-source AI-agent patterns, but the implementations here are being rebuilt as original portfolio projects with clearer data-engineering structure, test coverage, and business-facing documentation.

## 30-day roadmap

The plan is to complete six small projects in one month. Each project gets five days of focused work, with steady commits that build the application in realistic increments.

| Days | Project | Focus | Expected outcome |
| --- | --- | --- | --- |
| 1-5 | Auto EDA Analyst | pandas profiling, data quality checks, charts, business summary | CLI/app that turns CSV or Excel files into an analysis report |
| 6-10 | NL2SQL Analytics Agent | DuckDB/SQLite, schema inspection, safe SQL generation, result explanation | Ask business questions over a local analytics database |
| 11-15 | Report Q&A Agent | PDF/text ingestion, chunking, embeddings, retrieval, cited answers | Query long reports and return answers with source snippets |
| 16-20 | Competitive Intelligence Pipeline | web/research collection, entity comparison, scoring, summary tables | Structured competitor landscape report from public inputs |
| 21-25 | Financial Research Analyst | market data ingestion, ratios, time-series analysis, risk notes | Investment-style research notebook and reusable pipeline |
| 26-30 | Research Briefing Generator | topic monitoring, summarization, source ranking, digest output | Automated daily-style briefing in Markdown/HTML |

## Repository layout

```text
projects/
  01-auto-eda-analyst/
  02-nl2sql-analytics-agent/
  03-report-qa-agent/
  04-competitive-intelligence-pipeline/
  05-financial-research-analyst/
  06-research-briefing-generator/
shared/
  data_utils/
  report_utils/
tests/
docs/
```

Each project should include:

- `README.md` with problem statement, setup, usage, and examples
- reproducible sample data or data-generation scripts
- source code under `src/`
- tests for the core logic
- a short results section with screenshots or sample outputs where useful

## Project standards

- Python-first stack: pandas, DuckDB/SQLite, Pydantic, pytest, and Streamlit or FastAPI only where useful.
- Prefer deterministic local examples over API-only demos.
- Keep secrets out of the repo. Use `.env.example` files when credentials are optional.
- Make every project runnable from a clean checkout.
- Commit in small, readable steps that match how a developer would normally build the work.

## Current status

Roadmap setup is in progress. The first project will start with the Auto EDA Analyst: sample datasets, a profiling pipeline, and a Markdown report generator.
