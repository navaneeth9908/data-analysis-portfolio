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
3. Which products sold the most units?
4. Show monthly revenue trend for 2024
5. Show month over month revenue growth for 2024
6. Who are the top customers by revenue?
7. Which customers placed repeat orders?
8. Which product category generated the most revenue?
9. What share of revenue comes from each product category?
10. Which customer segment has the highest average order value?
11. Which region has the highest average order value?

These questions are covered by the offline rule-backed generator so the demo stays deterministic without API keys. They exercise joins, grouping, ranking, quantity analysis, repeat-customer analysis, date bucketing, category mix analysis, revenue-share calculations, window functions, month-over-month variance calculations, order-level CTEs, and CTE-style reasoning in the SQL generator and executor.

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

For month-over-month revenue growth, run:

```bash
python -m src.offline_demo "Show month over month revenue growth for 2024" --db-path examples/sales_mart.sqlite --limit 10
```

Expected result excerpt:

```text
month   | revenue | revenue_change | revenue_change_pct
--------+---------+----------------+-------------------
2024-03 | 4150.0  | 850.0          | 25.76
2024-04 | 1450.0  | -2700.0        | -65.06
```

For product demand analysis, run:

```bash
python -m src.offline_demo "Which products sold the most units?" --db-path examples/sales_mart.sqlite --limit 5
```

Expected result excerpt:

```text
product_name        | units_sold | revenue
--------------------+------------+--------
Pipeline Monitoring | 5          | 3210.0
Dashboard Enablement| 4          | 3800.0
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

For revenue contribution analysis, run:

```bash
python -m src.offline_demo "What share of revenue comes from each product category?" --db-path examples/sales_mart.sqlite --limit 10
```

Expected result excerpt:

```text
category | revenue | revenue_share_pct
---------+---------+------------------
Software | 7610.0  | 50.03
Services | 7600.0  | 49.97
```

For regional deal-size analysis, run:

```bash
python -m src.offline_demo "Which region has the highest average order value?" --db-path examples/sales_mart.sqlite --limit 10
```

Expected answer summary excerpt:

```text
**Northeast leads with average order value of 1,900.00.**
- Top row: region=Northeast, average_order_value=1,900.00.
```
