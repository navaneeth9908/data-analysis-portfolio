# NL2SQL Agent - Main Package
"""NL2SQL Agent - Natural Language to SQL Converter."""

__version__ = "1.0.0"
__author__ = "Navaneeth Thota"
__description__ = "Convert natural language questions into executable SQL queries with schema awareness, dialect support, and query validation."

from .config import Config, get_config, set_config
from .executor import QueryResult, QueryRunner
from .generator import GenerationResult, SQLGenerator
from .schema import DatabaseSchema, create_inspector, get_cache

__all__ = [
    "Config",
    "get_config",
    "set_config",
    "DatabaseSchema",
    "create_inspector",
    "get_cache",
    "SQLGenerator",
    "GenerationResult",
    "QueryRunner",
    "QueryResult",
]
