"""Test 13.8: event_participant user can only access allowed events."""
import boto3
import json
import base64

session = boto3.Session(profile_name='nonprofit-deploy', region_name='eu-west-1')
lambda_client = session.client('lambda')
dynamodb = session.resource('dynamodb', region_name='eu-west-1')
members_table = dynamodb.Table('Members-Test')

# Create an event_participant member with access to ONLY the rally event
members_table.put_item(Item={
    'member_id': 'test-participant-001',
    'email': 'participant@external-club.com',
    'member_type': 'event_participant',
    'allowed_events': ['test-event-rally-2027'],
    'status': 'active'
})
print("Created test event_participant member (rally access only)")
print()

# Build JWT for event_participant user
header = base64.urlsafe_b64encode(json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode()).decode().rstrip('=')
payload_data = {
    'sub': 'participant-sub-001',
    'cognito:groups': ['event_participant'],
    'email': 'participant@external-club.com',
    'token_use': 'access',
    'exp': 9999999999,
    'iat': 1781423528,
    'username': 'participant-sub-001'
}
payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip('=')
sig = base64.urlsafe_b64encode(b'fake').decode().rstrip('=')
TOKEN = f'{header}.{payload}.{sig}'

FN = 'h-dcn-test-GetOrderFunction-iXWvSJWlM7q6'


def invoke(source_id):
    event = json.dumps({
        'httpMethod': 'GET',
        'headers': {'Authorization': f'Bearer {TOKEN}'},
        'queryStringParameters': {'source_id': source_id},
        'pathParameters': None,
        'body': None,
        'requestContext': {}
    })
    resp = lambda_client.invoke(FunctionName=FN, Payload=event.encode())
    result = json.loads(resp['Payload'].read())
    status = result.get('statusCode', 0)
    body = json.loads(result.get('body', '{}'))
    return status, body


# Test 1: Allowed event (rally) - should succeed (201)
print("TEST 1: Access ALLOWED event (test-event-rally-2027)")
status, body = invoke('test-event-rally-2027')
passed1 = status == 201
icon = "✅" if passed1 else "❌"
print(f"  {icon} Status: {status} (expected 201)")
if passed1:
    print(f"     order_id: {body.get('order_id')}")
    print(f"     member_id: {body.get('member_id')}")
print()

# Test 2: NOT allowed event (presmeet) - should get 403
print("TEST 2: Access NOT ALLOWED event (test-event-presmeet-2027)")
status, body = invoke('test-event-presmeet-2027')
passed2 = status == 403
icon = "✅" if passed2 else "❌"
print(f"  {icon} Status: {status} (expected 403)")
print(f"     Error: {body.get('error', 'N/A')}")
print()

# Test 3: Webshop - should get 403 (no hdcnLeden group)
print("TEST 3: Access WEBSHOP (event_participant has no hdcnLeden)")
status, body = invoke('webshop')
passed3 = status == 403
icon = "✅" if passed3 else "❌"
print(f"  {icon} Status: {status} (expected 403)")
print(f"     Error: {body.get('error', 'N/A')}")
print()

# Summary
print("=" * 50)
all_passed = passed1 and passed2 and passed3
if all_passed:
    print("✅ ALL ACCESS RESTRICTION TESTS PASSED")
else:
    print("❌ SOME TESTS FAILED")
print("=" * 50)
