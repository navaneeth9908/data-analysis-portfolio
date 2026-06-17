# NL2SQL Agent - Database Schema Inspector
"""Inspect database schema and build internal representation."""

import logging
from typing import List, Dict, Optional, Any
from sqlalchemy import create_engine, inspect, text, MetaData, Table as SATable
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from ..config import get_config
from .models import (
    DatabaseSchema, Table, Column, ColumnType, Index, Constraint, Relationship
)

logger = logging.getLogger(__name__)


# Type mapping from SQLAlchemy to our ColumnType
TYPE_MAPPING = {
    "INTEGER": ColumnType.INTEGER,
    "BIGINT": ColumnType.BIGINT,
    "SMALLINT": ColumnType.SMALLINT,
    "NUMERIC": ColumnType.NUMERIC,
    "DECIMAL": ColumnType.DECIMAL,
    "FLOAT": ColumnType.REAL,
    "REAL": ColumnType.REAL,
    "DOUBLE PRECISION": ColumnType.DOUBLE,
    "VARCHAR": ColumnType.VARCHAR,
    "CHAR": ColumnType.CHAR,
    "TEXT": ColumnType.TEXT,
    "BOOLEAN": ColumnType.BOOLEAN,
    "DATE": ColumnType.DATE,
    "TIME": ColumnType.TIME,
    "TIMESTAMP": ColumnType.TIMESTAMP,
    "TIMESTAMP WITH TIME ZONE": ColumnType.TIMESTAMPTZ,
    "TIMESTAMPTZ": ColumnType.TIMESTAMPTZ,
    "JSON": ColumnType.JSON,
    "JSONB": ColumnType.JSONB,
    "UUID": ColumnType.UUID,
    "ARRAY": ColumnType.ARRAY,
    "ENUM": ColumnType.ENUM,
}


def map_column_type(sqlalchemy_type: Any) -> ColumnType:
    """Map SQLAlchemy type to our ColumnType."""
    type_str = str(sqlalchemy_type).upper()
    
    for key, value in TYPE_MAPPING.items():
        if key in type_str:
            return value
    
    # Try to extract base type
    if "(" in type_str:
        base = type_str.split("(")[0].strip()
        if base in TYPE_MAPPING:
            return TYPE_MAPPING[base]
    
    logger.warning(f"Unknown column type: {type_str}, defaulting to UNKNOWN")
    return ColumnType.UNKNOWN


class SchemaInspector:
    """Inspect database and build schema representation."""
    
    def __init__(self, engine: Optional[Engine] = None):
        self.config = get_config()
        self.engine = engine or create_engine(self.config.database.url)
        self.inspector = inspect(self.engine)
        self._schema_cache: Optional[DatabaseSchema] = None
    
    def inspect_schema(self, force_refresh: bool = False) -> DatabaseSchema:
        """Inspect database and return complete schema."""
        if self._schema_cache and not force_refresh:
            return self._schema_cache
        
        logger.info("Inspecting database schema...")
        
        schema = DatabaseSchema(dialect=self.config.generation.dialect)
        
        # Get table names
        table_names = self.inspector.get_table_names()
        view_names = self.inspector.get_view_names() if self.config.schema.include_views else []
        
        all_names = table_names + view_names
        
        for table_name in all_names:
            is_view = table_name in view_names
            table = self._inspect_table(table_name, is_view)
            if table:
                schema.add_table(table)
        
        # Build relationships from foreign keys
        self._build_relationships(schema)
        
        self._schema_cache = schema
        logger.info(f"Schema inspection complete: {len(schema.tables)} tables/views")
        
        return schema
    
    def _inspect_table(self, table_name: str, is_view: bool = False) -> Optional[Table]:
        """Inspect a single table/view."""
        try:
            # Get columns
            columns_info = self.inspector.get_columns(table_name)
            
            # Get primary keys
            pk_info = self.inspector.get_pk_constraint(table_name)
            pk_columns = set(pk_info.get("constrained_columns", []))
            
            # Get foreign keys
            fk_info = self.inspector.get_foreign_keys(table_name)
            fk_map = {}  # column -> (ref_table, ref_column)
            for fk in fk_info:
                for col, ref_col in zip(fk["constrained_columns"], fk["referred_columns"]):
                    fk_map[col] = (fk["referred_table"], ref_col)
            
            # Get indexes
            indexes = []
            if self.config.schema.include_indexes:
                for idx in self.inspector.get_indexes(table_name):
                    indexes.append(Index(
                        name=idx["name"],
                        table_name=table_name,
                        columns=idx["column_names"],
                        unique=idx.get("unique", False),
                        primary=idx.get("primary", False),
                    ))
            
            # Get constraints
            constraints = []
            if self.config.schema.include_constraints:
                for constraint in self.inspector.get_unique_constraints(table_name):
                    constraints.append(Constraint(
                        name=constraint["name"],
                        table_name=table_name,
                        type="UNIQUE",
                        columns=constraint["column_names"],
                    ))
                # Primary key constraint
                if pk_info.get("name"):
                    constraints.append(Constraint(
                        name=pk_info["name"],
                        table_name=table_name,
                        type="PRIMARY KEY",
                        columns=list(pk_columns),
                    ))
                # Foreign key constraints
                for fk in fk_info:
                    constraints.append(Constraint(
                        name=fk["name"],
                        table_name=table_name,
                        type="FOREIGN KEY",
                        columns=fk["constrained_columns"],
                        referenced_table=fk["referred_table"],
                        referenced_columns=fk["referred_columns"],
                    ))
            
            # Get row count (estimate for large tables)
            row_count = self._get_row_count(table_name) if not is_view else None
            
            # Build columns
            columns = []
            for i, col_info in enumerate(columns_info):
                col_name = col_info["name"]
                sa_type = col_info["type"]
                
                column = Column(
                    name=col_name,
                    type=map_column_type(sa_type),
                    raw_type=str(sa_type),
                    nullable=col_info.get("nullable", True),
                    default=str(col_info.get("default")) if col_info.get("default") else None,
                    is_primary_key=col_name in pk_columns,
                    is_foreign_key=col_name in fk_map,
                    foreign_key_table=fk_map.get(col_name, (None, None))[0],
                    foreign_key_column=fk_map.get(col_name, (None, None))[1],
                    comment=col_info.get("comment"),
                    ordinal_position=i,
                )
                
                # Extract length/precision/scale for relevant types
                if hasattr(sa_type, "length") and sa_type.length:
                    column.max_length = sa_type.length
                if hasattr(sa_type, "precision") and sa_type.precision:
                    column.precision = sa_type.precision
                if hasattr(sa_type, "scale") and sa_type.scale:
                    column.scale = sa_type.scale
                
                columns.append(column)
            
            table = Table(
                name=table_name,
                schema="public",  # Could be enhanced to support multiple schemas
                columns=columns,
                indexes=indexes,
                constraints=constraints,
                row_count=row_count,
                is_view=is_view,
            )
            
            return table
            
        except Exception as e:
            logger.error(f"Error inspecting table {table_name}: {e}")
            return None
    
    def _get_row_count(self, table_name: str) -> Optional[int]:
        """Get approximate row count for a table."""
        try:
            # Try to get statistics from pg_class for PostgreSQL
            dialect = self.engine.dialect.name
            if dialect == "postgresql":
                with self.engine.connect() as conn:
                    result = conn.execute(text(f"""
                        SELECT reltuples::bigint as estimate
                        FROM pg_class
                        WHERE relname = '{table_name}'
                    """))
                    row = result.fetchone()
                    if row and row[0] > 0:
                        return int(row[0])
            
            # Fallback: exact count (may be slow for large tables)
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                return result.scalar()
                
        except Exception as e:
            logger.warning(f"Could not get row count for {table_name}: {e}")
            return None
    
    def _build_relationships(self, schema: DatabaseSchema) -> None:
        """Build relationship graph from foreign keys."""
        for table in schema.get_all_tables():
            for column in table.get_foreign_keys():
                if column.foreign_key_table and column.foreign_key_column:
                    # Determine relationship type
                    ref_table = schema.get_table(column.foreign_key_table)
                    if ref_table:
                        ref_pks = ref_table.get_primary_keys()
                        if len(ref_pks) == 1 and ref_pks[0].name == column.foreign_key_column:
                            # Check if this FK is also a PK in current table (one-to-one)
                            if column.is_primary_key:
                                rel_type = "one-to-one"
                            else:
                                rel_type = "many-to-one"
                        else:
                            rel_type = "many-to-one"
                    else:
                        rel_type = "many-to-one"
                    
                    relationship = Relationship(
                        from_table=table.name,
                        from_column=column.name,
                        to_table=column.foreign_key_table,
                        to_column=column.foreign_key_column,
                        type=rel_type,
                    )
                    schema.relationships.append(relationship)
    
    def get_sample_data(self, table_name: str, limit: int = None) -> List[Dict]:
        """Get sample rows from a table."""
        limit = limit or self.config.schema.sample_rows
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT {limit}"))
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Error getting sample data for {table_name}: {e}")
            return []


def create_inspector(engine: Optional[Engine] = None) -> SchemaInspector:
    """Factory function to create a SchemaInspector."""
    return SchemaInspector(engine)