---
inclusion: manual
---

# H-DCN Dashboard Testing Guidelines

## Testing Strategy

### Frontend Testing (React TypeScript)

- **Unit Tests**: Jest for component logic and utilities
- **Integration Tests**: React Testing Library for user interactions
- **E2E Tests**: Custom test suite in `frontend/test-e2e.js`
- **Property-Based Tests**: Use fast-check for complex business logic
- **Visual Regression**: Consider adding screenshot testing for UI components

### Backend Testing (Python Lambda)

- **Unit Tests**: pytest for individual function testing
- **Integration Tests**: Mock AWS services with moto
- **API Tests**: Test API Gateway integration end-to-end
- **Property-Based Tests**: Use Hypothesis for data validation
- **Load Tests**: Test Lambda performance under load

## Test Organization

### Frontend Structure

```
frontend/
├── src/
│   ├── components/__tests__/          # Component unit tests
│   ├── modules/{feature}/__tests__/   # Feature-specific tests
│   ├── utils/__tests__/               # Utility function tests
│   └── __tests__/                     # App-level integration tests
└── test/
    ├── e2e/                           # End-to-end tests
    ├── fixtures/                      # Test data and mocks
    └── setup/                         # Test configuration
```

### Backend Test Structure

```
backend/
├── tests/
│   ├── unit/                          # Unit tests per handler
│   ├── integration/                   # API integration tests
│   ├── fixtures/                      # Test data and AWS mocks
│   └── conftest.py                    # pytest configuration
└── handler/
    └── {function}/
        ├── app.py                     # Lambda function
        ├── test_app.py                # Co-located unit tests
        └── requirements.txt
```

## Testing Best Practices

### Frontend Testing

- **Co-locate tests**: Place test files next to components
- **Mock external dependencies**: API calls, AWS SDK, third-party services
- **Test user behavior**: Focus on user interactions, not implementation details
- **Use data-testid**: For reliable element selection in tests
- **Test error states**: Loading, error boundaries, network failures

**Example Component Test:**

```typescript
// src/components/__tests__/MemberCard.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { MemberCard } from "../MemberCard";

describe("MemberCard", () => {
  it("displays member information correctly", () => {
    const member = { id: "1", name: "John Doe", email: "john@hdcn.nl" };
    render(<MemberCard member={member} />);

    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("john@hdcn.nl")).toBeInTheDocument();
  });
});
```

### Backend Testing

- **Test each Lambda handler independently**: Isolate function logic
- **Mock DynamoDB and other AWS services**: Use moto for AWS service mocking
- **Validate input/output schemas**: Ensure API contracts are maintained
- **Test error conditions and edge cases**: Invalid inputs, service failures
- **Use fixtures**: Consistent test data across tests

**Example Lambda Test:**

```python
# backend/handler/get_members/test_app.py
import pytest
from moto import mock_dynamodb
import boto3
from app import lambda_handler

@mock_dynamodb
def test_get_members_success():
    # Setup mock DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.create_table(
        TableName='Members',
        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        BillingMode='PAY_PER_REQUEST'
    )

    # Test the handler
    event = {'httpMethod': 'GET', 'path': '/members'}
    result = lambda_handler(event, {})

    assert result['statusCode'] == 200
```

## Coverage Requirements

### Minimum Coverage Targets

- **Frontend**: 80% line coverage, 70% branch coverage
- **Backend**: 85% line coverage, 75% branch coverage
- **Critical paths**: 95% coverage (authentication, payments, data validation)

### Coverage Commands

```bash
# Frontend coverage
cd frontend && npm test -- --coverage

# Backend coverage
cd backend && pytest --cov=handler --cov-report=html
```

## Test Data Management

### Frontend Test Data

- Use factories for consistent test objects
- Mock API responses with realistic data
- Test with both valid and invalid data sets

### Backend Test Data

- Use pytest fixtures for reusable test data
- Mock AWS services with realistic responses
- Test with edge cases (empty results, large datasets)

## Continuous Integration

### Pre-commit Hooks

- Run linting and type checking
- Execute fast unit tests
- Validate test coverage thresholds

### CI Pipeline Requirements

- All tests must pass before merge
- Coverage reports generated and tracked
- E2E tests run on staging environment
- Performance regression tests for critical paths

## Test Commands

### Frontend

```bash
# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run specific test file
npm test -- MemberCard.test.tsx

# Run with coverage
npm test -- --coverage --watchAll=false
```

### Backend

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_get_members.py

# Run with coverage
pytest --cov=handler --cov-report=term-missing

# Run integration tests only
pytest tests/integration/
```

## Debugging Tests

### Frontend Debugging

- Use `screen.debug()` to see rendered HTML
- Add `console.log` in test files for debugging
- Use VS Code Jest extension for debugging

### Backend Debugging

- Use `pytest -s` to see print statements
- Add `import pdb; pdb.set_trace()` for breakpoints
- Use `pytest --pdb` to drop into debugger on failures

## Performance Testing

### Frontend Performance

- Test component render times
- Monitor bundle size impact
- Test with large datasets

### Backend Performance

- Test Lambda cold start times
- Monitor DynamoDB query performance
- Test concurrent request handling
