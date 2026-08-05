# Contributing to Enterprise Fraud Detection Platform

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Development Setup

See [backend/README.md](backend/README.md) for detailed setup instructions.

## Code of Conduct

- Be respectful and inclusive
- Follow professional communication standards
- Focus on constructive feedback
- Help maintain a welcoming environment

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported
2. Create a new issue with:
   - Clear description of the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version)
   - Relevant logs or error messages

### Suggesting Features

1. Check if the feature has already been requested
2. Create a new issue with:
   - Clear description of the feature
   - Use case and business value
   - Proposed implementation approach
   - Any relevant examples or mockups

### Pull Requests

1. **Fork the repository**

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Follow coding standards**
   - Clean Architecture principles
   - SOLID principles
   - Type hints on all functions
   - Docstrings for all public methods
   - No circular imports

4. **Write tests**
   - Unit tests for domain logic
   - Integration tests for database operations
   - E2E tests for API endpoints
   - Maintain >80% code coverage

5. **Run quality checks**
   ```bash
   cd backend
   poetry run ruff check .
   poetry run black .
   poetry run isort .
   poetry run mypy src/
   poetry run pytest --cov=src
   ```

6. **Commit with conventional commits**
   ```
   feat: add new feature
   fix: resolve bug
   docs: update documentation
   test: add tests
   refactor: code improvements
   chore: maintenance tasks
   ```

7. **Push and create pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

8. **PR checklist**
   - [ ] Tests pass
   - [ ] Code coverage maintained
   - [ ] Linting passes
   - [ ] Type checking passes
   - [ ] Documentation updated
   - [ ] CHANGELOG.md updated

## Architecture Guidelines

### Domain Layer
- Pure Python only
- No external dependencies
- Business logic and invariants
- Entities, value objects, domain services

### Application Layer
- Orchestration logic
- Define interfaces (ports)
- Use cases
- DTOs for inter-layer communication

### Infrastructure Layer
- External concerns
- Database, ML, AWS, etc.
- Implement application interfaces

### Presentation Layer
- FastAPI routes
- Request/response schemas
- Middleware
- No business logic

## Testing Guidelines

### Unit Tests
- Test domain logic in isolation
- No database or external dependencies
- Fast execution (milliseconds)
- High coverage (>90% for domain layer)

### Integration Tests
- Test database operations
- Test API endpoints
- Use test database
- Moderate execution time

### E2E Tests
- Test complete workflows
- Minimal but critical paths
- Slower execution acceptable

## Code Review Process

1. Automated checks must pass (CI/CD)
2. At least one approval required
3. No unresolved comments
4. Branch up to date with main
5. No merge conflicts

## Release Process

1. Version bump in pyproject.toml
2. Update CHANGELOG.md
3. Create release branch
4. Deploy to staging
5. Run smoke tests
6. Deploy to production
7. Tag release in Git

## Questions?

- Open an issue for general questions
- Check existing documentation
- Review architecture documents

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
