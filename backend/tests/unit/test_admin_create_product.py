"""
Unit tests for the admin_create_product handler.

Tests the modified handler that supports:
- order_item_fields, purchase_rules fields
- Default_Variant creation (variant_schema no longer triggers sync)
- groep, subgroep, images catalog fields
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
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

# Handler path for importlib loading
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'admin_create_product', 'app.py')
)


def _load_handler():
    """Load handler module by file path, bypassing sys.path.

    Cleans stale shared modules from sys.modules to prevent cross-contamination
    when other tests (e.g. test_admin_bulk_create_variants) leave partial
    shared.variant_helpers in the module cache.
    """
    if 'app' in sys.modules:
        del sys.modules['app']

    # Remove stale shared.* modules that may have been left by other tests
    # with incomplete exports (e.g. missing create_default_variant)
    stale_keys = [k for k in sys.modules if k.startswith('shared.')]
    for key in stale_keys:
        del sys.modules[key]

    spec = importlib.util.spec_from_file_location('app', _handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['app'] = module
    spec.loader.exec_module(module)
    return module


def _make_event(body):
    """Create a mock API Gateway event."""
    return {
        'httpMethod': 'POST',
        'body': json.dumps(body),
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'admin@h-dcn.nl',
                    'cognito:groups': 'Products_CRUD'
                }
            }
        },
        'headers': {'Authorization': 'Bearer mock-token'}
    }


def _auth_patches():
    """Return a context manager that patches auth functions."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('admin@h-dcn.nl', ['Products_CRUD'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


@pytest.fixture
def producten_table():
    """Create a mocked Producten DynamoDB table and load handler."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'product_id', 'AttributeType': 'S'},
                {'AttributeName': 'parent_id', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'parent_id-index',
                    'KeySchema': [
                        {'AttributeName': 'parent_id', 'KeyType': 'HASH'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )

        handler_module = _load_handler()
        handler_module.table = table

        yield table


def test_create_simple_product_with_default_variant(producten_table):
    """Product without variant_schema gets a Default_Variant."""
    import app as handler_module

    event = _make_event({'name': 'Simple Product', 'price': 15, 'event_id': None})

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    body = json.loads(response['body'])
    assert response['statusCode'] == 200
    assert body['variant_count'] == 1
    assert body['variants'][0]['variant_attributes'] == {}


def test_create_product_with_variant_schema_ignored(producten_table):
    """variant_schema in request body is ignored; only Default_Variant is created."""
    import app as handler_module

    event = _make_event({
        'name': 'T-Shirt',
        'price': 25,
        'event_id': None,
        'variant_schema': {
            'Maat': ['S', 'M', 'L'],
            'Gender': ['Male', 'Female']
        }
    })

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    body = json.loads(response['body'])
    assert response['statusCode'] == 200
    # variant_schema no longer triggers sync — only Default_Variant is created
    assert body['variant_count'] == 1
    assert 'variant_sync' not in body


def test_create_product_with_order_item_fields(producten_table):
    """Product with order_item_fields stores them on the product record."""
    import app as handler_module

    event = _make_event({
        'name': 'Event Ticket',
        'price': 50,
        'event_id': 'evt-presmeet-2025',
        'order_item_fields': [
            {
                'id': 'attendee_name',
                'label': 'Naam deelnemer',
                'type': 'text',
                'required': True,
                'validation': {'min_length': 2, 'max_length': 100}
            }
        ]
    })

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    body = json.loads(response['body'])
    assert response['statusCode'] == 200
    product = body['product']
    assert product['order_item_fields'][0]['id'] == 'attendee_name'


def test_create_product_with_purchase_rules(producten_table):
    """Product with purchase_rules stores them correctly."""
    import app as handler_module

    event = _make_event({
        'name': 'Limited Edition',
        'price': 100,
        'event_id': None,
        'purchase_rules': {
            'max_per_order': 2,
            'max_per_member': 1,
            'requires_membership': True,
            'order_mode': 'single'
        }
    })

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    body = json.loads(response['body'])
    assert response['statusCode'] == 200
    product = body['product']
    assert product['purchase_rules']['max_per_order'] == 2
    assert product['purchase_rules']['requires_membership'] is True


def test_create_product_with_catalog_fields(producten_table):
    """Product with groep, subgroep, images stores them correctly."""
    import app as handler_module

    event = _make_event({
        'name': 'Club Shirt',
        'price': 30,
        'event_id': None,
        'groep': 'Kleding',
        'subgroep': 'T-shirts',
        'images': ['https://s3.example.com/img1.jpg', 'https://s3.example.com/img2.jpg']
    })

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    body = json.loads(response['body'])
    assert response['statusCode'] == 200
    product = body['product']
    assert product['groep'] == 'Kleding'
    assert product['subgroep'] == 'T-shirts'
    assert len(product['images']) == 2


def test_variant_schema_in_body_ignored(producten_table):
    """variant_schema in request body is silently ignored (no validation, no storage)."""
    import app as handler_module

    event = _make_event({
        'name': 'Bad Product',
        'price': 10,
        'variant_schema': {'Maat': []}  # previously invalid, now just ignored
    })

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    # No longer validated — product is created with Default_Variant
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['variant_count'] == 1
    # variant_schema not stored on the product record
    assert 'variant_schema' not in body['product']


def test_invalid_purchase_rules_rejected(producten_table):
    """Invalid purchase_rules returns 400."""
    import app as handler_module

    event = _make_event({
        'name': 'Bad Product',
        'price': 10,
        'purchase_rules': {'max_per_order': -5}  # negative, invalid
    })

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    assert response['statusCode'] == 400


def test_invalid_images_rejected(producten_table):
    """Too many images returns 400."""
    import app as handler_module

    event = _make_event({
        'name': 'Too Many Images',
        'price': 10,
        'images': [f'https://s3.example.com/img{i}.jpg' for i in range(11)]
    })

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    assert response['statusCode'] == 400


def test_all_three_fields_together(producten_table):
    """Product with order_item_fields, purchase_rules plus catalog fields works."""
    import app as handler_module

    event = _make_event({
        'name': 'PresMeet Full Product',
        'price': 75,
        'event_id': 'evt-presmeet-2025',
        'order_item_fields': [
            {'id': 'name', 'label': 'Name', 'type': 'text', 'required': True}
        ],
        'purchase_rules': {
            'max_per_club': 20,
            'min_per_club': 5,
            'order_mode': 'persistent'
        },
        'groep': 'Events',
        'subgroep': 'Conference'
    })

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    body = json.loads(response['body'])
    assert response['statusCode'] == 200
    # Default_Variant created (no variant_schema sync)
    assert body['variant_count'] == 1
    product = body['product']
    assert 'variant_schema' not in product
    assert product['order_item_fields'][0]['id'] == 'name'
    assert product['purchase_rules']['order_mode'] == 'persistent'
    assert product['groep'] == 'Events'


def test_invalid_json_body(producten_table):
    """Malformed JSON returns 400."""
    import app as handler_module

    event = {
        'httpMethod': 'POST',
        'body': 'not valid json{{{',
        'requestContext': {'authorizer': {'claims': {}}},
        'headers': {'Authorization': 'Bearer mock-token'}
    }

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    assert response['statusCode'] == 400


def test_groep_too_long_rejected(producten_table):
    """groep exceeding 50 chars is rejected."""
    import app as handler_module

    event = _make_event({
        'name': 'Product',
        'price': 10,
        'groep': 'A' * 51
    })

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    assert response['statusCode'] == 400


# ──────────────────────────────────────────────────────────────────────────────
# Tests for event_id / event_ids stripping (Requirements 3.1, 3.2, 3.3)
# ──────────────────────────────────────────────────────────────────────────────


def test_event_id_stripped_from_stored_product(producten_table):
    """event_id in payload is stripped and not persisted to DynamoDB.

    Validates: Requirements 3.1
    """
    import app as handler_module

    event = _make_event({
        'name': 'Product With Event ID',
        'price': 20,
        'event_id': 'evt-presmeet-2025',
    })

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    product_id = body['product']['product_id']

    # Verify directly in DynamoDB that event_id is not stored
    stored_item = producten_table.get_item(Key={'product_id': product_id})['Item']
    assert 'event_id' not in stored_item


def test_event_ids_stripped_from_stored_product(producten_table):
    """event_ids in payload is stripped and not persisted to DynamoDB.

    Validates: Requirements 3.2
    """
    import app as handler_module

    event = _make_event({
        'name': 'Product With Event IDs',
        'price': 25,
        'event_ids': ['evt-001', 'evt-002', 'evt-003'],
    })

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    product_id = body['product']['product_id']

    # Verify directly in DynamoDB that event_ids is not stored
    stored_item = producten_table.get_item(Key={'product_id': product_id})['Item']
    assert 'event_ids' not in stored_item


def test_both_event_id_and_event_ids_stripped(producten_table):
    """Both event_id and event_ids in payload are stripped simultaneously.

    Validates: Requirements 3.1, 3.2
    """
    import app as handler_module

    event = _make_event({
        'name': 'Product With Both Event Fields',
        'price': 30,
        'event_id': 'evt-main-event',
        'event_ids': ['evt-001', 'evt-002'],
    })

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    product_id = body['product']['product_id']

    # Verify neither field is stored in DynamoDB
    stored_item = producten_table.get_item(Key={'product_id': product_id})['Item']
    assert 'event_id' not in stored_item
    assert 'event_ids' not in stored_item


def test_valid_fields_still_stored_when_event_id_stripped(producten_table):
    """Valid fields are persisted correctly even when event_id/event_ids are present in payload.

    Validates: Requirements 3.3
    """
    import app as handler_module

    event = _make_event({
        'name': 'Full Product',
        'price': 45,
        'description': 'A nice product',
        'category': 'Merchandise',
        'groep': 'Kleding',
        'subgroep': 'Shirts',
        'event_id': 'evt-should-be-stripped',
        'event_ids': ['evt-also-stripped'],
    })

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    product_id = body['product']['product_id']

    # Verify valid fields are stored in DynamoDB
    stored_item = producten_table.get_item(Key={'product_id': product_id})['Item']
    assert stored_item['name'] == 'Full Product'
    assert stored_item['description'] == 'A nice product'
    assert stored_item['category'] == 'Merchandise'
    assert stored_item['groep'] == 'Kleding'
    assert stored_item['subgroep'] == 'Shirts'
    assert 'product_id' in stored_item
    assert 'created_at' in stored_item
    assert 'updated_at' in stored_item

    # And event fields are NOT stored
    assert 'event_id' not in stored_item
    assert 'event_ids' not in stored_item
