# Testing Guidelines

Comprehensive testing reference for the H-DCN project. For the concise steering-file version, see [`.kiro/steering/testing.md`](../../.kiro/steering/testing.md).

## Table of Contents

- [Test Organization](#test-organization)
- [Backend Testing (pytest + moto)](#backend-testing-pytest--moto)
- [Frontend Testing (Jest + RTL)](#frontend-testing-jest--rtl)
- [Property-Based Testing](#property-based-testing)
- [Coverage Commands and Interpretation](#coverage-commands-and-interpretation)
- [CI Pipeline Requirements](#ci-pipeline-requirements)
- [Debugging Test Failures](#debugging-test-failures)

---

## Test Organization

### Backend Structure (`backend/tests/`)

```
backend/tests/
├── unit/                    # Unit tests per handler (isolated, fast)
│   ├── test_get_members_filtered.py
│   ├── test_auth_logging.py
│   └── ...
├── integration/             # API integration tests (slower, may hit mocked services)
│   ├── test_api_gateway.py
│   ├── test_auth_performance.py
│   └── ...
├── fixtures/                # Shared test data and factories
│   └── member_data.py
├── conftest.py              # Shared pytest fixtures (AWS credentials, DynamoDB tables)
├── requirements.txt         # Test dependencies (pytest, moto, hypothesis, etc.)
└── __init__.py
```

**Conventions:**

- Unit tests go in `tests/unit/` and test a single handler's logic in isolation
- Integration tests go in `tests/integration/` and test cross-handler or API-level behavior
- Fixtures in `tests/fixtures/` provide reusable test data factories
- `conftest.py` provides shared fixtures available to all tests (mocked AWS credentials, DynamoDB tables)

### Frontend Structure (`frontend/src/`)

```
frontend/src/
├── components/
│   ├── MemberCard.tsx
│   └── MemberCard.test.tsx          # Co-located component test
├── modules/
│   └── members/
│       ├── MemberList.tsx
│       └── __tests__/
│           └── MemberList.test.tsx   # Feature-specific tests
├── services/
│   └── __tests__/
│       └── memberService.test.ts    # Service layer tests
├── utils/
│   └── __tests__/
│       └── formatters.test.ts       # Utility function tests
└── hooks/
    └── __tests__/
        └── useMembers.test.ts       # Custom hook tests
```

**Conventions:**

- Co-locate simple component tests next to the component: `Component.test.tsx`
- Feature-level tests go in `modules/{feature}/__tests__/`
- Service and utility tests go in their respective `__tests__/` directories
- Use `data-testid` attributes for reliable element selection

---

## Backend Testing (pytest + moto)

### Shared Fixtures (`conftest.py`)

The project uses a shared `conftest.py` that provides mocked AWS credentials and DynamoDB tables:

```python
# backend/tests/conftest.py
import pytest
import boto3
from moto import mock_aws
import os

@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'

@pytest.fixture
def dynamodb_table(aws_credentials):
    """Create a mocked DynamoDB table for testing."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        yield table

@pytest.fixture
def sample_member():
    """Sample member data for testing."""
    return {
        'id': 'test-member-1',
        'username': 'testuser',
        'email': 'test@hdcn.nl',
        'firstName': 'Test',
        'lastName': 'User',
        'status': 'active'
    }
```

### Example: Unit Test with moto

```python
# backend/tests/unit/test_get_members.py
import json
import pytest
from unittest.mock import patch, MagicMock
from moto import mock_aws
import boto3

# Add handler to path
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../handler/get_members'))

from app import lambda_handler


class TestGetMembers:
    """Test the get_members Lambda handler."""

    def create_auth_event(self, email="admin@hdcn.nl", groups=None):
        """Helper to create an authenticated API Gateway event."""
        import base64
        if groups is None:
            groups = ["Members_Read", "Regio_All"]
        payload = {"email": email, "cognito:groups": groups}
        encoded = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip('=')
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256"}).encode()
        ).decode().rstrip('=')
        token = f"{header}.{encoded}.signature"
        return {
            'httpMethod': 'GET',
            'headers': {'Authorization': f'Bearer {token}'}
        }

    @patch('app.load_members_from_dynamodb')
    @patch('app.filter_members_by_region')
    def test_returns_200_with_valid_permissions(self, mock_filter, mock_load):
        """Authenticated user with correct permissions gets member data."""
        mock_members = [
            {'lidnummer': '1', 'voornaam': 'Jan', 'regio': 'Utrecht'}
        ]
        mock_load.return_value = mock_members
        mock_filter.return_value = mock_members

        event = self.create_auth_event()
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert len(body['data']) == 1

    def test_returns_401_without_token(self):
        """Request without Authorization header returns 401."""
        event = {'httpMethod': 'GET', 'headers': {}}
        response = lambda_handler(event, None)
        assert response['statusCode'] == 401

    @patch('app.load_members_from_dynamodb')
    def test_returns_403_without_permission(self, mock_load):
        """User without Members_Read permission gets 403."""
        event = self.create_auth_event(groups=["hdcnLeden"])
        response = lambda_handler(event, None)
        assert response['statusCode'] == 403
        mock_load.assert_not_called()
```

### Example: Integration Test with moto

```python
# backend/tests/integration/test_member_flow.py
import pytest
import boto3
from moto import mock_aws
import os

@pytest.fixture
def members_table():
    """Full DynamoDB Members table with test data."""
    with mock_aws():
        os.environ['MEMBERS_TABLE_NAME'] = 'Members'
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'member_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        # Seed test data
        table.put_item(Item={
            'member_id': 'M001',
            'voornaam': 'Jan',
            'achternaam': 'de Vries',
            'regio': 'Utrecht',
            'status': 'Actief'
        })
        table.put_item(Item={
            'member_id': 'M002',
            'voornaam': 'Piet',
            'achternaam': 'Bakker',
            'regio': 'Zuid-Holland',
            'status': 'Actief'
        })
        yield table


def test_member_crud_flow(members_table):
    """Test creating, reading, and updating a member."""
    # Create
    members_table.put_item(Item={
        'member_id': 'M003',
        'voornaam': 'Kees',
        'achternaam': 'Jansen',
        'regio': 'Utrecht',
        'status': 'Actief'
    })

    # Read
    response = members_table.get_item(Key={'member_id': 'M003'})
    assert response['Item']['voornaam'] == 'Kees'

    # Update
    members_table.update_item(
        Key={'member_id': 'M003'},
        UpdateExpression='SET #s = :val',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={':val': 'Inactief'}
    )
    response = members_table.get_item(Key={'member_id': 'M003'})
    assert response['Item']['status'] == 'Inactief'
```

### Key Rules for Backend Tests

- **Always mock AWS services** — never hit real AWS in tests. Use `moto`'s `mock_aws()` context manager.
- **Set environment variables** in fixtures (`MEMBERS_TABLE_NAME`, `AWS_DEFAULT_REGION`, etc.)
- **Test the auth flow** — verify 401 (no token), 403 (wrong permissions), and 200 (valid) paths
- **Use `conftest.py`** for fixtures shared across multiple test files
- For authentication details, see [`.kiro/steering/authentication.md`](../../.kiro/steering/authentication.md)

---

## Frontend Testing (Jest + RTL)

### Example: Component Test

```typescript
// src/components/MemberCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import { MemberCard } from './MemberCard';

const renderWithChakra = (ui: React.ReactElement) =>
  render(<ChakraProvider>{ui}</ChakraProvider>);

describe('MemberCard', () => {
  const member = {
    id: '1',
    voornaam: 'Jan',
    achternaam: 'de Vries',
    email: 'jan@hdcn.nl',
    regio: 'Utrecht',
    status: 'Actief',
  };

  it('displays member name and email', () => {
    renderWithChakra(<MemberCard member={member} />);
    expect(screen.getByText('Jan de Vries')).toBeInTheDocument();
    expect(screen.getByText('jan@hdcn.nl')).toBeInTheDocument();
  });

  it('shows region badge', () => {
    renderWithChakra(<MemberCard member={member} />);
    expect(screen.getByText('Utrecht')).toBeInTheDocument();
  });

  it('calls onEdit when edit button is clicked', () => {
    const onEdit = jest.fn();
    renderWithChakra(<MemberCard member={member} onEdit={onEdit} />);
    fireEvent.click(screen.getByTestId('edit-member-btn'));
    expect(onEdit).toHaveBeenCalledWith(member);
  });
});
```

### Example: Service Test with Mocked API

```typescript
// src/services/__tests__/memberService.test.ts
import axios from "axios";
import { getMembers, createMember } from "../memberService";

jest.mock("axios");
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe("memberService", () => {
  afterEach(() => jest.clearAllMocks());

  it("fetches members from API", async () => {
    const members = [{ id: "1", voornaam: "Jan" }];
    mockedAxios.get.mockResolvedValueOnce({ data: { data: members } });

    const result = await getMembers();
    expect(result).toEqual(members);
    expect(mockedAxios.get).toHaveBeenCalledWith("/members");
  });

  it("throws on network error", async () => {
    mockedAxios.get.mockRejectedValueOnce(new Error("Network Error"));
    await expect(getMembers()).rejects.toThrow("Network Error");
  });
});
```

### Example: Hook Test

```typescript
// src/hooks/__tests__/useMembers.test.ts
import { renderHook, waitFor } from "@testing-library/react";
import { useMembers } from "../useMembers";
import * as memberService from "../../services/memberService";

jest.mock("../../services/memberService");

describe("useMembers", () => {
  it("returns members after loading", async () => {
    const members = [{ id: "1", voornaam: "Jan" }];
    (memberService.getMembers as jest.Mock).mockResolvedValue(members);

    const { result } = renderHook(() => useMembers());

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.members).toEqual(members);
  });
});
```

### Key Rules for Frontend Tests

- **Test user behavior**, not implementation details — use `getByText`, `getByRole`, `getByTestId`
- **Wrap Chakra UI components** in `<ChakraProvider>` when rendering
- **Mock API calls** with `jest.mock('axios')` — never hit real endpoints
- **Test error states** — loading spinners, error messages, empty states
- **Use `data-testid`** for elements that don't have accessible text/role
- For UI patterns and component conventions, see [`.kiro/steering/look-and-feel.md`](../../.kiro/steering/look-and-feel.md)

---

## Property-Based Testing

Property-based testing verifies that universal properties hold across many randomly generated inputs, catching edge cases that example-based tests miss.

### Backend: Hypothesis (Python)

```python
# backend/tests/unit/test_decimal_conversion_properties.py
from hypothesis import given, strategies as st, settings
from decimal import Decimal

# Import the function under test
from app import convert_dynamodb_to_python


@given(value=st.integers(min_value=-1_000_000, max_value=1_000_000))
def test_integer_decimals_always_convert_to_int(value):
    """Property: Any Decimal with no fractional part converts to int."""
    item = {'amount': Decimal(str(value))}
    result = convert_dynamodb_to_python(item)
    assert isinstance(result['amount'], int)
    assert result['amount'] == value


@given(
    integer_part=st.integers(min_value=-10000, max_value=10000),
    fractional=st.integers(min_value=1, max_value=99)
)
def test_fractional_decimals_always_convert_to_float(integer_part, fractional):
    """Property: Any Decimal with a non-zero fractional part converts to float."""
    value = Decimal(f"{integer_part}.{fractional:02d}")
    item = {'amount': value}
    result = convert_dynamodb_to_python(item)
    assert isinstance(result['amount'], float)


@given(data=st.dictionaries(
    keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('L',))),
    values=st.one_of(
        st.text(max_size=50),
        st.integers().map(lambda x: Decimal(str(x))),
        st.booleans(),
        st.none()
    ),
    min_size=1,
    max_size=10
))
@settings(max_examples=200)
def test_conversion_preserves_all_keys(data):
    """Property: Conversion never drops or adds keys."""
    result = convert_dynamodb_to_python(data)
    assert set(result.keys()) == set(data.keys())
```

### Frontend: fast-check (TypeScript)

```typescript
// src/utils/__tests__/formatters.property.test.ts
import fc from "fast-check";
import { formatCurrency, formatMemberNumber } from "../formatters";

describe("formatCurrency properties", () => {
  it("always produces a string starting with €", () => {
    fc.assert(
      fc.property(fc.float({ min: 0, max: 100000, noNaN: true }), (amount) => {
        const result = formatCurrency(amount);
        return result.startsWith("€");
      }),
    );
  });

  it("never returns empty string for valid input", () => {
    fc.assert(
      fc.property(fc.float({ min: 0, max: 100000, noNaN: true }), (amount) => {
        const result = formatCurrency(amount);
        return result.length > 0;
      }),
    );
  });
});

describe("formatMemberNumber properties", () => {
  it("always produces a fixed-length string", () => {
    fc.assert(
      fc.property(fc.integer({ min: 1, max: 99999 }), (num) => {
        const result = formatMemberNumber(num);
        return result.length === 5; // zero-padded to 5 digits
      }),
    );
  });

  it("round-trips through parseInt", () => {
    fc.assert(
      fc.property(fc.integer({ min: 1, max: 99999 }), (num) => {
        const formatted = formatMemberNumber(num);
        return parseInt(formatted, 10) === num;
      }),
    );
  });
});
```

### When to Use Property-Based Testing

| Use Case              | Example                               |
| --------------------- | ------------------------------------- |
| Data transformations  | DynamoDB Decimal → Python int/float   |
| Formatters/parsers    | Currency formatting, date parsing     |
| Validation logic      | Email validation, member number rules |
| Idempotent operations | Serialize → deserialize round-trips   |
| Business rules        | Regional filtering, permission checks |

### When NOT to Use Property-Based Testing

- Simple CRUD handlers with no complex logic
- UI rendering tests (use example-based RTL tests instead)
- Integration tests that depend on external service state

---

## Coverage Commands and Interpretation

### Running Coverage

```bash
# Backend — full coverage report with missing lines
cd backend
pytest --cov=handler --cov-report=term-missing

# Backend — HTML report (opens in browser)
pytest --cov=handler --cov-report=html
# Output: htmlcov/index.html

# Frontend — coverage report
cd frontend
npm test -- --coverage --watchAll=false

# Frontend — specific file coverage
npm test -- --coverage --collectCoverageFrom='src/modules/members/**/*.{ts,tsx}' --watchAll=false
```

### Interpreting Coverage Output

**Backend (`term-missing` output):**

```
Name                                    Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
handler/get_members/app.py                 45      3    93%   67-69
handler/create_member/app.py               62     12    81%   34-38, 55-60
handler/cognito_post_authentication/app.py 28      0   100%
---------------------------------------------------------------------
TOTAL                                     135     15    89%
```

- `Stmts`: Total executable statements
- `Miss`: Statements not executed by any test
- `Cover`: Percentage of statements covered
- `Missing`: Line numbers not covered — focus testing effort here

**Frontend (Jest output):**

```
----------|---------|----------|---------|---------|-------------------
File      | % Stmts | % Branch | % Funcs | % Lines | Uncovered Lines
----------|---------|----------|---------|---------|-------------------
All files |   82.5  |   71.3   |   78.9  |   82.5  |
 members/ |   91.2  |   85.0   |   90.0  |   91.2  |
  List.tsx|   88.0  |   80.0   |   85.7  |   88.0  | 45-48, 92
----------|---------|----------|---------|---------|-------------------
```

- `% Branch`: Percentage of if/else branches tested — often lower than line coverage
- Focus on `Uncovered Lines` to identify untested paths

### Coverage Targets

| Scope            | Line Coverage | Notes                           |
| ---------------- | ------------- | ------------------------------- |
| Frontend overall | 80%           | All `src/` code                 |
| Backend overall  | 85%           | All `handler/` code             |
| Critical paths   | 95%           | Auth, payments, data validation |

**Critical paths** include:

- Authentication handlers (`cognito_*`, auth layer)
- Payment processing (`create_payment`, `create_order`)
- Data validation logic (input sanitization, schema validation)

---

## CI Pipeline Requirements

### Current Setup (GitHub Actions)

Tests are triggered on push to `main` (path-filtered):

| Workflow              | Trigger Path  | Test Step                       |
| --------------------- | ------------- | ------------------------------- |
| `deploy-backend.yml`  | `backend/**`  | SAM build (implicit validation) |
| `deploy-frontend.yml` | `frontend/**` | `npm install` + `npm run build` |

### Requirements for Merge

1. **All tests must pass** — no merging with failing tests
2. **Secret scanning** — GitGuardian runs on every push (blocks on detected secrets)
3. **Build must succeed** — SAM build (backend) and npm build (frontend) must complete

### Adding Test Steps to CI

To add explicit test execution to the CI pipeline, add these steps before the build/deploy steps:

**Backend (add to `deploy-backend.yml`):**

```yaml
- name: Install test dependencies
  working-directory: backend
  run: pip install -r tests/requirements.txt

- name: Run tests
  working-directory: backend
  run: pytest tests/ --tb=short

- name: Check coverage
  working-directory: backend
  run: pytest --cov=handler --cov-report=term-missing --cov-fail-under=85
```

**Frontend (add to `deploy-frontend.yml`):**

```yaml
- name: Run tests
  working-directory: frontend
  run: npm test -- --watchAll=false --ci

- name: Check coverage
  working-directory: frontend
  run: npm test -- --coverage --watchAll=false --ci --coverageThreshold='{"global":{"lines":80}}'
```

### Local Pre-Merge Checklist

Before pushing to `main`, run locally:

```bash
# Backend
cd backend
pytest tests/ --tb=short
pytest --cov=handler --cov-report=term-missing

# Frontend
cd frontend
npm test -- --watchAll=false
npm test -- --coverage --watchAll=false
```

---

## Debugging Test Failures

### Backend Debugging

**See print output during tests:**

```bash
pytest tests/ -s                    # Show stdout/stderr
pytest tests/ -v                    # Verbose test names
pytest tests/ -s -v                 # Both
```

**Drop into debugger on failure:**

```bash
pytest tests/ --pdb                 # Opens pdb on first failure
pytest tests/ --pdb --pdbcls=IPython.terminal.debugger:TerminalPdb  # Use IPython
```

**Run a single test:**

```bash
pytest tests/unit/test_get_members_filtered.py::TestFilterMembersByRegion::test_regio_all_users_get_all_members -v
```

**Common issues:**

| Symptom                                  | Likely Cause                            | Fix                                                                |
| ---------------------------------------- | --------------------------------------- | ------------------------------------------------------------------ |
| `ModuleNotFoundError: shared`            | Handler path not in `sys.path`          | Add `sys.path.insert(0, ...)` at top of test                       |
| `botocore.exceptions.NoCredentialsError` | Missing moto mock                       | Wrap test in `@mock_aws` or use `aws_credentials` fixture          |
| `ResourceNotFoundException`              | Table not created in mock               | Create table in fixture before calling handler                     |
| `Decimal` assertion failures             | DynamoDB returns Decimal, not int/float | Use `convert_dynamodb_to_python()` or compare with `Decimal('45')` |

### Frontend Debugging

**See rendered HTML:**

```typescript
import { screen } from "@testing-library/react";

// In your test:
screen.debug(); // Print full DOM
screen.debug(screen.getByRole("button")); // Print specific element
```

**Run a single test file:**

```bash
npm test -- MemberCard.test.tsx --watchAll=false
npm test -- --testPathPattern="modules/members" --watchAll=false
```

**Common issues:**

| Symptom                           | Likely Cause                       | Fix                                               |
| --------------------------------- | ---------------------------------- | ------------------------------------------------- |
| `Unable to find role "button"`    | Element not rendered or wrong role | Use `screen.debug()` to inspect actual DOM        |
| `act(...)` warnings               | State update outside act boundary  | Wrap async operations in `waitFor()`              |
| `ChakraProvider` errors           | Component needs theme context      | Wrap render in `<ChakraProvider>`                 |
| `TypeError: Cannot read property` | Mock not returning expected shape  | Check mock return value matches real API response |
| `jest.mock` not working           | Mock path doesn't match import     | Ensure mock path matches the import path exactly  |

### Hypothesis (Property-Based) Debugging

```bash
# Show generated examples
pytest tests/ -s --hypothesis-show-statistics

# Reproduce a specific failure (Hypothesis stores failing examples)
pytest tests/ --hypothesis-seed=12345

# Increase verbosity
pytest tests/ -s  # Hypothesis prints the failing example automatically
```

The `.hypothesis/` directory in `backend/` stores previously found counterexamples. These are replayed on subsequent runs to ensure regressions don't reappear.

### fast-check (Property-Based) Debugging

```typescript
// Set verbose mode to see all generated values
fc.assert(
  fc.property(fc.integer(), (n) => {
    return myFunction(n) > 0;
  }),
  { verbose: fc.VerbosityLevel.VeryVerbose },
);

// Reproduce with a specific seed
fc.assert(
  fc.property(fc.integer(), (n) => myFunction(n) > 0),
  { seed: 42 },
);
```

---

## Cross-References

- **Authentication patterns**: See [`.kiro/steering/authentication.md`](../../.kiro/steering/authentication.md) for auth flow details used in test setup
- **DynamoDB conventions**: See [`.kiro/steering/aws-dynamodb.md`](../../.kiro/steering/aws-dynamodb.md) for table schemas and access patterns
- **Project structure**: See [`.kiro/steering/structure.md`](../../.kiro/steering/structure.md) for directory layout conventions
- **UI component patterns**: See [`docs/development/look-and-feel.md`](./look-and-feel.md) for component testing context
- **Deployment guardrails**: See [`docs/development/guardrails.md`](./guardrails.md) for safe deployment practices
