# Portfolio roadmap

This roadmap tracks the six data-focused projects planned for the portfolio.

## Selection criteria

Projects are prioritized when they demonstrate at least one of the following:

- analytics engineering and SQL skills
- data quality, profiling, or pipeline design
- applied AI for structured business workflows
- clear interview talking points for data engineering and analytics roles
- reproducible local execution without relying on private data

## Project roadmap

### 1. Auto EDA Analyst

Build a local analyst assistant that accepts CSV/Excel data, profiles columns, identifies data quality issues, creates useful charts, and writes a concise business summary.

Planned milestones:

- scaffold package and sample datasets
- implement schema and data-quality profiling
- generate Markdown reports and chart artifacts
- add CLI entry point and tests
- polish README with example output

### 2. NL2SQL Analytics Agent

Build a safe natural-language-to-SQL workflow over DuckDB or SQLite, focused on realistic warehouse-style analytics questions.

Planned milestones:

- create sample dimensional dataset
- inspect schema and business glossary
- generate SQL with safety checks
- execute and explain query results
- add tests and usage examples

### 3. Report Q&A Agent

Build a retrieval workflow for asking questions over long reports, PDFs, and policy-style documents.

Planned milestones:

- document ingestion and chunking
- local vector index or keyword fallback
- cited answer generation
- evaluation questions
- README with examples

### 4. Competitive Intelligence Pipeline

Build a structured market-research workflow that compares companies, products, or vendors using collected notes and scored criteria.

Planned milestones:

- source collection format
- extraction and normalization
- competitor scoring table
- summary report generation
- tests for scoring logic

### 5. Financial Research Analyst

Build a financial analytics project that combines market data, fundamentals-style metrics, and explanatory reporting.

Planned milestones:

- market data ingestion layer
- time-series metrics
- risk and performance summary
- notebook or report output
- tests for calculations

### 6. Research Briefing Generator

Build a briefing generator that converts collected articles or source notes into a ranked digest with key points and follow-up questions.

Planned milestones:

- source input schema
- summarization and ranking pipeline
- Markdown/HTML digest output
- recurring-run friendly structure
- final portfolio polish
