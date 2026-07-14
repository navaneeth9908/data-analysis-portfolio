"""SQL generation and validation tests for the NL2SQL agent."""

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


def load_module(name: str, path: Path):
    """Load a source module without importing optional API/DB dependencies."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


models = load_module("nl2sql_src.schema.models", SRC_ROOT / "schema" / "models.py")
load_module("nl2sql_src.config", SRC_ROOT / "config.py")
sql_generator = load_module(
    "nl2sql_src.generator.sql_generator", SRC_ROOT / "generator" / "sql_generator.py"
)
dialect = load_module("nl2sql_src.generator.dialect", SRC_ROOT / "generator" / "dialect.py")

SQLGenerator = sql_generator.SQLGenerator
SQLValidator = sql_generator.SQLValidator
get_dialect = dialect.get_dialect
adapt_sql = dialect.adapt_sql
Column = models.Column
ColumnType = models.ColumnType
DatabaseSchema = models.DatabaseSchema
Table = models.Table


def build_sales_schema() -> DatabaseSchema:
    """Create a compact schema used by generator tests."""
    schema = DatabaseSchema(dialect="postgresql")
    schema.add_table(
        Table(
            name="customer",
            columns=[
                Column("customer_id", ColumnType.INTEGER, "INTEGER", nullable=False, is_primary_key=True),
                Column("first_name", ColumnType.VARCHAR, "VARCHAR(100)", nullable=False),
                Column("last_name", ColumnType.VARCHAR, "VARCHAR(100)", nullable=False),
                Column("country", ColumnType.VARCHAR, "VARCHAR(100)"),
            ],
        )
    )
    schema.add_table(
        Table(
            name="invoice",
            columns=[
                Column("invoice_id", ColumnType.INTEGER, "INTEGER", nullable=False, is_primary_key=True),
                Column(
                    "customer_id",
                    ColumnType.INTEGER,
                    "INTEGER",
                    nullable=False,
                    is_foreign_key=True,
                    foreign_key_table="customer",
                    foreign_key_column="customer_id",
                ),
                Column("total", ColumnType.DECIMAL, "NUMERIC(10,2)", nullable=False),
            ],
        )
    )
    return schema


def build_sample_mart_schema() -> DatabaseSchema:
    """Create the portfolio sample mart schema used by offline demos."""
    schema = DatabaseSchema(dialect="sqlite")
    schema.add_table(
        Table(
            name="customers",
            columns=[
                Column("customer_id", ColumnType.INTEGER, "INTEGER", nullable=False, is_primary_key=True),
                Column("customer_name", ColumnType.TEXT, "TEXT", nullable=False),
                Column("region", ColumnType.TEXT, "TEXT", nullable=False),
                Column("segment", ColumnType.TEXT, "TEXT", nullable=False),
            ],
        )
    )
    schema.add_table(
        Table(
            name="products",
            columns=[
                Column("product_id", ColumnType.INTEGER, "INTEGER", nullable=False, is_primary_key=True),
                Column("product_name", ColumnType.TEXT, "TEXT", nullable=False),
                Column("category", ColumnType.TEXT, "TEXT", nullable=False),
                Column("list_price", ColumnType.REAL, "REAL", nullable=False),
            ],
        )
    )
    schema.add_table(
        Table(
            name="orders",
            columns=[
                Column("order_id", ColumnType.INTEGER, "INTEGER", nullable=False, is_primary_key=True),
                Column("customer_id", ColumnType.INTEGER, "INTEGER", nullable=False),
                Column("order_date", ColumnType.TEXT, "TEXT", nullable=False),
                Column("status", ColumnType.TEXT, "TEXT", nullable=False),
            ],
        )
    )
    schema.add_table(
        Table(
            name="order_items",
            columns=[
                Column("order_item_id", ColumnType.INTEGER, "INTEGER", nullable=False, is_primary_key=True),
                Column("order_id", ColumnType.INTEGER, "INTEGER", nullable=False),
                Column("product_id", ColumnType.INTEGER, "INTEGER", nullable=False),
                Column("quantity", ColumnType.INTEGER, "INTEGER", nullable=False),
                Column("unit_price", ColumnType.REAL, "REAL", nullable=False),
            ],
        )
    )
    return schema


def test_prompt_includes_schema_dialect_examples_and_question() -> None:
    generator = SQLGenerator(build_sales_schema())

    prompt = generator.prompt_builder.build_prompt("Top customers by spend", few_shot_count=1)

    assert "target dialect: postgresql" in prompt
    assert "Table: customer" in prompt
    assert "customer_id: INTEGER PK NOT NULL" in prompt
    assert "--- Example 1 ---" in prompt
    assert "Question: Top customers by spend" in prompt


def test_mock_generation_parses_sql_and_reports_tables() -> None:
    generator = SQLGenerator(build_sales_schema())

    result = generator.generate("Which customers spend the most?")

    assert result.sql.startswith("WITH customer_spending AS")
    assert result.tables_used == ["customer", "invoice"]
    assert result.validation_errors == []
    assert result.confidence == 0.8


def test_mock_generation_answers_sample_mart_region_revenue_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("Which region generated the most revenue?")

    assert "c.region" in result.sql
    assert "SUM(oi.quantity * oi.unit_price)" in result.sql
    assert result.tables_used == ["customers", "order_items", "orders"]
    assert result.validation_errors == []


def test_mock_generation_answers_sample_mart_product_ranking_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("What are the top three products by revenue?")

    assert "p.product_name" in result.sql
    assert "LIMIT 3" in result.sql
    assert result.tables_used == ["order_items", "products"]
    assert result.validation_errors == []


def test_mock_generation_answers_sample_mart_units_sold_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("Which products sold the most units?")

    assert "p.product_name" in result.sql
    assert "SUM(oi.quantity) AS units_sold" in result.sql
    assert "ORDER BY units_sold DESC" in result.sql
    assert result.tables_used == ["order_items", "products"]
    assert result.validation_errors == []


def test_mock_generation_answers_sample_mart_category_revenue_share_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("What share of revenue comes from each product category?")

    assert "category_revenue" in result.sql
    assert "revenue_share_pct" in result.sql
    assert "SUM(revenue) OVER ()" in result.sql
    assert result.tables_used == ["order_items", "products"]
    assert result.validation_errors == []


def test_mock_generation_answers_sample_mart_region_average_order_value_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("Which region has the highest average order value?")

    assert "WITH order_revenue AS" in result.sql
    assert "c.region" in result.sql
    assert "ROUND(AVG(revenue), 2) AS average_order_value" in result.sql
    assert result.tables_used == ["customers", "order_items", "orders"]
    assert result.validation_errors == []


def test_mock_generation_answers_sample_mart_discount_analysis_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("Which products were sold below list price?")

    assert "p.list_price" in result.sql
    assert "oi.unit_price < p.list_price" in result.sql
    assert "discount_amount" in result.sql
    assert result.tables_used == ["order_items", "products"]
    assert result.validation_errors == []


def test_mock_generation_answers_sample_mart_discount_rate_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("Which products have the highest discount rate?")

    assert "discount_rate_pct" in result.sql
    assert "oi.unit_price < p.list_price" in result.sql
    assert "SUM(p.list_price * oi.quantity)" in result.sql
    assert "ORDER BY discount_rate_pct DESC" in result.sql
    assert result.tables_used == ["order_items", "products"]
    assert result.validation_errors == []


def test_mock_generation_answers_sample_mart_average_selling_price_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("Which products have the highest average selling price?")

    assert "average_selling_price" in result.sql
    assert "SUM(oi.quantity * oi.unit_price) / SUM(oi.quantity)" in result.sql
    assert "units_sold" in result.sql
    assert "ORDER BY average_selling_price DESC" in result.sql
    assert result.tables_used == ["order_items", "products"]
    assert result.validation_errors == []


def test_mock_generation_answers_sample_mart_month_over_month_revenue_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("Show month over month revenue growth for 2024")

    assert "WITH monthly_revenue AS" in result.sql
    assert "LAG(revenue) OVER (ORDER BY month)" in result.sql
    assert "revenue_change" in result.sql
    assert "revenue_change_pct" in result.sql
    assert result.tables_used == ["order_items", "orders"]
    assert result.validation_errors == []


def test_mock_generation_answers_sample_mart_quarterly_region_revenue_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("Show quarterly revenue by region for 2024")

    assert "quarter" in result.sql
    assert "c.region" in result.sql
    assert "COUNT(DISTINCT o.order_id) AS order_count" in result.sql
    assert "GROUP BY quarter, c.region" in result.sql
    assert "ORDER BY quarter, revenue DESC" in result.sql
    assert result.tables_used == ["customers", "order_items", "orders"]
    assert result.validation_errors == []


def test_mock_generation_answers_sample_mart_top_customer_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("Who are the top customers by revenue?")

    assert "c.customer_name" in result.sql
    assert "SUM(oi.quantity * oi.unit_price)" in result.sql
    assert "ORDER BY revenue DESC" in result.sql
    assert result.tables_used == ["customers", "order_items", "orders"]
    assert result.validation_errors == []


def test_mock_generation_answers_sample_mart_repeat_customer_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("Which customers placed repeat orders?")

    assert "COUNT(o.order_id) AS order_count" in result.sql
    assert "HAVING COUNT(o.order_id) > 1" in result.sql
    assert "ORDER BY order_count DESC, c.customer_name" in result.sql
    assert result.tables_used == ["customers", "orders"]
    assert result.validation_errors == []


def test_mock_generation_answers_sample_mart_segment_revenue_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("Which customer segment generated the most revenue?")

    assert "c.segment" in result.sql
    assert "SUM(oi.quantity * oi.unit_price)" in result.sql
    assert "COUNT(DISTINCT o.order_id) AS order_count" in result.sql
    assert "ORDER BY revenue DESC" in result.sql
    assert result.tables_used == ["customers", "order_items", "orders"]
    assert result.validation_errors == []


def test_mock_generation_answers_sample_mart_region_software_revenue_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("Which regions generate the most software revenue?")

    assert "p.category = 'Software'" in result.sql
    assert "c.region" in result.sql
    assert "software_revenue" in result.sql
    assert "COUNT(DISTINCT o.order_id) AS order_count" in result.sql
    assert result.tables_used == ["customers", "order_items", "orders", "products"]
    assert result.validation_errors == []


def test_mock_generation_answers_sample_mart_region_services_revenue_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("Which regions generate the most services revenue?")

    assert "p.category = 'Services'" in result.sql
    assert "c.region" in result.sql
    assert "services_revenue" in result.sql
    assert "COUNT(DISTINCT o.order_id) AS order_count" in result.sql
    assert result.tables_used == ["customers", "order_items", "orders", "products"]
    assert result.validation_errors == []


def test_mock_generation_answers_sample_mart_customer_concentration_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("How concentrated is revenue by customer?")

    assert "WITH customer_revenue AS" in result.sql
    assert "revenue_share_pct" in result.sql
    assert "SUM(revenue) OVER ()" in result.sql
    assert "ORDER BY revenue DESC" in result.sql
    assert result.tables_used == ["customers", "order_items", "orders"]
    assert result.validation_errors == []



def test_mock_generation_answers_sample_mart_product_affinity_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("Which products are most often purchased together?")

    assert "oi1.order_id = oi2.order_id" in result.sql
    assert "oi1.product_id < oi2.product_id" in result.sql
    assert "shared_order_count" in result.sql
    assert "ORDER BY shared_order_count DESC" in result.sql
    assert result.tables_used == ["order_items", "products"]
    assert result.validation_errors == []


def test_mock_generation_answers_sample_mart_repeat_customers_by_region_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("Which regions have the most repeat customers?")

    assert "customer_order_counts" in result.sql
    assert "HAVING COUNT(o.order_id) > 1" in result.sql
    assert "COUNT(*) AS repeat_customer_count" in result.sql
    assert "ORDER BY repeat_customer_count DESC" in result.sql
    assert result.tables_used == ["customers", "orders"]
    assert result.validation_errors == []


def test_mock_generation_answers_sample_mart_region_product_mix_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("Which regions bought the widest product mix?")

    assert "COUNT(DISTINCT p.product_id) AS distinct_products" in result.sql
    assert "COUNT(DISTINCT p.category) AS category_count" in result.sql
    assert "ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue" in result.sql
    assert "ORDER BY distinct_products DESC, revenue DESC" in result.sql
    assert result.tables_used == ["customers", "order_items", "orders", "products"]
    assert result.validation_errors == []


def test_mock_generation_answers_sample_mart_top_product_by_region_question() -> None:
    generator = SQLGenerator(build_sample_mart_schema())

    result = generator.generate("Which products generate the most revenue in each region?")

    assert "regional_product_revenue" in result.sql
    assert "RANK() OVER" in result.sql
    assert "PARTITION BY c.region" in result.sql
    assert "WHERE revenue_rank = 1" in result.sql
    assert result.tables_used == ["customers", "order_items", "orders", "products"]
    assert result.validation_errors == []


def test_validator_flags_unknown_table_and_qualified_column() -> None:
    validator = SQLValidator(build_sales_schema())

    errors = validator.validate(
        "SELECT c.customer_id, c.missing_column FROM customer c JOIN payment p ON p.id = c.customer_id"
    )

    assert "Unknown table referenced: payment" in errors
    assert "Unknown column referenced: c.missing_column on table customer" in errors


def test_validator_flags_unknown_unqualified_columns_in_simple_queries() -> None:
    validator = SQLValidator(build_sales_schema())

    errors = validator.validate(
        "SELECT customer_id, lifetime_value FROM customer WHERE country = 'USA' AND cohort = 'enterprise'"
    )

    assert "Unknown column referenced: lifetime_value" in errors
    assert "Unknown column referenced: cohort" in errors
    assert "Unknown column referenced: customer_id" not in errors
    assert "Unknown column referenced: country" not in errors


def test_validator_blocks_write_queries_but_ignores_keywords_inside_literals() -> None:
    validator = SQLValidator(build_sales_schema())

    assert validator.validate("SELECT customer_id FROM customer WHERE last_name = 'Drop'") == []
    errors = validator.validate("DELETE FROM customer WHERE customer_id = 1")

    assert "Query must start with SELECT or WITH (read-only mode)" in errors
    assert "Blocked keyword detected: DELETE" in errors


def test_dialect_helpers_expose_features_and_basic_adaptation() -> None:
    mysql = get_dialect("mysql")

    assert mysql.ilike_operator == "LIKE"
    assert adapt_sql("SELECT * FROM customer WHERE country ILIKE 'us%'", "postgresql", "mysql") == (
        "SELECT * FROM customer WHERE country LIKE 'us%'"
    )
