# NL2SQL Agent - Main Package
"""NL2SQL Agent - Natural Language to SQL Converter."""

__version__ = "1.0.0"
__author__ = "Navaneeth Thota"
__description__ = "Convert natural language questions into executable SQL queries with schema awareness, dialect support, and query validation."

from .config import Config, get_config, set_config
from .schema import DatabaseSchema, create_inspector, get_cache
from .generator import SQLGenerator, GenerationResult
from .executor import QueryRunner, QueryResult
from .api import create_app
from .cli import cli

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
    "create_app",
    "cli",
]