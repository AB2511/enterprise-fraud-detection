"""Domain Layer - Pure business logic with zero external dependencies.

This layer contains:
- Entities: Core business objects with identity
- Value Objects: Immutable objects without identity
- Domain Services: Business logic that doesn't belong to a single entity
- Domain Exceptions: Business rule violations

Rules:
- NO framework dependencies (FastAPI, SQLAlchemy, etc.)
- NO infrastructure concerns (database, HTTP, AWS)
- Pure Python only
- 100% testable without mocks
"""
