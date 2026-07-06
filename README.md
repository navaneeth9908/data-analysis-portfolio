# Data Analysis Portfolio

A practical collection of data analysis, analytics engineering, and AI-assisted data products. Each project is designed like a small production system: documented inputs, reproducible pipelines, tests, and examples that can be explained clearly in interviews or technical discussions.

## Focus areas

My background is in analytics and data engineering, so this repo focuses on projects that connect business questions to reliable data workflows:

- natural-language analytics over tabular data
- SQL generation and validation for warehouse-style datasets
- document/report Q&A with retrieval-augmented generation
- market and competitive intelligence workflows
- financial research and metrics analysis
- automated research briefings and summarization

## Projects

| Project | Focus | Outcome |
| --- | --- | --- |
| Auto EDA Analyst | pandas profiling, data quality checks, charts, business summary | CLI/app that turns CSV or Excel files into an analysis report |
| NL2SQL Analytics Agent | DuckDB/SQLite, schema inspection, safe SQL generation, result explanation | Ask business questions over a local analytics database |
| Report Q&A Agent | PDF/text ingestion, chunking, embeddings, retrieval, cited answers | Query long reports and return answers with source snippets |
| Competitive Intelligence Pipeline | research collection, entity comparison, scoring, summary tables | Structured competitor landscape report from public inputs |
| Financial Research Analyst | market data ingestion, ratios, time-series analysis, risk notes | Investment-style research notebook and reusable pipeline |
| Research Briefing Generator | topic monitoring, summarization, source ranking, digest output | Briefing output in Markdown/HTML |

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
- Keep commits small and focused.

## Current status

The NL2SQL Analytics Agent is currently the most developed project. It includes a deterministic local sales mart, safe SQL generation patterns, executable sample questions, result insights, and focused tests.
