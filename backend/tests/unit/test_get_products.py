"""
Unit tests for the get_products handler.

Tests event_id-filtered product listing for webshop buyers,
covering access validation and product filtering by event_id.
"""

import json
import pytest
import sys
import os
import boto3
from moto import mock_aws
from decimal import Decimal

# Ensure shared layer is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')))


def _create_jwt_payload(email, groups):
    """Create a mock JWT token payload for testing."""
    import base64
    payload = json.dumps({
        "email": email,
        "cognito:groups": groups,
    })
    # Create a fake but structurally valid JWT (header.payload.signature)
    header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256"}).encode()).rstrip(b'=').decode()
    body = base64.urlsafe_b64encode(payload.encode()).rstrip(b'=').decode()
    sig = base64.urlsafe_b64encode(b'fake_signature').rstrip(b'=').decode()
    return f"{header}.{body}.{sig}"


def _build_event(event_id=None, groups=None, email="user@h-dcn.nl"):
    """Build an API Gateway event for the get_products handler."""
    if groups is None:
        groups = ["hdcnLeden"]
    token = _create_jwt_payload(email, groups)
    event = {
        "httpMethod": "GET",
        "headers": {
            "Authorization": f"Bearer {token}",
        },
        "queryStringParameters": {},
    }
    if event_id is not None:
        event["queryStringParameters"]["event_id"] = event_id
    return event


@pytest.fixture
def producten_table():
    """Create a mocked Producten DynamoDB table with test products."""
    with mock_aws():
        os.environ['PRODUCTEN_TABLE_NAME'] = 'Producten'
        os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
        os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'

        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )

        # Seed test products — webshop products (event_id=null)
        table.put_item(Item={
            'product_id': 'prod_hdcn_1',
            'name': 'H-DCN T-shirt',
            'description': 'Club T-shirt',
            'price': Decimal('25.00'),
            'event_id': None,
            'is_parent': True,
            'active': True,
            'groep': 'Kleding',
            'subgroep': 'T-shirts',
            'images': ['https://s3.example.com/img1.jpg'],
            'variant_schema': {'Maat': ['S', 'M', 'L']},
            'order_item_fields': None,
            'purchase_rules': {'max_per_order': 5},
        })
        table.put_item(Item={
            'product_id': 'prod_hdcn_2',
            'name': 'H-DCN Pet',
            'description': 'Club cap',
            'price': Decimal('15.00'),
            'event_id': None,
            'is_parent': True,
            'active': True,
            'groep': 'Accessoires',
            'subgroep': None,
            'images': [],
            'variant_schema': None,
            'order_item_fields': None,
            'purchase_rules': None,
        })
        # Event-linked product (event_id set)
        table.put_item(Item={
            'product_id': 'prod_presmeet_1',
            'name': 'PresMeet Diner',
            'description': 'Dinner reservation',
            'price': Decimal('50.00'),
            'event_id': 'evt_presmeet_2027',
            'is_parent': True,
            'active': True,
            'groep': 'Events',
            'subgroep': None,
            'images': [],
            'variant_schema': None,
            'order_item_fields': [{'id': 'name', 'label': 'Naam', 'type': 'text', 'required': True}],
            'purchase_rules': {'max_per_club': 10},
        })
        # Inactive product — should not appear
        table.put_item(Item={
            'product_id': 'prod_hdcn_inactive',
            'name': 'Old Product',
            'description': 'Inactive',
            'price': Decimal('10.00'),
            'event_id': None,
            'is_parent': True,
            'active': False,
            'groep': None,
            'subgroep': None,
            'images': [],
        })
        # Variant record — should not appear (is_parent=False)
        table.put_item(Item={
            'product_id': 'var_prod_hdcn_1_s',
            'name': 'H-DCN T-shirt - S',
            'event_id': None,
            'is_parent': False,
            'parent_id': 'prod_hdcn_1',
            'active': True,
            'variant_attributes': {'Maat': 'S'},
            'stock': 10,
        })
        # Legacy product without 'active' field — should still appear (backward compatibility)
        table.put_item(Item={
            'product_id': 'prod_hdcn_legacy',
            'name': 'Legacy Product',
            'description': 'No active field',
            'price': Decimal('12.00'),
            'event_id': None,
            'is_parent': True,
            'groep': 'Overig',
            'subgroep': None,
            'images': [],
        })

        yield table


class TestGetProductsHandler:
    """Tests for the get_products Lambda handler."""

    def _import_handler(self):
        """Import the handler fresh (after moto mock is active)."""
        # Remove cached module if it exists
        if 'backend.handler.get_products.app' in sys.modules:
            del sys.modules['backend.handler.get_products.app']

        handler_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', '..', 'handler', 'get_products'
        ))
        if handler_path not in sys.path:
            sys.path.insert(0, handler_path)

        # Remove previously cached app module
        if 'app' in sys.modules:
            del sys.modules['app']

        import app
        return app.lambda_handler

    def test_options_request(self, producten_table):
        handler = self._import_handler()
        event = {"httpMethod": "OPTIONS", "headers": {}}
        result = handler(event, None)
        assert result['statusCode'] == 200

    def test_returns_webshop_products_with_event_id_null(self, producten_table):
        """Filter by event_id=null returns only webshop products (including legacy without active field)."""
        handler = self._import_handler()
        event = _build_event(event_id="null", groups=["hdcnLeden"])
        result = handler(event, None)

        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['total_count'] == 3
        product_ids = [p['product_id'] for p in body['products']]
        assert 'prod_hdcn_1' in product_ids
        assert 'prod_hdcn_2' in product_ids
        assert 'prod_hdcn_legacy' in product_ids
        # Inactive and variant should not appear
        assert 'prod_hdcn_inactive' not in product_ids
        assert 'var_prod_hdcn_1_s' not in product_ids

    def test_returns_event_products_with_specific_event_id(self, producten_table):
        """Filter by specific event_id returns only that event's products."""
        handler = self._import_handler()
        event = _build_event(event_id="evt_presmeet_2027", groups=["Regio_Pressmeet"])
        result = handler(event, None)

        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['total_count'] == 1
        assert body['products'][0]['product_id'] == 'prod_presmeet_1'

    def test_returns_all_active_products_without_event_id_filter(self, producten_table):
        """No event_id filter returns all active parent products (including legacy without active field)."""
        handler = self._import_handler()
        event = _build_event(event_id=None, groups=["hdcnLeden", "Regio_Pressmeet"])
        result = handler(event, None)

        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        # All 3 active parent products + 1 legacy product without active field
        assert body['total_count'] == 4

    def test_product_fields_included_in_response(self, producten_table):
        handler = self._import_handler()
        event = _build_event(event_id="null", groups=["hdcnLeden"])
        result = handler(event, None)

        body = json.loads(result['body'])
        product = next(p for p in body['products'] if p['product_id'] == 'prod_hdcn_1')
        assert product['groep'] == 'Kleding'
        assert product['subgroep'] == 'T-shirts'
        assert product['images'] == ['https://s3.example.com/img1.jpg']
        assert product['variant_schema'] == {'Maat': ['S', 'M', 'L']}
        # DynamoDB returns Decimal values serialized as strings via json.dumps(default=str)
        assert product['purchase_rules'] == {'max_per_order': '5'}

    def test_unauthorized_returns_401(self, producten_table):
        handler = self._import_handler()
        event = {
            "httpMethod": "GET",
            "headers": {},  # No Authorization header
            "queryStringParameters": {},
        }
        result = handler(event, None)
        assert result['statusCode'] == 401

    def test_no_webshop_access_returns_403(self, producten_table):
        handler = self._import_handler()
        # verzoek_lid has no product access roles
        event = _build_event(event_id="null", groups=["verzoek_lid"])
        result = handler(event, None)
        assert result['statusCode'] == 403

    def test_inactive_products_excluded(self, producten_table):
        """Products with active=false are excluded from customer-facing listing."""
        handler = self._import_handler()
        event = _build_event(event_id=None, groups=["hdcnLeden", "Regio_Pressmeet"])
        result = handler(event, None)

        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        product_ids = [p['product_id'] for p in body['products']]
        assert 'prod_hdcn_inactive' not in product_ids

    def test_legacy_products_without_active_field_included(self, producten_table):
        """Products without an active field are included (backward compatibility)."""
        handler = self._import_handler()
        event = _build_event(event_id="null", groups=["hdcnLeden"])
        result = handler(event, None)

        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        product_ids = [p['product_id'] for p in body['products']]
        assert 'prod_hdcn_legacy' in product_ids
