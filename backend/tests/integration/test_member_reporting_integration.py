"""
Integration Tests for Member Reporting System

Tests the complete member reporting flow including:
- Backend regional filtering logic
- Different user roles (regional users, Regio_All, CRUD users)
- Performance requirements
- Decimal conversion
- Error scenarios

Note: These tests focus on the business logic and data processing.
Full end-to-end tests with real JWT tokens should be done in a deployed environment.
"""

import pytest
import json
import time
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add handler directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../handler/get_members_filtered'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../shared'))

from app import filter_members_by_region, convert_dynamodb_to_python


@pytest.fixture
def dynamodb_table():
    """Create a mock DynamoDB table with test member data"""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        
        # Create table
        table = dynamodb.create_table(
            TableName='Members',
            KeySchema=[
                {'AttributeName': 'lidnummer', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'lidnummer', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add test members from different regions
        test_members = [
            # Utrecht members
            {
                'lidnummer': 'UT001',
                'voornaam': 'Jan',
                'achternaam': 'Jansen',
                'email': 'jan@utrecht.nl',
                'regio': 'Utrecht',
                'status': 'Actief',
                'geboortedatum': '1980-05-15',
                'tijdstempel': '2020-01-01',
                'leeftijd': Decimal('44'),  # Test Decimal handling
                'jaren_lid': Decimal('5')
            },
            {
                'lidnummer': 'UT002',
                'voornaam': 'Piet',
                'achternaam': 'Pietersen',
                'email': 'piet@utrecht.nl',
                'regio': 'Utrecht',
                'status': 'Inactief',
                'geboortedatum': '1975-08-20',
                'tijdstempel': '2018-06-15'
            },
            {
                'lidnummer': 'UT003',
                'voornaam': 'Klaas',
                'achternaam': 'Klaassen',
                'email': 'klaas@utrecht.nl',
                'regio': 'Utrecht',
                'status': 'Opgezegd',
                'geboortedatum': '1990-12-10',
                'tijdstempel': '2019-03-20'
            },
            # Zuid-Holland members
            {
                'lidnummer': 'ZH001',
                'voornaam': 'Anna',
                'achternaam': 'de Vries',
                'email': 'anna@zuidholland.nl',
                'regio': 'Zuid-Holland',
                'status': 'Actief',
                'geboortedatum': '1985-03-25',
                'tijdstempel': '2021-02-10'
            },
            {
                'lidnummer': 'ZH002',
                'voornaam': 'Bas',
                'achternaam': 'Bakker',
                'email': 'bas@zuidholland.nl',
                'regio': 'Zuid-Holland',
                'status': 'Actief',
                'geboortedatum': '1992-07-30',
                'tijdstempel': '2022-05-15'
            },
            # Noord-Holland members
            {
                'lidnummer': 'NH001',
                'voornaam': 'Emma',
                'achternaam': 'Smit',
                'email': 'emma@noordholland.nl',
                'regio': 'Noord-Holland',
                'status': 'Actief',
                'geboortedatum': '1988-11-05',
                'tijdstempel': '2020-09-01'
            },
            {
                'lidnummer': 'NH002',
                'voornaam': 'Daan',
                'achternaam': 'Visser',
                'email': 'daan@noordholland.nl',
                'regio': 'Noord-Holland',
                'status': 'Verwijderd',
                'geboortedatum': '1995-02-14',
                'tijdstempel': '2019-11-20'
            }
        ]
        
        # Insert members
        for member in test_members:
            table.put_item(Item=member)
        
        yield table


class TestCompleteUserFlow:
    """Test complete user flows for different user types"""
    
    def test_regional_user_flow_utrecht(self, dynamodb_table):
        """
        Test complete flow for a regional user (Utrecht)
        
        Flow: Load → Filter → Verify regional isolation
        """
        # Simulate JWT token for Utrecht regional user
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': 'Bearer mock_jwt_token',
                'X-Enhanced-Groups': 'Regio_Utrecht,members_read'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'email': 'regional.user@utrecht.nl',
                        'cognito:groups': 'Regio_Utrecht,members_read'
                    }
                }
            }
        }
        
        # Set environment variable for table name
        os.environ['MEMBERS_TABLE_NAME'] = 'Members'
        
        # Call handler
        start_time = time.time()
        response = lambda_handler(event, None)
        elapsed_time = time.time() - start_time
        
        # Verify response
        assert response['statusCode'] == 200
        
        body = json.loads(response['body'])
        assert body['success'] is True
        assert 'data' in body
        
        members = body['data']
        
        # Verify only Utrecht members are returned
        assert len(members) == 3  # UT001, UT002, UT003
        assert all(m['regio'] == 'Utrecht' for m in members)
        
        # Verify all statuses are included (no status filtering)
        statuses = {m['status'] for m in members}
        assert 'Actief' in statuses
        assert 'Inactief' in statuses
        assert 'Opgezegd' in statuses
        
        # Verify metadata
        assert body['metadata']['region'] == 'Utrecht'
        assert body['metadata']['total_count'] == 3
        
        # Verify performance requirement (<1 second)
        assert elapsed_time < 1.0, f"Load time {elapsed_time}s exceeds 1 second requirement"
        
        print(f"✓ Regional user (Utrecht) flow completed in {elapsed_time:.3f}s")
    
    def test_regional_user_flow_zuid_holland(self, dynamodb_table):
        """
        Test complete flow for a regional user (Zuid-Holland)
        """
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': 'Bearer mock_jwt_token',
                'X-Enhanced-Groups': 'Regio_Zuid-Holland,members_read'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'email': 'regional.user@zuidholland.nl',
                        'cognito:groups': 'Regio_Zuid-Holland,members_read'
                    }
                }
            }
        }
        
        os.environ['MEMBERS_TABLE_NAME'] = 'Members'
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        members = body['data']
        
        # Verify only Zuid-Holland members are returned
        assert len(members) == 2  # ZH001, ZH002
        assert all(m['regio'] == 'Zuid-Holland' for m in members)
        
        print(f"✓ Regional user (Zuid-Holland) flow completed")
    
    def test_regio_all_user_flow(self, dynamodb_table):
        """
        Test complete flow for a Regio_All user (sees all regions)
        
        Flow: Load → Verify all regions visible
        """
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': 'Bearer mock_jwt_token',
                'X-Enhanced-Groups': 'Regio_All,members_read'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'email': 'admin@hdcn.nl',
                        'cognito:groups': 'Regio_All,members_read'
                    }
                }
            }
        }
        
        os.environ['MEMBERS_TABLE_NAME'] = 'Members'
        
        start_time = time.time()
        response = lambda_handler(event, None)
        elapsed_time = time.time() - start_time
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        members = body['data']
        
        # Verify all members from all regions are returned
        assert len(members) == 7  # All test members
        
        regions = {m['regio'] for m in members}
        assert 'Utrecht' in regions
        assert 'Zuid-Holland' in regions
        assert 'Noord-Holland' in regions
        
        # Verify metadata
        assert body['metadata']['region'] == 'All'
        assert body['metadata']['total_count'] == 7
        
        # Verify performance requirement (<2 seconds for Regio_All)
        assert elapsed_time < 2.0, f"Load time {elapsed_time}s exceeds 2 second requirement"
        
        print(f"✓ Regio_All user flow completed in {elapsed_time:.3f}s")
    
    def test_crud_user_permissions(self, dynamodb_table):
        """
        Test that CRUD users can access the API
        """
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': 'Bearer mock_jwt_token',
                'X-Enhanced-Groups': 'Regio_Utrecht,members_update,members_create'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'email': 'crud.user@utrecht.nl',
                        'cognito:groups': 'Regio_Utrecht,members_update,members_create'
                    }
                }
            }
        }
        
        os.environ['MEMBERS_TABLE_NAME'] = 'Members'
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        
        # CRUD users should get their regional data
        members = body['data']
        assert len(members) == 3  # Utrecht members
        assert all(m['regio'] == 'Utrecht' for m in members)
        
        print(f"✓ CRUD user permissions verified")


class TestPerformance:
    """Test performance requirements"""
    
    def test_regional_user_load_time(self, dynamodb_table):
        """
        Test that regional users get data within 1 second
        Requirement: Regional user load time <1 second
        """
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': 'Bearer mock_jwt_token',
                'X-Enhanced-Groups': 'Regio_Utrecht,members_read'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'email': 'test@utrecht.nl',
                        'cognito:groups': 'Regio_Utrecht,members_read'
                    }
                }
            }
        }
        
        os.environ['MEMBERS_TABLE_NAME'] = 'Members'
        
        # Measure multiple runs
        times = []
        for _ in range(5):
            start_time = time.time()
            response = lambda_handler(event, None)
            elapsed_time = time.time() - start_time
            times.append(elapsed_time)
            
            assert response['statusCode'] == 200
        
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        # Verify performance requirements
        assert avg_time < 1.0, f"Average load time {avg_time:.3f}s exceeds 1 second"
        assert max_time < 1.5, f"Max load time {max_time:.3f}s exceeds acceptable threshold"
        
        print(f"✓ Performance test passed: avg={avg_time:.3f}s, max={max_time:.3f}s")
    
    def test_decimal_conversion_performance(self):
        """
        Test that Decimal conversion doesn't impact performance
        """
        # Create test data with many Decimal fields
        test_data = {
            'lidnummer': '12345',
            'leeftijd': Decimal('45'),
            'jaren_lid': Decimal('10'),
            'contributie': Decimal('125.50'),
            'nested': {
                'value1': Decimal('100'),
                'value2': Decimal('200.75')
            },
            'list_field': [
                {'amount': Decimal('50')},
                {'amount': Decimal('75.25')}
            ]
        }
        
        start_time = time.time()
        for _ in range(1000):
            result = convert_dynamodb_to_python(test_data)
        elapsed_time = time.time() - start_time
        
        # Should process 1000 conversions in under 100ms
        assert elapsed_time < 0.1, f"Decimal conversion too slow: {elapsed_time:.3f}s for 1000 iterations"
        
        # Verify conversion correctness
        assert isinstance(result['leeftijd'], int)
        assert isinstance(result['contributie'], float)
        assert result['contributie'] == 125.50
        
        print(f"✓ Decimal conversion performance: {elapsed_time*1000:.1f}ms for 1000 iterations")


class TestErrorScenarios:
    """Test error handling and edge cases"""
    
    def test_missing_jwt_token(self, dynamodb_table):
        """
        Test that requests without JWT token are rejected
        """
        event = {
            'httpMethod': 'GET',
            'headers': {}  # No Authorization header
        }
        
        os.environ['MEMBERS_TABLE_NAME'] = 'Members'
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'Authentication' in body['error'] or 'Unauthorized' in body['error']
        
        print(f"✓ Missing JWT token correctly rejected")
    
    def test_invalid_permissions(self, dynamodb_table):
        """
        Test that users without member permissions are rejected
        """
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': 'Bearer mock_jwt_token',
                'X-Enhanced-Groups': 'some_other_permission'  # No member permissions
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'email': 'user@example.com',
                        'cognito:groups': 'some_other_permission'
                    }
                }
            }
        }
        
        os.environ['MEMBERS_TABLE_NAME'] = 'Members'
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'permission' in body['error'].lower() or 'access denied' in body['error'].lower()
        
        print(f"✓ Invalid permissions correctly rejected")
    
    def test_empty_database(self):
        """
        Test behavior when database is empty
        """
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            
            # Create empty table
            table = dynamodb.create_table(
                TableName='Members',
                KeySchema=[
                    {'AttributeName': 'lidnummer', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'lidnummer', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            
            event = {
                'httpMethod': 'GET',
                'headers': {
                    'Authorization': 'Bearer mock_jwt_token',
                    'X-Enhanced-Groups': 'Regio_All,members_read'
                },
                'requestContext': {
                    'authorizer': {
                        'claims': {
                            'email': 'admin@hdcn.nl',
                            'cognito:groups': 'Regio_All,members_read'
                        }
                    }
                }
            }
            
            os.environ['MEMBERS_TABLE_NAME'] = 'Members'
            
            response = lambda_handler(event, None)
            
            assert response['statusCode'] == 200
            body = json.loads(response['body'])
            assert body['success'] is True
            assert body['data'] == []
            assert body['metadata']['total_count'] == 0
            
            print(f"✓ Empty database handled correctly")
    
    def test_malformed_member_data(self, dynamodb_table):
        """
        Test handling of members with missing or malformed fields
        """
        # Add member with missing fields
        dynamodb_table.put_item(Item={
            'lidnummer': 'BAD001',
            'voornaam': 'Test',
            # Missing achternaam, email, regio, status
        })
        
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': 'Bearer mock_jwt_token',
                'X-Enhanced-Groups': 'Regio_All,members_read'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'email': 'admin@hdcn.nl',
                        'cognito:groups': 'Regio_All,members_read'
                    }
                }
            }
        }
        
        os.environ['MEMBERS_TABLE_NAME'] = 'Members'
        
        # Should not crash, should return all valid members
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert len(body['data']) >= 7  # At least the original test members
        
        print(f"✓ Malformed member data handled gracefully")


class TestRegionalIsolation:
    """Test that regional filtering properly isolates data"""
    
    def test_regional_user_cannot_see_other_regions(self, dynamodb_table):
        """
        Test that Utrecht users cannot see Zuid-Holland members
        """
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': 'Bearer mock_jwt_token',
                'X-Enhanced-Groups': 'Regio_Utrecht,members_read'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'email': 'user@utrecht.nl',
                        'cognito:groups': 'Regio_Utrecht,members_read'
                    }
                }
            }
        }
        
        os.environ['MEMBERS_TABLE_NAME'] = 'Members'
        
        response = lambda_handler(event, None)
        body = json.loads(response['body'])
        
        members = body['data']
        member_ids = {m['lidnummer'] for m in members}
        
        # Verify Utrecht members are present
        assert 'UT001' in member_ids
        assert 'UT002' in member_ids
        assert 'UT003' in member_ids
        
        # Verify other regions are NOT present
        assert 'ZH001' not in member_ids
        assert 'ZH002' not in member_ids
        assert 'NH001' not in member_ids
        assert 'NH002' not in member_ids
        
        print(f"✓ Regional isolation verified: Utrecht user cannot see other regions")
    
    def test_all_statuses_included_for_regional_users(self, dynamodb_table):
        """
        Test that regional users see ALL statuses (no status filtering)
        This is a key requirement - backend only filters by region, not status
        """
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': 'Bearer mock_jwt_token',
                'X-Enhanced-Groups': 'Regio_Utrecht,members_read'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'email': 'user@utrecht.nl',
                        'cognito:groups': 'Regio_Utrecht,members_read'
                    }
                }
            }
        }
        
        os.environ['MEMBERS_TABLE_NAME'] = 'Members'
        
        response = lambda_handler(event, None)
        body = json.loads(response['body'])
        
        members = body['data']
        statuses = {m['status'] for m in members}
        
        # Verify all statuses are present (Actief, Inactief, Opgezegd)
        assert 'Actief' in statuses
        assert 'Inactief' in statuses
        assert 'Opgezegd' in statuses
        
        # Verify count matches all Utrecht members regardless of status
        assert len(members) == 3
        
        print(f"✓ All statuses included for regional users (no status filtering)")


class TestDecimalConversion:
    """Test DynamoDB Decimal conversion"""
    
    def test_decimal_to_int_conversion(self):
        """Test that whole number Decimals convert to int"""
        data = {
            'age': Decimal('45'),
            'years': Decimal('10'),
            'count': Decimal('0')
        }
        
        result = convert_dynamodb_to_python(data)
        
        assert isinstance(result['age'], int)
        assert result['age'] == 45
        assert isinstance(result['years'], int)
        assert result['years'] == 10
        assert isinstance(result['count'], int)
        assert result['count'] == 0
    
    def test_decimal_to_float_conversion(self):
        """Test that decimal Decimals convert to float"""
        data = {
            'price': Decimal('125.50'),
            'percentage': Decimal('33.33'),
            'small': Decimal('0.01')
        }
        
        result = convert_dynamodb_to_python(data)
        
        assert isinstance(result['price'], float)
        assert result['price'] == 125.50
        assert isinstance(result['percentage'], float)
        assert abs(result['percentage'] - 33.33) < 0.01
        assert isinstance(result['small'], float)
        assert result['small'] == 0.01
    
    def test_nested_decimal_conversion(self):
        """Test that nested Decimals are converted"""
        data = {
            'member': {
                'age': Decimal('45'),
                'contribution': Decimal('125.50')
            },
            'stats': {
                'total': Decimal('1000'),
                'average': Decimal('33.33')
            }
        }
        
        result = convert_dynamodb_to_python(data)
        
        assert isinstance(result['member']['age'], int)
        assert isinstance(result['member']['contribution'], float)
        assert isinstance(result['stats']['total'], int)
        assert isinstance(result['stats']['average'], float)
    
    def test_list_decimal_conversion(self):
        """Test that Decimals in lists are converted"""
        data = {
            'payments': [
                {'amount': Decimal('100')},
                {'amount': Decimal('125.50')}
            ]
        }
        
        result = convert_dynamodb_to_python(data)
        
        assert isinstance(result['payments'][0]['amount'], int)
        assert result['payments'][0]['amount'] == 100
        assert isinstance(result['payments'][1]['amount'], float)
        assert result['payments'][1]['amount'] == 125.50
    
    def test_json_serialization_after_conversion(self, dynamodb_table):
        """
        Test that converted data can be JSON serialized
        This is the critical test - ensures no Decimal objects leak through
        """
        event = {
            'httpMethod': 'GET',
            'headers': {
                'Authorization': 'Bearer mock_jwt_token',
                'X-Enhanced-Groups': 'Regio_Utrecht,members_read'
            },
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'email': 'user@utrecht.nl',
                        'cognito:groups': 'Regio_Utrecht,members_read'
                    }
                }
            }
        }
        
        os.environ['MEMBERS_TABLE_NAME'] = 'Members'
        
        response = lambda_handler(event, None)
        
        # If this doesn't raise an exception, JSON serialization worked
        body = json.loads(response['body'])
        
        # Verify we can re-serialize the data
        json_str = json.dumps(body)
        assert len(json_str) > 0
        
        # Verify no Decimal objects in the response
        assert 'Decimal' not in json_str
        
        print(f"✓ JSON serialization successful after Decimal conversion")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
