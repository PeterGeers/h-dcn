"""Quick script to list all events in both Events and Events-Test tables."""
import boto3
from decimal import Decimal

session = boto3.Session(profile_name='nonprofit-deploy', region_name='eu-west-1')
dynamodb = session.resource('dynamodb')

# Check both tables
for table_name in ['Events', 'Events-Test']:
    print(f"\n{'='*60}")
    print(f"TABLE: {table_name}")
    print(f"{'='*60}")
    try:
        table = dynamodb.Table(table_name)
        items = []
        response = table.scan()
        items.extend(response['Items'])
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])

        print(f"Total events: {len(items)}\n")
        print(f"{'title':<45} {'status':<15} {'participation':<15} {'event_type'}")
        print("-" * 120)
        for item in sorted(items, key=lambda x: x.get('title', x.get('naam', '?'))):
            title = item.get('title', item.get('naam', '(none)'))
            status = item.get('status', '(none)')
            participation = item.get('participation', '(none)')
            event_type = item.get('event_type', item.get('type', '(none)'))
            print(f"{title:<45} {status:<15} {participation:<15} {event_type}")
    except Exception as e:
        print(f"  Error: {e}")
