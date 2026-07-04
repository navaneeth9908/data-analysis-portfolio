"""Offline end-to-end demo for the NL2SQL sample sales mart.

This module wires together the deterministic SQLite mart, rule-backed SQL
fallback generation, safe execution, and table formatting so the portfolio demo
can be exercised without API keys or private databases.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine

from .executor.insights import ResultInsight, explain_result
from .executor.runner import QueryRunner, ResultFormatter
from .generator.sql_generator import SQLGenerator
from .sample_data import build_sales_mart
from .schema.models import Column, ColumnType, DatabaseSchema, Table


@dataclass
class DemoAnswer:
    """Complete offline response for a natural-language analytics question."""

    question: str
    sql: str
    reasoning: str
    tables_used: list[str]
    validation_errors: list[str]
    rows: list[dict[str, Any]]
    table: str
    insight: ResultInsight | None = None


def build_sample_mart_schema() -> DatabaseSchema:
    """Return the schema model for the deterministic SQLite sales mart."""
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


def answer_sample_question(
    question: str,
    db_path: str | Path = "examples/sales_mart.sqlite",
    limit: int = 10,
) -> DemoAnswer:
    """Generate SQL for a sample question, execute it, and format the result."""
    path = Path(db_path)
    build_sales_mart(path)

    schema = build_sample_mart_schema()
    generation = SQLGenerator(schema).generate(question)
    if generation.validation_errors:
        return DemoAnswer(
            question=question,
            sql=generation.sql,
            reasoning=generation.reasoning,
            tables_used=generation.tables_used,
            validation_errors=generation.validation_errors,
            rows=[],
            table="Validation failed; query was not executed.",
        )

    engine = create_engine(f"sqlite:///{path.as_posix()}")
    try:
        result = QueryRunner(engine, schema).execute(generation.sql, limit=limit)
        rendered = ResultFormatter.to_table(result)
        insight = explain_result(question, result)
        rows = result.rows
    finally:
        engine.dispose()

    return DemoAnswer(
        question=question,
        sql=generation.sql,
        reasoning=generation.reasoning,
        tables_used=generation.tables_used,
        validation_errors=[],
        rows=rows,
        table=rendered,
        insight=insight,
    )


def main(argv: list[str] | None = None) -> int:
    """Run the offline demo from the command line."""
    parser = argparse.ArgumentParser(description="Ask an offline question against the sample sales mart.")
    parser.add_argument("question", help="Natural-language analytics question to answer.")
    parser.add_argument(
        "--db-path",
        default="examples/sales_mart.sqlite",
        help="Path where the generated SQLite demo mart should live.",
    )
    parser.add_argument("--limit", type=int, default=10, help="Maximum result rows to display.")
    args = parser.parse_args(argv)

    answer = answer_sample_question(args.question, db_path=args.db_path, limit=args.limit)
    print(f"Question: {answer.question}")
    print("\nReasoning:")
    print(answer.reasoning)
    print("\nGenerated SQL:")
    print(answer.sql)
    if answer.validation_errors:
        print("\nValidation errors:")
        for error in answer.validation_errors:
            print(f"- {error}")
        return 1
    print("\nAnswer Summary:")
    if answer.insight is not None:
        print(answer.insight.to_markdown())
    print("\nResult:")
    print(answer.table)
    return 0


if __name__ == "__main__":  # pragma: no cover - covered by direct main() test
    raise SystemExit(main())
