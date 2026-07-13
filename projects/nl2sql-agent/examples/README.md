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
10. Which customer segment generated the most revenue?
11. Which regions generate the most software revenue?
12. Which regions generate the most services revenue?
13. Which customer segment has the highest average order value?
14. Which region has the highest average order value?
15. Which products were sold below list price?
16. Which products have the highest discount rate?
17. Which products have the highest average selling price?
18. How concentrated is revenue by customer?
19. Which products are most often purchased together?
20. Which regions have the most repeat customers?
21. Which regions bought the widest product mix?

These questions are covered by the offline rule-backed generator so the demo stays deterministic without API keys. They exercise joins, self-joins, grouping, ranking, category filtering, quantity analysis, realized-price analysis, repeat-customer analysis, repeat-customer regional concentration, regional product-mix breadth, product affinity analysis, date bucketing, customer-segment revenue analysis, regional software-revenue analysis, regional services-revenue analysis, customer concentration analysis, category mix analysis, revenue-share calculations, window functions, month-over-month variance calculations, order-level CTEs, list-price variance analysis, discount-rate analysis, and CTE-style reasoning in the SQL generator and executor.

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

For customer segment revenue mix, run:

```bash
python -m src.offline_demo "Which customer segment generated the most revenue?" --db-path examples/sales_mart.sqlite --limit 10
```

Expected result excerpt:

```text
segment    | revenue | order_count
-----------+---------+------------
CPG        | 3910.0  | 2
Healthcare | 2650.0  | 2
Logistics  | 2350.0  | 2
```

For regional software revenue mix, run:

```bash
python -m src.offline_demo "Which regions generate the most software revenue?" --db-path examples/sales_mart.sqlite --limit 5
```

Expected result excerpt:

```text
region  | software_revenue | order_count
--------+------------------+------------
West    | 3710.0           | 3
South   | 2750.0           | 2
Midwest | 1150.0           | 1
```

For regional services revenue mix, run:

```bash
python -m src.offline_demo "Which regions generate the most services revenue?" --db-path examples/sales_mart.sqlite --limit 5
```

Expected result excerpt:

```text
region    | services_revenue | order_count
----------+------------------+------------
West      | 2350.0           | 3
South     | 2150.0           | 1
Northeast | 1900.0           | 1
```

For customer concentration analysis, run:

```bash
python -m src.offline_demo "How concentrated is revenue by customer?" --db-path examples/sales_mart.sqlite --limit 10
```

Expected result excerpt:

```text
customer_name   | revenue | revenue_share_pct
----------------+---------+------------------
Bluebird Foods  | 3910.0  | 25.71
Cedar Health    | 2650.0  | 17.42
Delta Logistics | 2350.0  | 15.45
```

For repeat-customer concentration by region, run:

```bash
python -m src.offline_demo "Which regions have the most repeat customers?" --db-path examples/sales_mart.sqlite --limit 5
```

Expected result excerpt:

```text
region  | repeat_customer_count
--------+----------------------
West    | 2
Midwest | 1
South   | 1
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

For list-price variance analysis, run:

```bash
python -m src.offline_demo "Which products were sold below list price?" --db-path examples/sales_mart.sqlite --limit 10
```

Expected result excerpt:

```text
product_name        | category | discount_amount | discounted_units
--------------------+----------+-----------------+-----------------
Data Quality Audit  | Services | 1000.0          | 1
Pipeline Monitoring | Software | 40.0            | 1
```

For discount-rate analysis, run:

```bash
python -m src.offline_demo "Which products have the highest discount rate?" --db-path examples/sales_mart.sqlite --limit 10
```

Expected result excerpt:

```text
product_name        | category | discount_rate_pct | discount_amount
--------------------+----------+-------------------+----------------
Data Quality Audit  | Services | 83.33             | 1000.0
Pipeline Monitoring | Software | 6.15              | 40.0
```

For realized selling-price analysis, run:

```bash
python -m src.offline_demo "Which products have the highest average selling price?" --db-path examples/sales_mart.sqlite --limit 5
```

Expected result excerpt:

```text
product_name         | category | average_selling_price | units_sold
---------------------+----------+-----------------------+-----------
Dashboard Enablement | Services | 950.0                 | 4
Data Quality Audit   | Services | 950.0                 | 4
Forecasting Add-on   | Software | 800.0                 | 3
```

For product affinity analysis, run:

```bash
python -m src.offline_demo "Which products are most often purchased together?" --db-path examples/sales_mart.sqlite --limit 5
```

Expected result excerpt:

```text
product_a          | product_b           | shared_order_count
-------------------+---------------------+-------------------
Forecasting Add-on | Pipeline Monitoring | 2
Analytics Starter  | Data Quality Audit  | 1
```

For regional product-mix breadth, run:

```bash
python -m src.offline_demo "Which regions bought the widest product mix?" --db-path examples/sales_mart.sqlite --limit 5
```

Expected result excerpt:

```text
region    | distinct_products | category_count | revenue
----------+-------------------+----------------+--------
West      | 5                 | 2              | 6060.0
South     | 5                 | 2              | 4900.0
Midwest   | 3                 | 2              | 2350.0
Northeast | 1                 | 1              | 1900.0
```

