"""
Unit tests for the delete_member handler.

Tests:
- Happy path: deletes member successfully
- Unauthorized: returns 403 when permissions insufficient
- Not found / non-existent member_id: delete_item is idempotent (no error)
- Invalid request: missing member_id path parameter
- OPTIONS request: returns CORS preflight response
"""

import json
import os
import sys
import importlib.util
import pytest
import boto3
from unittest.mock import patch
from moto import mock_aws

# Set environment before importing handler
os.environ['MEMBERS_TABLE_NAME'] = 'Members'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

# Handler path for importlib loading
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'delete_member', 'app.py')
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


def _make_event(member_id=None):
    """Create a mock API Gateway DELETE event."""
    path_params = {}
    if member_id is not None:
        path_params['id'] = member_id

    return {
        'httpMethod': 'DELETE',
        'pathParameters': path_params if path_params else None,
        'body': None,
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'admin@h-dcn.nl',
                    'cognito:groups': 'Members_CRUD'
                }
            }
        },
        'headers': {'Authorization': 'Bearer mock-token'}
    }


def _auth_patches():
    """Return a context manager that patches auth functions for authorized access."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('admin@h-dcn.nl', ['Members_CRUD'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


def _denied_auth_patches():
    """Return a context manager that patches auth functions to deny access."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('viewer@h-dcn.nl', ['Members_Read'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (
            False,
            {'statusCode': 403, 'body': json.dumps({'message': 'Forbidden'})},
            {}
        ),
        log_successful_access=lambda *a, **kw: None,
    )


@pytest.fixture
def table_and_handler():
    """Create mocked DynamoDB Members table and load the handler."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')

        members_table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[{'AttributeName': 'member_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'member_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        handler_module = _load_handler()
        handler_module.table = members_table

        yield members_table, handler_module


def test_delete_member_success(table_and_handler):
    """Member is deleted successfully and returns 200."""
    members_table, handler = table_and_handler

    # Create a member to delete
    members_table.put_item(Item={
        'member_id': 'member-123',
        'naam': 'Jan de Vries',
        'email': 'jan@example.nl',
        'regio': 'Noord',
        'active': True,
    })

    event = _make_event('member-123')

    with _auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'deleted successfully' in body['message']

    # Verify member is gone
    result = members_table.get_item(Key={'member_id': 'member-123'})
    assert 'Item' not in result


def test_delete_member_permission_denied(table_and_handler):
    """User without members_delete permission returns 403."""
    _, handler = table_and_handler

    event = _make_event('member-123')

    with _denied_auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 403


def test_delete_member_nonexistent(table_and_handler):
    """Deleting a non-existent member_id succeeds (DynamoDB delete_item is idempotent)."""
    _, handler = table_and_handler

    event = _make_event('nonexistent-member')

    with _auth_patches():
        response = handler.lambda_handler(event, {})

    # DynamoDB delete_item does not raise on missing key — returns 200
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'deleted successfully' in body['message']


def test_delete_member_missing_path_params(table_and_handler):
    """Missing pathParameters (None) returns 500 — TypeError caught by generic handler."""
    _, handler = table_and_handler

    event = {
        'httpMethod': 'DELETE',
        'pathParameters': None,
        'body': None,
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'admin@h-dcn.nl',
                    'cognito:groups': 'Members_CRUD'
                }
            }
        },
        'headers': {'Authorization': 'Bearer mock-token'}
    }

    with _auth_patches():
        response = handler.lambda_handler(event, {})

    # pathParameters=None causes TypeError (not KeyError), caught by generic Exception handler
    assert response['statusCode'] == 500


def test_delete_member_missing_id_in_path(table_and_handler):
    """pathParameters present but 'id' key missing returns 400."""
    _, handler = table_and_handler

    event = {
        'httpMethod': 'DELETE',
        'pathParameters': {},
        'body': None,
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'admin@h-dcn.nl',
                    'cognito:groups': 'Members_CRUD'
                }
            }
        },
        'headers': {'Authorization': 'Bearer mock-token'}
    }

    with _auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 400


def test_delete_member_options_request(table_and_handler):
    """OPTIONS request returns CORS preflight response."""
    _, handler = table_and_handler

    event = {
        'httpMethod': 'OPTIONS',
        'pathParameters': None,
        'body': None,
        'requestContext': {},
        'headers': {}
    }

    with _auth_patches():
        response = handler.lambda_handler(event, {})

    assert response['statusCode'] == 200
