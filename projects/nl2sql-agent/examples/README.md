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

These questions are designed to exercise joins, grouping, ranking, and CTE-style reasoning in the SQL generator and executor.
