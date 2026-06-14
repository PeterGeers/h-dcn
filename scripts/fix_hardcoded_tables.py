"""Fix hardcoded DynamoDB table names in handler files."""
import os

BACKEND = r'c:\Users\peter\aws\h-dcn\backend'

handlers = {
    # (filepath relative to backend, table_name, env_var)
    'handler/get_orders/app.py': ('Orders', 'ORDERS_TABLE_NAME'),
    'handler/get_order_byid/app.py': ('Orders', 'ORDERS_TABLE_NAME'),
    'handler/get_payments/app.py': ('Payments', 'PAYMENTS_TABLE_NAME'),
    'handler/get_payment_byid/app.py': ('Payments', 'PAYMENTS_TABLE_NAME'),
    'handler/get_member_payments/app.py': ('Payments', 'PAYMENTS_TABLE_NAME'),
    'handler/delete_payment/app.py': ('Payments', 'PAYMENTS_TABLE_NAME'),
    'handler/get_events/app.py': ('Events', 'EVENTS_TABLE_NAME'),
    'handler/get_event_byid/app.py': ('Events', 'EVENTS_TABLE_NAME'),
    'handler/get_memberships/app.py': ('Memberships', 'MEMBERSHIPS_TABLE_NAME'),
    'handler/get_membership_byid/app.py': ('Memberships', 'MEMBERSHIPS_TABLE_NAME'),
    'handler/create_membership/app.py': ('Memberships', 'MEMBERSHIPS_TABLE_NAME'),
    'handler/update_membership/app.py': ('Memberships', 'MEMBERSHIPS_TABLE_NAME'),
    'handler/delete_membership/app.py': ('Memberships', 'MEMBERSHIPS_TABLE_NAME'),
    'handler/create_payment/app.py': ('Payments', 'PAYMENTS_TABLE_NAME'),
}

for rel_path, (table_name, env_var) in handlers.items():
    filepath = os.path.join(BACKEND, rel_path)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    old = f"dynamodb.Table('{table_name}')"
    new = f"dynamodb.Table(os.environ.get('{env_var}', '{table_name}'))"
    
    if old not in content:
        print(f'SKIP {rel_path}: pattern not found')
        continue
    
    content = content.replace(old, new)
    
    # Add import os if missing
    if 'import os' not in content:
        content = content.replace('import json\n', 'import json\nimport os\n', 1)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f'FIXED {rel_path}: {table_name} -> {env_var}')

# Also fix create_payment which has both Payments AND Orders hardcoded
filepath = os.path.join(BACKEND, 'handler/create_payment/app.py')
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_orders = "dynamodb.Table('Orders')"
new_orders = "dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))"
if old_orders in content:
    content = content.replace(old_orders, new_orders)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'FIXED handler/create_payment/app.py: Orders -> ORDERS_TABLE_NAME')

print('\nDone!')
