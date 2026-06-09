"""
Unit tests for the admin_create_product handler.

Tests the modified handler that supports:
- variant_schema, order_item_fields, purchase_rules fields
- Variant generation from variant_schema
- Default_Variant creation when no variant_schema
- groep, subgroep, images catalog fields
"""

import json
import os
import sys
import pytest
import boto3
from unittest.mock import patch
from moto import mock_aws

# Ensure auth layer is importable
_layers_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
)
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)

# Ensure handler is importable
_handler_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'admin_create_product')
)
if _handler_path not in sys.path:
    sys.path.insert(0, _handler_path)

# Set environment before importing handler
os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'


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
    """Create a mocked Producten DynamoDB table."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        # Ensure our handler path is first in sys.path so `import app` resolves correctly
        if sys.path[0] != _handler_path:
            if _handler_path in sys.path:
                sys.path.remove(_handler_path)
            sys.path.insert(0, _handler_path)

        # Clear any stale app module cache
        if 'app' in sys.modules:
            del sys.modules['app']

        # Patch the handler's table reference to use the mocked table
        import app as handler_module
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


def test_create_product_with_variant_schema(producten_table):
    """Product with variant_schema generates correct number of variants."""
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
    # 3 sizes * 2 genders = 6 variants
    assert body['variant_count'] == 6
    for variant in body['variants']:
        assert 'Maat' in variant['variant_attributes']
        assert 'Gender' in variant['variant_attributes']


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


def test_invalid_variant_schema_rejected(producten_table):
    """Invalid variant_schema returns 400 with structured errors."""
    import app as handler_module

    event = _make_event({
        'name': 'Bad Product',
        'price': 10,
        'variant_schema': {'Maat': []}  # empty axis values
    })

    with _auth_patches():
        response = handler_module.lambda_handler(event, {})

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'errors' in body


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
    """Product with all three new fields plus catalog fields works."""
    import app as handler_module

    event = _make_event({
        'name': 'PresMeet Full Product',
        'price': 75,
        'event_id': 'evt-presmeet-2025',
        'variant_schema': {'Gender': ['Male', 'Female']},
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
    assert body['variant_count'] == 2
    product = body['product']
    assert product['variant_schema'] == {'Gender': ['Male', 'Female']}
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
