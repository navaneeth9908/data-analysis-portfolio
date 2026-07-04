"""Result insight generation tests for portfolio-friendly NL2SQL answers."""

import importlib.util
import sys
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

package = types.ModuleType("nl2sql_src")
package.__path__ = [str(SRC_ROOT)]
sys.modules["nl2sql_src"] = package
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


runner_module = load_module("nl2sql_src.executor.runner", SRC_ROOT / "executor" / "runner.py")
insights_module = load_module("nl2sql_src.executor.insights", SRC_ROOT / "executor" / "insights.py")
QueryResult = runner_module.QueryResult
ResultInsight = insights_module.ResultInsight
explain_result = insights_module.explain_result


def test_explain_result_highlights_leading_metric_and_context() -> None:
    result = QueryResult(
        columns=["region", "revenue"],
        rows=[{"region": "West", "revenue": 6060.0}, {"region": "South", "revenue": 4120.5}],
        row_count=2,
        execution_time_ms=3.4,
        query="SELECT region, revenue FROM sales ORDER BY revenue DESC",
    )

    insight = explain_result("Which region generated the most revenue?", result)

    assert insight == ResultInsight(
        headline="West leads with revenue of 6,060.00.",
        details=[
            "Returned 2 rows across 2 columns in 3.4ms.",
            "Top row: region=West, revenue=6,060.00.",
        ],
    )
    assert "West leads" in insight.to_markdown()


def test_explain_result_humanizes_metric_column_names() -> None:
    result = QueryResult(
        columns=["segment", "average_order_value"],
        rows=[{"segment": "Financial Services", "average_order_value": 2250.0}],
        row_count=1,
        execution_time_ms=2.5,
        query="SELECT segment, average_order_value FROM segment_metrics",
    )

    insight = explain_result("Which segment has the highest average order value?", result)

    assert insight.headline == (
        "Financial Services leads with average order value of 2,250.00."
    )


def test_explain_result_reports_empty_and_truncated_outputs() -> None:
    empty = QueryResult(
        columns=["customer_name"],
        rows=[],
        row_count=0,
        execution_time_ms=1.0,
        query="SELECT customer_name FROM customers WHERE 1=0",
    )
    assert explain_result("No matching customers", empty).headline == "No rows matched the question."

    truncated = QueryResult(
        columns=["customer_name", "revenue"],
        rows=[{"customer_name": "Apex Retail", "revenue": 1000}],
        row_count=1,
        execution_time_ms=2.0,
        query="SELECT customer_name, revenue FROM customers",
        truncated=True,
    )

    insight = explain_result("Top customers", truncated)

    assert "limited preview" in insight.details[-1]
