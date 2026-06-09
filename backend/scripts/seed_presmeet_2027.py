#!/usr/bin/env python3
"""
Seed script for PresMeet 2027 (PM2027) event setup.

Creates the 4 UnifiedProduct records and 1 Event_Record required for the
Presidents Meeting 2027. Also cleans up any existing presmeet test data
to ensure a fresh start.

This script is idempotent — safe to run multiple times. Products and event
are written with put_item (upsert), and cleanup only deletes records that
match the presmeet channel/event_type.

Tables affected:
    - Producten  (PK: product_id) — 4 product records created
    - Events     (PK: event_id)   — 1 event record created
    - Orders     (PK: order_id)   — existing presmeet orders deleted (cleanup)

Prerequisites:
    - AWS profile with DynamoDB read/write permissions on the target tables
    - Tables must exist in eu-west-1

Usage:
    # Preview what would happen (no changes)
    python backend/scripts/seed_presmeet_2027.py --dry-run

    # Run the seed (default profile: nonprofit-deploy)
    python backend/scripts/seed_presmeet_2027.py

    # Use a different profile
    python backend/scripts/seed_presmeet_2027.py --profile nonprofit-admin
"""

import argparse
import sys
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError


REGION = "eu-west-1"

# Table names
PRODUCTEN_TABLE = "Producten"
EVENTS_TABLE = "Events"
ORDERS_TABLE = "Orders"

# Fixed product IDs for PM2027 (deterministic for idempotency)
PRODUCT_ID_MEETING = "prod-meeting-2027"
PRODUCT_ID_PARTY = "prod-party-2027"
PRODUCT_ID_TSHIRT = "prod-tshirt-2027"
PRODUCT_ID_TRANSFER = "prod-transfer-2027"

# Fixed event ID for PM2027 (deterministic for idempotency)
EVENT_ID_PM2027 = "pm2027-event"

# ─────────────────────────────────────────────────────────────────────────────
# Product definitions (UnifiedProduct schema)
# ─────────────────────────────────────────────────────────────────────────────

PRODUCTS = [
    {
        "product_id": PRODUCT_ID_MEETING,
        "name": "Meeting Ticket PM2027",
        "channel": "presmeet",
        "event_type": "presmeet",
        "price": Decimal("50.00"),
        "order_item_fields": [
            {"id": "name", "label": "Naam", "type": "text", "required": True},
            {"id": "role", "label": "Functie", "type": "text", "required": True},
            {
                "id": "attend_party",
                "label": "Feest bijwonen",
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
        "variant_schema": None,
    },
    {
        "product_id": PRODUCT_ID_PARTY,
        "name": "Party Ticket PM2027",
        "channel": "presmeet",
        "event_type": "presmeet",
        "price": Decimal("25.00"),
        "order_item_fields": [
            {"id": "name", "label": "Naam", "type": "text", "required": True},
            {
                "id": "person_type",
                "label": "Type persoon",
                "type": "select",
                "required": True,
                "options": ["delegate", "guest"],
            },
        ],
        "purchase_rules": {
            "max_per_club": 13,
            "order_mode": "persistent",
        },
        "variant_schema": None,
    },
    {
        "product_id": PRODUCT_ID_TSHIRT,
        "name": "T-Shirt PM2027",
        "channel": "presmeet",
        "event_type": "presmeet",
        "price": Decimal("25.00"),
        "order_item_fields": [
            {"id": "person_name", "label": "Naam persoon", "type": "text", "required": True},
        ],
        "purchase_rules": {
            "max_per_club": 13,
            "order_mode": "persistent",
        },
        "variant_schema": [
            {"name": "Size", "values": ["S", "M", "L", "XL", "XXL", "3XL", "4XL"]},
            {"name": "Gender", "values": ["Male", "Female"]},
        ],
    },
    {
        "product_id": PRODUCT_ID_TRANSFER,
        "name": "Airport Transfer PM2027",
        "channel": "presmeet",
        "event_type": "presmeet",
        "price": Decimal("25.00"),
        "order_item_fields": [
            {"id": "flight_number", "label": "Vluchtnummer", "type": "text", "required": True},
            {"id": "date", "label": "Datum", "type": "date", "required": True},
            {"id": "time", "label": "Tijd", "type": "text", "required": True},
            {
                "id": "persons",
                "label": "Aantal personen",
                "type": "number",
                "required": True,
                "min": 1,
                "max": 20,
            },
        ],
        "purchase_rules": {
            "max_per_club": 20,
            "order_mode": "persistent",
        },
        "variant_schema": [
            {"name": "Direction", "values": ["Pickup", "Dropoff"]},
            {"name": "Airport", "values": ["AMS", "RTM", "EIN"]},
        ],
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Event definition
# ─────────────────────────────────────────────────────────────────────────────

EVENT_PM2027 = {
    "event_id": EVENT_ID_PM2027,
    "event_type": "presmeet",
    "name": "Presidents Meeting 2027",
    "location": "Hotel Amersfoort",
    "status": "draft",
    "start_date": "2027-06-20",
    "end_date": "2027-06-22",
    "registration_open": "2027-01-01",
    "registration_close": "2027-05-01",
    "payment_deadline": "2027-05-15",
    "product_ids": [
        PRODUCT_ID_MEETING,
        PRODUCT_ID_PARTY,
        PRODUCT_ID_TSHIRT,
        PRODUCT_ID_TRANSFER,
    ],
    "constraints": [
        {
            "key": "max_meeting_attendees",
            "label": "Maximum vergaderdeelnemers",
            "max": 150,
            "counting_rule": "count_items_by_product",
            "product_id": PRODUCT_ID_MEETING,
        },
        {
            "key": "max_party_guests",
            "label": "Maximum feestgangers",
            "max": 500,
            "counting_rule": "count_items_by_product",
            "product_id": PRODUCT_ID_PARTY,
        },
    ],
    "created_at": datetime.now(timezone.utc).isoformat(),
    "created_by": "seed_script",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────


def get_dynamodb_resource(profile: str | None = None):
    """Create a DynamoDB resource with the specified profile."""
    session_kwargs = {"region_name": REGION}
    if profile:
        session_kwargs["profile_name"] = profile

    session = boto3.Session(**session_kwargs)
    return session.resource("dynamodb", region_name=REGION)


def scan_all_items(table, filter_expression=None, expression_values=None, expression_names=None) -> list[dict]:
    """Scan all items from a DynamoDB table with optional filter, handling pagination."""
    items = []
    scan_kwargs = {}
    if filter_expression:
        scan_kwargs["FilterExpression"] = filter_expression
    if expression_values:
        scan_kwargs["ExpressionAttributeValues"] = expression_values
    if expression_names:
        scan_kwargs["ExpressionAttributeNames"] = expression_names

    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    return items


# ─────────────────────────────────────────────────────────────────────────────
# Cleanup: delete existing presmeet test data
# ─────────────────────────────────────────────────────────────────────────────


def cleanup_orders(dynamodb, dry_run: bool) -> int:
    """Delete all orders with channel='presmeet' or event_type='presmeet'."""
    print("\n  🗑️  Cleaning up existing presmeet orders...")
    table = dynamodb.Table(ORDERS_TABLE)

    try:
        table.load()
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print("     ⚠️  Orders table not found — skipping cleanup.")
            return 0
        raise

    # Find orders with channel=presmeet OR event_type=presmeet
    items = scan_all_items(
        table,
        filter_expression="#ch = :presmeet OR #et = :presmeet",
        expression_values={":presmeet": "presmeet"},
        expression_names={"#ch": "channel", "#et": "event_type"},
    )

    if not items:
        print("     No existing presmeet orders found.")
        return 0

    print(f"     Found {len(items)} presmeet order(s) to delete.")

    if dry_run:
        for item in items:
            print(f"     [DRY RUN] Would delete order: {item.get('order_id')}")
        return len(items)

    deleted = 0
    for item in items:
        order_id = item.get("order_id")
        if order_id:
            table.delete_item(Key={"order_id": order_id})
            deleted += 1
            print(f"     ✅ Deleted order: {order_id}")

    return deleted


def cleanup_products(dynamodb, dry_run: bool) -> int:
    """Delete all products with channel='presmeet'."""
    print("\n  🗑️  Cleaning up existing presmeet products...")
    table = dynamodb.Table(PRODUCTEN_TABLE)

    try:
        table.load()
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print("     ⚠️  Producten table not found — skipping cleanup.")
            return 0
        raise

    # Find products with channel=presmeet
    items = scan_all_items(
        table,
        filter_expression="#ch = :presmeet",
        expression_values={":presmeet": "presmeet"},
        expression_names={"#ch": "channel"},
    )

    if not items:
        print("     No existing presmeet products found.")
        return 0

    print(f"     Found {len(items)} presmeet product(s) to delete.")

    if dry_run:
        for item in items:
            print(f"     [DRY RUN] Would delete product: {item.get('product_id')} ({item.get('name', '?')})")
        return len(items)

    deleted = 0
    for item in items:
        product_id = item.get("product_id") or item.get("id")
        if product_id:
            table.delete_item(Key={"id": product_id})
            deleted += 1
            print(f"     ✅ Deleted product: {product_id}")

    return deleted


def cleanup_event(dynamodb, dry_run: bool) -> int:
    """Delete existing PM2027 event record (if any)."""
    print("\n  🗑️  Cleaning up existing PM2027 event...")
    table = dynamodb.Table(EVENTS_TABLE)

    try:
        table.load()
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print("     ⚠️  Events table not found — skipping cleanup.")
            return 0
        raise

    # Check if our specific event exists
    response = table.get_item(Key={"event_id": EVENT_ID_PM2027})
    item = response.get("Item")

    if not item:
        print("     No existing PM2027 event found.")
        return 0

    print(f"     Found existing PM2027 event: {item.get('name', EVENT_ID_PM2027)}")

    if dry_run:
        print(f"     [DRY RUN] Would delete event: {EVENT_ID_PM2027}")
        return 1

    table.delete_item(Key={"event_id": EVENT_ID_PM2027})
    print(f"     ✅ Deleted event: {EVENT_ID_PM2027}")
    return 1


# ─────────────────────────────────────────────────────────────────────────────
# Seed: create products and event
# ─────────────────────────────────────────────────────────────────────────────


def seed_products(dynamodb, dry_run: bool) -> int:
    """Create the 4 PM2027 product records."""
    print("\n  📦 Creating PM2027 products...")
    table = dynamodb.Table(PRODUCTEN_TABLE)

    created = 0
    for product in PRODUCTS:
        product_id = product["product_id"]
        name = product["name"]
        price = product["price"]

        if dry_run:
            print(f"     [DRY RUN] Would create: {product_id} — {name} (€{price})")
        else:
            # Filter out None values (variant_schema=None should not be stored)
            item = {k: v for k, v in product.items() if v is not None}
            # DynamoDB key is 'id', ensure it's set (same value as product_id)
            item["id"] = product_id
            table.put_item(Item=item)
            print(f"     ✅ Created: {product_id} — {name} (€{price})")

        created += 1

    return created


def seed_event(dynamodb, dry_run: bool) -> int:
    """Create the PM2027 event record."""
    print("\n  📅 Creating PM2027 event...")
    table = dynamodb.Table(EVENTS_TABLE)

    if dry_run:
        print(f"     [DRY RUN] Would create event: {EVENT_PM2027['name']}")
        print(f"               event_id: {EVENT_PM2027['event_id']}")
        print(f"               event_type: {EVENT_PM2027['event_type']}")
        print(f"               dates: {EVENT_PM2027['start_date']} – {EVENT_PM2027['end_date']}")
        print(f"               registration: {EVENT_PM2027['registration_open']} – {EVENT_PM2027['registration_close']}")
        print(f"               constraints: {len(EVENT_PM2027['constraints'])} configured")
        print(f"               products: {len(EVENT_PM2027['product_ids'])} linked")
        return 1

    table.put_item(Item=EVENT_PM2027)
    print(f"     ✅ Created event: {EVENT_PM2027['name']}")
    print(f"        event_id: {EVENT_PM2027['event_id']}")
    print(f"        status: {EVENT_PM2027['status']}")
    print(f"        dates: {EVENT_PM2027['start_date']} – {EVENT_PM2027['end_date']}")
    print(f"        registration: {EVENT_PM2027['registration_open']} – {EVENT_PM2027['registration_close']}")
    print(f"        constraints: {len(EVENT_PM2027['constraints'])} configured")
    print(f"        products: {len(EVENT_PM2027['product_ids'])} linked")
    return 1


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Seed the PresMeet 2027 event and product data into DynamoDB. "
            "Cleans up existing presmeet test data first, then creates 4 products "
            "and 1 event record. Idempotent — safe to run multiple times."
        )
    )
    parser.add_argument(
        "--profile",
        default="nonprofit-deploy",
        help="AWS CLI profile to use (default: nonprofit-deploy)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be created/deleted without making changes",
    )
    args = parser.parse_args()

    mode = "🔍 DRY RUN" if args.dry_run else "🚀 SEED PM2027"
    print(f"{'═' * 60}")
    print(f"  {mode} — PresMeet 2027 Setup")
    print(f"  Region:  {REGION}")
    print(f"  Profile: {args.profile}")
    print(f"{'═' * 60}")

    if not args.dry_run:
        print("\n  ⚠️  This will modify production data. Press Ctrl+C to abort.")

    dynamodb = get_dynamodb_resource(args.profile)
    start_time = time.time()

    # Phase 1: Cleanup
    print(f"\n{'─' * 60}")
    print("  PHASE 1: CLEANUP")
    print(f"{'─' * 60}")

    orders_deleted = cleanup_orders(dynamodb, args.dry_run)
    products_deleted = cleanup_products(dynamodb, args.dry_run)
    events_deleted = cleanup_event(dynamodb, args.dry_run)

    # Phase 2: Seed
    print(f"\n{'─' * 60}")
    print("  PHASE 2: SEED DATA")
    print(f"{'─' * 60}")

    products_created = seed_products(dynamodb, args.dry_run)
    events_created = seed_event(dynamodb, args.dry_run)

    # Summary
    elapsed = time.time() - start_time
    print(f"\n{'═' * 60}")
    print("  📊 SUMMARY")
    print(f"{'═' * 60}")
    print(f"  Cleanup:")
    print(f"    Orders deleted:   {orders_deleted}")
    print(f"    Products deleted: {products_deleted}")
    print(f"    Events deleted:   {events_deleted}")
    print(f"  Seed:")
    print(f"    Products created: {products_created}")
    print(f"    Events created:   {events_created}")
    print(f"\n  ⏱️  Elapsed: {elapsed:.1f}s")

    if args.dry_run:
        print("\n  🔍 Dry run complete — no changes were made.")
        print("  Run without --dry-run to apply the seed.")
    else:
        print("\n  ✅ PM2027 seed complete!")
        print(f"  Event ID: {EVENT_ID_PM2027}")
        print(f"  Product IDs: {PRODUCT_ID_MEETING}, {PRODUCT_ID_PARTY}, {PRODUCT_ID_TSHIRT}, {PRODUCT_ID_TRANSFER}")


if __name__ == "__main__":
    main()
