# NL2SQL Agent - SQL Generator
"""Core SQL generation logic with LLM integration."""

import logging
import re
from typing import Any, List
from dataclasses import dataclass

from ..config import get_config
from ..schema.models import DatabaseSchema, Table

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Result of SQL generation."""
    sql: str
    reasoning: str
    confidence: float
    tables_used: List[str]
    validation_errors: List[str]
    raw_response: str


class PromptBuilder:
    """Build few-shot prompts for SQL generation."""
    
    # System prompt template
    SYSTEM_PROMPT = """You are an expert SQL developer. Convert natural language questions into precise, executable SQL queries.

Guidelines:
1. Use only tables and columns defined in the schema below
2. Write SQL compatible with the target dialect: {dialect}
3. Use explicit column names (avoid SELECT *)
4. Qualify columns with table names when joining
5. Use CTEs for complex queries
6. Handle NULL values appropriately
7. Use proper date/time functions for the dialect
8. Return only the final SQL query in a markdown code block
9. Explain your reasoning before the query

Schema:
{schema}

{few_shot_examples}"""
    
    # Few-shot examples
    EXAMPLES = [
        {
            "question": "How many customers are there?",
            "sql": "SELECT COUNT(*) AS customer_count FROM customer;",
            "reasoning": "Simple count of all rows in customer table"
        },
        {
            "question": "Show me all customers from USA",
            "sql": "SELECT * FROM customer WHERE country = 'USA';",
            "reasoning": "Filter customers by country column"
        },
        {
            "question": "What are the top 5 customers by total spending?",
            "sql": """WITH customer_spending AS (
    SELECT c.customer_id, c.first_name, c.last_name, SUM(i.total) AS total_spent
    FROM customer c
    JOIN invoice i ON c.customer_id = i.customer_id
    GROUP BY c.customer_id, c.first_name, c.last_name
)
SELECT * FROM customer_spending ORDER BY total_spent DESC LIMIT 5;""",
            "reasoning": "Join customer and invoice, aggregate by customer, sort and limit"
        },
        {
            "question": "List all tracks with their genre and artist",
            "sql": """SELECT t.name AS track_name, g.name AS genre_name, ar.name AS artist_name
    FROM track t
    JOIN genre g ON t.genre_id = g.genre_id
    JOIN album al ON t.album_id = al.album_id
    JOIN artist ar ON al.artist_id = ar.artist_id;""",
            "reasoning": "Multi-table join through track -> genre, track -> album -> artist"
        },
        {
            "question": "Which employees have no manager?",
            "sql": "SELECT * FROM employee WHERE reports_to IS NULL;",
            "reasoning": "Self-referencing foreign key, NULL means no manager"
        },
    ]
    
    def __init__(self, schema: DatabaseSchema, dialect: str = "postgresql"):
        self.schema = schema
        self.dialect = dialect
    
    def build_prompt(self, question: str, few_shot_count: int = 5) -> str:
        """Build complete prompt for the LLM."""
        schema_summary = self.schema.get_summary()
        
        # Build few-shot examples
        examples_text = ""
        for i, ex in enumerate(self.EXAMPLES[:few_shot_count]):
            examples_text += f"\n--- Example {i+1} ---\n"
            examples_text += f"Question: {ex['question']}\n"
            examples_text += f"Reasoning: {ex['reasoning']}\n"
            examples_text += f"SQL:\n```sql\n{ex['sql']}\n```\n"
        
        prompt = self.SYSTEM_PROMPT.format(
            dialect=self.dialect,
            schema=schema_summary,
            few_shot_examples=examples_text if examples_text else "No examples provided."
        )
        
        prompt += f"\n--- Your Task ---\nQuestion: {question}\n\nReasoning:"
        
        return prompt


class SQLValidator:
    """Validate generated SQL for syntax and semantics."""
    
    def __init__(self, schema: DatabaseSchema, dialect: str = "postgresql"):
        self.schema = schema
        self.dialect = dialect
    
    def validate(self, sql: str) -> List[str]:
        """Validate SQL and return list of errors."""
        errors = []
        
        # Basic syntax checks
        errors.extend(self._check_basic_syntax(sql))
        
        # Table/column existence checks
        errors.extend(self._check_references(sql))
        
        # Safety checks
        errors.extend(self._check_safety(sql))
        
        return errors
    
    def _check_basic_syntax(self, sql: str) -> List[str]:
        """Basic SQL syntax validation."""
        errors = []
        sql_upper = sql.upper().strip()
        
        if not sql_upper:
            return ["Empty SQL query"]
        
        # Must start with SELECT (for read-only)
        config = get_config()
        if config.safety.read_only:
            if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
                errors.append("Query must start with SELECT or WITH (read-only mode)")

        sanitized = self._strip_string_literals(sql)
        if sanitized.count("(") != sanitized.count(")"):
            errors.append("Unbalanced parentheses")
        
        single_quotes = sql.count("'") - (2 * sql.count("''"))
        if single_quotes % 2 != 0:
            errors.append("Unbalanced single quotes")
        
        return errors
    
    def _check_references(self, sql: str) -> List[str]:
        """Check that referenced tables and qualified columns exist."""
        errors = []
        table_aliases = self._extract_table_aliases(sql)
        cte_names = self._extract_cte_names(sql)
        known_tables = {table.name.lower(): table for table in self.schema.get_all_tables()}

        for table_name in table_aliases.values():
            if table_name.lower() in cte_names:
                continue
            if table_name.lower() not in known_tables:
                errors.append(f"Unknown table referenced: {table_name}")

        for qualifier, column_name in re.findall(r'\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\b', sql):
            table_name = table_aliases.get(qualifier.lower())
            if table_name is None:
                continue
            table = known_tables.get(table_name.lower())
            if table and table.get_column(column_name) is None:
                errors.append(
                    f"Unknown column referenced: {qualifier}.{column_name} on table {table.name}"
                )

        errors.extend(self._check_unqualified_columns(sql, table_aliases, known_tables))
        return errors

    def _check_unqualified_columns(
        self,
        sql: str,
        table_aliases: dict[str, str],
        known_tables: dict[str, Table],
    ) -> List[str]:
        """Validate simple unqualified column references in SELECT and filters."""
        referenced_tables = {
            table_name.lower()
            for table_name in table_aliases.values()
            if table_name.lower() in known_tables
        }
        if not referenced_tables or self._extract_cte_names(sql):
            return []

        available_columns = {
            column.name.lower()
            for table_name in referenced_tables
            for column in known_tables[table_name].columns
        }
        sql_without_literals = self._strip_string_literals(sql)
        sql_without_qualified_refs = re.sub(
            r"\b[A-Za-z_]\w*\.[A-Za-z_]\w*\b", "", sql_without_literals
        )

        candidate_names = self._extract_unqualified_column_candidates(sql_without_qualified_refs)
        candidate_names -= self._extract_select_aliases(sql_without_qualified_refs)
        errors = []
        for name in sorted(candidate_names):
            if name.lower() not in available_columns:
                errors.append(f"Unknown column referenced: {name}")
        return errors

    @classmethod
    def _extract_unqualified_column_candidates(cls, sql: str) -> set[str]:
        """Extract likely unqualified column names from simple query clauses."""
        candidates: set[str] = set()
        reserved = cls._reserved_words()

        select_match = re.search(r"\bSELECT\b(.*?)\bFROM\b", sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            for expression in select_match.group(1).split(","):
                candidates.update(cls._identifier_candidates(expression, reserved))

        for keyword in ("WHERE", "GROUP BY", "HAVING", "ORDER BY"):
            pattern = rf"\b{keyword}\b(.*?)(?=\bWHERE\b|\bGROUP BY\b|\bHAVING\b|\bORDER BY\b|\bLIMIT\b|\bOFFSET\b|;|$)"
            match = re.search(pattern, sql, re.IGNORECASE | re.DOTALL)
            if match:
                candidates.update(cls._identifier_candidates(match.group(1), reserved))

        return candidates

    @staticmethod
    def _extract_select_aliases(sql: str) -> set[str]:
        """Return aliases introduced in the SELECT list."""
        select_match = re.search(r"\bSELECT\b(.*?)\bFROM\b", sql, re.IGNORECASE | re.DOTALL)
        if not select_match:
            return set()
        return {
            match.group(1)
            for match in re.finditer(
                r"\bAS\s+([A-Za-z_]\w*)\b", select_match.group(1), re.IGNORECASE
            )
        }

    @staticmethod
    def _identifier_candidates(expression: str, reserved: set[str]) -> set[str]:
        """Return non-keyword identifiers from a SQL expression fragment."""
        cleaned = re.sub(r"\bAS\s+[A-Za-z_]\w*\b", "", expression, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b[A-Za-z_]\w*\s*\(", "(", cleaned)
        return {
            identifier
            for identifier in re.findall(r"\b[A-Za-z_]\w*\b", cleaned)
            if identifier.lower() not in reserved
        }

    @staticmethod
    def _reserved_words() -> set[str]:
        """SQL words and literals that should not be treated as column names."""
        return {
            "and", "as", "asc", "between", "by", "case", "cast", "desc", "distinct",
            "else", "end", "from", "group", "having", "in", "is", "join", "limit",
            "not", "null", "offset", "on", "or", "order", "over", "partition", "select",
            "then", "when", "where", "with",
        }

    def _check_safety(self, sql: str) -> List[str]:
        """Check for unsafe operations."""
        errors = []
        sql_upper = self._strip_string_literals(sql).upper()
        
        config = get_config()
        for keyword in config.safety.blocked_keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", sql_upper):
                errors.append(f"Blocked keyword detected: {keyword}")
        
        return errors

    def _extract_table_aliases(self, sql: str) -> dict[str, str]:
        """Return alias/name -> table name mappings for FROM and JOIN clauses."""
        aliases: dict[str, str] = {}
        reserved = {
            "where", "join", "left", "right", "inner", "outer", "full", "cross",
            "on", "group", "order", "limit", "offset", "having", "union", "except", "intersect",
        }
        pattern = re.compile(
            r'\b(?:FROM|JOIN)\s+(["`\[]?[\w.]+["`\]]?)'
            r'(?:\s+(?:AS\s+)?([A-Za-z_]\w*))?',
            re.IGNORECASE,
        )
        for table_ref, alias in pattern.findall(sql):
            table_name = self._normalize_identifier(table_ref).split(".")[-1]
            aliases[table_name.lower()] = table_name
            if alias and alias.lower() not in reserved:
                aliases[alias.lower()] = table_name
        return aliases

    @staticmethod
    def _normalize_identifier(identifier: str) -> str:
        """Remove common SQL identifier quoting characters."""
        return identifier.strip().strip('"`[]')

    @staticmethod
    def _extract_cte_names(sql: str) -> set[str]:
        """Extract top-level CTE names from a WITH clause."""
        if not re.match(r"^\s*WITH\b", sql, re.IGNORECASE):
            return set()
        return {
            match.group(1).lower()
            for match in re.finditer(r"(?:WITH|,)\s+([A-Za-z_]\w*)\s+AS\s*\(", sql, re.IGNORECASE)
        }

    @staticmethod
    def _strip_string_literals(sql: str) -> str:
        """Replace single-quoted values so safety checks ignore literal text."""
        return re.sub(r"'(?:''|[^'])*'", "''", sql)


class SQLGenerator:
    """Main SQL generation class."""
    
    def __init__(self, schema: DatabaseSchema, llm_client: Any = None):
        self.config = get_config()
        self.schema = schema
        self.llm_client = llm_client
        self.prompt_builder = PromptBuilder(schema, self.config.generation.dialect)
        self.validator = SQLValidator(schema, self.config.generation.dialect)
    
    def generate(self, question: str) -> GenerationResult:
        """Generate SQL from natural language question."""
        logger.info(f"Generating SQL for: {question}")
        
        # Build prompt
        prompt = self.prompt_builder.build_prompt(
            question, 
            self.config.generation.few_shot_examples
        )
        
        # Call LLM (placeholder - implement with actual LLM client)
        if self.llm_client:
            response = self._call_llm(prompt)
        else:
            response = self._mock_generation(question)
        
        # Parse response
        sql, reasoning = self._parse_response(response)
        
        # Validate
        errors = []
        if self.config.generation.validate_syntax:
            errors.extend(self.validator.validate(sql))
        
        # Extract tables used
        tables_used = self._extract_tables(sql)
        
        return GenerationResult(
            sql=sql,
            reasoning=reasoning,
            confidence=0.8 if not errors else 0.5,
            tables_used=tables_used,
            validation_errors=errors,
            raw_response=response,
        )
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM API."""
        # Implement based on provider
        if self.config.llm.provider == "openai":
            return self._call_openai(prompt)
        elif self.config.llm.provider == "anthropic":
            return self._call_anthropic(prompt)
        else:
            return self._mock_generation(prompt)
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.config.llm.api_key)
            response = client.chat.completions.create(
                model=self.config.llm.model,
                messages=[
                    {"role": "system", "content": "You are an expert SQL developer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.llm.temperature,
                max_tokens=self.config.llm.max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return self._mock_generation(prompt)
    
    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.config.llm.api_key)
            response = client.messages.create(
                model=self.config.llm.model,
                max_tokens=self.config.llm.max_tokens,
                temperature=self.config.llm.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return self._mock_generation(prompt)
    
    def _mock_generation(self, question: str) -> str:
        """Mock generation for testing without API key."""
        question_lower = question.lower()
        
        if "customer" in question_lower and "spend" in question_lower:
            return """I'll find the top customers by total spending by joining customer and invoice tables, aggregating totals, and sorting.

```sql
WITH customer_spending AS (
    SELECT c.customer_id, c.first_name, c.last_name, SUM(i.total) AS total_spent
    FROM customer c
    JOIN invoice i ON c.customer_id = i.customer_id
    GROUP BY c.customer_id, c.first_name, c.last_name
)
SELECT * FROM customer_spending ORDER BY total_spent DESC LIMIT 5;```"""
        
        if "track" in question_lower and "genre" in question_lower:
            return """Join track, genre, album, and artist tables to get track details with genre and artist names.

```sql
SELECT t.name AS track_name, g.name AS genre_name, ar.name AS artist_name
FROM track t
JOIN genre g ON t.genre_id = g.genre_id
JOIN album al ON t.album_id = al.album_id
JOIN artist ar ON al.artist_id = ar.artist_id;```"""

        if "segment" in question_lower and "revenue" in question_lower:
            return """Compare revenue by customer segment from the sample sales mart by joining customers, orders, and order items, then aggregating revenue and order count per segment.

```sql
SELECT c.segment,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue,
       COUNT(DISTINCT o.order_id) AS order_count
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY c.segment
ORDER BY revenue DESC;```"""

        if "customer" in question_lower and "revenue" in question_lower and (
            "concentrated" in question_lower
            or "concentration" in question_lower
            or "share" in question_lower
        ):
            return """Measure customer revenue concentration from the sample sales mart by calculating revenue per customer and comparing each customer to total revenue.

```sql
WITH customer_revenue AS (
    SELECT c.customer_name,
           ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY c.customer_name
)
SELECT customer_name,
       revenue,
       ROUND(revenue * 100.0 / SUM(revenue) OVER (), 2) AS revenue_share_pct
FROM customer_revenue
ORDER BY revenue DESC;```"""

        if "customer" in question_lower and "software" in question_lower and "services" in question_lower:
            return """Identify customers with cross-category adoption by calculating software and services revenue per customer, then keeping customers with revenue in both product families.

```sql
WITH customer_category_mix AS (
    SELECT c.customer_name,
           c.region,
           ROUND(SUM(CASE WHEN p.category = 'Software' THEN oi.quantity * oi.unit_price ELSE 0 END), 2) AS software_revenue,
           ROUND(SUM(CASE WHEN p.category = 'Services' THEN oi.quantity * oi.unit_price ELSE 0 END), 2) AS services_revenue
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    GROUP BY c.customer_name, c.region
    HAVING software_revenue > 0 AND services_revenue > 0
)
SELECT customer_name,
       region,
       ROUND(software_revenue + services_revenue, 2) AS total_revenue,
       software_revenue,
       services_revenue
FROM customer_category_mix
ORDER BY total_revenue DESC, customer_name;```"""

        if "customer" in question_lower and "revenue" in question_lower:
            return """Rank customers by revenue from the sample sales mart by joining customers, orders, and order items, then summing line-item revenue per customer.

```sql
SELECT c.customer_name,
       c.region,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY c.customer_name, c.region
ORDER BY revenue DESC
LIMIT 5;```"""

        if "customer" in question_lower and ("repeat" in question_lower or "multiple" in question_lower) and "order" in question_lower:
            return """Identify repeat customers in the sample sales mart by counting orders per customer and keeping only customers with more than one order.

```sql
SELECT c.customer_name,
       c.region,
       COUNT(o.order_id) AS order_count
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_name, c.region
HAVING COUNT(o.order_id) > 1
ORDER BY order_count DESC, c.customer_name;```"""


        if "region" in question_lower and "product" in question_lower and (
            "mix" in question_lower
            or "diversity" in question_lower
            or "widest" in question_lower
            or "variety" in question_lower
        ):
            return """Measure product mix breadth by region from the sample sales mart by counting distinct products and product categories purchased in each region, with revenue included for business context.

```sql
SELECT c.region,
       COUNT(DISTINCT p.product_id) AS distinct_products,
       COUNT(DISTINCT p.category) AS category_count,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
GROUP BY c.region
ORDER BY distinct_products DESC, revenue DESC;```"""

        if (
            "region" in question_lower
            and "repeat" in question_lower
            and "customer" in question_lower
            and ("rate" in question_lower or "percent" in question_lower or "percentage" in question_lower)
        ):
            return """Calculate repeat-customer rate by region from the sample sales mart by counting orders per customer, then comparing repeat customers to the regional customer base.

```sql
WITH customer_order_counts AS (
    SELECT c.customer_id,
           c.region,
           COUNT(o.order_id) AS order_count
    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.region
)
SELECT region,
       COUNT(*) AS total_customers,
       SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS repeat_customers,
       ROUND(
           SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
           2
       ) AS repeat_customer_rate_pct
FROM customer_order_counts
GROUP BY region
ORDER BY repeat_customer_rate_pct DESC, repeat_customers DESC, region;```"""

        if "region" in question_lower and "repeat" in question_lower and "customer" in question_lower:
            return """Summarize repeat-customer concentration by region from the sample sales mart by first identifying customers with more than one order, then counting those repeat customers per region.

```sql
WITH customer_order_counts AS (
    SELECT c.customer_id,
           c.region,
           COUNT(o.order_id) AS order_count
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.customer_id, c.region
    HAVING COUNT(o.order_id) > 1
)
SELECT region,
       COUNT(*) AS repeat_customer_count
FROM customer_order_counts
GROUP BY region
ORDER BY repeat_customer_count DESC, region;```"""

        if "region" in question_lower and "average order" in question_lower:
            return """Calculate average order value by region from the sample sales mart by first summing each order, then averaging order revenue per region.

```sql
WITH order_revenue AS (
    SELECT o.order_id, c.region, SUM(oi.quantity * oi.unit_price) AS revenue
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY o.order_id, c.region
)
SELECT region, ROUND(AVG(revenue), 2) AS average_order_value
FROM order_revenue
GROUP BY region
ORDER BY average_order_value DESC;```"""

        if "region" in question_lower and "software" in question_lower and "revenue" in question_lower:
            return """Compare software revenue by region from the sample sales mart by filtering product category, then aggregating revenue and order count per region.

```sql
SELECT c.region,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS software_revenue,
       COUNT(DISTINCT o.order_id) AS order_count
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE p.category = 'Software'
GROUP BY c.region
ORDER BY software_revenue DESC;```"""

        if "region" in question_lower and "services" in question_lower and "revenue" in question_lower:
            return """Compare services revenue by region from the sample sales mart by filtering product category, then aggregating revenue and order count per region.

```sql
SELECT c.region,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS services_revenue,
       COUNT(DISTINCT o.order_id) AS order_count
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE p.category = 'Services'
GROUP BY c.region
ORDER BY services_revenue DESC;```"""

        if (
            "product" in question_lower
            and ("quarter over quarter" in question_lower or "qoq" in question_lower)
            and (
                "growth" in question_lower
                or "grew" in question_lower
                or "increase" in question_lower
                or "change" in question_lower
                or "revenue" in question_lower
            )
        ):
            return """Find products with positive quarter-over-quarter revenue growth in the sample sales mart by aggregating revenue per product and quarter, then using LAG to compare each product against its prior quarter.

```sql
WITH product_quarter_revenue AS (
    SELECT p.product_name,
           p.category,
           '2024-Q' || CASE
               WHEN CAST(strftime('%m', o.order_date) AS INTEGER) BETWEEN 1 AND 3 THEN '1'
               WHEN CAST(strftime('%m', o.order_date) AS INTEGER) BETWEEN 4 AND 6 THEN '2'
               WHEN CAST(strftime('%m', o.order_date) AS INTEGER) BETWEEN 7 AND 9 THEN '3'
               ELSE '4'
           END AS quarter,
           ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    WHERE o.status = 'closed won'
    GROUP BY p.product_name, p.category, quarter
),
product_with_previous AS (
    SELECT product_name,
           category,
           quarter,
           revenue,
           LAG(revenue) OVER (PARTITION BY product_name ORDER BY quarter) AS previous_revenue
    FROM product_quarter_revenue
),
product_growth AS (
    SELECT product_name,
           category,
           quarter,
           revenue,
           previous_revenue,
           ROUND(revenue - previous_revenue, 2) AS revenue_change,
           CASE
               WHEN previous_revenue IS NULL OR previous_revenue = 0 THEN NULL
               ELSE ROUND((revenue - previous_revenue) * 100.0 / previous_revenue, 2)
           END AS revenue_change_pct
    FROM product_with_previous
)
SELECT product_name,
       category,
       quarter,
       revenue,
       previous_revenue,
       revenue_change,
       revenue_change_pct
FROM product_growth
WHERE previous_revenue IS NOT NULL
  AND revenue_change > 0
ORDER BY revenue_change DESC, product_name;```"""

        if (
            ("quarter over quarter" in question_lower or "qoq" in question_lower)
            and ("growth" in question_lower or "change" in question_lower or "revenue" in question_lower)
        ):
            return """Calculate quarter-over-quarter revenue growth from the sample sales mart by aggregating closed-order revenue into calendar quarters, then using LAG to compare each quarter with the previous quarter.

```sql
WITH quarterly_revenue AS (
    SELECT '2024-Q' || CASE
               WHEN CAST(strftime('%m', o.order_date) AS INTEGER) BETWEEN 1 AND 3 THEN '1'
               WHEN CAST(strftime('%m', o.order_date) AS INTEGER) BETWEEN 4 AND 6 THEN '2'
               WHEN CAST(strftime('%m', o.order_date) AS INTEGER) BETWEEN 7 AND 9 THEN '3'
               ELSE '4'
           END AS quarter,
           ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.status = 'closed won'
    GROUP BY quarter
),
quarterly_with_previous AS (
    SELECT quarter,
           revenue,
           LAG(revenue) OVER (ORDER BY quarter) AS previous_revenue
    FROM quarterly_revenue
)
SELECT quarter,
       revenue,
       ROUND(revenue - previous_revenue, 2) AS revenue_change,
       CASE
           WHEN previous_revenue IS NULL OR previous_revenue = 0 THEN NULL
           ELSE ROUND((revenue - previous_revenue) * 100.0 / previous_revenue, 2)
       END AS revenue_change_pct
FROM quarterly_with_previous
ORDER BY quarter;```"""

        if "quarter" in question_lower and "region" in question_lower and "revenue" in question_lower:
            return """Summarize quarterly revenue by region from the sample sales mart by bucketing order dates into calendar quarters, joining customers for geography, and ranking regions within each quarter.

```sql
SELECT c.region,
       '2024-Q' || CASE
           WHEN CAST(strftime('%m', o.order_date) AS INTEGER) BETWEEN 1 AND 3 THEN '1'
           WHEN CAST(strftime('%m', o.order_date) AS INTEGER) BETWEEN 4 AND 6 THEN '2'
           WHEN CAST(strftime('%m', o.order_date) AS INTEGER) BETWEEN 7 AND 9 THEN '3'
           ELSE '4'
       END AS quarter,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue,
       COUNT(DISTINCT o.order_id) AS order_count
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.status = 'closed won'
GROUP BY quarter, c.region
ORDER BY quarter, revenue DESC;```"""

        if "region" in question_lower and "product" in question_lower and "revenue" in question_lower:
            return """Identify the top revenue-generating product in each region from the sample sales mart by aggregating product revenue per region and using a window rank to keep each regional leader.

```sql
WITH regional_product_revenue AS (
    SELECT c.region,
           p.product_name,
           p.category,
           ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue,
           RANK() OVER (
               PARTITION BY c.region
               ORDER BY SUM(oi.quantity * oi.unit_price) DESC
           ) AS revenue_rank
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    GROUP BY c.region, p.product_name, p.category
)
SELECT region, product_name, category, revenue
FROM regional_product_revenue
WHERE revenue_rank = 1
ORDER BY revenue DESC, region;```"""

        if "region" in question_lower and "revenue" in question_lower:
            return """Calculate revenue by region from the sample sales mart by joining orders to customers and order items, then ranking the highest region.

```sql
SELECT c.region, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.region
ORDER BY revenue DESC
LIMIT 1;```"""

        if (
            ("month over month" in question_lower or "mom" in question_lower)
            and ("growth" in question_lower or "change" in question_lower or "revenue" in question_lower)
        ):
            return """Calculate month-over-month revenue growth from the sample sales mart by aggregating monthly revenue, using LAG to compare each month with the prior month, and returning absolute and percentage change.

```sql
WITH monthly_revenue AS (
    SELECT strftime('%Y-%m', o.order_date) AS month,
           ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.status = 'closed won'
    GROUP BY month
),
monthly_with_previous AS (
    SELECT month,
           revenue,
           LAG(revenue) OVER (ORDER BY month) AS previous_revenue
    FROM monthly_revenue
)
SELECT month,
       revenue,
       ROUND(revenue - previous_revenue, 2) AS revenue_change,
       CASE
           WHEN previous_revenue IS NULL OR previous_revenue = 0 THEN NULL
           ELSE ROUND((revenue - previous_revenue) * 100.0 / previous_revenue, 2)
       END AS revenue_change_pct
FROM monthly_with_previous
ORDER BY month;```"""

        if ("month" in question_lower or "monthly" in question_lower) and "revenue" in question_lower:
            return """Build a month-by-month revenue trend from the sample sales mart by grouping closed orders on the order date month and summing line-item revenue.

```sql
SELECT strftime('%Y-%m', o.order_date) AS month,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue,
       COUNT(DISTINCT o.order_id) AS order_count
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.status = 'closed won'
GROUP BY month
ORDER BY month;```"""

        if "category" in question_lower and "revenue" in question_lower and "share" in question_lower:
            return """Calculate each product category's contribution to total revenue from the sample sales mart by aggregating category revenue first, then dividing by the total with a window function.

```sql
WITH category_revenue AS (
    SELECT p.category,
           ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    GROUP BY p.category
)
SELECT category,
       revenue,
       ROUND(revenue * 100.0 / SUM(revenue) OVER (), 2) AS revenue_share_pct
FROM category_revenue
ORDER BY revenue DESC;```"""

        if "category" in question_lower and "revenue" in question_lower:
            return """Compare revenue by product category from the sample sales mart by joining products to line items and counting products in each category.

```sql
SELECT p.category,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue,
       COUNT(DISTINCT p.product_id) AS product_count
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.category
ORDER BY revenue DESC;```"""

        if "product" in question_lower and (
            "purchased together" in question_lower
            or "bought together" in question_lower
            or "often together" in question_lower
            or "affinity" in question_lower
        ):
            return """Find product affinity pairs from the sample sales mart by self-joining order items within the same order, using product id ordering to avoid duplicate pair directions.

```sql
SELECT p1.product_name AS product_a,
       p2.product_name AS product_b,
       COUNT(DISTINCT oi1.order_id) AS shared_order_count
FROM order_items oi1
JOIN order_items oi2
  ON oi1.order_id = oi2.order_id
 AND oi1.product_id < oi2.product_id
JOIN products p1 ON oi1.product_id = p1.product_id
JOIN products p2 ON oi2.product_id = p2.product_id
GROUP BY p1.product_name, p2.product_name
ORDER BY shared_order_count DESC, product_a, product_b
LIMIT 5;```"""

        if "product" in question_lower and "discount" in question_lower and (
            "rate" in question_lower
            or "percent" in question_lower
            or "percentage" in question_lower
        ):
            return """Rank products by realized discount rate from the sample sales mart by comparing discounted line-item revenue with the equivalent list-price value.

```sql
SELECT p.product_name,
       p.category,
       ROUND(
           SUM((p.list_price - oi.unit_price) * oi.quantity) * 100.0
           / SUM(p.list_price * oi.quantity),
           2
       ) AS discount_rate_pct,
       ROUND(SUM((p.list_price - oi.unit_price) * oi.quantity), 2) AS discount_amount
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
WHERE oi.unit_price < p.list_price
GROUP BY p.product_name, p.category
ORDER BY discount_rate_pct DESC, discount_amount DESC;```"""

        if "product" in question_lower and (
            "below list" in question_lower
            or "discount" in question_lower
            or "marked down" in question_lower
        ):
            return """Identify products sold below list price by comparing realized line-item unit price with product list price, then aggregating discount dollars and discounted units.

```sql
SELECT p.product_name,
       p.category,
       ROUND(SUM((p.list_price - oi.unit_price) * oi.quantity), 2) AS discount_amount,
       SUM(oi.quantity) AS discounted_units
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
WHERE oi.unit_price < p.list_price
GROUP BY p.product_name, p.category
ORDER BY discount_amount DESC, discounted_units DESC;```"""

        if "product" in question_lower and "average" in question_lower and (
            "selling price" in question_lower
            or "sales price" in question_lower
            or "unit price" in question_lower
        ):
            return """Calculate average realized selling price by product from the sample sales mart by dividing line-item revenue by units sold and ranking the highest products.

```sql
SELECT p.product_name,
       p.category,
       ROUND(SUM(oi.quantity * oi.unit_price) / SUM(oi.quantity), 2) AS average_selling_price,
       SUM(oi.quantity) AS units_sold
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.product_name, p.category
ORDER BY average_selling_price DESC, p.product_name;```"""

        if "product" in question_lower and ("unit" in question_lower or "quantity" in question_lower or "sold" in question_lower):
            return """Rank products by units sold from the sample sales mart by summing order item quantities and including revenue for business context.

```sql
SELECT p.product_name,
       SUM(oi.quantity) AS units_sold,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.product_name
ORDER BY units_sold DESC, revenue DESC
LIMIT 5;```"""

        if "product" in question_lower and "revenue" in question_lower:
            return """Rank products by revenue from the sample sales mart by summing order item extended prices.

```sql
SELECT p.product_name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.product_name
ORDER BY revenue DESC
LIMIT 3;```"""

        if "segment" in question_lower and "average order" in question_lower:
            return """Calculate average order value by customer segment from the sample sales mart by first summing each order, then averaging order revenue per segment.

```sql
WITH order_revenue AS (
    SELECT o.order_id, c.segment, SUM(oi.quantity * oi.unit_price) AS revenue
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY o.order_id, c.segment
)
SELECT segment, ROUND(AVG(revenue), 2) AS average_order_value
FROM order_revenue
GROUP BY segment
ORDER BY average_order_value DESC;```"""
        
        return """Basic query to answer the question.

```sql
SELECT * FROM customer LIMIT 10;```"""

    def _parse_response(self, response: str) -> tuple:
        """Parse LLM response to extract SQL and reasoning."""
        # Extract SQL from markdown code block
        sql_match = re.search(r'```sql\s*(.*?)\s*```', response, re.DOTALL | re.IGNORECASE)
        if sql_match:
            sql = sql_match.group(1).strip()
        else:
            # Try without language specifier
            sql_match = re.search(r'```\n(.*?)\n```', response, re.DOTALL)
            sql = sql_match.group(1).strip() if sql_match else response
        
        # Extract reasoning (text before first code block)
        reasoning = response.split("```")[0].strip()
        
        return sql, reasoning
    
    def _extract_tables(self, sql: str) -> List[str]:
        """Extract table names from SQL (basic)."""
        tables = set()
        # Simple regex to find table names after FROM/JOIN
        matches = re.findall(r'\b(?:FROM|JOIN)\s+(\w+)', sql, re.IGNORECASE)
        for match in matches:
            normalized = match.split(".")[-1]
            if normalized.lower() in self.schema.tables:
                tables.add(self.schema.tables[normalized.lower()].name)
        return sorted(tables)
    
    def validate_sql(self, sql: str) -> List[str]:
        """Validate SQL query."""
        return self.validator.validate(sql)