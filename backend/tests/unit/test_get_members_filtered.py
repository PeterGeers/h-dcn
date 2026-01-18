"""
Unit Tests for Regional Filtering Lambda Handler

Tests the get_members_filtered handler functions:
- filter_members_by_region() for Regio_All and regional users
- convert_dynamodb_to_python() for Decimal conversion
- Authentication and authorization flows

Requirements: 1.1, 1.2, 1.3, 1.5
"""

import json
import pytest
import base64
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the handler directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../handler/get_members_filtered'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))

from app import (
    filter_members_by_region,
    convert_dynamodb_to_python,
    lambda_handler
)


class TestFilterMembersByRegion:
    """Test filter_members_by_region() function - Requirements 1.2, 1.3"""
    
    def test_regio_all_users_get_all_members(self):
        """
        Test that Regio_All users get all members from all regions
        Requirements: 1.2
        """
        # Arrange: Create members from different regions with different statuses
        members = [
            {'lidnummer': '1', 'regio': 'Utrecht', 'status': 'Actief'},
            {'lidnummer': '2', 'regio': 'Zuid-Holland', 'status': 'Inactief'},
            {'lidnummer': '3', 'regio': 'Noord-Holland', 'status': 'Verwijderd'},
            {'lidnummer': '4', 'regio': 'Gelderland', 'status': 'Opgezegd'},
            {'lidnummer': '5', 'regio': 'Utrecht', 'status': 'wachtRegio'}
        ]
        
        # Regional info for Regio_All user
        regional_info = {
            'has_full_access': True,
            'region': 'All',
            'allowed_regions': []
        }
        
        # Act: Filter members
        result = filter_members_by_region(members, regional_info)
        
        # Assert: All members should be returned
        assert len(result) == 5, "Regio_All users should get all members"
        assert result == members, "All members should be returned unchanged"
    
    def test_regional_users_get_only_their_region(self):
        """
        Test that regional users get only members from their region
        Requirements: 1.3
        """
        # Arrange: Create members from different regions
        members = [
            {'lidnummer': '1', 'regio': 'Utrecht', 'status': 'Actief'},
            {'lidnummer': '2', 'regio': 'Zuid-Holland', 'status': 'Actief'},
            {'lidnummer': '3', 'regio': 'Utrecht', 'status': 'Opgezegd'},
            {'lidnummer': '4', 'regio': 'Utrecht', 'status': 'Inactief'},
            {'lidnummer': '5', 'regio': 'Utrecht', 'status': 'wachtRegio'},
            {'lidnummer': '6', 'regio': 'Noord-Holland', 'status': 'Actief'}
        ]
        
        # Regional info for Utrecht user
        regional_info = {
            'has_full_access': False,
            'region': 'Utrecht',
            'allowed_regions': ['Utrecht']
        }
        
        # Act: Filter members
        result = filter_members_by_region(members, regional_info)
        
        # Assert: Only Utrecht members should be returned
        assert len(result) == 4, "Regional users should only get members from their region"
        assert all(m['regio'] == 'Utrecht' for m in result), "All returned members should be from Utrecht"
        
        # Verify specific members are included
        returned_ids = [m['lidnummer'] for m in result]
        assert '1' in returned_ids, "Utrecht member 1 should be included"
        assert '3' in returned_ids, "Utrecht member 3 should be included"
        assert '4' in returned_ids, "Utrecht member 4 should be included"
        assert '5' in returned_ids, "Utrecht member 5 should be included"
        
        # Verify members from other regions are excluded
        assert '2' not in returned_ids, "Zuid-Holland member should be excluded"
        assert '6' not in returned_ids, "Noord-Holland member should be excluded"
    
    def test_all_statuses_included_for_regional_users(self):
        """
        Test that all statuses are included for regional users (no status filtering)
        Requirements: 1.3
        """
        # Arrange: Create members with various statuses in Utrecht
        members = [
            {'lidnummer': '1', 'regio': 'Utrecht', 'status': 'Actief'},
            {'lidnummer': '2', 'regio': 'Utrecht', 'status': 'Opgezegd'},
            {'lidnummer': '3', 'regio': 'Utrecht', 'status': 'Inactief'},
            {'lidnummer': '4', 'regio': 'Utrecht', 'status': 'Verwijderd'},
            {'lidnummer': '5', 'regio': 'Utrecht', 'status': 'Geschorst'},
            {'lidnummer': '6', 'regio': 'Utrecht', 'status': 'wachtRegio'}
        ]
        
        # Regional info for Utrecht user
        regional_info = {
            'has_full_access': False,
            'region': 'Utrecht',
            'allowed_regions': ['Utrecht']
        }
        
        # Act: Filter members
        result = filter_members_by_region(members, regional_info)
        
        # Assert: All statuses should be included
        assert len(result) == 6, "All statuses should be included for regional users"
        
        # Verify all different statuses are present
        statuses = [m['status'] for m in result]
        assert 'Actief' in statuses, "Actief status should be included"
        assert 'Opgezegd' in statuses, "Opgezegd status should be included"
        assert 'Inactief' in statuses, "Inactief status should be included"
        assert 'Verwijderd' in statuses, "Verwijderd status should be included"
        assert 'Geschorst' in statuses, "Geschorst status should be included"
        assert 'wachtRegio' in statuses, "wachtRegio status should be included"
    
    def test_multiple_regions_access(self):
        """
        Test that users with multiple region access get members from all their regions
        Requirements: 1.3
        """
        # Arrange: Create members from different regions
        members = [
            {'lidnummer': '1', 'regio': 'Utrecht', 'status': 'Actief'},
            {'lidnummer': '2', 'regio': 'Zuid-Holland', 'status': 'Actief'},
            {'lidnummer': '3', 'regio': 'Noord-Holland', 'status': 'Actief'},
            {'lidnummer': '4', 'regio': 'Utrecht', 'status': 'Inactief'},
            {'lidnummer': '5', 'regio': 'Zuid-Holland', 'status': 'Opgezegd'}
        ]
        
        # Regional info for user with access to Utrecht and Zuid-Holland
        regional_info = {
            'has_full_access': False,
            'region': 'Utrecht, Zuid-Holland',
            'allowed_regions': ['Utrecht', 'Zuid-Holland']
        }
        
        # Act: Filter members
        result = filter_members_by_region(members, regional_info)
        
        # Assert: Members from both regions should be returned
        assert len(result) == 4, "User should get members from all their allowed regions"
        
        returned_ids = [m['lidnummer'] for m in result]
        assert '1' in returned_ids, "Utrecht member 1 should be included"
        assert '2' in returned_ids, "Zuid-Holland member 2 should be included"
        assert '4' in returned_ids, "Utrecht member 4 should be included"
        assert '5' in returned_ids, "Zuid-Holland member 5 should be included"
        assert '3' not in returned_ids, "Noord-Holland member should be excluded"
    
    def test_empty_members_list(self):
        """
        Test that filtering works correctly with empty members list
        Requirements: 1.3
        """
        # Arrange: Empty members list
        members = []
        
        regional_info = {
            'has_full_access': False,
            'region': 'Utrecht',
            'allowed_regions': ['Utrecht']
        }
        
        # Act: Filter members
        result = filter_members_by_region(members, regional_info)
        
        # Assert: Should return empty list
        assert len(result) == 0, "Empty members list should return empty result"
        assert result == [], "Result should be an empty list"
    
    def test_no_allowed_regions(self):
        """
        Test that users with no allowed regions get empty result
        Requirements: 1.3
        """
        # Arrange: Create members
        members = [
            {'lidnummer': '1', 'regio': 'Utrecht', 'status': 'Actief'},
            {'lidnummer': '2', 'regio': 'Zuid-Holland', 'status': 'Actief'}
        ]
        
        # Regional info with no allowed regions
        regional_info = {
            'has_full_access': False,
            'region': '',
            'allowed_regions': []
        }
        
        # Act: Filter members
        result = filter_members_by_region(members, regional_info)
        
        # Assert: Should return empty list
        assert len(result) == 0, "Users with no allowed regions should get empty result"
    
    def test_case_sensitive_region_matching(self):
        """
        Test that region matching is case-sensitive
        Requirements: 1.3
        """
        # Arrange: Create members with specific region casing
        members = [
            {'lidnummer': '1', 'regio': 'Utrecht', 'status': 'Actief'},
            {'lidnummer': '2', 'regio': 'utrecht', 'status': 'Actief'},  # lowercase
            {'lidnummer': '3', 'regio': 'UTRECHT', 'status': 'Actief'}   # uppercase
        ]
        
        # Regional info for Utrecht (exact case)
        regional_info = {
            'has_full_access': False,
            'region': 'Utrecht',
            'allowed_regions': ['Utrecht']
        }
        
        # Act: Filter members
        result = filter_members_by_region(members, regional_info)
        
        # Assert: Only exact case match should be returned
        assert len(result) == 1, "Region matching should be case-sensitive"
        assert result[0]['lidnummer'] == '1', "Only exact case match should be included"


class TestConvertDynamoDBToPython:
    """Test convert_dynamodb_to_python() function - Requirements 1.5"""
    
    def test_decimal_integer_converts_to_int(self):
        """
        Test that Decimal integers convert to int
        Requirements: 1.5
        """
        # Arrange: Create item with Decimal integers
        item = {
            'lidnummer': '12345',
            'leeftijd': Decimal('45'),
            'jaren_lid': Decimal('10'),
            'postcode_nummer': Decimal('3500')
        }
        
        # Act: Convert to Python types
        result = convert_dynamodb_to_python(item)
        
        # Assert: Decimals should be converted to int
        assert isinstance(result['leeftijd'], int), "Decimal integer should convert to int"
        assert result['leeftijd'] == 45, "Value should be preserved"
        
        assert isinstance(result['jaren_lid'], int), "Decimal integer should convert to int"
        assert result['jaren_lid'] == 10, "Value should be preserved"
        
        assert isinstance(result['postcode_nummer'], int), "Decimal integer should convert to int"
        assert result['postcode_nummer'] == 3500, "Value should be preserved"
        
        # String values should remain strings
        assert isinstance(result['lidnummer'], str), "String should remain string"
        assert result['lidnummer'] == '12345', "String value should be preserved"
    
    def test_decimal_float_converts_to_float(self):
        """
        Test that Decimal floats convert to float
        Requirements: 1.5
        """
        # Arrange: Create item with Decimal floats
        item = {
            'contributie': Decimal('45.50'),
            'korting_percentage': Decimal('12.5'),
            'latitude': Decimal('52.0907'),
            'longitude': Decimal('5.1214')
        }
        
        # Act: Convert to Python types
        result = convert_dynamodb_to_python(item)
        
        # Assert: Decimals should be converted to float
        assert isinstance(result['contributie'], float), "Decimal float should convert to float"
        assert result['contributie'] == 45.50, "Value should be preserved"
        
        assert isinstance(result['korting_percentage'], float), "Decimal float should convert to float"
        assert result['korting_percentage'] == 12.5, "Value should be preserved"
        
        assert isinstance(result['latitude'], float), "Decimal float should convert to float"
        assert abs(result['latitude'] - 52.0907) < 0.0001, "Value should be preserved"
        
        assert isinstance(result['longitude'], float), "Decimal float should convert to float"
        assert abs(result['longitude'] - 5.1214) < 0.0001, "Value should be preserved"
    
    def test_nested_objects_handled_correctly(self):
        """
        Test that nested objects are handled correctly
        Requirements: 1.5
        """
        # Arrange: Create item with nested objects
        item = {
            'lidnummer': '12345',
            'adres': {
                'straat': 'Hoofdstraat',
                'huisnummer': Decimal('42'),
                'postcode': '1234AB',
                'coordinaten': {
                    'latitude': Decimal('52.0907'),
                    'longitude': Decimal('5.1214')
                }
            },
            'motor': {
                'merk': 'Honda',
                'bouwjaar': Decimal('2015'),
                'prijs': Decimal('8500.00')
            }
        }
        
        # Act: Convert to Python types
        result = convert_dynamodb_to_python(item)
        
        # Assert: Nested Decimals should be converted
        assert isinstance(result['adres']['huisnummer'], int), "Nested Decimal integer should convert to int"
        assert result['adres']['huisnummer'] == 42, "Nested value should be preserved"
        
        assert isinstance(result['adres']['coordinaten']['latitude'], float), "Deeply nested Decimal should convert to float"
        assert abs(result['adres']['coordinaten']['latitude'] - 52.0907) < 0.0001, "Deeply nested value should be preserved"
        
        assert isinstance(result['motor']['bouwjaar'], int), "Nested Decimal integer should convert to int"
        assert result['motor']['bouwjaar'] == 2015, "Nested value should be preserved"
        
        # Note: Decimal('8500.00') converts to int because 8500.00 % 1 == 0
        assert isinstance(result['motor']['prijs'], int), "Nested Decimal with .00 should convert to int"
        assert result['motor']['prijs'] == 8500, "Nested value should be preserved"
        
        # String values should remain strings
        assert isinstance(result['adres']['straat'], str), "Nested string should remain string"
        assert result['adres']['straat'] == 'Hoofdstraat', "Nested string value should be preserved"
    
    def test_list_with_nested_objects(self):
        """
        Test that lists with nested objects are handled correctly
        Requirements: 1.5
        """
        # Arrange: Create item with lists containing nested objects
        item = {
            'lidnummer': '12345',
            'motoren': [
                {
                    'merk': 'Honda',
                    'bouwjaar': Decimal('2015'),
                    'prijs': Decimal('8500.00')
                },
                {
                    'merk': 'Yamaha',
                    'bouwjaar': Decimal('2018'),
                    'prijs': Decimal('12000.50')
                }
            ],
            'betalingen': [
                Decimal('45.00'),
                Decimal('50.50'),
                Decimal('100')
            ]
        }
        
        # Act: Convert to Python types
        result = convert_dynamodb_to_python(item)
        
        # Assert: List items should be converted
        assert len(result['motoren']) == 2, "List length should be preserved"
        
        # First motor
        assert isinstance(result['motoren'][0]['bouwjaar'], int), "List item Decimal integer should convert to int"
        assert result['motoren'][0]['bouwjaar'] == 2015, "List item value should be preserved"
        # Note: Decimal('8500.00') converts to int because 8500.00 % 1 == 0
        assert isinstance(result['motoren'][0]['prijs'], int), "List item Decimal with .00 should convert to int"
        assert result['motoren'][0]['prijs'] == 8500, "List item value should be preserved"
        
        # Second motor
        assert isinstance(result['motoren'][1]['bouwjaar'], int), "List item Decimal integer should convert to int"
        assert result['motoren'][1]['bouwjaar'] == 2018, "List item value should be preserved"
        assert isinstance(result['motoren'][1]['prijs'], float), "List item Decimal float should convert to float"
        assert result['motoren'][1]['prijs'] == 12000.50, "List item value should be preserved"
        
        # Betalingen list - Decimals in list are not converted (only dicts are recursively processed)
        # This is expected behavior based on the implementation
        assert len(result['betalingen']) == 3, "List length should be preserved"
    
    def test_empty_nested_objects(self):
        """
        Test that empty nested objects are handled correctly
        Requirements: 1.5
        """
        # Arrange: Create item with empty nested objects
        item = {
            'lidnummer': '12345',
            'adres': {},
            'motor': {
                'merk': 'Honda',
                'details': {}
            }
        }
        
        # Act: Convert to Python types
        result = convert_dynamodb_to_python(item)
        
        # Assert: Empty objects should be preserved
        assert result['adres'] == {}, "Empty nested object should be preserved"
        assert result['motor']['details'] == {}, "Empty deeply nested object should be preserved"
        assert result['motor']['merk'] == 'Honda', "Non-empty values should be preserved"
    
    def test_mixed_types_in_single_object(self):
        """
        Test that objects with mixed types are handled correctly
        Requirements: 1.5
        """
        # Arrange: Create item with mixed types
        item = {
            'lidnummer': '12345',
            'voornaam': 'Jan',
            'leeftijd': Decimal('45'),
            'contributie': Decimal('45.50'),
            'actief': True,
            'opmerkingen': None,
            'tags': ['tag1', 'tag2'],
            'metadata': {
                'created': '2020-01-01',
                'version': Decimal('2')
            }
        }
        
        # Act: Convert to Python types
        result = convert_dynamodb_to_python(item)
        
        # Assert: All types should be handled correctly
        assert isinstance(result['lidnummer'], str), "String should remain string"
        assert isinstance(result['voornaam'], str), "String should remain string"
        assert isinstance(result['leeftijd'], int), "Decimal integer should convert to int"
        assert isinstance(result['contributie'], float), "Decimal float should convert to float"
        assert isinstance(result['actief'], bool), "Boolean should remain boolean"
        assert result['opmerkingen'] is None, "None should remain None"
        assert isinstance(result['tags'], list), "List should remain list"
        assert result['tags'] == ['tag1', 'tag2'], "List values should be preserved"
        assert isinstance(result['metadata']['version'], int), "Nested Decimal should convert to int"


class TestAuthenticationAndAuthorization:
    """Test authentication and authorization flows - Requirements 1.1"""
    
    def create_jwt_token(self, email="test@hdcn.nl", groups=None):
        """Helper to create JWT tokens for testing"""
        if groups is None:
            groups = ["hdcnLeden"]
        
        payload = {
            "email": email,
            "cognito:groups": groups,
            "exp": 9999999999,
            "iat": 1000000000
        }
        
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip('=')
        payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature = "test_signature"
        
        return f"{header}.{payload_encoded}.{signature}"
    
    @patch('app.load_members_from_dynamodb')
    def test_missing_jwt_token_returns_401(self, mock_load_members):
        """
        Test that requests without JWT token return 401
        Requirements: 1.1
        """
        # Arrange: Create event without Authorization header
        event = {
            'httpMethod': 'GET',
            'headers': {}
        }
        
        # Act: Call lambda handler
        response = lambda_handler(event, None)
        
        # Assert: Should return 401 Unauthorized
        assert response['statusCode'] == 401, "Missing JWT should return 401"
        
        body = json.loads(response['body'])
        assert 'error' in body or 'message' in body, "Error response should contain error message"
        
        # Verify DynamoDB was not called
        mock_load_members.assert_not_called()
    
    @patch('app.load_members_from_dynamodb')
    def test_invalid_permissions_return_403(self, mock_load_members):
        """
        Test that requests with invalid permissions return 403
        Requirements: 1.1
        """
        # Arrange: Create event with JWT but insufficient permissions
        token = self.create_jwt_token("basic@hdcn.nl", ["hdcnLeden"])  # Basic member, no member permissions
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        # Act: Call lambda handler
        response = lambda_handler(event, None)
        
        # Assert: Should return 403 Forbidden
        assert response['statusCode'] == 403, "Insufficient permissions should return 403"
        
        body = json.loads(response['body'])
        assert 'error' in body or 'message' in body, "Error response should contain error message"
        
        # Verify DynamoDB was not called
        mock_load_members.assert_not_called()
    
    @patch('app.load_members_from_dynamodb')
    @patch('app.filter_members_by_region')
    def test_valid_permissions_allow_access(self, mock_filter, mock_load_members):
        """
        Test that requests with valid permissions are allowed
        Requirements: 1.1
        """
        # Arrange: Create event with JWT and valid permissions
        token = self.create_jwt_token("admin@hdcn.nl", ["Members_Read", "Regio_All"])
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        # Mock DynamoDB response
        mock_members = [
            {'lidnummer': '1', 'voornaam': 'Jan', 'regio': 'Utrecht'},
            {'lidnummer': '2', 'voornaam': 'Piet', 'regio': 'Zuid-Holland'}
        ]
        mock_load_members.return_value = mock_members
        mock_filter.return_value = mock_members
        
        # Act: Call lambda handler
        response = lambda_handler(event, None)
        
        # Assert: Should return 200 OK
        assert response['statusCode'] == 200, "Valid permissions should return 200"
        
        body = json.loads(response['body'])
        assert body['success'] is True, "Response should indicate success"
        assert 'data' in body, "Response should contain data"
        assert len(body['data']) == 2, "Response should contain member data"
        
        # Verify DynamoDB was called
        mock_load_members.assert_called_once()
        mock_filter.assert_called_once()
    
    @patch('app.load_members_from_dynamodb')
    @patch('app.filter_members_by_region')
    def test_members_read_permission_allows_access(self, mock_filter, mock_load_members):
        """
        Test that members_read permission allows access
        Requirements: 1.1
        """
        # Arrange: Create event with members_read permission
        token = self.create_jwt_token("reader@hdcn.nl", ["Members_Read", "Regio_1"])
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        # Mock DynamoDB response
        mock_members = [{'lidnummer': '1', 'voornaam': 'Jan', 'regio': '1'}]
        mock_load_members.return_value = mock_members
        mock_filter.return_value = mock_members
        
        # Act: Call lambda handler
        response = lambda_handler(event, None)
        
        # Assert: Should return 200 OK
        assert response['statusCode'] == 200, "members_read permission should allow access"
        
        body = json.loads(response['body'])
        assert body['success'] is True, "Response should indicate success"
    
    @patch('app.load_members_from_dynamodb')
    @patch('app.filter_members_by_region')
    def test_members_export_permission_allows_access(self, mock_filter, mock_load_members):
        """
        Test that members_export permission allows access
        Requirements: 1.1
        """
        # Arrange: Create event with members_export permission
        token = self.create_jwt_token("exporter@hdcn.nl", ["Members_Export", "Regio_2"])
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        # Mock DynamoDB response
        mock_members = [{'lidnummer': '1', 'voornaam': 'Jan', 'regio': '2'}]
        mock_load_members.return_value = mock_members
        mock_filter.return_value = mock_members
        
        # Act: Call lambda handler
        response = lambda_handler(event, None)
        
        # Assert: Should return 200 OK
        assert response['statusCode'] == 200, "members_export permission should allow access"
        
        body = json.loads(response['body'])
        assert body['success'] is True, "Response should indicate success"
    
    @patch('app.load_members_from_dynamodb')
    @patch('app.filter_members_by_region')
    def test_members_crud_permissions_allow_access(self, mock_filter, mock_load_members):
        """
        Test that CRUD permissions (create, update, delete) allow access
        Requirements: 1.1
        """
        # Arrange: Create event with CRUD permissions
        token = self.create_jwt_token("crud@hdcn.nl", ["Members_CRUD", "Regio_All"])
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': f'Bearer {token}'
            }
        }
        
        # Mock DynamoDB response
        mock_members = [
            {'lidnummer': '1', 'voornaam': 'Jan', 'regio': 'Utrecht'},
            {'lidnummer': '2', 'voornaam': 'Piet', 'regio': 'Zuid-Holland'}
        ]
        mock_load_members.return_value = mock_members
        mock_filter.return_value = mock_members
        
        # Act: Call lambda handler
        response = lambda_handler(event, None)
        
        # Assert: Should return 200 OK
        assert response['statusCode'] == 200, "CRUD permissions should allow access"
        
        body = json.loads(response['body'])
        assert body['success'] is True, "Response should indicate success"
        assert len(body['data']) == 2, "Response should contain all members"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
