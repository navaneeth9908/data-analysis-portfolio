# Competitive Intelligence Pipeline

A deterministic, offline workflow for turning public-source competitor notes into a structured landscape summary. The current milestone focuses on source collection, normalization, confidence-weighted signal rollups, and a Markdown CLI output that can be reproduced from a clean checkout.

## Why this project matters

Competitive intelligence work is most useful when analysts can trace summary claims back to consistent source notes. This project demonstrates a practical analytics-engineering pattern for market research:

- collect public observations in a repeatable JSON format
- normalize company names, source types, themes, and signal sentiment
- roll up strengths, gaps, and risks with transparent confidence scores
- publish a portfolio-ready Markdown comparison table

## Project layout

```text
projects/04-competitive-intelligence-pipeline/
  examples/source_notes.json      # deterministic public-source note fixture
  examples/landscape.md           # generated sample competitor landscape
  src/competitive_intel/
    source_collection.py          # note models, normalization, scoring, rendering
    cli.py                        # Markdown report CLI
  tests/test_source_collection.py
```

## Quick start

From this project directory:

```bash
python -m venv .venv
source .venv/Scripts/activate  # Git Bash on Windows
pip install -r requirements.txt
pytest tests/ -q
PYTHONPATH=src python -m competitive_intel.cli examples/source_notes.json \
  --output examples/landscape.md \
  --title "Sample Analytics Competitor Landscape" \
  --priority governance=2 \
  --priority support=2 \
  --priority delivery=1 \
  --coverage-as-of 2026-07-02 \
  --max-note-age-days 7
```

Expected CLI message:

```text
Landscape written to examples\landscape.md
```

Expected landscape excerpt:

```text
# Sample Analytics Competitor Landscape

Scores are confidence-weighted rollups from public-source notes.

| Company | Notes | Signals | Strength | Gap | Risk | Top themes | Sources |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Acme Analytics | 2 | 3 | 7 | 0 | 2 | product, delivery, pricing | press release, webinar |
| Northstar BI | 2 | 3 | 8 | 3 | 0 | support, ecosystem, governance | review, website |
| Orion Data Cloud | 2 | 3 | 4 | 3 | 0 | governance, ecosystem, onboarding | analyst note, job posting |

## Buyer-fit priority scorecard

Strength signals add points; gap and risk signals subtract concern points.

| Company | Fit score | Strength points | Concern points | Matched themes |
| --- | ---: | ---: | ---: | --- |
| Orion Data Cloud | 8 | 8 | 0 | governance |
| Northstar BI | 4 | 10 | 6 | support, governance |
| Acme Analytics | 3 | 3 | 0 | delivery |

## Evidence highlights

Source-backed snippets show why each competitor earned its score.

### Orion Data Cloud
- **2026-06-21 · job posting · Customer success implementation role** — Orion is hiring implementation specialists to standardize customer onboarding playbooks.

## Research coverage watchlist

Use these checks before turning the landscape into buying recommendations.

- **Acme Analytics · stale-latest-source** — Acme Analytics's latest source is 12 days old as of 2026-07-02; refresh threshold is 7 days.
```

## Source note format

Each note captures one public observation about one competitor:

```json
{
  "id": "acme-finance-webinar-2026-06",
  "company": "Acme Analytics",
  "source_type": "webinar",
  "source": "Finance analytics product webinar",
  "published_date": "2026-06-18",
  "summary": "Acme positioned governed self-service dashboards for finance teams.",
  "signals": [
    {
      "theme": "product",
      "sentiment": "strength",
      "detail": "Finance-ready semantic layer templates shorten dashboard setup.",
      "confidence": 4
    }
  ]
}
```

Supported score buckets are `strength`, `gap`, and `risk`. Other sentiments are retained as evidence themes but do not affect the three score columns, which is useful for neutral signals such as hiring plans or product-roadmap hints.

## Current capabilities

- Loads deterministic JSON source-note collections.
- Normalizes whitespace, source types, themes, and signal sentiment.
- Validates required fields and 1-5 confidence scores.
- Aggregates competitor profiles by note count, signal count, source types, latest source date, top themes, and confidence-weighted strength/gap/risk scores.
- Ranks competitors against buyer-specific priority themes using weighted strength, gap, and risk evidence.
- Renders a Markdown landscape table, optional buyer-fit scorecard, source-backed evidence highlights, and source coverage watchlist for portfolio demos or stakeholder briefings.
- Provides a small CLI smoke path with reproducible sample data.

## Planned next milestones

- Add a richer Markdown report with executive summary and recommended follow-up research.
- Add lightweight trend deltas across repeated landscape runs.
