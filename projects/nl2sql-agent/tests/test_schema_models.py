"""Schema domain model tests for the NL2SQL agent."""

import importlib.util
import json
from pathlib import Path


MODELS_PATH = Path(__file__).resolve().parents[1] / "src" / "schema" / "models.py"
spec = importlib.util.spec_from_file_location("schema_models", MODELS_PATH)
assert spec is not None
schema_models = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(schema_models)

Column = schema_models.Column
ColumnType = schema_models.ColumnType
Constraint = schema_models.Constraint
DatabaseSchema = schema_models.DatabaseSchema
Index = schema_models.Index
Relationship = schema_models.Relationship
Table = schema_models.Table


def build_sample_schema() -> DatabaseSchema:
    """Create a representative schema graph for serialization tests."""
    customers = Table(
        name="customers",
        columns=[
            Column("customer_id", ColumnType.INTEGER, "INTEGER", nullable=False, is_primary_key=True),
            Column("email", ColumnType.VARCHAR, "VARCHAR(255)", nullable=False, max_length=255),
        ],
        indexes=[Index("idx_customers_email", "customers", ["email"], unique=True)],
        constraints=[Constraint("pk_customers", "customers", "PRIMARY KEY", ["customer_id"])],
        row_count=42,
    )
    orders = Table(
        name="orders",
        columns=[
            Column("order_id", ColumnType.INTEGER, "INTEGER", nullable=False, is_primary_key=True),
            Column(
                "customer_id",
                ColumnType.INTEGER,
                "INTEGER",
                nullable=False,
                is_foreign_key=True,
                foreign_key_table="customers",
                foreign_key_column="customer_id",
            ),
        ],
        constraints=[
            Constraint("pk_orders", "orders", "PRIMARY KEY", ["order_id"]),
            Constraint(
                "fk_orders_customers",
                "orders",
                "FOREIGN KEY",
                ["customer_id"],
                referenced_table="customers",
                referenced_columns=["customer_id"],
            ),
        ],
    )

    schema = DatabaseSchema(dialect="sqlite", catalog="analytics")
    schema.add_table(customers)
    schema.add_table(orders)
    schema.relationships.append(
        Relationship("orders", "customer_id", "customers", "customer_id", "many-to-one")
    )
    return schema


def test_schema_round_trip_preserves_tables_columns_and_relationships() -> None:
    schema = build_sample_schema()

    restored = DatabaseSchema.from_dict(json.loads(schema.to_json()))

    assert restored.dialect == "sqlite"
    assert restored.catalog == "analytics"
    assert restored.get_table("CUSTOMERS") is not None
    assert restored.get_table("orders").get_column("customer_id").is_foreign_key
    assert restored.relationships[0].to_table == "customers"
    assert restored.get_table("customers").indexes[0].unique is True


def test_schema_summary_filters_views_and_marks_keys() -> None:
    schema = build_sample_schema()
    schema.add_table(
        Table(
            name="active_customers",
            columns=[Column("customer_id", ColumnType.INTEGER, "INTEGER")],
            is_view=True,
        )
    )

    summary = schema.get_summary(include_views=False)

    assert "Table: customers" in summary
    assert "customer_id: INTEGER PK NOT NULL" in summary
    assert "FK→customers.customer_id" in summary
    assert "active_customers" not in summary
