# NL2SQL Agent - Query Executor
"""Safe SQL query execution with cost estimation."""

import json
import logging
import re
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.engine import Engine, CursorResult
from sqlalchemy.exc import SQLAlchemyError

from ..config import get_config
from ..schema.models import DatabaseSchema

logger = logging.getLogger(__name__)


def strip_string_literals(sql: str) -> str:
    """Replace single-quoted literals so SQL keyword checks ignore user data."""
    return re.sub(r"'(?:''|[^'])*'", "''", sql)


@dataclass
class QueryResult:
    """Result of query execution."""
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float
    query: str
    truncated: bool = False


@dataclass
class CostEstimate:
    """Query cost estimation."""
    estimated_rows: int
    estimated_cost: float
    complexity: str  # LOW, MEDIUM, HIGH
    warnings: List[str]


class CostEstimator:
    """Estimate query execution cost."""

    def __init__(self, schema: DatabaseSchema, engine: Engine):
        self.schema = schema
        self.engine = engine
        self.config = get_config()

    def estimate(self, sql: str) -> CostEstimate:
        """Estimate query cost using EXPLAIN."""
        warnings = []
        estimated_rows = 0
        estimated_cost = 0

        try:
            with self.engine.connect() as conn:
                # Use EXPLAIN for cost estimation
                dialect = self.engine.dialect.name
                if dialect == "postgresql":
                    result = conn.execute(text(f"EXPLAIN (FORMAT JSON) {sql}"))
                    plan = result.scalar()
                    if plan and isinstance(plan, list) and plan:
                        plan_data = plan[0].get("Plan", {})
                        estimated_rows = plan_data.get("Plan Rows", 0)
                        estimated_cost = plan_data.get("Total Cost", 0)
                elif dialect == "mysql":
                    result = conn.execute(text(f"EXPLAIN FORMAT=JSON {sql}"))
                    plan = result.scalar()
                    if plan:
                        if isinstance(plan, str):
                            plan = json.loads(plan)
                        estimated_rows = plan.get("query_block", {}).get("table", {}).get("rows_examined_per_scan", 0)
                        estimated_cost = estimated_rows * 0.1  # Rough estimate
                else:
                    # Fallback: rough estimate from query structure
                    estimated_rows, estimated_cost = self._rough_estimate(sql)

        except Exception as e:
            logger.warning(f"Cost estimation failed: {e}")
            estimated_rows, estimated_cost = self._rough_estimate(sql)
            warnings.append(f"Cost estimation failed: {e}")

        # Determine complexity
        if estimated_cost < 100:
            complexity = "LOW"
        elif estimated_cost < 1000:
            complexity = "MEDIUM"
        else:
            complexity = "HIGH"
            warnings.append(f"High estimated cost: {estimated_cost:.0f}")

        # Check against limit
        if estimated_cost > self.config.safety.max_query_cost:
            warnings.append(f"Estimated cost ({estimated_cost:.0f}) exceeds limit ({self.config.safety.max_query_cost})")

        return CostEstimate(
            estimated_rows=int(estimated_rows),
            estimated_cost=estimated_cost,
            complexity=complexity,
            warnings=warnings,
        )

    def _rough_estimate(self, sql: str) -> tuple:
        """Rough cost estimate from query structure."""
        sql_upper = strip_string_literals(sql).upper()
        base_cost = 10

        # Count joins
        join_count = sql_upper.count("JOIN")
        base_cost += join_count * 50

        # Count subqueries
        subquery_count = sql_upper.count("SELECT") - 1
        base_cost += subquery_count * 30

        # Check for aggregations
        if "GROUP BY" in sql_upper:
            base_cost += 20
        if "ORDER BY" in sql_upper:
            base_cost += 10
        if "DISTINCT" in sql_upper:
            base_cost += 15

        # Estimate rows (very rough)
        estimated_rows = base_cost * 10

        return estimated_rows, float(base_cost)


class QueryRunner:
    """Execute SQL queries safely."""

    def __init__(self, engine: Engine, schema: DatabaseSchema):
        self.engine = engine
        self.schema = schema
        self.config = get_config()
        self.cost_estimator = CostEstimator(schema, engine)

    def execute(self, sql: str, limit: Optional[int] = None) -> QueryResult:
        """Execute a query safely."""
        start_time = time.time()

        # Safety checks
        if self.config.safety.read_only:
            if not self._is_read_only(sql):
                raise ValueError("Only SELECT queries allowed in read-only mode")

        # Cost estimation
        if self.config.safety.max_query_cost > 0:
            estimate = self.cost_estimator.estimate(sql)
            if estimate.estimated_cost > self.config.safety.max_query_cost:
                raise ValueError(f"Query cost too high: {estimate.estimated_cost:.0f} > {self.config.safety.max_query_cost}")
            for warning in estimate.warnings:
                logger.warning(f"Cost estimate warning: {warning}")

        # Apply a sentinel row limit so the runner can detect truncation without
        # returning more than the configured maximum to callers.
        max_rows = limit or self.config.safety.max_rows
        sql = self._apply_limit(sql, max_rows + 1)

        # Execute
        try:
            with self.engine.connect() as conn:
                # Set statement timeout
                dialect = self.engine.dialect.name
                if dialect == "postgresql":
                    timeout_ms = self.config.safety.max_execution_time * 1000
                    conn.execute(text(f"SET LOCAL statement_timeout = {timeout_ms}"))

                result: CursorResult = conn.execute(text(sql))

                columns = list(result.keys()) if result.keys() else []
                rows = []

                for row in result.fetchmany(max_rows + 1):
                    rows.append(dict(row._mapping))

                truncated = len(rows) > max_rows
                if truncated:
                    rows = rows[:max_rows]

                execution_time = (time.time() - start_time) * 1000

                return QueryResult(
                    columns=columns,
                    rows=rows,
                    row_count=len(rows),
                    execution_time_ms=execution_time,
                    query=sql,
                    truncated=truncated,
                )

        except SQLAlchemyError as e:
            logger.error(f"Query execution failed: {e}")
            raise ValueError(f"Execution failed: {e}")

    def _is_read_only(self, sql: str) -> bool:
        """Check if query is read-only."""
        sql_upper = self._strip_comments_and_literals(sql).upper().strip()

        # Must start with SELECT or WITH
        if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
            return False

        # Check for blocked keywords
        for keyword in self.config.safety.blocked_keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", sql_upper):
                return False

        return True

    @staticmethod
    def _strip_comments_and_literals(sql: str) -> str:
        """Remove comments and string contents before read-only safety checks."""
        without_literals = strip_string_literals(sql)
        without_block_comments = re.sub(r"/\*.*?\*/", " ", without_literals, flags=re.DOTALL)
        return re.sub(r"--[^\n]*(?:\n|$)", " ", without_block_comments)

    def _apply_limit(self, sql: str, limit: int) -> str:
        """Apply LIMIT to query if not present."""
        sql_upper = strip_string_literals(sql).upper()

        # Check if LIMIT already present
        if re.search(r"\bLIMIT\b", sql_upper):
            return sql

        # Add LIMIT before final semicolon
        sql = sql.rstrip().rstrip(";")
        dialect = self.engine.dialect.name

        if dialect in ["postgresql", "mysql", "sqlite", "duckdb"]:
            return f"{sql} LIMIT {limit};"
        elif dialect in ["bigquery", "snowflake"]:
            return f"{sql} LIMIT {limit};"
        else:
            return f"{sql} LIMIT {limit};"


class ResultFormatter:
    """Format query results for display."""

    @staticmethod
    def to_table(result: QueryResult) -> str:
        """Format as ASCII table."""
        if not result.columns:
            return "(no results)"

        # Calculate column widths
        widths = {col: len(col) for col in result.columns}
        for row in result.rows:
            for col, val in row.items():
                widths[col] = max(widths[col], len(str(val)) if val else 4)

        # Cap widths
        for col in widths:
            widths[col] = min(widths[col], 50)

        # Build header
        header = " | ".join(col.ljust(widths[col]) for col in result.columns)
        separator = "-+-".join("-" * widths[col] for col in result.columns)

        lines = [header, separator]

        for row in result.rows:
            line = " | ".join(
                ("NULL" if row.get(col) is None else str(row.get(col, "")))[: widths[col]].ljust(widths[col])
                for col in result.columns
            )
            lines.append(line)

        if result.truncated:
            lines.append(f"\n... ({result.row_count} rows shown, more available)")

        lines.append(f"\n{result.row_count} rows in {result.execution_time_ms:.1f}ms")

        return "\n".join(lines)

    @staticmethod
    def to_json(result: QueryResult) -> str:
        """Format as JSON."""
        import json
        return json.dumps({
            "columns": result.columns,
            "rows": result.rows,
            "row_count": result.row_count,
            "execution_time_ms": result.execution_time_ms,
            "truncated": result.truncated,
        }, indent=2, default=str)

    @staticmethod
    def to_csv(result: QueryResult) -> str:
        """Format as CSV."""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(result.columns)
        for row in result.rows:
            writer.writerow([row.get(col, "") for col in result.columns])
        return output.getvalue()


@contextmanager
def query_context(engine: Engine):
    """Context manager for query execution with cleanup."""
    try:
        yield engine
    finally:
        pass  # Engine handles connection pooling


__all__ = [
    "QueryResult",
    "CostEstimate",
    "CostEstimator",
    "QueryRunner",
    "ResultFormatter",
    "query_context",
]
