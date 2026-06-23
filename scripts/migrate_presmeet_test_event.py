"""
Migration script: Create a proper UUID-based test event for the closed community booking flow.

Replaces the old non-UUID test event IDs (presmeet_2025_test, presmeet-2027,
test-event-presmeet-2027) with a single canonical UUID event record that has
all required fields for the booking flow.

Steps:
1. Create a new event record with UUID, event_password, registry_config, status=published
2. Update Members.allowed_events: replace old IDs with new UUID
3. Update Orders.source_id: replace old IDs with new UUID
4. Upload a test invitee_registry.json to S3

Usage:
    python scripts/migrate_presmeet_test_event.py --dry-run --profile nonprofit-deploy
    python scripts/migrate_presmeet_test_event.py --profile nonprofit-deploy
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone

import boto3
import bcrypt

# --- Configuration ---
REGION = 'eu-west-1'
EVENTS_TABLE = 'Events'
MEMBERS_TABLE = 'Members'
ORDERS_TABLE = 'Orders'
S3_BUCKET = 'h-dcn-data-506221081911'

# Old event IDs to replace
OLD_EVENT_IDS = [
    'presmeet_2025_test',
    'presmeet-2027',
    'test-event-presmeet-2027',
    'evt-presmeet-2027',
]

# New event configuration
NEW_EVENT_PASSWORD = 'PM2027Lithuania'  # Same as the reference site
NEW_EVENT_NAME = 'Presidents Meeting 2027'
NEW_EVENT_SLUG = 'presmeet-2027'


def get_session(profile: str):
    """Create boto3 session with the given profile."""
    return boto3.Session(profile_name=profile, region_name=REGION)


def hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    password_bytes = password.encode('utf-8')[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')


def create_new_event(events_table, new_event_id: str, password_hash: str, dry_run: bool):
    """Create the new event record with all required booking flow fields."""
    now = datetime.now(timezone.utc).isoformat()
    s3_path = f'events/{new_event_id}/invitee_registry.json'

    event_item = {
        'event_id': new_event_id,
        'name': NEW_EVENT_NAME,
        'event_type': 'presmeet',
        'event_category': 'international',
        'participation': 'closed',
        'status': 'published',
        'linked_regio': 'regio_all',
        'location': 'Vilnius, Lithuania',
        'slug': NEW_EVENT_SLUG,
        'start_date': '2027-06-15T09:00',
        'end_date': '2027-06-20T18:00',
        'registration_open': '2026-12-01T00:00',
        'registration_close': '2027-05-01T23:59',
        'event_password': password_hash,
        'registry_config': {
            's3_path': s3_path,
            'row_label': 'club',
            'claim_mode': 'first_come_first_served',
            'allow_logo_upload': True,
        },
        'registry_claims': {},
        'landing_page': {
            'enabled': True,
            'slug': NEW_EVENT_SLUG,
            'hero_image_url': '',
            'tagline': 'Presidents Meeting 2027 - Lithuania',
            'registration_label': 'Register Now',
            'logos': [],
            'sections': [],
        },
        'created_at': now,
        'created_by': 'migration-script',
    }

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Creating new event:")
    print(f"  event_id: {new_event_id}")
    print(f"  name: {NEW_EVENT_NAME}")
    print(f"  slug: {NEW_EVENT_SLUG}")
    print(f"  status: published")
    print(f"  event_password: (bcrypt hash set)")
    print(f"  registry_config.s3_path: {s3_path}")

    if not dry_run:
        events_table.put_item(Item=event_item)
        print("  ✅ Event created successfully")
    return s3_path


def update_members_allowed_events(members_table, new_event_id: str, dry_run: bool):
    """Scan Members table, replace old event IDs in allowed_events with new UUID."""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Scanning Members for old event IDs...")

    updated_count = 0
    scanned_count = 0
    last_key = None

    while True:
        scan_params = {
            'ProjectionExpression': 'member_id, allowed_events, email',
            'FilterExpression': 'attribute_exists(allowed_events)',
        }
        if last_key:
            scan_params['ExclusiveStartKey'] = last_key

        response = members_table.scan(**scan_params)
        items = response.get('Items', [])
        scanned_count += len(items)

        for member in items:
            member_id = member['member_id']
            allowed_events = member.get('allowed_events', [])

            # Check if any old IDs are present
            old_ids_found = [eid for eid in allowed_events if eid in OLD_EVENT_IDS]
            if not old_ids_found:
                continue

            # Build new list: replace old IDs with new UUID (avoid duplicates)
            new_allowed = [eid for eid in allowed_events if eid not in OLD_EVENT_IDS]
            if new_event_id not in new_allowed:
                new_allowed.append(new_event_id)

            email = member.get('email', '?')
            print(f"  Member {member_id} ({email}): {old_ids_found} → {new_event_id}")

            if not dry_run:
                members_table.update_item(
                    Key={'member_id': member_id},
                    UpdateExpression='SET allowed_events = :new_events',
                    ExpressionAttributeValues={':new_events': new_allowed},
                )

            updated_count += 1

        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break

    print(f"  Scanned {scanned_count} members with allowed_events, updated {updated_count}")
    return updated_count


def update_orders_source_id(orders_table, new_event_id: str, dry_run: bool):
    """Scan Orders table, replace old event IDs in source_id with new UUID."""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Scanning Orders for old event IDs in source_id...")

    updated_count = 0
    scanned_count = 0
    last_key = None

    while True:
        scan_params = {
            'ProjectionExpression': 'order_id, source_id',
            'FilterExpression': 'attribute_exists(source_id)',
        }
        if last_key:
            scan_params['ExclusiveStartKey'] = last_key

        response = orders_table.scan(**scan_params)
        items = response.get('Items', [])
        scanned_count += len(items)

        for order in items:
            order_id = order['order_id']
            source_id = order.get('source_id', '')

            if source_id not in OLD_EVENT_IDS:
                continue

            print(f"  Order {order_id}: source_id '{source_id}' → '{new_event_id}'")

            if not dry_run:
                orders_table.update_item(
                    Key={'order_id': order_id},
                    UpdateExpression='SET source_id = :new_id',
                    ExpressionAttributeValues={':new_id': new_event_id},
                )

            updated_count += 1

        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break

    print(f"  Scanned {scanned_count} orders with source_id, updated {updated_count}")
    return updated_count


def delete_old_events(events_table, dry_run: bool):
    """Delete old event records if they exist."""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Checking for old event records to delete...")

    for old_id in OLD_EVENT_IDS:
        response = events_table.get_item(
            Key={'event_id': old_id},
            ProjectionExpression='event_id, #n',
            ExpressionAttributeNames={'#n': 'name'},
        )
        if 'Item' in response:
            name = response['Item'].get('name', '(no name)')
            print(f"  Found old event: {old_id} ({name})")
            if not dry_run:
                events_table.delete_item(Key={'event_id': old_id})
                print(f"    ✅ Deleted")
        else:
            print(f"  Not found: {old_id} (skipping)")


def upload_test_registry(s3_client, s3_path: str, dry_run: bool):
    """Upload a test invitee_registry.json to S3."""
    registry_data = {
        'version': '1.0',
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'rows': [
            {
                'row_id': 'club-nl-001',
                'label': 'H-DCN Nederland',
                'logo_url': '',
                'allowed_emails': [],
                'max_delegates': 5,
                'metadata': {'country': 'NL'},
            },
            {
                'row_id': 'club-de-001',
                'label': 'HOG Hamburg',
                'logo_url': '',
                'allowed_emails': [],
                'max_delegates': 3,
                'metadata': {'country': 'DE'},
            },
            {
                'row_id': 'club-be-001',
                'label': 'Belgium Chapter',
                'logo_url': '',
                'allowed_emails': [],
                'max_delegates': 3,
                'metadata': {'country': 'BE'},
            },
            {
                'row_id': 'club-lt-001',
                'label': 'Lithuania HOG',
                'logo_url': '',
                'allowed_emails': [],
                'max_delegates': 4,
                'metadata': {'country': 'LT'},
            },
            {
                'row_id': 'club-fr-001',
                'label': 'Paris Chapter',
                'logo_url': '',
                'allowed_emails': [],
                'max_delegates': 3,
                'metadata': {'country': 'FR'},
            },
        ],
    }

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Uploading test registry to S3:")
    print(f"  Bucket: {S3_BUCKET}")
    print(f"  Key: {s3_path}")
    print(f"  Rows: {len(registry_data['rows'])}")

    if not dry_run:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_path,
            Body=json.dumps(registry_data, indent=2),
            ContentType='application/json',
        )
        print("  ✅ Registry uploaded successfully")


def main():
    parser = argparse.ArgumentParser(description='Migrate presmeet test event to UUID-based record')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--profile', default='nonprofit-deploy', help='AWS profile to use')
    parser.add_argument('--event-id', default=None, help='Override the new event UUID (for reproducibility)')
    args = parser.parse_args()

    # Generate or use provided event ID
    new_event_id = args.event_id or str(uuid.uuid4())

    print("=" * 60)
    print("Migration: Presmeet Test Event → UUID-based Record")
    print("=" * 60)
    print(f"Profile: {args.profile}")
    print(f"Dry run: {args.dry_run}")
    print(f"New event ID: {new_event_id}")
    print(f"Old IDs to replace: {OLD_EVENT_IDS}")

    # Connect to AWS
    session = get_session(args.profile)
    dynamodb = session.resource('dynamodb', region_name=REGION)
    s3_client = session.client('s3', region_name=REGION)

    events_table = dynamodb.Table(EVENTS_TABLE)
    members_table = dynamodb.Table(MEMBERS_TABLE)
    orders_table = dynamodb.Table(ORDERS_TABLE)

    # Step 1: Create new event
    password_hash = hash_password(NEW_EVENT_PASSWORD)
    s3_path = create_new_event(events_table, new_event_id, password_hash, args.dry_run)

    # Step 2: Update Members.allowed_events
    members_updated = update_members_allowed_events(members_table, new_event_id, args.dry_run)

    # Step 3: Update Orders.source_id
    orders_updated = update_orders_source_id(orders_table, new_event_id, args.dry_run)

    # Step 4: Delete old event records
    delete_old_events(events_table, args.dry_run)

    # Step 5: Upload test registry JSON to S3
    upload_test_registry(s3_client, s3_path, args.dry_run)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"New event ID: {new_event_id}")
    print(f"Event password: {NEW_EVENT_PASSWORD}")
    print(f"Members updated: {members_updated}")
    print(f"Orders updated: {orders_updated}")
    print(f"S3 registry path: {s3_path}")
    if args.dry_run:
        print("\n⚠️  DRY RUN — no changes were made. Remove --dry-run to apply.")
    else:
        print("\n✅ Migration complete!")
        print(f"\nTo test the flow, visit: https://portal.h-dcn.nl/events/{NEW_EVENT_SLUG}")
        print(f"Password: {NEW_EVENT_PASSWORD}")


if __name__ == '__main__':
    main()
