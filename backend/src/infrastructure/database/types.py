"""Portable database type definitions.

Provides database types that work across different dialects
(PostgreSQL for production, SQLite for testing).
"""

from sqlalchemy import JSON, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB


class PortableJSON(TypeDecorator):
    """Portable JSON type that uses JSONB on PostgreSQL and JSON elsewhere.
    
    This allows us to use PostgreSQL's JSONB type in production for better
    performance while maintaining compatibility with SQLite for testing.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Load the appropriate type based on the database dialect."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB(astext_type=Text()))
        else:
            return dialect.type_descriptor(JSON())
