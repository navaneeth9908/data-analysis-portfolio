"""Deterministic sample sales mart for local NL2SQL demos.

The project should be runnable without private databases or API keys. This module
creates a small SQLite star schema that is large enough for joins,
aggregations, date filters, and ranking questions while staying easy to inspect
in interviews.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Any

CUSTOMERS = [
    (1, "Acme Retail", "West", "Retail"),
    (2, "Bluebird Foods", "West", "CPG"),
    (3, "Cedar Health", "South", "Healthcare"),
    (4, "Delta Logistics", "Midwest", "Logistics"),
    (5, "Evergreen Schools", "Northeast", "Education"),
    (6, "Futura Bank", "South", "Financial Services"),
]

PRODUCTS = [
    (101, "Analytics Starter", "Software", 500.0),
    (102, "Data Quality Audit", "Services", 1200.0),
    (103, "Forecasting Add-on", "Software", 800.0),
    (104, "Dashboard Enablement", "Services", 950.0),
    (105, "Pipeline Monitoring", "Software", 650.0),
]

ORDERS = [
    (1001, 1, "2024-01-15", "closed won"),
    (1002, 2, "2024-01-20", "closed won"),
    (1003, 3, "2024-02-05", "closed won"),
    (1004, 4, "2024-02-18", "closed won"),
    (1005, 5, "2024-03-02", "closed won"),
    (1006, 6, "2024-03-11", "closed won"),
    (1007, 1, "2024-04-03", "closed won"),
    (1008, 3, "2024-04-19", "closed won"),
    (1009, 4, "2024-05-07", "closed won"),
    (1010, 2, "2024-05-16", "closed won"),
]

ORDER_ITEMS = [
    (1, 1001, 101, 2, 500.0),
    (2, 1001, 102, 1, 200.0),
    (3, 1002, 103, 1, 800.0),
    (4, 1002, 105, 2, 650.0),
    (5, 1003, 102, 1, 1200.0),
    (6, 1003, 104, 1, 950.0),
    (7, 1004, 101, 1, 500.0),
    (8, 1004, 105, 1, 650.0),
    (9, 1005, 104, 2, 950.0),
    (10, 1006, 103, 2, 800.0),
    (11, 1006, 105, 1, 650.0),
    (12, 1007, 104, 1, 950.0),
    (13, 1008, 101, 1, 500.0),
    (14, 1009, 102, 1, 1200.0),
    (15, 1010, 102, 1, 1200.0),
    (16, 1010, 105, 1, 610.0),
]

SCHEMA_SQL = """
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL,
    region TEXT NOT NULL,
    segment TEXT NOT NULL
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    list_price REAL NOT NULL
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    order_date TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(order_id),
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL
);
"""


def build_sales_mart(db_path: str | Path) -> dict[str, int]:
    """Create the sample SQLite sales mart and return loaded row counts."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", CUSTOMERS)
        conn.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", PRODUCTS)
        conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?)", ORDERS)
        conn.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?)", ORDER_ITEMS)
        conn.commit()

        return {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("customers", "products", "orders", "order_items")
        }
    finally:
        conn.close()


def default_question_examples() -> list[dict[str, str]]:
    """Return portfolio-friendly example questions and reference SQL."""
    return [
        {
            "difficulty": "basic",
            "question": "Which region generated the most revenue?",
            "sql": """
SELECT c.region, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.region
ORDER BY revenue DESC
LIMIT 1;
""".strip(),
        },
        {
            "difficulty": "intermediate",
            "question": "What are the top three products by revenue?",
            "sql": """
SELECT p.product_name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.product_name
ORDER BY revenue DESC
LIMIT 3;
""".strip(),
        },
        {
            "difficulty": "intermediate",
            "question": "Which products sold the most units?",
            "sql": """
SELECT p.product_name,
       SUM(oi.quantity) AS units_sold,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.product_name
ORDER BY units_sold DESC, revenue DESC
LIMIT 5;
""".strip(),
        },
        {
            "difficulty": "intermediate",
            "question": "Show monthly revenue trend for 2024",
            "sql": """
SELECT strftime('%Y-%m', o.order_date) AS month,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue,
       COUNT(DISTINCT o.order_id) AS order_count
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.status = 'closed won'
GROUP BY month
ORDER BY month;
""".strip(),
        },
        {
            "difficulty": "intermediate",
            "question": "Who are the top customers by revenue?",
            "sql": """
SELECT c.customer_name,
       c.region,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY c.customer_name, c.region
ORDER BY revenue DESC
LIMIT 5;
""".strip(),
        },
        {
            "difficulty": "intermediate",
            "question": "Which customers placed repeat orders?",
            "sql": """
SELECT c.customer_name,
       c.region,
       COUNT(o.order_id) AS order_count
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_name, c.region
HAVING COUNT(o.order_id) > 1
ORDER BY order_count DESC, c.customer_name;
""".strip(),
        },
        {
            "difficulty": "intermediate",
            "question": "Which product category generated the most revenue?",
            "sql": """
SELECT p.category,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue,
       COUNT(DISTINCT p.product_id) AS product_count
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.category
ORDER BY revenue DESC;
""".strip(),
        },
        {
            "difficulty": "advanced",
            "question": "What share of revenue comes from each product category?",
            "sql": """
WITH category_revenue AS (
    SELECT p.category,
           ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    GROUP BY p.category
)
SELECT category,
       revenue,
       ROUND(revenue * 100.0 / SUM(revenue) OVER (), 2) AS revenue_share_pct
FROM category_revenue
ORDER BY revenue DESC;
""".strip(),
        },
        {
            "difficulty": "intermediate",
            "question": "Which customer segment generated the most revenue?",
            "sql": """
SELECT c.segment,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue,
       COUNT(DISTINCT o.order_id) AS order_count
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY c.segment
ORDER BY revenue DESC;
""".strip(),
        },
        {
            "difficulty": "advanced",
            "question": "Which customer segment has the highest average order value?",
            "sql": """
WITH order_revenue AS (
    SELECT o.order_id, c.segment, SUM(oi.quantity * oi.unit_price) AS revenue
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY o.order_id, c.segment
)
SELECT segment, ROUND(AVG(revenue), 2) AS average_order_value
FROM order_revenue
GROUP BY segment
ORDER BY average_order_value DESC;
""".strip(),
        },
        {
            "difficulty": "advanced",
            "question": "Which region has the highest average order value?",
            "sql": """
WITH order_revenue AS (
    SELECT o.order_id, c.region, SUM(oi.quantity * oi.unit_price) AS revenue
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY o.order_id, c.region
)
SELECT region, ROUND(AVG(revenue), 2) AS average_order_value
FROM order_revenue
GROUP BY region
ORDER BY average_order_value DESC;
""".strip(),
        },
        {
            "difficulty": "advanced",
            "question": "Which products were sold below list price?",
            "sql": """
SELECT p.product_name,
       p.category,
       ROUND(SUM((p.list_price - oi.unit_price) * oi.quantity), 2) AS discount_amount,
       SUM(oi.quantity) AS discounted_units
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
WHERE oi.unit_price < p.list_price
GROUP BY p.product_name, p.category
ORDER BY discount_amount DESC, discounted_units DESC;
""".strip(),
        },
        {
            "difficulty": "advanced",
            "question": "Show month over month revenue growth for 2024",
            "sql": """
WITH monthly_revenue AS (
    SELECT strftime('%Y-%m', o.order_date) AS month,
           ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.status = 'closed won'
    GROUP BY month
),
monthly_with_previous AS (
    SELECT month,
           revenue,
           LAG(revenue) OVER (ORDER BY month) AS previous_revenue
    FROM monthly_revenue
)
SELECT month,
       revenue,
       ROUND(revenue - previous_revenue, 2) AS revenue_change,
       CASE
           WHEN previous_revenue IS NULL OR previous_revenue = 0 THEN NULL
           ELSE ROUND((revenue - previous_revenue) * 100.0 / previous_revenue, 2)
       END AS revenue_change_pct
FROM monthly_with_previous
ORDER BY month;
""".strip(),
        },
    ]


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for generating the local demo database."""
    parser = argparse.ArgumentParser(description="Build the NL2SQL sample SQLite sales mart.")
    parser.add_argument(
        "--output",
        default="examples/sales_mart.sqlite",
        help="Path where the SQLite database should be created.",
    )
    args = parser.parse_args(argv)

    counts = build_sales_mart(args.output)
    print(f"Created {args.output}")
    for table, row_count in counts.items():
        print(f"{table}: {row_count} rows")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by CLI smoke tests
    raise SystemExit(main())
