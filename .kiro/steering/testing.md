---
inclusion: fileMatch
fileMatchPattern: "**/*.test.*,**/*.spec.*,**/tests/**"
---

# Testing

Concise testing rules for AI-assisted development. For full guidelines, examples, and debugging tips, see the [detailed testing reference](../../docs/development/testing.md).

## Frameworks

| Layer    | Unit + Integration           | Property-Based |
| -------- | ---------------------------- | -------------- |
| Backend  | pytest + moto                | Hypothesis     |
| Frontend | Jest + React Testing Library | fast-check     |

## Directory Structure

### Backend (`backend/tests/`)

```
tests/
├── unit/           # Unit tests per handler
├── integration/    # API integration tests
├── fixtures/       # Test data and AWS mocks
└── conftest.py     # Shared pytest fixtures
```

### Frontend (`frontend/src/`)

- Co-locate tests next to components: `Component.test.tsx`
- Feature tests: `modules/{feature}/__tests__/`
- Utility tests: `utils/__tests__/`

## Coverage Targets

| Scope          | Line Coverage |
| -------------- | ------------- |
| Frontend       | 80%           |
| Backend        | 85%           |
| Critical paths | 95%           |

Critical paths: authentication, payments, data validation.

## Commands

### Backend

```bash
pytest tests/                                      # Run all tests
pytest --cov=handler --cov-report=term-missing     # Coverage report
```

### Frontend

```bash
npm test -- --watchAll=false                        # Run all tests
npm test -- --coverage --watchAll=false             # Coverage report
```

> **Important:** Always use `npx react-scripts test` (or `npm test`) — never `npx jest` directly. The CRA Babel config required for TypeScript is only applied through react-scripts. Running jest directly causes parse errors on type annotations.

## Key Rules

- Mock AWS services with moto (never hit real AWS in tests)
- Use `data-testid` for reliable element selection in frontend tests
- Test user behavior, not implementation details
- All tests must pass before merge
- Property-based tests target complex business logic and data validation
- Use pytest fixtures for reusable backend test data
- Use factories for consistent frontend test objects
