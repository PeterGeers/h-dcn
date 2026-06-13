#!/usr/bin/env python3
"""
Seed event-booking test data into the test environment.

Creates test events, products, and updates test members with `allowed_events`
to enable end-to-end testing of the generic event booking system.

This script is idempotent — safe to run multiple times. All items use
deterministic IDs and are written with put_item (upsert).

Tables affected:
    - Events-Test   (PK: event_id)    — 2 event records created
    - Producten-Test (PK: product_id) — 5 product records created
    - Members-Test  (PK: member_id)   — 3 member records updated (allowed_events)

Prerequisites:
    - AWS profile `nonprofit-deploy` configured
    - Tables must exist in eu-west-1
    - Members SEED-admin-001, SEED-members-001, SEED-members-002 must exist

Usage:
    # Seed test data (test environment)
    python backend/scripts/seed_event_test_data.py --stage test

    # Clear test seed data before re-seeding
    python backend/scripts/seed_event_test_data.py --stage test --clear

    # Preview with a different profile
    python backend/scripts/seed_event_test_data.py --stage test --profile nonprofit-admin
"""

import argparse
import sys
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError


REGION = "eu-west-1"
PROFILE = "nonprofit-deploy"

STAGE_TABLE_MAP = {
    "test": {
        "events": "Events-Test",
        "products": "Producten-Test",
        "members": "Members-Test",
    },
    "prod": {
        "events": "Events",
        "products": "Producten",
        "members": "Members",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Deterministic test IDs
# ─────────────────────────────────────────────────────────────────────────────

EVENT_PRESMEET = "test-event-presmeet-2027"
EVENT_RALLY = "test-event-rally-2027"

PRODUCT_DINNER = "test-product-dinner"
PRODUCT_TSHIRT = "test-product-tshirt"
PRODUCT_PARKING = "test-product-parking"
PRODUCT_RALLY_TICKET = "test-product-rally-ticket"
PRODUCT_CAMPING = "test-product-camping"

MEMBER_ADMIN = "SEED-admin-001"
MEMBER_001 = "SEED-members-001"
MEMBER_002 = "SEED-members-002"

# ─────────────────────────────────────────────────────────────────────────────
# Event definitions
# ─────────────────────────────────────────────────────────────────────────────

EVENTS = [
    {
        "event_id": EVENT_PRESMEET,
        "name": "Presidents Meeting 2027",
        "event_type": "presmeet",
        "status": "open",
        "order_scope": "club",
        "registration_open": "2025-01-01",
        "registration_close": "2027-05-01",
        "start_date": "2027-06-01",
        "end_date": "2027-06-03",
        "product_ids": [PRODUCT_DINNER, PRODUCT_TSHIRT, PRODUCT_PARKING],
        "constraints": [
            {"type": "max_per_club", "field": "total_persons", "max": 10},
            {"type": "max_per_event", "field": "total_persons", "max": 200},
        ],
    },
    {
        "event_id": EVENT_RALLY,
        "name": "Summer Rally 2027",
        "event_type": "rally",
        "status": "open",
        "order_scope": "member",
        "registration_open": "2025-01-01",
        "registration_close": "2027-08-01",
        "start_date": "2027-08-15",
        "end_date": "2027-08-17",
        "product_ids": [PRODUCT_RALLY_TICKET, PRODUCT_CAMPING],
        "constraints": [
            {"type": "max_per_member", "field": "total_persons", "max": 4},
            {"type": "max_per_event", "field": "total_persons", "max": 500},
        ],
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Product definitions
# ─────────────────────────────────────────────────────────────────────────────

PRODUCTS = [
    {
        "product_id": PRODUCT_DINNER,
        "name": "Gala Dinner",
        "price": Decimal("75.00"),
        "status": "active",
        "purchase_rules": {
            "max_per_club": 10,
            "order_mode": "persistent",
        },
        "order_item_fields": [
            {"id": "name", "label": "Name", "type": "text", "required": True},
            {
                "id": "dietary",
                "label": "Dietary requirements",
                "type": "text",
                "required": False,
            },
        ],
    },
    {
        "product_id": PRODUCT_TSHIRT,
        "name": "Event T-shirt",
        "price": Decimal("25.00"),
        "status": "active",
        "purchase_rules": {
            "max_per_club": 10,
            "order_mode": "persistent",
        },
        "order_item_fields": [
            {"id": "name", "label": "Name", "type": "text", "required": True},
        ],
        "variant_schema": [
            {"name": "Size", "values": ["S", "M", "L", "XL"]},
        ],
    },
    {
        "product_id": PRODUCT_PARKING,
        "name": "Parking Pass",
        "price": Decimal("15.00"),
        "status": "active",
        "purchase_rules": {
            "max_per_club": 5,
            "order_mode": "persistent",
        },
        "order_item_fields": [
            {"id": "license_plate", "label": "License plate", "type": "text", "required": True},
        ],
    },
    {
        "product_id": PRODUCT_RALLY_TICKET,
        "name": "Rally Ticket",
        "price": Decimal("50.00"),
        "status": "active",
        "purchase_rules": {
            "max_per_member": 4,
            "order_mode": "persistent",
        },
        "order_item_fields": [
            {"id": "name", "label": "Name", "type": "text", "required": True},
            {"id": "phone", "label": "Phone", "type": "text", "required": True},
        ],
    },
    {
        "product_id": PRODUCT_CAMPING,
        "name": "Camping Spot",
        "price": Decimal("30.00"),
        "status": "active",
        "purchase_rules": {
            "max_per_member": 2,
            "order_mode": "persistent",
        },
        "order_item_fields": [
            {"id": "tent_size", "label": "Tent size (persons)", "type": "number", "required": True},
        ],
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Member updates (allowed_events)
# ─────────────────────────────────────────────────────────────────────────────

MEMBER_UPDATES = [
    {
        "member_id": MEMBER_ADMIN,
        "allowed_events": [EVENT_PRESMEET, EVENT_RALLY],
    },
    {
        "member_id": MEMBER_001,
        "allowed_events": [EVENT_PRESMEET],
        "club_id": "test-club-001",
    },
    {
        "member_id": MEMBER_002,
        "allowed_events": [EVENT_RALLY],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────


def get_table_names(stage: str) -> dict:
    """Map stage to DynamoDB table names."""
    if stage not in STAGE_TABLE_MAP:
        print(f"❌ Invalid stage '{stage}'. Must be 'test' or 'prod'.")
        sys.exit(1)
    return STAGE_TABLE_MAP[stage]


def get_session(profile: str = PROFILE) -> boto3.Session:
    """Create a boto3 session with the specified profile."""
    return boto3.Session(profile_name=profile, region_name=REGION)


# ─────────────────────────────────────────────────────────────────────────────
# Seed functions
# ─────────────────────────────────────────────────────────────────────────────


def seed_events(session: boto3.Session, table_name: str) -> int:
    """Seed event records into the Events table."""
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    print(f"\n📅 Seeding events into '{table_name}'...")

    count = 0
    for event in EVENTS:
        try:
            table.put_item(Item=event)
            print(f"   ✅ {event['event_id']}: {event['name']} (scope={event['order_scope']})")
            count += 1
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            print(f"   ❌ Failed to seed event '{event['event_id']}': [{error_code}] {error_message}")

    return count


def seed_products(session: boto3.Session, table_name: str) -> int:
    """Seed product records into the Producten table."""
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    print(f"\n🛍️  Seeding products into '{table_name}'...")

    count = 0
    for product in PRODUCTS:
        try:
            table.put_item(Item=product)
            has_variants = "variant_schema" in product
            variant_info = " (with variants)" if has_variants else ""
            print(f"   ✅ {product['product_id']}: {product['name']} — €{product['price']}{variant_info}")
            count += 1
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            print(f"   ❌ Failed to seed product '{product['product_id']}': [{error_code}] {error_message}")

    return count


def update_members(session: boto3.Session, table_name: str) -> int:
    """Update test members with allowed_events (and optionally club_id)."""
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    print(f"\n👤 Updating members in '{table_name}' with allowed_events...")

    count = 0
    for update in MEMBER_UPDATES:
        member_id = update["member_id"]
        allowed_events = update["allowed_events"]

        # Build update expression
        update_expr = "SET allowed_events = :events"
        expr_values = {":events": allowed_events}

        if "club_id" in update:
            update_expr += ", club_id = :club_id"
            expr_values[":club_id"] = update["club_id"]

        try:
            table.update_item(
                Key={"member_id": member_id},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values,
            )
            extras = f", club_id={update['club_id']}" if "club_id" in update else ""
            print(f"   ✅ {member_id}: allowed_events={allowed_events}{extras}")
            count += 1
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            print(f"   ❌ Failed to update member '{member_id}': [{error_code}] {error_message}")

    return count


# ─────────────────────────────────────────────────────────────────────────────
# Clear functions
# ─────────────────────────────────────────────────────────────────────────────


def clear_events(session: boto3.Session, table_name: str) -> int:
    """Delete seeded test events from the Events table."""
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    print(f"\n🗑️  Clearing test events from '{table_name}'...")

    count = 0
    for event in EVENTS:
        event_id = event["event_id"]
        try:
            table.delete_item(Key={"event_id": event_id})
            print(f"   🗑️  Deleted: {event_id}")
            count += 1
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            print(f"   ❌ Failed to delete event '{event_id}': [{error_code}] {error_message}")

    return count


def clear_products(session: boto3.Session, table_name: str) -> int:
    """Delete seeded test products from the Producten table."""
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    print(f"\n🗑️  Clearing test products from '{table_name}'...")

    count = 0
    for product in PRODUCTS:
        product_id = product["product_id"]
        try:
            table.delete_item(Key={"product_id": product_id})
            print(f"   🗑️  Deleted: {product_id}")
            count += 1
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            print(f"   ❌ Failed to delete product '{product_id}': [{error_code}] {error_message}")

    return count


def clear_member_events(session: boto3.Session, table_name: str) -> int:
    """Remove allowed_events from test members."""
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    print(f"\n🗑️  Clearing allowed_events from test members in '{table_name}'...")

    count = 0
    for update in MEMBER_UPDATES:
        member_id = update["member_id"]
        try:
            table.update_item(
                Key={"member_id": member_id},
                UpdateExpression="SET allowed_events = :empty",
                ExpressionAttributeValues={":empty": []},
            )
            print(f"   🗑️  Cleared: {member_id}")
            count += 1
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            print(f"   ❌ Failed to clear member '{member_id}': [{error_code}] {error_message}")

    return count


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Seed event-booking test data into the test environment. "
            "Creates test events, products, and updates member records."
        )
    )
    parser.add_argument(
        "--stage",
        required=True,
        choices=["test", "prod"],
        help="Target stage: 'test' → *-Test tables, 'prod' → production tables",
    )
    parser.add_argument(
        "--profile",
        default=PROFILE,
        help=f"AWS CLI profile to use (default: {PROFILE})",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete test seed data before re-seeding",
    )
    args = parser.parse_args()

    tables = get_table_names(args.stage)
    session = get_session(args.profile)

    print("=" * 60)
    print("🌱 Event Booking Test Data Seeder")
    print("=" * 60)
    print(f"   Stage:   {args.stage}")
    print(f"   Profile: {args.profile}")
    print(f"   Region:  {REGION}")
    print(f"   Tables:")
    print(f"     Events:   {tables['events']}")
    print(f"     Products: {tables['products']}")
    print(f"     Members:  {tables['members']}")
    print("=" * 60)

    # --- Clear (if requested) ---
    if args.clear:
        print("\n" + "─" * 60)
        print("🗑️  CLEARING existing test seed data...")
        print("─" * 60)

        cleared_events = clear_events(session, tables["events"])
        cleared_products = clear_products(session, tables["products"])
        cleared_members = clear_member_events(session, tables["members"])

        print(f"\n   Cleared: {cleared_events} events, {cleared_products} products, {cleared_members} member updates")

    # --- Seed ---
    print("\n" + "─" * 60)
    print("🌱 SEEDING test data...")
    print("─" * 60)

    seeded_events = seed_events(session, tables["events"])
    seeded_products = seed_products(session, tables["products"])
    seeded_members = update_members(session, tables["members"])

    # --- Summary ---
    print("\n" + "=" * 60)
    print("✅ Seeding complete!")
    print("=" * 60)
    print(f"   Events seeded:   {seeded_events} / {len(EVENTS)}")
    print(f"   Products seeded: {seeded_products} / {len(PRODUCTS)}")
    print(f"   Members updated: {seeded_members} / {len(MEMBER_UPDATES)}")
    print()
    print("   Events:")
    for event in EVENTS:
        print(f"     • {event['event_id']} ({event['order_scope']} scope)")
    print("   Products:")
    for product in PRODUCTS:
        print(f"     • {product['product_id']}: {product['name']}")
    print("   Members:")
    for update in MEMBER_UPDATES:
        print(f"     • {update['member_id']}: events={update['allowed_events']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
