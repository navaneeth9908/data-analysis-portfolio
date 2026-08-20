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

Progress:

- Added deterministic CSV schema warnings for blank header names and data rows whose field count differs from the header, including a CLI example fixture and focused tests.
- Added an optional standalone SVG missingness chart artifact via the CLI so CSV quality issues are shareable beyond the Markdown report.
- Added a concise analyst-summary section that turns row/column shape, missingness, duplicate rows, numeric ranges, and IQR outliers into immediately reviewable findings.
- Added a ranked missingness-details table so reports prioritize incomplete columns by blank-value count and percentage before deeper profiling.
- Added ISO date-column inference and a date-range report section so timeline fields show their populated coverage without being treated as categorical dimensions.
- Added complete-row coverage to the analyst summary and data-quality section so reports show how many records are immediately analysis-ready across every column.

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

Progress:

- Added an offline Markdown ingestion, keyword retrieval, and cited extractive-answer path under `projects/03-report-qa-agent`.
- Added a deterministic evaluation question set with expected answer terms, citation checks, and CLI pass/fail reporting.
- Added plain-text report ingestion with heading-based line citations and a customer-success memo smoke example.
- Added Markdown answer brief rendering with citations, ranked supporting snippets, and a reproducible CLI output file.
- Added a dependency-free text-layer PDF ingestion adapter with a partner-launch memo smoke example.
- Added a multi-question Markdown evaluation summary export for offline evaluation runs.

### 4. Competitive Intelligence Pipeline

Build a structured market-research workflow that compares companies, products, or vendors using collected notes and scored criteria.

Planned milestones:

- source collection format
- extraction and normalization
- competitor scoring table
- summary report generation
- tests for scoring logic

Progress:

- Added an offline JSON source-note format with normalized company, source, theme, sentiment, and confidence fields.
- Added confidence-weighted competitor profile rollups and a Markdown landscape CLI over deterministic sample notes.
- Added buyer-specific priority scoring with weighted strength/gap/risk evidence and a CLI scorecard option.
- Added source-backed evidence highlights beneath the scorecard so each competitor profile links back to the newest public notes and signal details.
- Added source coverage checks that flag stale latest notes, thin note counts, or single-source profiles before turning a landscape into buying recommendations.
- Added executive summary bullets and recommended follow-up research tasks so the Markdown landscape is closer to a stakeholder-ready intelligence brief.
- Added reusable profile snapshots and Markdown trend deltas so repeated landscape runs show source, signal, score, and theme movement over time.
- Added analyst-handoff CSV table exports for competitor rollups, buyer-fit scoring, trend deltas, and source coverage watchlists.

### 5. Financial Research Analyst

Build a financial analytics project that combines market data, fundamentals-style metrics, and explanatory reporting.

Planned milestones:

- market data ingestion layer
- time-series metrics
- risk and performance summary
- notebook or report output
- tests for calculations

Progress:

- Started the Financial Research Analyst with deterministic local price-history CSV data, return/risk metric calculations, benchmark comparison, short-vs-long moving-average trend signals, Markdown brief rendering, and a tested CLI smoke path.
- Added rule-backed risk notes that flag elevated volatility, deep drawdowns, benchmark underperformance, and weak moving-average trends in the generated Markdown brief.
- Added deterministic trailing-twelve-month fundamentals inputs with price-to-sales, net margin, and return-on-equity calculations plus an optional CLI report section.
- Added chronological fundamentals loading and a two-snapshot valuation/profitability trend table in the CLI-generated Markdown brief.
- Added benchmark-aware drawdown notes that distinguish asset-specific weakness from market-wide declines in the risk section.
- Added aligned-return benchmark sensitivity reporting with correlation and beta so the brief separates absolute performance from market exposure.
- Added a dependency-free self-contained HTML report format with semantic tables and the same deterministic calculations, alongside the Markdown analyst brief.
- Added duplicate-date validation for selected-ticker fundamentals histories so valuation snapshots and trend comparisons remain deterministic.
- Added volume-based liquidity profiles so generated briefs show average volume, latest volume, and latest-vs-average activity for the selected ticker window.

### 6. Research Briefing Generator

Build a briefing generator that converts collected articles or source notes into a ranked digest with key points and follow-up questions.

Planned milestones:

- source input schema
- summarization and ranking pipeline
- Markdown/HTML digest output
- recurring-run friendly structure
- final portfolio polish

Progress:

- Added a deterministic local JSON source-note schema, transparent relevance/source-quality/freshness scoring, a ranked Markdown digest CLI, bundled AI-policy notes, and an end-to-end test. The reporting date is an explicit CLI input, so recurring runs are reproducible and source priority is auditable.
- Added an optional self-contained HTML digest that retains ranked evidence, transparent scoring inputs, and follow-up questions for browser-based sharing.
- Added publisher-coverage source mix summaries to the Markdown and HTML digests so reviewers can quickly see how concentrated the evidence base is.
- Added freshness-band source mix summaries to the Markdown and HTML digests so recurring briefings show whether the evidence is fresh, recent, or older.
- Added deterministic source-coverage notes that flag thin or single-publisher evidence before the ranked digest is reused in stakeholder updates.
- Polished the root portfolio navigation with accurate links to all six project directories and documented a single repeatable regression command for their independent test suites.
- Added a root portfolio verifier that confirms root-README navigation plus the required structure of all six projects before running their isolated test suites, with a `--check-only` mode for quick repository-health checks.
- Added a focused `--project` option to the root portfolio verifier so one project suite can run behind the same layout and navigation guardrails during small milestone work.
