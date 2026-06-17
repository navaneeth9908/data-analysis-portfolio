# NL2SQL Agent - Schema Models
"""Data models for database schema representation."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import json


class ColumnType(Enum):
    """Standardized column types across dialects."""
    INTEGER = "INTEGER"
    BIGINT = "BIGINT"
    SMALLINT = "SMALLINT"
    DECIMAL = "DECIMAL"
    NUMERIC = "NUMERIC"
    REAL = "REAL"
    DOUBLE = "DOUBLE PRECISION"
    VARCHAR = "VARCHAR"
    CHAR = "CHAR"
    TEXT = "TEXT"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    TIME = "TIME"
    TIMESTAMP = "TIMESTAMP"
    TIMESTAMPTZ = "TIMESTAMPTZ"
    JSON = "JSON"
    JSONB = "JSONB"
    UUID = "UUID"
    ARRAY = "ARRAY"
    ENUM = "ENUM"
    UNKNOWN = "UNKNOWN"


@dataclass
class Column:
    """Represents a database column."""
    name: str
    type: ColumnType
    raw_type: str
    nullable: bool = True
    default: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_key_table: Optional[str] = None
    foreign_key_column: Optional[str] = None
    comment: Optional[str] = None
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    ordinal_position: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type.value,
            "raw_type": self.raw_type,
            "nullable": self.nullable,
            "default": self.default,
            "is_primary_key": self.is_primary_key,
            "is_foreign_key": self.is_foreign_key,
            "foreign_key_table": self.foreign_key_table,
            "foreign_key_column": self.foreign_key_column,
            "comment": self.comment,
            "max_length": self.max_length,
            "precision": self.precision,
            "scale": self.scale,
            "ordinal_position": self.ordinal_position,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Column":
        return cls(
            name=data["name"],
            type=ColumnType(data["type"]),
            raw_type=data["raw_type"],
            nullable=data.get("nullable", True),
            default=data.get("default"),
            is_primary_key=data.get("is_primary_key", False),
            is_foreign_key=data.get("is_foreign_key", False),
            foreign_key_table=data.get("foreign_key_table"),
            foreign_key_column=data.get("foreign_key_column"),
            comment=data.get("comment"),
            max_length=data.get("max_length"),
            precision=data.get("precision"),
            scale=data.get("scale"),
            ordinal_position=data.get("ordinal_position", 0),
        )


@dataclass
class Index:
    """Represents a database index."""
    name: str
    table_name: str
    columns: List[str]
    unique: bool = False
    primary: bool = False
    method: str = "btree"
    condition: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "table_name": self.table_name,
            "columns": self.columns,
            "unique": self.unique,
            "primary": self.primary,
            "method": self.method,
            "condition": self.condition,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Index":
        """Rehydrate an index from serialized cache data."""
        return cls(
            name=data["name"],
            table_name=data["table_name"],
            columns=list(data.get("columns", [])),
            unique=data.get("unique", False),
            primary=data.get("primary", False),
            method=data.get("method", "btree"),
            condition=data.get("condition"),
        )


@dataclass
class Constraint:
    """Represents a database constraint."""
    name: str
    table_name: str
    type: str  # PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK, NOT NULL
    columns: List[str]
    referenced_table: Optional[str] = None
    referenced_columns: List[str] = field(default_factory=list)
    definition: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "table_name": self.table_name,
            "type": self.type,
            "columns": self.columns,
            "referenced_table": self.referenced_table,
            "referenced_columns": self.referenced_columns,
            "definition": self.definition,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Constraint":
        """Rehydrate a constraint from serialized cache data."""
        return cls(
            name=data["name"],
            table_name=data["table_name"],
            type=data["type"],
            columns=list(data.get("columns", [])),
            referenced_table=data.get("referenced_table"),
            referenced_columns=list(data.get("referenced_columns", [])),
            definition=data.get("definition"),
        )


@dataclass
class Table:
    """Represents a database table."""
    name: str
    schema: str = "public"
    columns: List[Column] = field(default_factory=list)
    indexes: List[Index] = field(default_factory=list)
    constraints: List[Constraint] = field(default_factory=list)
    row_count: Optional[int] = None
    comment: Optional[str] = None
    is_view: bool = False
    view_definition: Optional[str] = None

    def get_column(self, name: str) -> Optional[Column]:
        """Get column by name (case-insensitive)."""
        for col in self.columns:
            if col.name.lower() == name.lower():
                return col
        return None

    def get_primary_keys(self) -> List[Column]:
        """Get primary key columns."""
        return [c for c in self.columns if c.is_primary_key]

    def get_foreign_keys(self) -> List[Column]:
        """Get foreign key columns."""
        return [c for c in self.columns if c.is_foreign_key]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "schema": self.schema,
            "columns": [c.to_dict() for c in self.columns],
            "indexes": [i.to_dict() for i in self.indexes],
            "constraints": [c.to_dict() for c in self.constraints],
            "row_count": self.row_count,
            "comment": self.comment,
            "is_view": self.is_view,
            "view_definition": self.view_definition,
        }

    def to_summary(self) -> str:
        """Generate a concise summary for LLM context."""
        cols = []
        for c in self.columns:
            pk = " PK" if c.is_primary_key else ""
            fk = f" FK→{c.foreign_key_table}.{c.foreign_key_column}" if c.is_foreign_key else ""
            nullable = "" if c.nullable else " NOT NULL"
            cols.append(f"  {c.name}: {c.type.value}{pk}{fk}{nullable}")
        return f"Table: {self.name} ({'VIEW' if self.is_view else 'TABLE'})\n" + "\n".join(cols)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Table":
        """Rehydrate a table and nested objects from serialized cache data."""
        return cls(
            name=data["name"],
            schema=data.get("schema", "public"),
            columns=[Column.from_dict(c) for c in data.get("columns", [])],
            indexes=[Index.from_dict(i) for i in data.get("indexes", [])],
            constraints=[Constraint.from_dict(c) for c in data.get("constraints", [])],
            row_count=data.get("row_count"),
            comment=data.get("comment"),
            is_view=data.get("is_view", False),
            view_definition=data.get("view_definition"),
        )


@dataclass
class Relationship:
    """Represents a relationship between tables."""
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    type: str = "many-to-one"  # many-to-one, one-to-many, one-to-one, many-to-many

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_table": self.from_table,
            "from_column": self.from_column,
            "to_table": self.to_table,
            "to_column": self.to_column,
            "type": self.type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relationship":
        """Rehydrate a relationship from serialized cache data."""
        return cls(
            from_table=data["from_table"],
            from_column=data["from_column"],
            to_table=data["to_table"],
            to_column=data["to_column"],
            type=data.get("type", "many-to-one"),
        )


@dataclass
class DatabaseSchema:
    """Complete database schema representation."""
    tables: Dict[str, Table] = field(default_factory=dict)
    relationships: List[Relationship] = field(default_factory=list)
    dialect: str = "postgresql"
    catalog: Optional[str] = None

    def add_table(self, table: Table) -> None:
        self.tables[table.name.lower()] = table

    def get_table(self, name: str) -> Optional[Table]:
        return self.tables.get(name.lower())

    def get_all_tables(self) -> List[Table]:
        return list(self.tables.values())

    def get_summary(self, include_views: bool = True) -> str:
        """Generate schema summary for LLM context."""
        summaries = []
        for table in self.tables.values():
            if not include_views and table.is_view:
                continue
            summaries.append(table.to_summary())
        return "\n\n".join(summaries)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tables": {k: v.to_dict() for k, v in self.tables.items()},
            "relationships": [r.to_dict() for r in self.relationships],
            "dialect": self.dialect,
            "catalog": self.catalog,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatabaseSchema":
        """Rehydrate a complete database schema from serialized cache data."""
        schema = cls(
            dialect=data.get("dialect", "postgresql"),
            catalog=data.get("catalog"),
        )
        for table_data in data.get("tables", {}).values():
            schema.add_table(Table.from_dict(table_data))
        schema.relationships = [
            Relationship.from_dict(rel) for rel in data.get("relationships", [])
        ]
        return schema

    @classmethod
    def from_json(cls, payload: str) -> "DatabaseSchema":
        """Rehydrate a complete database schema from a JSON string."""
        return cls.from_dict(json.loads(payload))