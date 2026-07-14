"""Deterministic sample analytics dataset tests for the NL2SQL agent."""

import importlib.util
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"


def load_module(name: str, path: Path):
    """Load a source module directly from the project src tree."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sample_data = load_module("sample_data", SRC_ROOT / "sample_data.py")


def test_build_sales_mart_creates_joinable_star_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "sales_mart.sqlite"

    summary = sample_data.build_sales_mart(db_path)

    assert summary["customers"] == 6
    assert summary["products"] == 5
    assert summary["orders"] == 10
    assert summary["order_items"] == 16
    assert db_path.exists()

    conn = sqlite3.connect(db_path)
    try:
        top_region = conn.execute(
            """
            SELECT c.region, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            JOIN customers c ON o.customer_id = c.customer_id
            GROUP BY c.region
            ORDER BY revenue DESC
            LIMIT 1
            """
        ).fetchone()
    finally:
        conn.close()

    assert top_region == ("West", 6060.0)

    db_path.unlink()
    assert not db_path.exists()


def test_default_question_examples_match_sales_mart_tables() -> None:
    examples = sample_data.default_question_examples()

    assert examples[0]["question"] == "Which region generated the most revenue?"
    assert "JOIN orders" in examples[0]["sql"]
    assert "order_items" in examples[0]["sql"]
    assert {example["difficulty"] for example in examples} == {"basic", "intermediate", "advanced"}
    assert any(
        example["question"] == "Show monthly revenue trend for 2024"
        and "strftime('%Y-%m', o.order_date)" in example["sql"]
        for example in examples
    )
    assert any(
        example["question"] == "What share of revenue comes from each product category?"
        and "SUM(revenue) OVER ()" in example["sql"]
        and "revenue_share_pct" in example["sql"]
        for example in examples
    )
    assert any(
        example["question"] == "Which region has the highest average order value?"
        and "AVG(revenue)" in example["sql"]
        and "GROUP BY region" in example["sql"]
        for example in examples
    )
    assert any(
        example["question"] == "Show month over month revenue growth for 2024"
        and "LAG(revenue) OVER (ORDER BY month)" in example["sql"]
        and "revenue_change_pct" in example["sql"]
        for example in examples
    )
    assert any(
        example["question"] == "Which products were sold below list price?"
        and "oi.unit_price < p.list_price" in example["sql"]
        and "discount_amount" in example["sql"]
        for example in examples
    )
    assert any(
        example["question"] == "Which customer segment generated the most revenue?"
        and "GROUP BY c.segment" in example["sql"]
        and "COUNT(DISTINCT o.order_id) AS order_count" in example["sql"]
        for example in examples
    )
    assert any(
        example["question"] == "Which regions generate the most software revenue?"
        and "p.category = 'Software'" in example["sql"]
        and "software_revenue" in example["sql"]
        for example in examples
    )
    assert any(
        example["question"] == "Which regions generate the most services revenue?"
        and "p.category = 'Services'" in example["sql"]
        and "services_revenue" in example["sql"]
        for example in examples
    )
    assert any(
        example["question"] == "How concentrated is revenue by customer?"
        and "WITH customer_revenue AS" in example["sql"]
        and "revenue_share_pct" in example["sql"]
        for example in examples
    )
    assert any(
        example["question"] == "Which products are most often purchased together?"
        and "oi1.order_id = oi2.order_id" in example["sql"]
        and "shared_order_count" in example["sql"]
        for example in examples
    )
    assert any(
        example["question"] == "Which regions have the most repeat customers?"
        and "customer_order_counts" in example["sql"]
        and "repeat_customer_count" in example["sql"]
        for example in examples
    )
    assert any(
        example["question"] == "Which regions bought the widest product mix?"
        and "distinct_products" in example["sql"]
        and "category_count" in example["sql"]
        for example in examples
    )
    assert any(
        example["question"] == "Which products generate the most revenue in each region?"
        and "regional_product_revenue" in example["sql"]
        and "PARTITION BY c.region" in example["sql"]
        for example in examples
    )

