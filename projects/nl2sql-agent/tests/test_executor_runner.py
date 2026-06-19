"""Query execution safety and formatting tests for the NL2SQL agent."""

import importlib.util
import sys
import types
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

package = types.ModuleType("nl2sql_src")
package.__path__ = [str(SRC_ROOT)]
sys.modules["nl2sql_src"] = package
schema_package = types.ModuleType("nl2sql_src.schema")
schema_package.__path__ = [str(SRC_ROOT / "schema")]
sys.modules["nl2sql_src.schema"] = schema_package
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


config_module = load_module("nl2sql_src.config", SRC_ROOT / "config.py")
models = load_module("nl2sql_src.schema.models", SRC_ROOT / "schema" / "models.py")
runner_module = load_module("nl2sql_src.executor.runner", SRC_ROOT / "executor" / "runner.py")

Column = models.Column
ColumnType = models.ColumnType
Config = config_module.Config
DatabaseSchema = models.DatabaseSchema
QueryRunner = runner_module.QueryRunner
ResultFormatter = runner_module.ResultFormatter
SafetyConfig = config_module.SafetyConfig
Table = models.Table


@pytest.fixture(autouse=True)
def safe_config() -> None:
    """Use deterministic safety limits that keep tests fast and read-only."""
    config_module.set_config(
        Config(safety=SafetyConfig(read_only=True, max_query_cost=1000, max_rows=2))
    )


@pytest.fixture()
def sqlite_runner() -> QueryRunner:
    """Create an in-memory SQLite database and matching schema model."""
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE customer (customer_id INTEGER PRIMARY KEY, name TEXT, spend REAL)"))
        conn.execute(
            text(
                "INSERT INTO customer (customer_id, name, spend) VALUES "
                "(1, 'Ada', 10.5), (2, 'Grace', 0), (3, NULL, 5.25)"
            )
        )

    schema = DatabaseSchema(dialect="sqlite")
    schema.add_table(
        Table(
            name="customer",
            columns=[
                Column("customer_id", ColumnType.INTEGER, "INTEGER", nullable=False, is_primary_key=True),
                Column("name", ColumnType.TEXT, "TEXT"),
                Column("spend", ColumnType.REAL, "REAL"),
            ],
        )
    )
    return QueryRunner(engine, schema)


def test_execute_applies_default_limit_and_reports_truncation(sqlite_runner: QueryRunner) -> None:
    result = sqlite_runner.execute("SELECT customer_id, name, spend FROM customer ORDER BY customer_id")

    assert result.columns == ["customer_id", "name", "spend"]
    assert result.row_count == 2
    assert result.truncated is True
    assert result.query.endswith("LIMIT 3;")
    assert result.rows[1]["spend"] == 0


def test_execute_rejects_write_queries_and_ignores_keywords_in_literals(
    sqlite_runner: QueryRunner,
) -> None:
    assert sqlite_runner._is_read_only("SELECT name FROM customer WHERE name = 'DROP'") is True

    with pytest.raises(ValueError, match="Only SELECT queries allowed"):
        sqlite_runner.execute("DELETE FROM customer WHERE customer_id = 1")


def test_limit_detection_ignores_literal_text(sqlite_runner: QueryRunner) -> None:
    limited = sqlite_runner._apply_limit("SELECT 'limit' AS word FROM customer", 5)

    assert limited == "SELECT 'limit' AS word FROM customer LIMIT 5;"


def test_formatter_preserves_zero_values_and_renders_null() -> None:
    result = runner_module.QueryResult(
        columns=["name", "spend"],
        rows=[{"name": "Grace", "spend": 0}, {"name": None, "spend": 5.25}],
        row_count=2,
        execution_time_ms=1.2,
        query="SELECT name, spend FROM customer",
    )

    rendered = ResultFormatter.to_table(result)

    assert "Grace" in rendered
    assert "0" in rendered
    assert "NULL" in rendered
