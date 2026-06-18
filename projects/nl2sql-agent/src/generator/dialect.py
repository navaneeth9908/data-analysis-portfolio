# NL2SQL Agent - Dialect Adapter
"""Dialect-specific SQL adaptations."""

import re
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class DialectFeatures:
    """Features supported by a SQL dialect."""
    name: str
    supports_cte: bool = True
    supports_window_functions: bool = True
    supports_json: bool = True
    supports_arrays: bool = False
    supports_pivot: bool = False
    supports_unnest: bool = False
    date_trunc_function: str = "DATE_TRUNC"
    current_timestamp: str = "CURRENT_TIMESTAMP"
    limit_syntax: str = "LIMIT {n}"
    offset_syntax: str = "OFFSET {n}"
    ilike_operator: str = "ILIKE"
    regexp_operator: str = "~*"
    cast_syntax: str = "CAST({expr} AS {type})"
    string_concat: str = "||"
    boolean_true: str = "TRUE"
    boolean_false: str = "FALSE"


DIALECTS: Dict[str, DialectFeatures] = {
    "postgresql": DialectFeatures(
        name="postgresql",
        supports_arrays=True,
        supports_json=True,
        supports_pivot=False,
        supports_unnest=True,
        date_trunc_function="DATE_TRUNC",
        current_timestamp="CURRENT_TIMESTAMP",
        limit_syntax="LIMIT {n}",
        offset_syntax="OFFSET {n}",
        ilike_operator="ILIKE",
        regexp_operator="~*",
        cast_syntax="CAST({expr} AS {type})",
        string_concat="||",
    ),
    "mysql": DialectFeatures(
        name="mysql",
        supports_window_functions=True,
        supports_json=True,
        date_trunc_function="DATE_FORMAT",
        current_timestamp="NOW()",
        limit_syntax="LIMIT {n}",
        offset_syntax="OFFSET {n}",
        ilike_operator="LIKE",  # MySQL LIKE is case-insensitive by default
        regexp_operator="REGEXP",
        cast_syntax="CAST({expr} AS {type})",
        string_concat="CONCAT",
    ),
    "sqlite": DialectFeatures(
        name="sqlite",
        supports_window_functions=True,
        supports_json=True,
        date_trunc_function="STRFTIME",
        current_timestamp="CURRENT_TIMESTAMP",
        limit_syntax="LIMIT {n}",
        offset_syntax="OFFSET {n}",
        ilike_operator="LIKE",
        regexp_operator="REGEXP",
        cast_syntax="CAST({expr} AS {type})",
        string_concat="||",
    ),
    "bigquery": DialectFeatures(
        name="bigquery",
        supports_cte=True,
        supports_window_functions=True,
        supports_json=True,
        supports_arrays=True,
        supports_pivot=True,
        supports_unnest=True,
        date_trunc_function="DATE_TRUNC",
        current_timestamp="CURRENT_TIMESTAMP()",
        limit_syntax="LIMIT {n}",
        offset_syntax="OFFSET {n}",
        ilike_operator="LIKE",  # BigQuery LIKE is case-sensitive
        regexp_operator="REGEXP_CONTAINS",
        cast_syntax="CAST({expr} AS {type})",
        string_concat="||",
    ),
    "snowflake": DialectFeatures(
        name="snowflake",
        supports_cte=True,
        supports_window_functions=True,
        supports_json=True,
        supports_arrays=True,
        supports_pivot=True,
        supports_unnest=True,
        date_trunc_function="DATE_TRUNC",
        current_timestamp="CURRENT_TIMESTAMP()",
        limit_syntax="LIMIT {n}",
        offset_syntax="OFFSET {n}",
        ilike_operator="ILIKE",
        regexp_operator="REGEXP_LIKE",
        cast_syntax="CAST({expr} AS {type})",
        string_concat="||",
    ),
    "duckdb": DialectFeatures(
        name="duckdb",
        supports_cte=True,
        supports_window_functions=True,
        supports_json=True,
        supports_arrays=True,
        supports_pivot=True,
        supports_unnest=True,
        date_trunc_function="DATE_TRUNC",
        current_timestamp="CURRENT_TIMESTAMP",
        limit_syntax="LIMIT {n}",
        offset_syntax="OFFSET {n}",
        ilike_operator="ILIKE",
        regexp_operator="~*",
        cast_syntax="CAST({expr} AS {type})",
        string_concat="||",
    ),
}


def get_dialect(name: str) -> DialectFeatures:
    """Get dialect features by name."""
    return DIALECTS.get(name.lower(), DIALECTS["postgresql"])


def adapt_sql(sql: str, from_dialect: str, to_dialect: str) -> str:
    """Adapt SQL from one dialect to another (basic)."""
    from_features = get_dialect(from_dialect)
    to_features = get_dialect(to_dialect)
    
    adapted = sql
    
    # Replace LIMIT/OFFSET syntax
    adapted = re.sub(
        r'\bLIMIT\s+(\d+)', 
        lambda m: to_features.limit_syntax.format(n=m.group(1)),
        adapted,
        flags=re.IGNORECASE
    )
    adapted = re.sub(
        r'\bOFFSET\s+(\d+)', 
        lambda m: to_features.offset_syntax.format(n=m.group(1)),
        adapted,
        flags=re.IGNORECASE
    )
    
    # Replace ILIKE
    adapted = re.sub(
        r'\bILIKE\b',
        to_features.ilike_operator,
        adapted,
        flags=re.IGNORECASE
    )
    
    # Replace CURRENT_TIMESTAMP
    adapted = re.sub(
        r'\bCURRENT_TIMESTAMP\b',
        to_features.current_timestamp,
        adapted,
        flags=re.IGNORECASE
    )
    
    # Replace DATE_TRUNC
    adapted = re.sub(
        r'\bDATE_TRUNC\s*\(',
        f"{to_features.date_trunc_function}(",
        adapted,
        flags=re.IGNORECASE
    )
    
    # Replace string concatenation (PostgreSQL || to MySQL CONCAT)
    if from_features.string_concat == "||" and to_features.string_concat == "CONCAT":
        # This is complex - would need proper parsing
        pass
    
    return adapted


def get_dialect_specific_functions(dialect: str) -> Dict[str, str]:
    """Get dialect-specific function mappings."""
    features = get_dialect(dialect)
    return {
        "date_trunc": features.date_trunc_function,
        "current_timestamp": features.current_timestamp,
        "limit": features.limit_syntax,
        "offset": features.offset_syntax,
        "ilike": features.ilike_operator,
        "regexp": features.regexp_operator,
        "cast": features.cast_syntax,
        "concat": features.string_concat,
    }


__all__ = [
    "DialectFeatures",
    "DIALECTS",
    "get_dialect",
    "adapt_sql",
    "get_dialect_specific_functions",
]