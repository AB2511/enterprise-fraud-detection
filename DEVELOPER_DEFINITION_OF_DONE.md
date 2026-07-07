# Developer Definition of Done (DoD)

**Version:** 1.0  
**Last Updated:** July 7, 2026  
**Status:** Active

---

## Purpose

This document defines the acceptance criteria that MUST be met before any feature, module, or change is considered "complete" and ready for merge. Following this DoD ensures consistent quality across the codebase as the platform grows.

---

## Definition of Done Checklist

A feature is only considered **DONE** when ALL of the following criteria are met:

### ✅ 1. Code Implementation

- [ ] **Feature complete** - All acceptance criteria from the specification are implemented
- [ ] **Clean Architecture** - Code follows the established layered architecture:
  - Domain entities are pure business logic with no infrastructure dependencies
  - Application services orchestrate workflows
  - Infrastructure implementations are abstracted behind interfaces
  - Presentation layer handles HTTP concerns only
- [ ] **SOLID principles** followed
- [ ] **No commented-out code** - Remove dead code, don't comment it out
- [ ] **No TODO comments** introduced (unless tracked in issue tracker with ticket number)
- [ ] **Code is self-documenting** - Clear naming, proper structure
- [ ] **Docstrings present** for all public classes and methods
- [ ] **Type hints present** for all function signatures

### ✅ 2. Testing

- [ ] **Unit tests written** for all new domain entities and business logic
- [ ] **Integration tests written** for repository implementations
- [ ] **API tests written** for all new endpoints
- [ ] **All tests passing** - 100% pass rate (no skipped, no xfail)
- [ ] **Test coverage** maintained or improved (target: 90%+)
- [ ] **Edge cases tested** - Validation errors, not found scenarios, boundary conditions
- [ ] **Happy path tested** - Normal successful operations
- [ ] **Error scenarios tested** - Exception handling, rollback behavior

### ✅ 3. Code Quality

- [ ] **Ruff linting passes** - `ruff check backend/src backend/tests`
- [ ] **Black formatting applied** - `black backend/src backend/tests`
- [ ] **Mypy type checking passes** - `mypy backend/src`
- [ ] **No new warnings** introduced in test output
- [ ] **Code review** completed (if team size > 1)
- [ ] **Security review** for sensitive operations (auth, data access, PII handling)

### ✅ 4. Documentation

- [ ] **README updated** (if public API or usage changes)
- [ ] **API documentation updated** (OpenAPI spec current)
- [ ] **Architecture docs updated** (if new patterns or layers introduced)
- [ ] **Docstrings complete** for new classes and public methods
- [ ] **Migration guide** provided (if breaking changes)
- [ ] **Configuration docs** updated (if new settings added)

### ✅ 5. Database & Persistence

- [ ] **Migration scripts created** (if schema changes)
- [ ] **Migration tested** (up and down migrations work)
- [ ] **Indexes added** for query performance
- [ ] **Soft-delete implemented** for entities requiring audit trail
- [ ] **No data loss** on migration

### ✅ 6. API Design

- [ ] **RESTful conventions** followed
- [ ] **HTTP status codes** correct (200, 201, 404, 409, 422, 500)
- [ ] **Request validation** implemented (Pydantic models)
- [ ] **Response DTOs** defined (no domain entities in responses)
- [ ] **Error responses standardized** (following existing error format)
- [ ] **OpenAPI spec** updated (Swagger docs accurate)
- [ ] **Backward compatibility** maintained (or breaking change documented)

### ✅ 7. Audit & Compliance

- [ ] **Audit logs created** for all Create/Update/Delete operations
- [ ] **Sensitive operations logged** (data access, exports, deletions)
- [ ] **PII handling compliant** with data protection requirements
- [ ] **Soft-delete used** for entities requiring audit trail
- [ ] **User attribution** captured (who performed the action)

### ✅ 8. Error Handling

- [ ] **All exceptions handled** appropriately
- [ ] **Domain exceptions used** (not generic exceptions)
- [ ] **Error messages are user-friendly** (no stack traces in API responses)
- [ ] **Logging includes context** (entity IDs, user IDs, operation details)
- [ ] **No silent failures** (all errors logged)

### ✅ 9. Performance

- [ ] **No N+1 queries** (use joins or eager loading)
- [ ] **Database indexes** added for frequently queried fields
- [ ] **Pagination implemented** for list endpoints
- [ ] **No blocking operations** in async code
- [ ] **Resource cleanup** (database connections, file handles)

### ✅ 10. Security

- [ ] **Input validation** on all user inputs
- [ ] **SQL injection protected** (parameterized queries)
- [ ] **Authentication enforced** (if auth is implemented)
- [ ] **Authorization checked** (user has permission for operation)
- [ ] **Sensitive data encrypted** (passwords, tokens)
- [ ] **No secrets in code** (use environment variables)
- [ ] **CORS configured** appropriately

### ✅ 11. Code Review

- [ ] **PR description complete** - What changed, why, how to test
- [ ] **No merge conflicts**
- [ ] **Branch up to date** with main/develop
- [ ] **Reviewer approved** (if team review process exists)
- [ ] **All review comments addressed**

### ✅ 12. Integration

- [ ] **No circular imports** introduced
- [ ] **Dependencies added to requirements.txt** (if new packages used)
- [ ] **Environment variables documented** (if new config added)
- [ ] **Docker build succeeds** (if using containers)
- [ ] **CI pipeline passes** (when CI/CD is set up)

---

## Feature-Specific Criteria

### For New Domain Entities

- [ ] **Validation in `__post_init__`** - All business rules enforced
- [ ] **Immutable where appropriate** - Use frozen dataclasses for value objects
- [ ] **Factory methods** for complex creation logic
- [ ] **Domain exceptions** for validation failures
- [ ] **No infrastructure dependencies** - Pure business logic only
- [ ] **Unit tests** cover all validation rules and methods

### For New API Endpoints

- [ ] **Request DTO** defined with Pydantic validation
- [ ] **Response DTO** defined (no domain entities exposed)
- [ ] **Use case layer** orchestrates the operation
- [ ] **Exception handling** returns appropriate HTTP status
- [ ] **OpenAPI documentation** auto-generated correctly
- [ ] **Integration tests** verify full request/response cycle

### For New Repository Methods

- [ ] **Interface defined** in `application/interfaces/`
- [ ] **Implementation** in `infrastructure/database/repositories/`
- [ ] **Soft-delete filter** applied (where appropriate)
- [ ] **Integration tests** verify database operations
- [ ] **Query optimization** (indexes, joins)

### For Database Migrations

- [ ] **Migration script** created (Alembic or similar)
- [ ] **Up migration** tested
- [ ] **Down migration** tested (rollback works)
- [ ] **Seed data** provided (if needed for development)
- [ ] **Production data** migration plan (if modifying existing tables)

---

## Quality Gates

Before merging, run all quality gates:

```bash
# 1. Run tests
pytest tests/ -v --cov=backend/src --cov-report=term-missing

# 2. Check linting
ruff check backend/src backend/tests

# 3. Check formatting
black --check backend/src backend/tests

# 4. Check type hints
mypy backend/src

# 5. Security scan (if available)
bandit -r backend/src
```

**All gates must pass** before merge.

---

## When to Skip Criteria (Exceptions)

Some criteria may be skipped ONLY in these scenarios:

### Prototype / Spike Work
- Clearly marked as `[PROTOTYPE]` in PR title
- Never merged to main branch
- Used for exploration/validation only

### Hotfix (Production Emergency)
- Clearly marked as `[HOTFIX]` in PR title
- Requires manager approval
- Follow-up issue created to add missing criteria
- Retrospective required after incident

### Documentation-Only Changes
- No code changes
- README, docs, or comment updates only
- Still requires spell-check and review

---

## Definition of Ready (Before Starting Work)

Before starting implementation, ensure:

- [ ] **User story/requirement** is clear and understood
- [ ] **Acceptance criteria** defined
- [ ] **Design reviewed** (architecture, data model, API design)
- [ ] **Dependencies identified** (blocking work, external systems)
- [ ] **Test strategy** defined
- [ ] **Estimated effort** reasonable (if too large, break into smaller tasks)

---

## Enforcement

### Pull Request Template

Use this template for all PRs:

```markdown
## Description
[What changed and why]

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Definition of Done Checklist
- [ ] Code implementation complete
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Linting passes
- [ ] Type checking passes
- [ ] Documentation updated
- [ ] OpenAPI spec updated (if API changes)
- [ ] No new TODOs introduced
- [ ] Audit logs added (if needed)

## Testing
[How to test this change]

## Screenshots (if applicable)
[Visual changes]

## Related Issues
Closes #[issue-number]
```

### Code Review Checklist

Reviewers should verify:

- [ ] DoD checklist in PR is complete
- [ ] Code follows established patterns (reference: Customer module)
- [ ] Tests are meaningful (not just for coverage)
- [ ] Error handling is appropriate
- [ ] Documentation is clear
- [ ] No obvious performance or security issues

---

## Reference Implementation

**Customer Module** is the reference implementation for this DoD.

When implementing new features, follow the Customer module pattern:

- `backend/src/domain/entities/customer.py` - Domain entity example
- `backend/src/application/use_cases/customer_use_cases.py` - Use case example
- `backend/src/application/services/customer_service.py` - Service example
- `backend/src/infrastructure/database/repositories/customer_repository_impl.py` - Repository example
- `backend/src/presentation/api/v1/routes/customers.py` - API endpoint example
- `backend/tests/` - Test examples at all layers

---

## Continuous Improvement

This DoD is a living document. It should be reviewed and updated:

- **Quarterly** - Regular review for improvements
- **When gaps discovered** - Update after post-mortems or issues
- **When patterns emerge** - Codify new best practices

To propose changes:
1. Create an issue with `[DoD Update]` prefix
2. Discuss with team
3. Update document with consensus
4. Increment version number

---

## Success Metrics

Track these metrics to measure DoD effectiveness:

- **Defect escape rate** - Bugs found in production vs. caught in dev/test
- **Test coverage** - Should trend toward 90%+
- **Code review cycle time** - Should be < 1 day
- **Rework rate** - PRs requiring significant changes after review
- **Production incidents** - Should trend downward

---

## Summary

**Before marking any work as "DONE":**

1. ✅ All DoD checklist items completed
2. ✅ All quality gates pass
3. ✅ Code review approved
4. ✅ Documentation updated
5. ✅ Tests passing (100%)

**Remember:** Taking shortcuts now creates technical debt later. Following this DoD ensures:
- Consistent code quality
- Maintainable codebase
- Reliable deployments
- Happy developers
- Satisfied users

---

**Questions or suggestions?** Open an issue with `[DoD]` prefix.
