# NL2SQL Agent — Natural Language to SQL Converter

An intelligent agent that converts natural language questions into executable SQL queries with schema awareness, dialect support, and query validation.

## Features

- **Multi-dialect support**: PostgreSQL, MySQL, SQLite, BigQuery, Snowflake, DuckDB
- **Schema-aware**: Auto-discovers tables, columns, relationships, constraints
- **Query validation**: Syntax check, semantic analysis, dry-run execution
- **Explainability**: Shows reasoning, intermediate steps, generated SQL
- **Safety**: Read-only mode, query cost estimation, injection prevention
- **Interactive**: REPL mode, batch processing, API server

## Architecture

```
nl2sql-agent/
├── src/
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── schema/
│   │   ├── __init__.py
│   │   ├── inspector.py       # Database schema inspection
│   │   ├── cache.py           # Schema caching
│   │   └── models.py          # Table, Column, Relationship models
│   ├── generator/
│   │   ├── __init__.py
│   │   ├── prompt_builder.py  # Few-shot prompt construction
│   │   ├── sql_generator.py   # Core generation logic
│   │   ├── validators.py      # Syntax/semantic validation
│   │   └── dialect.py         # Dialect-specific adaptations
│   ├── executor/
│   │   ├── __init__.py
│   │   ├── runner.py          # Safe query execution
│   │   ├── cost_estimator.py  # Query cost estimation
│   │   └── formatter.py       # Result formatting
│   ├── api/
│   │   ├── __init__.py
│   │   ├── server.py          # FastAPI server
│   │   └── models.py          # Request/Response models
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py            # CLI entry point
│   │   ├── repl.py            # Interactive REPL
│   │   └── commands.py        # CLI commands
│   └── utils/
│       ├── __init__.py
│       ├── logging.py
│       └── exceptions.py
├── tests/
│   ├── test_schema.py
│   ├── test_generator.py
│   ├── test_executor.py
│   └── fixtures/
├── examples/
│   ├── chinook/               # Sample Chinook database
│   └── queries.yaml           # Example NL→SQL pairs
├── requirements.txt
├── pyproject.toml
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Quick Start

```bash
# Install
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your database connection

# Run interactively
nl2sql repl

# Or start API server
nl2sql serve --host 0.0.0.0 --port 8000
```

## Configuration

```yaml
# .env
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
# Or SQLite for testing
# DATABASE_URL=sqlite:///chinook.db

LLM_PROVIDER=openai  # or anthropic, local
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0

# Safety
READ_ONLY=true
MAX_QUERY_COST=1000
ALLOW_DDL=false

# Schema
SCHEMA_CACHE_TTL=3600
INCLUDE_VIEWS=true
INCLUDE_SYSTEM_TABLES=false
```

## Offline sample sales mart

For portfolio demos without private data or API keys, generate a deterministic SQLite sales mart:

```bash
python src/sample_data.py --output examples/sales_mart.sqlite
```

The generated database includes `customers`, `products`, `orders`, and `order_items` tables with foreign keys and enough variation for joins, revenue aggregation, date filtering, and ranking questions. See `examples/README.md` for suggested business questions.

Run an end-to-end offline NL2SQL demo against that mart:

```bash
python -m src.offline_demo "Which region generated the most revenue?" --limit 5
```

The demo builds the SQLite mart if needed, generates a safe SQL query, validates table and column references, executes the query in read-only mode, adds a deterministic business-facing answer summary, and prints an interview-friendly result table. The offline fallback currently covers revenue-by-region, top-products-by-revenue, product units-sold ranking, monthly revenue trend, month-over-month revenue growth, top-customers-by-revenue, repeat-customer detection, product-category revenue mix, category revenue-share contribution, segment average-order-value, region average-order-value, and below-list-price discount analysis questions.

Example output includes an `Answer Summary` block such as:

```text
**West leads with revenue of 6,060.00.**
- Returned 1 row across 2 columns in 2.0ms.
- Top row: region=West, revenue=6,060.00.
```

## Usage Examples

### Natural Language → SQL

```
User: "Show me the top 5 customers by total spending in 2023"

Generated SQL:
WITH customer_spending AS (
  SELECT c.customer_id, c.first_name, c.last_name,
         SUM(i.total) as total_spent
  FROM customer c
  JOIN invoice i ON c.customer_id = i.customer_id
  WHERE strftime('%Y', i.invoice_date) = '2023'
  GROUP BY c.customer_id, c.first_name, c.last_name
)
SELECT * FROM customer_spending
ORDER BY total_spent DESC
LIMIT 5;
```

### Complex Queries Supported

- Multi-table JOINs with automatic relationship detection
- Subqueries and CTEs
- Window functions (ROW_NUMBER, RANK, LAG/LEAD)
- Aggregations with GROUP BY / HAVING
- Date/time operations and relative ranges
- PIVOT / UNPIVOT (dialect-specific)
- Recursive CTEs for hierarchies

## API Endpoints

```
POST   /api/v1/generate      # NL → SQL
POST   /api/v1/validate      # Validate SQL
POST   /api/v1/execute       # Execute query (if enabled)
GET    /api/v1/schema        # Get schema info
GET    /api/v1/health        # Health check
```

## Testing

```bash
pytest tests/ -v --cov=src
```

## License

MIT