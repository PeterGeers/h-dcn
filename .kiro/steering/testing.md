# Testing Conventions

## Critical Rules

### Never hardcode DynamoDB table names in handlers

Always use environment variables with a fallback:

```python
table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))
```

The SAM template must pass the table name via `Environment.Variables`. This enables the test environment to use different table names (e.g., `Members-Test`).

### Never use `import app` via sys.path in tests

When testing a handler's `app.py`, **never** rely on `sys.path` manipulation to import it. This causes cross-contamination when the full test suite runs in alphabetical order.

**Correct approach — use `importlib.util`:**

```python
import importlib.util

_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', '<handler_name>', 'app.py')
)

def _load_handler():
    """Load handler module by file path, bypassing sys.path."""
    if 'app' in sys.modules:
        del sys.modules['app']
    spec = importlib.util.spec_from_file_location('app', _handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['app'] = module
    spec.loader.exec_module(module)
    return module
```

**Alternative approach — use full module path (when handler doesn't use bare `import app` internally):**

```python
from handler.submit_order.app import lambda_handler
```

### Patching auth in handler tests

When the handler is loaded as `'app'` module, patch auth like this:

```python
from unittest.mock import patch

def _auth_patches():
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('user@h-dcn.nl', ['Products_Read'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )
```

### Moto (mock_aws) usage

Always load the handler **inside** the `mock_aws()` context so boto3 resources created during handler execution are intercepted:

```python
@pytest.fixture
def my_table():
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(...)
        handler_module = _load_handler()
        yield table, handler_module
```

### Environment variables for tests

Set these before importing handlers:

```python
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
```

## Test File Structure

```
backend/tests/
├── unit/              # Unit tests (pytest + moto)
│   ├── test_<handler_name>.py          # Standard unit tests
│   ├── test_<handler_name>_properties.py  # Property-based tests (hypothesis)
│   └── conftest.py   # Shared fixtures + sys.path cleanup
├── integration/       # Integration tests
├── fixtures/          # Test data fixtures
└── conftest.py        # Root conftest (auth layer path setup)
```

## Running Tests

```bash
# From backend/ directory
pytest tests/                          # Full suite
pytest tests/unit/test_<name>.py       # Single file
pytest tests/ -k "scan_product"        # By keyword
pytest tests/ --tb=short -q            # Concise output
```
