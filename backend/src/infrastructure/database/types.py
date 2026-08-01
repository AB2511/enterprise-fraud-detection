"""Portable database type definitions.

Provides database types that work across different dialects
(PostgreSQL for production, SQLite for testing).
"""

from sqlalchemy import JSON, String, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.engine import Dialect
from sqlalchemy.sql.type_api import TypeEngine


class PortableJSON(TypeDecorator):
    """Portable JSON type that uses JSONB on PostgreSQL and JSON elsewhere.

    This allows us to use PostgreSQL's JSONB type in production for better
    performance while maintaining compatibility with SQLite for testing.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[object]:
        """Load the appropriate type based on the database dialect."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB(astext_type=Text()))
        else:
            return dialect.type_descriptor(JSON())


class PortableUUID(TypeDecorator):
    """Portable UUID type that uses PostgreSQL UUID or String(36) for SQLite.

    For PostgreSQL: Uses native UUID type with as_uuid=True
    For SQLite: Uses CHAR(36) to store UUID as string
    """

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine[str]:
        """Load the appropriate type based on the database dialect."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PostgreSQLUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        """Convert UUID to string for SQLite."""
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        else:
            # For SQLite, convert UUID to string
            if hasattr(value, "hex"):  # It's a UUID object
                return str(value)
            return str(value)  # Already a string

    def process_result_value(self, value, dialect):
        """Convert string back to UUID for SQLite."""
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        else:
            # For SQLite, return as string (SQLAlchemy ORM will handle UUID conversion)
            return value
