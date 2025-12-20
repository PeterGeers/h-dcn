# pytest configuration for H-DCN Dashboard backend tests

import pytest
import boto3
from moto import mock_dynamodb
import os

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
    with mock_dynamodb():
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