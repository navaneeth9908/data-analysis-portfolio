# NL2SQL Agent - Schema Cache
"""Schema caching for performance."""

import json
import time
import logging
from pathlib import Path
from typing import Optional

from .models import DatabaseSchema
from ..config import get_config

logger = logging.getLogger(__name__)


class SchemaCache:
    """Cache database schema to disk for faster startup."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.config = get_config()
        self.cache_dir = cache_dir or Path.home() / ".cache" / "nl2sql"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "schema_cache.json"
        self.metadata_file = self.cache_dir / "schema_meta.json"
    
    def save(self, schema: DatabaseSchema) -> bool:
        """Save schema to cache."""
        try:
            # Save schema data
            with open(self.cache_file, "w") as f:
                json.dump(schema.to_dict(), f, indent=2)
            
            # Save metadata
            meta = {
                "saved_at": time.time(),
                "dialect": schema.dialect,
                "table_count": len(schema.tables),
                "ttl": self.config.schema.cache_ttl,
            }
            with open(self.metadata_file, "w") as f:
                json.dump(meta, f, indent=2)
            
            logger.info(f"Schema cached: {len(schema.tables)} tables")
            return True
        except Exception as e:
            logger.error(f"Failed to save schema cache: {e}")
            return False
    
    def load(self) -> Optional[DatabaseSchema]:
        """Load schema from cache if valid."""
        if not self.cache_file.exists() or not self.metadata_file.exists():
            return None
        
        try:
            with open(self.metadata_file) as f:
                meta = json.load(f)
            
            # Check TTL
            age = time.time() - meta.get("saved_at", 0)
            if age > meta.get("ttl", self.config.schema.cache_ttl):
                logger.info("Schema cache expired")
                return None
            
            with open(self.cache_file) as f:
                data = json.load(f)
            
            schema = DatabaseSchema.from_dict(data)
            
            logger.info(f"Schema loaded from cache: {len(schema.tables)} tables (age: {age:.0f}s)")
            return schema
            
        except Exception as e:
            logger.error(f"Failed to load schema cache: {e}")
            return None
    
    def invalidate(self) -> bool:
        """Invalidate cache."""
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
            if self.metadata_file.exists():
                self.metadata_file.unlink()
            logger.info("Schema cache invalidated")
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate cache: {e}")
            return False


def get_cache() -> SchemaCache:
    """Get global cache instance."""
    return SchemaCache()