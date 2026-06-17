# NL2SQL Agent - Configuration
"""Configuration management for NL2SQL Agent."""

import os
from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    url: str = "sqlite:///chinook.db"
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: str = "openai"  # openai, anthropic, local
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 4096
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 60


@dataclass
class SafetyConfig:
    """Safety and execution limits."""
    read_only: bool = True
    max_query_cost: int = 1000
    max_rows: int = 10000
    max_execution_time: int = 30
    allow_ddl: bool = False
    allow_dml: bool = False
    blocked_keywords: List[str] = field(default_factory=lambda: [
        "DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE"
    ])


@dataclass
class SchemaConfig:
    """Schema inspection configuration."""
    cache_ttl: int = 3600
    include_views: bool = True
    include_system_tables: bool = False
    include_indexes: bool = True
    include_constraints: bool = True
    sample_rows: int = 3


@dataclass
class GenerationConfig:
    """SQL generation configuration."""
    few_shot_examples: int = 5
    max_retries: int = 3
    validate_syntax: bool = True
    validate_semantics: bool = True
    explain_reasoning: bool = True
    dialect: str = "postgresql"  # postgresql, mysql, sqlite, bigquery, snowflake, duckdb


@dataclass
class ServerConfig:
    """API server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    rate_limit: int = 60


@dataclass
class Config:
    """Main configuration class."""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    schema: SchemaConfig = field(default_factory=SchemaConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    log_level: str = "INFO"
    log_format: str = "json"

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "Config":
        """Load configuration from environment variables."""
        if env_file:
            from dotenv import load_dotenv
            load_dotenv(env_file)

        return cls(
            database=DatabaseConfig(
                url=os.getenv("DATABASE_URL", "sqlite:///chinook.db"),
                pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
                echo=os.getenv("DB_ECHO", "false").lower() == "true",
            ),
            llm=LLMConfig(
                provider=os.getenv("LLM_PROVIDER", "openai"),
                model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
                api_key=os.getenv("LLM_API_KEY"),
                base_url=os.getenv("LLM_BASE_URL"),
            ),
            safety=SafetyConfig(
                read_only=os.getenv("READ_ONLY", "true").lower() == "true",
                max_query_cost=int(os.getenv("MAX_QUERY_COST", "1000")),
                allow_ddl=os.getenv("ALLOW_DDL", "false").lower() == "true",
            ),
            schema=SchemaConfig(
                cache_ttl=int(os.getenv("SCHEMA_CACHE_TTL", "3600")),
            ),
            generation=GenerationConfig(
                dialect=os.getenv("SQL_DIALECT", "postgresql"),
            ),
            server=ServerConfig(
                host=os.getenv("SERVER_HOST", "0.0.0.0"),
                port=int(os.getenv("SERVER_PORT", "8000")),
            ),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """Set global configuration instance."""
    global _config
    _config = config