"""
Bug condition exploration test for scan_product handler.

Validates: Requirements 1.1, 1.2, 1.3

This test encodes the EXPECTED behavior after the fix:
- scan_product response MUST include `groep`, `subgroep`, and `images` for each product

On UNFIXED code, this test MUST FAIL — proving the bugs exist.
After the fix is applied, this test should PASS.

Counterexample (unfixed code): The response products contain only
product_id, name, price, variant_schema, is_parent, event_id, active —
but NOT groep, subgroep, or images.
"""

import json
import os
import sys
import importlib.util
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

# Path to the handler module (used for explicit import)
_handler_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'scan_product', 'app.py')
)

# Set environment before importing handler
os.environ['DYNAMODB_TABLE'] = 'Producten'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'


def _load_handler():
    """Load the scan_product handler module by file path, bypassing sys.path."""
    if 'app' in sys.modules:
        del sys.modules['app']
    spec = importlib.util.spec_from_file_location('app', _handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['app'] = module
    spec.loader.exec_module(module)
    return module


def _make_event():
    """Create a mock API Gateway event for GET /scan-product/."""
    return {
        'httpMethod': 'GET',
        'body': None,
        'requestContext': {
            'authorizer': {
                'claims': {
                    'email': 'user@h-dcn.nl',
                    'cognito:groups': 'Products_Read'
                }
            }
        },
        'headers': {'Authorization': 'Bearer mock-token'}
    }


def _auth_patches():
    """Return a context manager that patches auth functions."""
    return patch.multiple(
        'app',
        extract_user_credentials=lambda event: ('user@h-dcn.nl', ['Products_Read'], None),
        validate_permissions_with_regions=lambda roles, perms, email, region: (True, None, {}),
        log_successful_access=lambda *a, **kw: None,
    )


@pytest.fixture
def producten_table():
    """Create a mocked Producten DynamoDB table and load the handler."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Producten',
            KeySchema=[{'AttributeName': 'product_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'product_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )

        handler_module = _load_handler()
        yield table, handler_module


class TestScanProductBugCondition:
    """
    Bug condition exploration: scan_product omits groep, subgroep, and images.

    These tests assert the EXPECTED (correct) behavior. On unfixed code they
    MUST FAIL, confirming the bug exists.
    """

    def test_response_includes_groep_field(self, producten_table):
        """scan_product response must include 'groep' when DynamoDB item has it.

        Bug 1.1: On unfixed code, the normalized response omits 'groep',
        so the ProductFilter cannot build its group filter tree.
        """
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'prod-001',
            'name': 'Club Polo',
            'price': 45,
            'groep': 'Kleding',
            'subgroep': 'Polo',
            'is_parent': True,
            'active': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body) == 1
        product = body[0]
        assert 'groep' in product, (
            f"Bug confirmed: 'groep' missing from scan_product response. "
            f"Keys returned: {list(product.keys())}"
        )
        assert product['groep'] == 'Kleding'

    def test_response_includes_subgroep_field(self, producten_table):
        """scan_product response must include 'subgroep' when DynamoDB item has it.

        Bug 1.1: On unfixed code, the normalized response omits 'subgroep',
        so the ProductFilter cannot build its subgroup filter tree.
        """
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'prod-002',
            'name': 'Harley Cap',
            'price': 25,
            'groep': 'Accessoires',
            'subgroep': 'Petten',
            'is_parent': True,
            'active': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body) == 1
        product = body[0]
        assert 'subgroep' in product, (
            f"Bug confirmed: 'subgroep' missing from scan_product response. "
            f"Keys returned: {list(product.keys())}"
        )
        assert product['subgroep'] == 'Petten'

    def test_response_includes_images_field(self, producten_table):
        """scan_product response must include 'images' when DynamoDB item has it.

        Bug 1.2: On unfixed code, the normalized response omits 'images',
        so ProductCard displays "Geen afbeelding" placeholder instead of
        actual product images.
        """
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'prod-003',
            'name': 'Club Jacket',
            'price': 120,
            'groep': 'Kleding',
            'subgroep': 'Jassen',
            'images': ['s3://bucket/jacket-front.jpg', 's3://bucket/jacket-back.jpg'],
            'is_parent': True,
            'active': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body) == 1
        product = body[0]
        assert 'images' in product, (
            f"Bug confirmed: 'images' missing from scan_product response. "
            f"Keys returned: {list(product.keys())}"
        )
        assert product['images'] == ['s3://bucket/jacket-front.jpg', 's3://bucket/jacket-back.jpg']

    def test_all_three_fields_present_together(self, producten_table):
        """scan_product response must include groep, subgroep, AND images together.

        Combined check: all three missing fields must be present in a single product.
        """
        table, handler = producten_table

        table.put_item(Item={
            'product_id': 'prod-004',
            'name': 'Event T-shirt 2027',
            'price': 35,
            'groep': 'Evenementen',
            'subgroep': 'T-shirts',
            'images': ['s3://bucket/tshirt.jpg'],
            'is_parent': True,
            'event_id': 'evt-2027',
            'active': True,
        })

        with _auth_patches():
            response = handler.lambda_handler(_make_event(), {})

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body) == 1
        product = body[0]

        missing_fields = []
        if 'groep' not in product:
            missing_fields.append('groep')
        if 'subgroep' not in product:
            missing_fields.append('subgroep')
        if 'images' not in product:
            missing_fields.append('images')

        assert not missing_fields, (
            f"Bug confirmed: fields {missing_fields} missing from scan_product response. "
            f"Keys returned: {list(product.keys())}"
        )
