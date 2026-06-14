"""Quick integration test of the new event booking API endpoints on h-dcn-test."""
import boto3
import json
import base64

session = boto3.Session(profile_name='nonprofit-deploy', region_name='eu-west-1')
lambda_client = session.client('lambda')

# Build a fake JWT token with test admin claims
header = base64.urlsafe_b64encode(json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode()).decode().rstrip('=')
payload_data = {
    'sub': 'f2b57414-4041-7058-fbc0-4f02ba61868c',
    'cognito:groups': ['hdcnLeden', 'Events_CRUD', 'System_CRUD', 'Members_CRUD'],
    'email': 'webmaster+testadmin@h-dcn.nl',
    'token_use': 'access',
    'exp': 9999999999,
    'iat': 1781423528,
    'username': 'f2b57414-4041-7058-fbc0-4f02ba61868c'
}
payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip('=')
sig = base64.urlsafe_b64encode(b'fake').decode().rstrip('=')
TOKEN = f'{header}.{payload}.{sig}'


def invoke(function_name, method='GET', query_params=None, path_params=None, body=None):
    event = json.dumps({
        'httpMethod': method,
        'headers': {'Authorization': f'Bearer {TOKEN}'},
        'queryStringParameters': query_params,
        'pathParameters': path_params,
        'body': json.dumps(body) if body else None,
        'requestContext': {}
    })
    resp = lambda_client.invoke(FunctionName=function_name, Payload=event.encode())
    result = json.loads(resp['Payload'].read())
    return result['statusCode'], json.loads(result.get('body', '{}'))


# --- Test 1: Webshop order ---
print("=" * 60)
print("TEST 1: GET /booking?source_id=webshop")
print("=" * 60)
status, body = invoke('h-dcn-test-GetOrderFunction-iXWvSJWlM7q6', query_params={'source_id': 'webshop'})
print(f"  Status: {status}")
print(f"  source_id: {body.get('source_id')}")
print(f"  member_id: {body.get('member_id')}")
print(f"  order_id: {body.get('order_id')}")
print(f"  status: {body.get('status')}")
print()

# --- Test 2: Get existing rally order (should return 200 now, not 201) ---
print("=" * 60)
print("TEST 2: GET /booking?source_id=test-event-rally-2027 (existing)")
print("=" * 60)
status, body = invoke('h-dcn-test-GetOrderFunction-iXWvSJWlM7q6', query_params={'source_id': 'test-event-rally-2027'})
print(f"  Status: {status}")
print(f"  order_id: {body.get('order_id')}")
print(f"  status: {body.get('status')}")
print()

# --- Test 3: List event access ---
print("=" * 60)
print("TEST 3: GET /admin/events/test-event-presmeet-2027/access")
print("=" * 60)
# Find the ListEventAccess function
cf = session.client('cloudformation')
all_resources = []
next_token = None
while True:
    kwargs = {'StackName': 'h-dcn-test'}
    if next_token:
        kwargs['NextToken'] = next_token
    resp = cf.list_stack_resources(**kwargs)
    all_resources.extend(resp['StackResourceSummaries'])
    next_token = resp.get('NextToken')
    if not next_token:
        break

access_fns = [r['PhysicalResourceId'] for r in all_resources 
              if 'ListEventAccess' in r['LogicalResourceId'] 
              and r['ResourceType'] == 'AWS::Lambda::Function']

if access_fns:
    status, body = invoke(access_fns[0], path_params={'event_id': 'test-event-presmeet-2027'})
    print(f"  Status: {status}")
    print(f"  event_id: {body.get('event_id')}")
    members = body.get('members', [])
    print(f"  Members with access: {len(members)}")
    for m in members:
        print(f"    - {m.get('member_id')}: {m.get('email', 'N/A')}")
else:
    print("  ListEventAccess function not found")
print()

# --- Test 4: Lock orders (empty - no submitted orders yet) ---
print("=" * 60)
print("TEST 4: POST /admin/booking/lock?source_id=test-event-rally-2027")
print("=" * 60)
lock_fns = [r['PhysicalResourceId'] for r in all_resources 
            if 'AdminLockOrders' in r['LogicalResourceId'] 
            and r['ResourceType'] == 'AWS::Lambda::Function']

if lock_fns:
    status, body = invoke(lock_fns[0], method='POST', query_params={'source_id': 'test-event-rally-2027'})
    print(f"  Status: {status}")
    print(f"  locked_count: {body.get('locked_count')}")
    print(f"  skipped_count: {body.get('skipped_count')}")
    print(f"  message: {body.get('message')}")
else:
    print("  LockOrders function not found")
print()

print("=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)
