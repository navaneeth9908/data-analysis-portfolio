# Research Briefing Generator

A deterministic, source-backed research-briefing project. It turns a local JSON file of reviewed source notes into a ranked Markdown digest with transparent priority scores, key points, source links, and follow-up questions.

## Why this project matters

A useful research brief should make its evidence and prioritization visible. This first vertical slice demonstrates an offline workflow that:

- accepts a documented JSON source-note schema
- validates required text, dates, URLs, and one-to-five ratings
- scores each source against a fixed reporting date
- ranks the digest deterministically, including stable tie-breaking
- writes source links, analyst-provided key points, and follow-up questions to Markdown

The tool does **not** fetch websites or invent summaries. It makes a previously reviewed set of source notes repeatable and easy to audit.

## Quick start

From this project directory:

```bash
python -m pytest tests/ -q
PYTHONPATH=src python -m research_briefing.cli \
  examples/ai_policy_sources.json \
  --as-of 2026-08-10 \
  --output /tmp/ai_policy_briefing.md
```

Expected CLI message:

```text
Briefing written to /tmp/ai_policy_briefing.md
```

The generated report begins with a ranked digest like this:

```markdown
# AI policy weekly briefing

As of: 2026-08-10

Sources reviewed: 2

## Ranked digest

1. **Regulator publishes implementation timetable** — National AI Office (2026-08-08)
   - Score: 17/18 | Relevance 5/5 | Source quality 4/5 | Freshness 3/3
   - The first reporting deadline is scheduled for October.
   - Source: [Read source](https://example.com/timetable)
```

## Source-note schema

The input must be a UTF-8 JSON object with a non-empty `briefing_title` and at least one source:

```json
{
  "briefing_title": "AI policy weekly briefing",
  "sources": [
    {
      "title": "Regulator publishes implementation timetable",
      "publisher": "National AI Office",
      "published_on": "2026-08-08",
      "url": "https://example.com/timetable",
      "key_point": "The first reporting deadline is scheduled for October.",
      "follow_up_question": "Which internal teams own the October reporting deadline?",
      "relevance": 5,
      "source_quality": 4
    }
  ]
}
```

`published_on` must use `YYYY-MM-DD`. `relevance` and `source_quality` are integer ratings from 1 through 5.

## Ranking contract

Each source has a transparent maximum score of 18:

```text
score = (2 × relevance) + source_quality + freshness
```

Freshness is calculated relative to the required `--as-of` date:

| Source age | Freshness score |
| --- | ---: |
| 0–7 days | 3 |
| 8–30 days | 2 |
| More than 30 days | 1 |

Higher scores appear first. Equal scores are resolved by title and then publisher, so the same source notes and reporting date always produce the same report.

## Project layout

```text
projects/06-research-briefing-generator/
  examples/ai_policy_sources.json
  src/research_briefing/briefing.py
  src/research_briefing/cli.py
  tests/test_cli.py
```

## Current capabilities

- Local JSON source-note ingestion and validation.
- Deterministic source scoring and ranked Markdown digests.
- Key-point, source-link, and follow-up-question rendering.
- A fixed-date CLI path and end-to-end test using the bundled sample.
