"""
Event Status Scheduler Lambda Handler.

Triggered by EventBridge on a schedule (hourly) to automatically transition
event statuses based on registration dates:
- draft → open: when registration_open <= today
- open → closed: when registration_close <= today

On close transition, all submitted orders for that event are auto-locked
with a status_history entry.

This handler requires no auth (invoked by EventBridge, not by users).

Requirements: 4.4, 4.5, 4.6
"""

import boto3
import os
from datetime import datetime, date, timezone

dynamodb = boto3.resource('dynamodb')
events_table_name = os.environ.get('EVENTS_TABLE_NAME', 'Events')
orders_table_name = os.environ.get('ORDERS_TABLE_NAME', 'Orders')
events_table = dynamodb.Table(events_table_name)
orders_table = dynamodb.Table(orders_table_name)

# GSI used to find orders by source_id (which holds event_id for event orders)
EVENT_MEMBER_INDEX = 'event-member-index'


def lambda_handler(event, context):
    """
    Scheduled handler: check event dates and transition statuses.

    Returns a summary of transitions performed.
    """
    today = date.today().isoformat()  # "YYYY-MM-DD"
    print(f"Event status scheduler running. Today: {today}")

    results = {
        'today': today,
        'opened': [],
        'closed': [],
        'orders_locked': 0,
    }

    # Scan for events in draft or open status
    events_to_check = _scan_active_events()

    for evt in events_to_check:
        event_id = evt['event_id']
        status = evt.get('status', 'draft')
        reg_open = evt.get('registration_open', '')
        reg_close = evt.get('registration_close', '')

        # draft → open: when registration_open <= today
        if status == 'draft' and reg_open and reg_open <= today:
            _transition_event(event_id, 'draft', 'open')
            results['opened'].append(event_id)
            print(f"Event {event_id} transitioned draft → open (registration_open={reg_open})")

        # open → closed: when registration_close <= today
        elif status == 'open' and reg_close and reg_close <= today:
            _transition_event(event_id, 'open', 'closed')
            results['closed'].append(event_id)
            print(f"Event {event_id} transitioned open → closed (registration_close={reg_close})")

            # Auto-lock all submitted orders for this event
            locked_count = _auto_lock_orders(event_id)
            results['orders_locked'] += locked_count
            print(f"Auto-locked {locked_count} orders for event {event_id}")

    print(f"Scheduler complete. Opened: {len(results['opened'])}, "
          f"Closed: {len(results['closed'])}, Orders locked: {results['orders_locked']}")

    return results


def _scan_active_events():
    """
    Scan Events table for events with status 'draft' or 'open'.

    Uses a FilterExpression to only return relevant events.
    """
    all_events = []
    scan_kwargs = {
        'FilterExpression': '#s IN (:draft, :open)',
        'ExpressionAttributeNames': {'#s': 'status'},
        'ExpressionAttributeValues': {':draft': 'draft', ':open': 'open'},
    }

    while True:
        response = events_table.scan(**scan_kwargs)
        all_events.extend(response.get('Items', []))

        if 'LastEvaluatedKey' not in response:
            break
        scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

    return all_events


def _transition_event(event_id, from_status, to_status):
    """
    Update event status with a conditional check on current status.
    """
    now = datetime.now(timezone.utc).isoformat()
    events_table.update_item(
        Key={'event_id': event_id},
        UpdateExpression='SET #status = :new_status, updated_at = :now, '
                         'status_changed_at = :now, status_changed_by = :by',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={
            ':new_status': to_status,
            ':now': now,
            ':by': 'system',
            ':current': from_status,
        },
        ConditionExpression='#status = :current',
    )


def _auto_lock_orders(event_id):
    """
    Find all submitted orders for the given event and lock them.

    Uses the event-member-index GSI to find orders by source_id
    (which holds the event_id for event orders), then filters for status=submitted.

    Returns the count of orders locked.
    """
    locked_count = 0
    query_kwargs = {
        'IndexName': EVENT_MEMBER_INDEX,
        'KeyConditionExpression': 'source_id = :eid',
        'ExpressionAttributeValues': {':eid': event_id},
    }

    while True:
        response = orders_table.query(**query_kwargs)
        orders = response.get('Items', [])

        for order in orders:
            if order.get('status') == 'submitted':
                _lock_order(order)
                locked_count += 1

        if 'LastEvaluatedKey' not in response:
            break
        query_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

    return locked_count


def _lock_order(order):
    """
    Set order status to locked and add status_history entry.
    """
    now = datetime.now(timezone.utc).isoformat()
    order_id = order['order_id']

    history_entry = {
        'from': 'submitted',
        'to': 'locked',
        'at': now,
        'by': 'system',
        'source': 'auto_close',
    }

    # Get existing status_history or start empty
    existing_history = order.get('status_history', [])
    new_history = existing_history + [history_entry]

    orders_table.update_item(
        Key={'order_id': order_id},
        UpdateExpression='SET #status = :locked, updated_at = :now, '
                         'status_history = :history',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={
            ':locked': 'locked',
            ':now': now,
            ':history': new_history,
            ':submitted': 'submitted',
        },
        ConditionExpression='#status = :submitted',
    )
