"""End-to-end offline demo tests for the sample NL2SQL sales mart."""

import importlib.util
import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

package = types.ModuleType("nl2sql_src")
package.__path__ = [str(SRC_ROOT)]
sys.modules["nl2sql_src"] = package
schema_package = types.ModuleType("nl2sql_src.schema")
schema_package.__path__ = [str(SRC_ROOT / "schema")]
sys.modules["nl2sql_src.schema"] = schema_package
generator_package = types.ModuleType("nl2sql_src.generator")
generator_package.__path__ = [str(SRC_ROOT / "generator")]
sys.modules["nl2sql_src.generator"] = generator_package
executor_package = types.ModuleType("nl2sql_src.executor")
executor_package.__path__ = [str(SRC_ROOT / "executor")]
sys.modules["nl2sql_src.executor"] = executor_package


def load_module(name: str, path: Path):
    """Load a source module while preserving its package-relative imports."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


load_module("nl2sql_src.config", SRC_ROOT / "config.py")
load_module("nl2sql_src.schema.models", SRC_ROOT / "schema" / "models.py")
load_module("nl2sql_src.generator.sql_generator", SRC_ROOT / "generator" / "sql_generator.py")
load_module("nl2sql_src.executor.runner", SRC_ROOT / "executor" / "runner.py")
load_module("nl2sql_src.sample_data", SRC_ROOT / "sample_data.py")
offline_demo = load_module("nl2sql_src.offline_demo", SRC_ROOT / "offline_demo.py")


def test_answer_sample_question_builds_database_generates_sql_and_returns_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "sales_mart.sqlite"

    answer = offline_demo.answer_sample_question(
        "Which region generated the most revenue?",
        db_path=db_path,
        limit=5,
    )

    assert db_path.exists()
    assert answer.question == "Which region generated the most revenue?"
    assert answer.validation_errors == []
    assert answer.tables_used == ["customers", "order_items", "orders"]
    assert answer.rows == [{"region": "West", "revenue": 6060.0}]
    assert answer.insight.headline == "West leads with revenue of 6,060.00."
    assert "GROUP BY c.region" in answer.sql
    assert "region" in answer.table
    assert "West" in answer.table


def test_answer_sample_question_handles_segment_average_order_value(tmp_path: Path) -> None:
    db_path = tmp_path / "sales_mart.sqlite"

    answer = offline_demo.answer_sample_question(
        "Which customer segment has the highest average order value?",
        db_path=db_path,
        limit=5,
    )

    assert answer.validation_errors == []
    assert answer.tables_used == ["customers", "order_items", "orders"]
    assert answer.rows[0] == {"segment": "Financial Services", "average_order_value": 2250.0}
    assert answer.insight.headline == (
        "Financial Services leads with average order value of 2,250.00."
    )
    assert "WITH order_revenue AS" in answer.sql
    assert "AVG(revenue)" in answer.sql


def test_answer_sample_question_handles_top_customers_by_revenue(tmp_path: Path) -> None:
    db_path = tmp_path / "sales_mart.sqlite"

    answer = offline_demo.answer_sample_question(
        "Who are the top customers by revenue?",
        db_path=db_path,
        limit=5,
    )

    assert answer.validation_errors == []
    assert answer.tables_used == ["customers", "order_items", "orders"]
    assert answer.rows[:2] == [
        {"customer_name": "Bluebird Foods", "region": "West", "revenue": 3910.0},
        {"customer_name": "Cedar Health", "region": "South", "revenue": 2650.0},
    ]
    assert answer.insight.headline == "Bluebird Foods leads with revenue of 3,910.00."
    assert "GROUP BY c.customer_name, c.region" in answer.sql
    assert "Bluebird Foods" in answer.table


def test_answer_sample_question_handles_monthly_revenue_trend(tmp_path: Path) -> None:
    db_path = tmp_path / "sales_mart.sqlite"

    answer = offline_demo.answer_sample_question(
        "Show monthly revenue trend for 2024",
        db_path=db_path,
        limit=10,
    )

    assert answer.validation_errors == []
    assert answer.tables_used == ["order_items", "orders"]
    assert answer.rows == [
        {"month": "2024-01", "revenue": 3300.0, "order_count": 2},
        {"month": "2024-02", "revenue": 3300.0, "order_count": 2},
        {"month": "2024-03", "revenue": 4150.0, "order_count": 2},
        {"month": "2024-04", "revenue": 1450.0, "order_count": 2},
        {"month": "2024-05", "revenue": 3010.0, "order_count": 2},
    ]
    assert "strftime('%Y-%m', o.order_date)" in answer.sql
    assert "COUNT(DISTINCT o.order_id)" in answer.sql
    assert "2024-03" in answer.table


def test_main_prints_portfolio_friendly_demo_output(tmp_path: Path, capsys) -> None:
    exit_code = offline_demo.main(
        [
            "Which region generated the most revenue?",
            "--db-path",
            str(tmp_path / "sales_mart.sqlite"),
            "--limit",
            "5",
        ]
    )

    captured = capsys.readouterr().out
    assert exit_code == 0
    assert "Question: Which region generated the most revenue?" in captured
    assert "Generated SQL:" in captured
    assert "Answer Summary:" in captured
    assert "West leads with revenue of 6,060.00." in captured
    assert "Result:" in captured
    assert "West" in captured
