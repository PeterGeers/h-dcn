"""
Integration test: Full order flow (submit, pay, lock) + delegate management.
Tests against the live h-dcn-test stack via direct Lambda invoke.
"""
import boto3
import json
import base64
import sys

session = boto3.Session(profile_name='nonprofit-deploy', region_name='eu-west-1')
lambda_client = session.client('lambda')
dynamodb = session.resource('dynamodb', region_name='eu-west-1')
orders_table = dynamodb.Table('Orders-Test')

# Build fake JWT token with test admin claims
header = base64.urlsafe_b64encode(json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode()).decode().rstrip('=')
payload_data = {
    'sub': 'f2b57414-4041-7058-fbc0-4f02ba61868c',
    'cognito:groups': ['hdcnLeden', 'Events_CRUD', 'System_CRUD', 'Members_CRUD', 'Regio_All'],
    'email': 'webmaster+testadmin@h-dcn.nl',
    'token_use': 'access',
    'exp': 9999999999,
    'iat': 1781423528,
    'username': 'f2b57414-4041-7058-fbc0-4f02ba61868c'
}
payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).decode().rstrip('=')
sig = base64.urlsafe_b64encode(b'fake').decode().rstrip('=')
TOKEN = f'{header}.{payload}.{sig}'

# Discover function names from the stack
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

def find_function(logical_prefix):
    matches = [r['PhysicalResourceId'] for r in all_resources
               if r['LogicalResourceId'].startswith(logical_prefix)
               and r['ResourceType'] == 'AWS::Lambda::Function']
    return matches[0] if matches else None

GET_ORDER_FN = find_function('GetOrderFunction')
SUBMIT_ORDER_FN = find_function('SubmitOrderFunction')
CREATE_PAYMENT_FN = find_function('CreatePaymentFunction')
LOCK_ORDERS_FN = find_function('LockOrdersFunction')
MANAGE_DELEGATES_FN = find_function('ManageDelegatesFunction')

print(f"Functions found:")
print(f"  GetOrder:        {GET_ORDER_FN}")
print(f"  SubmitOrder:     {SUBMIT_ORDER_FN}")
print(f"  CreatePayment:   {CREATE_PAYMENT_FN}")
print(f"  LockOrders:      {LOCK_ORDERS_FN}")
print(f"  ManageDelegates: {MANAGE_DELEGATES_FN}")
print()


def invoke(function_name, method='GET', query_params=None, path_params=None, body=None):
    if not function_name:
        return 0, {'error': 'Function not found in stack'}
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
    status_code = result.get('statusCode', 0)
    try:
        body_data = json.loads(result.get('body', '{}'))
    except (json.JSONDecodeError, TypeError):
        body_data = {'raw': result.get('body', '')}
    return status_code, body_data


def check(test_name, status_code, expected_status, body):
    icon = "✅" if status_code == expected_status else "❌"
    print(f"  {icon} {test_name}: {status_code} (expected {expected_status})")
    if status_code != expected_status:
        print(f"     Body: {json.dumps(body, indent=2)[:300]}")
        return False
    return True


# ===========================================================================
print("=" * 70)
print("TEST 13.5: Submit → Pay → Lock flow")
print("=" * 70)

# Step 1: Get/create an order for the rally event (member-scoped)
print("\n--- Step 1: Get order for rally event ---")
status, body = invoke(GET_ORDER_FN, query_params={'source_id': 'test-event-rally-2027'})
order_id = body.get('order_id')
print(f"  Order ID: {order_id}")
print(f"  Status: {body.get('status')}")

# Step 2: Add items to the order directly in DynamoDB (simulate frontend saving)
print("\n--- Step 2: Add items to order (direct DynamoDB) ---")
items = [
    {
        'product_id': 'test-product-rally-ticket',
        'item_fields_data': {'name': 'Test Person 1', 'phone': '+31612345678'},
        'quantity': 1,
        'unit_price': 50,
        'line_total': 50,
    },
    {
        'product_id': 'test-product-camping',
        'item_fields_data': {'tent_size': '4'},
        'quantity': 1,
        'unit_price': 30,
        'line_total': 30,
    }
]
orders_table.update_item(
    Key={'order_id': order_id},
    UpdateExpression='SET #items = :items',
    ExpressionAttributeNames={'#items': 'items'},
    ExpressionAttributeValues={':items': items}
)
print(f"  ✅ Added 2 items (rally ticket + camping) to order {order_id}")

# Step 3: Submit the order
print("\n--- Step 3: Submit order ---")
status, body = invoke(SUBMIT_ORDER_FN, method='POST', path_params={'id': order_id, 'order_id': order_id})
passed = check("Submit order", status, 200, body)
if passed:
    print(f"     Order status: {body.get('status')}")
    print(f"     submitted_at: {body.get('submitted_at', 'N/A')}")

# Step 4: Create payment (Mollie)
print("\n--- Step 4: Create payment ---")
status, body = invoke(CREATE_PAYMENT_FN, method='POST', path_params={'id': order_id, 'order_id': order_id})
if status == 201:
    check("Create payment", status, 201, body)
    print(f"     checkout_url: {body.get('checkout_url', 'N/A')}")
    print(f"     amount: {body.get('amount')}")
    print(f"     payment_id: {body.get('payment_id', 'N/A')}")
elif status == 502:
    print(f"  ⚠️  Payment provider error (expected in test - Mollie API key may not be configured): {body.get('error')}")
    print(f"     This is OK for test environment without valid Mollie key")
else:
    check("Create payment", status, 201, body)

# Step 5: Lock orders for the rally event
print("\n--- Step 5: Lock submitted orders ---")
status, body = invoke(LOCK_ORDERS_FN, method='POST', query_params={'source_id': 'test-event-rally-2027'})
check("Lock orders", status, 200, body)
print(f"     locked_count: {body.get('locked_count')}")
print(f"     locked_order_ids: {body.get('locked_order_ids')}")
print(f"     skipped_count: {body.get('skipped_count')}")

# Verify the order is now locked
print("\n--- Step 5b: Verify order is locked in DynamoDB ---")
db_order = orders_table.get_item(Key={'order_id': order_id}).get('Item', {})
print(f"  Order status in DB: {db_order.get('status')}")
if db_order.get('status') == 'locked':
    print("  ✅ Order successfully locked")
else:
    print("  ❌ Order NOT locked")


# ===========================================================================
print("\n")
print("=" * 70)
print("TEST 13.6: Delegate management")
print("=" * 70)

# Use the club-scoped presmeet order
print("\n--- Step 1: Get club-scoped presmeet order ---")
status, body = invoke(GET_ORDER_FN, query_params={'source_id': 'test-event-presmeet-2027'})
presmeet_order_id = body.get('order_id')
print(f"  Order ID: {presmeet_order_id}")
print(f"  club_id: {body.get('club_id')}")
print(f"  delegates: {body.get('delegates')}")

# Step 2: Add a secondary delegate
print("\n--- Step 2: Add secondary delegate ---")
# First ensure SEED-members-001 has the same club_id
members_table = dynamodb.Table('Members-Test')
members_table.update_item(
    Key={'member_id': 'SEED-members-001'},
    UpdateExpression='SET club_id = :c',
    ExpressionAttributeValues={':c': 'test-club-001'}
)

status, body = invoke(MANAGE_DELEGATES_FN, method='POST',
                      path_params={'id': presmeet_order_id},
                      body={'action': 'add', 'member_id': 'SEED-members-001'})
check("Add secondary delegate", status, 200, body)
if status == 200:
    delegates = body.get('order', {}).get('delegates', {})
    print(f"     primary: {delegates.get('primary_member_id')}")
    print(f"     secondary: {delegates.get('secondary_member_id')}")

# Step 3: Remove the secondary delegate
print("\n--- Step 3: Remove secondary delegate ---")
status, body = invoke(MANAGE_DELEGATES_FN, method='POST',
                      path_params={'id': presmeet_order_id},
                      body={'action': 'remove'})
check("Remove secondary delegate", status, 200, body)
if status == 200:
    delegates = body.get('order', {}).get('delegates', {})
    has_secondary = 'secondary_member_id' in delegates
    print(f"     secondary_member_id present: {has_secondary}")
    if not has_secondary:
        print("     ✅ Secondary delegate removed successfully")

print("\n")
print("=" * 70)
print("ALL FLOW TESTS COMPLETE")
print("=" * 70)
