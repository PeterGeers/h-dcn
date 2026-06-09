#!/usr/bin/env python3
"""
PresMeet v3 Deployment Script — Req 14: Migration & Seed

Performs a clean deployment of the PresMeet v3 system:
1. Deletes all existing PresMeet test records from the Orders table
   (records with event_type='presmeet' or channel='presmeet')
2. Deletes legacy PresMeet-specific records from the Producten table
   (records with product_id starting with 'config_presmeet_' or source='presmeet_config')
3. Seeds the 4 UnifiedProduct records for PM2027
4. Seeds the PresMeet 2027 Event_Record
5. Seeds the club registry JSON to S3

Usage:
    python backend/scripts/deploy_presmeet_v3.py --dry-run
    python backend/scripts/deploy_presmeet_v3.py
    python backend/scripts/deploy_presmeet_v3.py --profile nonprofit-deploy

Requirements: 14.1, 14.2, 14.3, 14.5
"""

import argparse
import json
import uuid
import logging
import os
from datetime import datetime, timezone, date
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr

REGION = "eu-west-1"
PROFILE_DEFAULT = "nonprofit-deploy"

# Table names
ORDERS_TABLE = os.environ.get("ORDERS_TABLE_NAME", "Orders")
PRODUCTEN_TABLE = os.environ.get("PRODUCTEN_TABLE_NAME", "Producten")
EVENTS_TABLE = os.environ.get("EVENTS_TABLE_NAME", "Events")
MEMBERS_TABLE = os.environ.get("MEMBERS_TABLE_NAME", "Members")
S3_REPORTS_BUCKET = os.environ.get("S3_REPORTS_BUCKET", "h-dcn-reports")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── PM2027 Product Definitions (Req 14.2) ──────────────────────────────────

PM2027_PRODUCTS = [
    {
        "id": "prod-pm2027-meeting",
        "product_id": "prod-pm2027-meeting",
        "name": "Meeting Ticket PM2027",
        "channel": "presmeet",
        "event_type": "presmeet",
        "price": Decimal("50.00"),
        "active": True,
        "order_item_fields": [
            {"id": "name", "label": "Name", "type": "text", "required": True},
            {"id": "role", "label": "Role", "type": "text", "required": True},
            {
                "id": "attend_party",
                "label": "Attend party",
                "type": "select",
                "required": True,
                "options": ["yes", "no"],
            },
        ],
        "purchase_rules": {
            "min_per_club": 1,
            "max_per_club": 3,
            "order_mode": "persistent",
        },
    },
    {
        "id": "prod-pm2027-party",
        "product_id": "prod-pm2027-party",
        "name": "Party Ticket PM2027",
        "channel": "presmeet",
        "event_type": "presmeet",
        "price": Decimal("99.50"),
        "active": True,
        "order_item_fields": [
            {"id": "name", "label": "Name", "type": "text", "required": True},
            {
                "id": "person_type",
                "label": "Person type",
                "type": "select",
                "required": True,
                "options": ["delegate", "guest"],
            },
        ],
        "purchase_rules": {
            "max_per_club": 13,
            "order_mode": "persistent",
        },
    },
    {
        "id": "prod-pm2027-tshirt",
        "product_id": "prod-pm2027-tshirt",
        "name": "T-Shirt PM2027",
        "channel": "presmeet",
        "event_type": "presmeet",
        "price": Decimal("25.00"),
        "active": True,
        "variant_schema": [
            {"name": "Size", "values": ["S", "M", "L", "XL", "XXL", "3XL", "4XL"]},
            {"name": "Gender", "values": ["Male", "Female"]},
        ],
        "order_item_fields": [
            {"id": "person_name", "label": "Person name", "type": "text", "required": True},
        ],
        "purchase_rules": {
            "max_per_club": 13,
            "order_mode": "persistent",
        },
    },
    {
        "id": "prod-pm2027-transfer",
        "product_id": "prod-pm2027-transfer",
        "name": "Airport Transfer PM2027",
        "channel": "presmeet",
        "event_type": "presmeet",
        "price": Decimal("5.00"),
        "active": True,
        "variant_schema": [
            {"name": "Direction", "values": ["Pickup", "Dropoff"]},
            {"name": "Airport", "values": ["AMS", "RTM", "EIN"]},
        ],
        "order_item_fields": [
            {"id": "flight_number", "label": "Flight number", "type": "text", "required": True},
            {"id": "date", "label": "Date", "type": "date", "required": True},
            {"id": "time", "label": "Time", "type": "text", "required": True},
            {
                "id": "persons",
                "label": "Persons",
                "type": "number",
                "required": True,
                "validation": {"minimum": 1, "maximum": 20},
            },
        ],
        "purchase_rules": {
            "max_per_club": 20,
            "order_mode": "persistent",
        },
    },
]

# ─── PM2027 Event Record (Req 14.3) ─────────────────────────────────────────

PM2027_EVENT = {
    "event_id": "evt-pm2027",
    "name": "Presidents' Meeting 2027",
    "event_type": "presmeet",
    "location": "TBD",
    "status": "open",
    "start_date": "2027-06-15",
    "end_date": "2027-06-18",
    "registration_open": "2026-01-01",
    "registration_close": "2027-05-01",
    "payment_deadline": "2027-05-15",
    "product_ids": [p["product_id"] for p in PM2027_PRODUCTS],
    "constraints": [
        {
            "key": "max_meeting_attendees",
            "label": "Maximum meeting attendees",
            "max": 100,
            "counting_rule": "count_items_by_product",
            "product_id": "prod-pm2027-meeting",
        },
        {
            "key": "max_party_attendees",
            "label": "Maximum party attendees",
            "max": 200,
            "counting_rule": "count_items_by_product",
            "product_id": "prod-pm2027-party",
        },
    ],
    "created_at": datetime.now(timezone.utc).isoformat(),
    "created_by": "deploy_presmeet_v3",
}

# ─── Club Registry (Req 14 / Req 12) ────────────────────────────────────────

# Sample club registry — add real clubs as needed
CLUB_REGISTRY = {
    "clubs": [
        {"club_id": "club-nl-001", "name": "H-DCN Nederland", "country": "NL"},
        {"club_id": "club-de-001", "name": "H-DC Deutschland", "country": "DE"},
        {"club_id": "club-be-001", "name": "H-DC Belgium", "country": "BE"},
        {"club_id": "club-at-001", "name": "H-DC Austria", "country": "AT"},
        {"club_id": "club-ch-001", "name": "H-DC Switzerland", "country": "CH"},
        {"club_id": "club-dk-001", "name": "H-DC Denmark", "country": "DK"},
        {"club_id": "club-se-001", "name": "H-DC Sweden", "country": "SE"},
        {"club_id": "club-no-001", "name": "H-DC Norway", "country": "NO"},
        {"club_id": "club-fi-001", "name": "H-DC Finland", "country": "FI"},
        {"club_id": "club-fr-001", "name": "H-DC France", "country": "FR"},
        {"club_id": "club-it-001", "name": "H-DC Italy", "country": "IT"},
        {"club_id": "club-es-001", "name": "H-DC Spain", "country": "ES"},
        {"club_id": "club-uk-001", "name": "H-DC United Kingdom", "country": "GB"},
        {"club_id": "club-ie-001", "name": "H-DC Ireland", "country": "IE"},
        {"club_id": "club-pl-001", "name": "H-DC Poland", "country": "PL"},
    ],
    "last_updated": datetime.now(timezone.utc).isoformat(),
}


def get_session(profile: str | None = None):
    """Create a boto3 session."""
    kwargs = {"region_name": REGION}
    if profile:
        kwargs["profile_name"] = profile
    return boto3.Session(**kwargs)


# ─── Step 1: Clean Orders table ─────────────────────────────────────────────

def clean_presmeet_orders(session, dry_run: bool) -> int:
    """Delete all presmeet orders from the Orders table."""
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(ORDERS_TABLE)

    print(f"\n{'─' * 60}")
    print(f"Step 1: Cleaning PresMeet orders from '{ORDERS_TABLE}'")
    print(f"{'─' * 60}")

    # Scan for presmeet records (event_type='presmeet' OR channel='presmeet' OR tenant='presmeet')
    items_to_delete = []
    scan_kwargs = {}

    while True:
        response = table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            if (
                item.get("event_type") == "presmeet"
                or item.get("channel") == "presmeet"
                or item.get("tenant") == "presmeet"
            ):
                items_to_delete.append(item)

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    print(f"  Found {len(items_to_delete)} presmeet order(s) to delete")

    if dry_run:
        for item in items_to_delete[:10]:
            print(f"    [DRY] Would delete: {item.get('order_id')} (club: {item.get('club_id')}, status: {item.get('status')})")
        if len(items_to_delete) > 10:
            print(f"    ... and {len(items_to_delete) - 10} more")
        return len(items_to_delete)

    deleted = 0
    for item in items_to_delete:
        try:
            table.delete_item(Key={"order_id": item["order_id"]})
            deleted += 1
            logger.info(f"  🗑️  Deleted order: {item['order_id']}")
        except Exception as e:
            logger.error(f"  ❌ Failed to delete {item['order_id']}: {e}")

    print(f"  ✅ Deleted {deleted} presmeet order(s)")
    return deleted


# ─── Step 2: Clean Producten table ──────────────────────────────────────────

def clean_presmeet_products(session, dry_run: bool) -> int:
    """Delete legacy presmeet product records from the Producten table."""
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(PRODUCTEN_TABLE)

    print(f"\n{'─' * 60}")
    print(f"Step 2: Cleaning legacy PresMeet products from '{PRODUCTEN_TABLE}'")
    print(f"{'─' * 60}")

    items_to_delete = []
    scan_kwargs = {}

    while True:
        response = table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            product_id = item.get("product_id", "")
            # Match legacy config records and old presmeet products
            if (
                product_id.startswith("config_presmeet_")
                or item.get("source") == "presmeet_config"
                or (item.get("channel") == "presmeet" and item.get("event_type") == "presmeet")
                or (item.get("tenant") == "presmeet")
            ):
                items_to_delete.append(item)

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    print(f"  Found {len(items_to_delete)} legacy presmeet product(s) to delete")

    if dry_run:
        for item in items_to_delete:
            print(f"    [DRY] Would delete: {item.get('product_id')} ({item.get('name', 'unnamed')})")
        return len(items_to_delete)

    deleted = 0
    for item in items_to_delete:
        try:
            table.delete_item(Key={"id": item.get("id", item.get("product_id"))})
            deleted += 1
            logger.info(f"  🗑️  Deleted product: {item.get('product_id', item.get('id'))}")
        except Exception as e:
            logger.error(f"  ❌ Failed to delete {item.get('product_id', item.get('id'))}: {e}")

    print(f"  ✅ Deleted {deleted} legacy presmeet product(s)")
    return deleted


# ─── Step 3: Seed PM2027 products ───────────────────────────────────────────

def seed_products(session, dry_run: bool) -> int:
    """Seed the 4 PM2027 UnifiedProduct records."""
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(PRODUCTEN_TABLE)

    print(f"\n{'─' * 60}")
    print(f"Step 3: Seeding PM2027 products into '{PRODUCTEN_TABLE}'")
    print(f"{'─' * 60}")

    if dry_run:
        for p in PM2027_PRODUCTS:
            print(f"    [DRY] Would create: {p['product_id']} — {p['name']} (€{p['price']})")
        return len(PM2027_PRODUCTS)

    created = 0
    for product in PM2027_PRODUCTS:
        item = {**product, "created_at": datetime.now(timezone.utc).isoformat()}
        try:
            table.put_item(Item=item)
            created += 1
            print(f"  ✅ Created: {product['product_id']} — {product['name']}")
        except Exception as e:
            logger.error(f"  ❌ Failed to create {product['product_id']}: {e}")

    print(f"  ✅ Seeded {created} PM2027 product(s)")
    return created


# ─── Step 4: Seed PM2027 event ───────────────────────────────────────────────

def seed_event(session, dry_run: bool) -> bool:
    """Seed the PM2027 event record."""
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(EVENTS_TABLE)

    print(f"\n{'─' * 60}")
    print(f"Step 4: Seeding PM2027 event into '{EVENTS_TABLE}'")
    print(f"{'─' * 60}")

    if dry_run:
        print(f"    [DRY] Would create event: {PM2027_EVENT['event_id']} — {PM2027_EVENT['name']}")
        print(f"           Status: {PM2027_EVENT['status']}, Registration: {PM2027_EVENT['registration_open']} → {PM2027_EVENT['registration_close']}")
        return True

    try:
        table.put_item(Item=PM2027_EVENT)
        print(f"  ✅ Created event: {PM2027_EVENT['event_id']} — {PM2027_EVENT['name']}")
        print(f"     Status: {PM2027_EVENT['status']}")
        print(f"     Registration: {PM2027_EVENT['registration_open']} → {PM2027_EVENT['registration_close']}")
        print(f"     Products: {', '.join(PM2027_EVENT['product_ids'])}")
        return True
    except Exception as e:
        logger.error(f"  ❌ Failed to create event: {e}")
        return False


# ─── Step 5: Seed club registry to S3 ───────────────────────────────────────

def seed_club_registry(session, dry_run: bool) -> bool:
    """Upload the club registry JSON to S3."""
    s3 = session.client("s3", region_name=REGION)
    key = "presmeet/club_registry.json"

    print(f"\n{'─' * 60}")
    print(f"Step 5: Seeding club registry to 's3://{S3_REPORTS_BUCKET}/{key}'")
    print(f"{'─' * 60}")

    if dry_run:
        print(f"    [DRY] Would upload {len(CLUB_REGISTRY['clubs'])} clubs to S3")
        for club in CLUB_REGISTRY["clubs"][:5]:
            print(f"           {club['club_id']}: {club['name']} ({club['country']})")
        print(f"           ... and {len(CLUB_REGISTRY['clubs']) - 5} more")
        return True

    try:
        s3.put_object(
            Bucket=S3_REPORTS_BUCKET,
            Key=key,
            Body=json.dumps(CLUB_REGISTRY, indent=2),
            ContentType="application/json",
        )
        print(f"  ✅ Uploaded {len(CLUB_REGISTRY['clubs'])} clubs to S3")
        return True
    except Exception as e:
        logger.error(f"  ❌ Failed to upload club registry: {e}")
        return False


# ─── Step 6: Clean presmeet club_id from Members (optional) ─────────────────

def clean_member_club_ids(session, dry_run: bool) -> int:
    """Remove club_id from Members records that were assigned during testing.
    
    Only removes club_id if the member has status='presmeet' (test records)
    or if club_id starts with 'test-' (test assignments).
    """
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(MEMBERS_TABLE)

    print(f"\n{'─' * 60}")
    print(f"Step 6: Cleaning test club_id assignments from '{MEMBERS_TABLE}'")
    print(f"{'─' * 60}")

    items_to_clean = []
    scan_kwargs = {}

    while True:
        response = table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            club_id = item.get("club_id")
            if club_id:
                # Only clean test assignments, not real ones
                if (
                    item.get("status") == "presmeet"
                    or str(club_id).startswith("test-")
                ):
                    items_to_clean.append(item)

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    print(f"  Found {len(items_to_clean)} test club_id assignment(s) to clean")

    if dry_run:
        for item in items_to_clean[:10]:
            print(f"    [DRY] Would remove club_id from: {item.get('email', item.get('member_id'))} (club: {item.get('club_id')})")
        return len(items_to_clean)

    cleaned = 0
    for item in items_to_clean:
        try:
            table.update_item(
                Key={"member_id": item["member_id"]},
                UpdateExpression="REMOVE club_id",
            )
            cleaned += 1
            logger.info(f"  🧹 Removed club_id from: {item.get('email', item['member_id'])}")
        except Exception as e:
            logger.error(f"  ❌ Failed to clean {item.get('email', item['member_id'])}: {e}")

    print(f"  ✅ Cleaned {cleaned} test club_id assignment(s)")
    return cleaned


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Deploy PresMeet v3: clean old data and seed fresh configuration"
    )
    parser.add_argument(
        "--profile",
        default=PROFILE_DEFAULT,
        help=f"AWS CLI profile to use (default: {PROFILE_DEFAULT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to DynamoDB/S3",
    )
    parser.add_argument(
        "--skip-clean",
        action="store_true",
        help="Skip cleanup steps, only seed new data",
    )
    args = parser.parse_args()

    mode = "DRY RUN" if args.dry_run else "LIVE"
    print(f"{'🔍' if args.dry_run else '🚀'} PresMeet v3 Deployment [{mode}]")
    print(f"   Profile: {args.profile}")
    print(f"   Region: {REGION}")
    print(f"   Tables: Orders={ORDERS_TABLE}, Producten={PRODUCTEN_TABLE}, Events={EVENTS_TABLE}")
    print(f"   S3 Bucket: {S3_REPORTS_BUCKET}")

    session = get_session(args.profile)

    if not args.skip_clean:
        # Step 1: Clean orders
        clean_presmeet_orders(session, args.dry_run)

        # Step 2: Clean products
        clean_presmeet_products(session, args.dry_run)

        # Step 6: Clean test club_id from members
        clean_member_club_ids(session, args.dry_run)

    # Step 3: Seed products
    seed_products(session, args.dry_run)

    # Step 4: Seed event
    seed_event(session, args.dry_run)

    # Step 5: Seed club registry
    seed_club_registry(session, args.dry_run)

    # Summary
    print(f"\n{'═' * 60}")
    print(f"{'🔍 DRY RUN COMPLETE' if args.dry_run else '🎉 DEPLOYMENT COMPLETE'}")
    print(f"{'═' * 60}")
    if not args.dry_run:
        print("\n  Next steps:")
        print("  1. Deploy the backend: sam build && sam deploy")
        print("  2. Deploy the frontend: npm run build:prod && sync to S3")
        print("  3. Test with webmaster@h-dcn.nl (admin) and a regular user")
    else:
        print("\n  Run without --dry-run to apply changes.")


if __name__ == "__main__":
    main()
