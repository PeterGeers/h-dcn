# pytest configuration for H-DCN Dashboard backend tests

import pytest
import boto3
from moto import mock_aws
import os
import sys
import importlib

# Ensure the auth layer path is available for all tests, so that
# handlers importing from `shared.event_validation` (etc.) can resolve correctly.
# This must come before the backend/shared/ path to take priority.
_layers_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'layers', 'auth-layer', 'python'))
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)


def pytest_collectstart(collector):
    """
    Clear cached 'app' module before collecting each test module.

    Multiple test files add different handler directories to sys.path and then
    do `from app import ...`. Without clearing the module cache, Python reuses
    the first 'app' module it ever imported, causing ImportErrors when a
    different test file expects a different handler's app.py.
    """
    if 'app' in sys.modules:
        del sys.modules['app']

    # Also remove stale handler paths from previous test modules
    handler_base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'handler'))
    # Use os.sep-normalized comparison to work on both Windows and Linux
    handler_base_normalized = os.path.normpath(handler_base) + os.sep
    sys.path[:] = [
        p for p in sys.path
        if not (os.path.normpath(p) + os.sep).startswith(handler_base_normalized)
        and os.path.normpath(p) != os.path.normpath(handler_base)
    ]


def pytest_runtest_setup(item):
    """
    Clear cached 'app' module before each test runs and ensure the correct
    handler directory is at the front of sys.path.

    This handles the case where `from app import ...` is done inside test
    methods (not at module level), ensuring each test uses the correct
    handler's app module based on its sys.path setup.

    Also cleans up stale handler paths from previous test modules to prevent
    cross-contamination when tests are run in the full suite.
    """
    if 'app' in sys.modules:
        del sys.modules['app']

    # Remove all handler directories from sys.path, then let each test
    # re-add its own. This prevents stale paths from earlier tests causing
    # the wrong app.py to be imported.
    handler_base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'handler'))
    handler_base_normalized = os.path.normpath(handler_base) + os.sep
    sys.path[:] = [
        p for p in sys.path
        if not (os.path.normpath(p) + os.sep).startswith(handler_base_normalized)
        and os.path.normpath(p) != os.path.normpath(handler_base)
    ]

    # Re-add handler path if the test module defines _handler_path or _handler_dir
    test_module = item.module if hasattr(item, 'module') else None
    if test_module:
        handler_path = getattr(test_module, '_handler_path', None) or getattr(test_module, '_handler_dir', None)
        if handler_path and handler_path not in sys.path:
            sys.path.insert(0, handler_path)

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
        
        # Create Members table
        table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                }
            ],
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