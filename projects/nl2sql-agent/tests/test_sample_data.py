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

    with sqlite3.connect(db_path) as conn:
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

    assert top_region == ("West", 6060.0)


def test_default_question_examples_match_sales_mart_tables() -> None:
    examples = sample_data.default_question_examples()

    assert examples[0]["question"] == "Which region generated the most revenue?"
    assert "JOIN orders" in examples[0]["sql"]
    assert "order_items" in examples[0]["sql"]
    assert {example["difficulty"] for example in examples} == {"basic", "intermediate", "advanced"}
