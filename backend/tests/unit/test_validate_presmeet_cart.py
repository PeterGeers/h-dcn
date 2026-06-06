"""
Unit Tests for validate_presmeet_cart Lambda Handler

Tests the validate_presmeet_cart handler:
- Authentication and authorization flows
- Club-based access control (403 for missing club assignment)
- JSON body parsing and error handling
- Cart item validation against product_type schemas
- Return of validation errors with item_id, field, message, constraint

Requirements: 1.7, 8.1, 8.2, 10.2–10.6
"""

import json
import pytest
import base64
import sys
import os
from unittest.mock import patch, MagicMock

# Add the auth layer and backend root to sys.path for package-style imports
_layers_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../layers/auth-layer/python'))
_backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)
if _backend_path not in sys.path:
    sys.path.insert(1, _backend_path)

# Clear any previously cached `shared` module so it reloads from layers path
for mod_name in list(sys.modules.keys()):
    if mod_name == 'shared' or mod_name.startswith('shared.'):
        del sys.modules[mod_name]

# Set env var before importing
os.environ.setdefault('PRODUCTEN_TABLE_NAME', 'Producten')

# Use package-style import to avoid polluting the bare 'app' module cache
import handler.validate_presmeet_cart.app as app
from handler.validate_presmeet_cart.app import lambda_handler


def create_jwt_token(email="club@fhd.nl", groups=None):
    """Helper to create JWT tokens for testing."""
    if groups is None:
        groups = ["hdcnLeden", "Regio_Pressmeet", "club_amsterdam"]

    payload = {
        "email": email,
        "cognito:groups": groups,
        "exp": 9999999999,
        "iat": 1000000000,
    }

    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
    ).decode().rstrip('=')
    payload_encoded = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode().rstrip('=')
    signature = "test_signature"

    return f"{header}.{payload_encoded}.{signature}"


def make_event(token=None, body=None, method='POST'):
    """Helper to create an API Gateway event."""
    event = {
        'httpMethod': method,
        'headers': {},
        'queryStringParameters': None,
        'body': json.dumps(body) if body is not None else None,
    }
    if token:
        event['headers']['Authorization'] = f'Bearer {token}'
    return event


class TestValidatePresMeetCartAuth:
    """Test authentication flows."""

    @patch.object(app, 'producten_table')
    def test_missing_auth_returns_401(self, mock_table):
        """Unauthenticated request returns 401."""
        event = make_event(token=None, body={"items": []})
        response = lambda_handler(event, None)
        assert response['statusCode'] == 401

    @patch.object(app, 'producten_table')
    def test_no_club_group_returns_403(self, mock_table):
        """User without Regio_Pressmeet group returns 403 (PresMeet access required)."""
        token = create_jwt_token(groups=["hdcnLeden"])
        event = make_event(token=token, body={"items": []})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'PresMeet access required' in body.get('error', '')

    @patch('handler.validate_presmeet_cart.app.get_club_id', return_value=None)
    @patch.object(app, 'producten_table')
    def test_no_club_assignment_returns_403(self, mock_table, mock_club_id):
        """User with Regio_Pressmeet but no club_id returns 403."""
        token = create_jwt_token(groups=["hdcnLeden", "Regio_Pressmeet"])
        event = make_event(token=token, body={"items": []})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'Missing club assignment' in body.get('error', '')


class TestValidatePresMeetCartBodyParsing:
    """Test request body parsing and validation."""

    @patch('handler.validate_presmeet_cart.app.get_club_id', return_value='club_amsterdam')
    @patch.object(app, 'producten_table')
    def test_missing_body_returns_400(self, mock_table, mock_club_id):
        """Missing request body returns 400."""
        token = create_jwt_token()
        event = make_event(token=token)
        event['body'] = None
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid JSON' in body.get('error', '')

    @patch('handler.validate_presmeet_cart.app.get_club_id', return_value='club_amsterdam')
    @patch.object(app, 'producten_table')
    def test_invalid_json_returns_400(self, mock_table, mock_club_id):
        """Invalid JSON in body returns 400."""
        token = create_jwt_token()
        event = make_event(token=token)
        event['body'] = 'not valid json{'
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'Invalid JSON' in body.get('error', '')

    @patch('handler.validate_presmeet_cart.app.get_club_id', return_value='club_amsterdam')
    @patch.object(app, 'producten_table')
    def test_missing_items_field_returns_400(self, mock_table, mock_club_id):
        """Body without 'items' field returns 400."""
        token = create_jwt_token()
        event = make_event(token=token, body={"delegates": []})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'items' in body.get('error', '')

    @patch('handler.validate_presmeet_cart.app.get_club_id', return_value='club_amsterdam')
    @patch.object(app, 'producten_table')
    def test_items_not_array_returns_400(self, mock_table, mock_club_id):
        """Body with 'items' not as array returns 400."""
        token = create_jwt_token()
        event = make_event(token=token, body={"items": "not_an_array"})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'array' in body.get('error', '')


class TestValidatePresMeetCartValidation:
    """Test cart item validation logic."""

    @patch('handler.validate_presmeet_cart.app.get_club_id', return_value='club_amsterdam')
    @patch.object(app, 'producten_table')
    def test_valid_meeting_ticket_returns_success(self, mock_table, mock_club_id):
        """Valid meeting_ticket item passes validation."""
        mock_table.scan.return_value = {'Items': []}

        token = create_jwt_token()
        items = [{
            "item_id": "item-1",
            "product_type": "meeting_ticket",
            "attributes": {"name": "Jan de Vries", "role": "President"}
        }]
        event = make_event(token=token, body={"items": items})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['valid'] is True
        assert body['errors'] == []

    @patch('handler.validate_presmeet_cart.app.get_club_id', return_value='club_amsterdam')
    @patch.object(app, 'producten_table')
    def test_invalid_product_type_returns_error(self, mock_table, mock_club_id):
        """Invalid product_type returns validation error."""
        mock_table.scan.return_value = {'Items': []}

        token = create_jwt_token()
        items = [{
            "item_id": "item-1",
            "product_type": "invalid_type",
            "attributes": {}
        }]
        event = make_event(token=token, body={"items": items})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['valid'] is False
        assert len(body['errors']) == 1
        error = body['errors'][0]
        assert error['item_id'] == 'item-1'
        assert error['field'] == 'product_type'
        assert error['constraint'] == 'enum'

    @patch('handler.validate_presmeet_cart.app.get_club_id', return_value='club_amsterdam')
    @patch.object(app, 'producten_table')
    def test_missing_required_attribute_returns_error(self, mock_table, mock_club_id):
        """Missing required attribute returns validation error."""
        mock_table.scan.return_value = {'Items': []}

        token = create_jwt_token()
        items = [{
            "item_id": "item-2",
            "product_type": "meeting_ticket",
            "attributes": {"name": "Jan"}  # Missing 'role'
        }]
        event = make_event(token=token, body={"items": items})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['valid'] is False
        errors = body['errors']
        assert any(e['field'] == 'role' and e['constraint'] == 'required' for e in errors)

    @patch('handler.validate_presmeet_cart.app.get_club_id', return_value='club_amsterdam')
    @patch.object(app, 'producten_table')
    def test_invalid_enum_value_returns_error(self, mock_table, mock_club_id):
        """Invalid enum value returns validation error."""
        mock_table.scan.return_value = {'Items': []}

        token = create_jwt_token()
        items = [{
            "item_id": "item-3",
            "product_type": "tshirt",
            "attributes": {"name": "Piet", "gender": "other", "size": "M"}
        }]
        event = make_event(token=token, body={"items": items})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['valid'] is False
        errors = body['errors']
        assert any(e['field'] == 'gender' and e['constraint'] == 'enum' for e in errors)

    @patch('handler.validate_presmeet_cart.app.get_club_id', return_value='club_amsterdam')
    @patch.object(app, 'producten_table')
    def test_multiple_items_validated(self, mock_table, mock_club_id):
        """Multiple items are each validated independently."""
        mock_table.scan.return_value = {'Items': []}

        token = create_jwt_token()
        items = [
            {
                "item_id": "good-item",
                "product_type": "meeting_ticket",
                "attributes": {"name": "Jan", "role": "President"}
            },
            {
                "item_id": "bad-item",
                "product_type": "meeting_ticket",
                "attributes": {}  # Missing name and role
            }
        ]
        event = make_event(token=token, body={"items": items})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['valid'] is False
        errors = body['errors']
        # Only errors from bad-item
        assert all(e['item_id'] == 'bad-item' for e in errors)

    @patch('handler.validate_presmeet_cart.app.get_club_id', return_value='club_amsterdam')
    @patch.object(app, 'producten_table')
    def test_empty_items_returns_valid(self, mock_table, mock_club_id):
        """Empty items array returns valid=true with no errors."""
        mock_table.scan.return_value = {'Items': []}

        token = create_jwt_token()
        event = make_event(token=token, body={"items": []})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['valid'] is True
        assert body['errors'] == []

    @patch('handler.validate_presmeet_cart.app.get_club_id', return_value='club_amsterdam')
    @patch.object(app, 'producten_table')
    def test_missing_product_type_returns_error(self, mock_table, mock_club_id):
        """Item without product_type returns validation error."""
        mock_table.scan.return_value = {'Items': []}

        token = create_jwt_token()
        items = [{
            "item_id": "item-no-type",
            "attributes": {"name": "test"}
        }]
        event = make_event(token=token, body={"items": items})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['valid'] is False
        errors = body['errors']
        assert any(e['field'] == 'product_type' and e['constraint'] == 'required' for e in errors)

    @patch('handler.validate_presmeet_cart.app.get_club_id', return_value='club_amsterdam')
    @patch.object(app, 'producten_table')
    def test_type_constraint_violation_returns_error(self, mock_table, mock_club_id):
        """Attribute with wrong type returns validation error."""
        mock_table.scan.return_value = {'Items': []}

        token = create_jwt_token()
        items = [{
            "item_id": "item-type-err",
            "product_type": "airport_transfer",
            "attributes": {
                "direction": "pickup",
                "airport": "AMS",
                "flight": "KL1234",
                "date": "2025-09-15",
                "time": "14:30",
                "persons": "three"  # Should be integer
            }
        }]
        event = make_event(token=token, body={"items": items})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['valid'] is False
        errors = body['errors']
        assert any(e['field'] == 'persons' and e['constraint'] == 'type' for e in errors)


class TestValidatePresMeetCartWithConfig:
    """Test validation using config records from Producten table."""

    @patch('handler.validate_presmeet_cart.app.get_club_id', return_value='club_amsterdam')
    @patch.object(app, 'producten_table')
    def test_uses_db_config_when_available(self, mock_table, mock_club_id):
        """Uses config from Producten table instead of defaults when available."""
        # Config record with custom schema
        config_item = {
            'product_id': 'config_presmeet_meeting_ticket',
            'product_type': 'meeting_ticket',
            'source': 'presmeet_config',
            'required_attributes': {
                'name': {'type': 'string', 'required': True, 'min_length': 1, 'max_length': 50},
                'role': {'type': 'string', 'required': True, 'min_length': 1, 'max_length': 50},
            }
        }
        mock_table.scan.return_value = {'Items': [config_item]}

        token = create_jwt_token()
        # Name exceeds custom max_length of 50
        items = [{
            "item_id": "item-cfg",
            "product_type": "meeting_ticket",
            "attributes": {"name": "A" * 51, "role": "President"}
        }]
        event = make_event(token=token, body={"items": items})
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['valid'] is False
        errors = body['errors']
        assert any(e['field'] == 'name' and e['constraint'] == 'max_length' for e in errors)


class TestOptionsRequest:
    """Test CORS preflight handling."""

    @patch.object(app, 'producten_table')
    def test_options_returns_cors_headers(self, mock_table):
        """OPTIONS request returns CORS preflight response."""
        event = make_event(method='OPTIONS')
        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        mock_table.scan.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
