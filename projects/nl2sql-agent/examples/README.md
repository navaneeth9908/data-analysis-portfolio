# NL2SQL sample sales mart

This folder is for reproducible local demos. The SQLite database is generated on demand and is intentionally not committed.

## Build the database

```bash
python src/sample_data.py --output examples/sales_mart.sqlite
```

The generated database contains a small star schema:

- `customers` — customer region and segment attributes
- `products` — product category and list price
- `orders` — order header with date and status
- `order_items` — line-item quantities and realized unit prices

## Example business questions

1. Which region generated the most revenue?
2. What are the top three products by revenue?
3. Which customer segment has the highest average order value?

These questions are covered by the offline rule-backed generator so the demo stays deterministic without API keys. They exercise joins, grouping, ranking, and CTE-style reasoning in the SQL generator and executor.

## Offline demo runner

Use the demo runner to exercise the full local path without an LLM provider:

```bash
python -m src.offline_demo "Which region generated the most revenue?" --db-path examples/sales_mart.sqlite --limit 5
```

Expected result excerpt:

```text
Question: Which region generated the most revenue?

Generated SQL:
SELECT c.region, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
...

Result:
region | revenue
-------+--------
West   | 6060.0
```

A more advanced CTE-backed question is also supported:

```bash
python -m src.offline_demo "Which customer segment has the highest average order value?" --db-path examples/sales_mart.sqlite --limit 10
```

Expected answer summary excerpt:

```text
**Financial Services leads with average order value of 2,250.00.**
- Top row: segment=Financial Services, average_order_value=2,250.00.
```
