#!/usr/bin/env python3
"""
seed-dynamodb-local.py — create the H-DCN tables in DynamoDB Local and insert
small, synthetic fixtures for the local backend testing (Tier 2) flow.

Part of the `local-backend-testing` spec (T2.4, R7.4/R7.5; guardrails:
financial fields as DynamoDB Number type).

What it does:
  - Connects to DynamoDB Local (default http://localhost:8000) using dummy
    credentials so it works fully offline against the local emulator, never
    real AWS.
  - Creates each table (PAY_PER_REQUEST / on-demand, matching prod conventions)
    with the correct primary key. Skips creation if the table already exists,
    unless --reset is passed (in which case it deletes + recreates).
  - Inserts a handful (2-5) of small SYNTHETIC items per table using EXACT
    Field Registry keys/types. No prod copy, no PII — obviously-fake values
    only (TEST-*, *@example.invalid, fake region codes).
  - Financial fields (prijs, price, unit_price, line_total, total_amount,
    total_paid, cost, revenue, ...) are written as DynamoDB Number type via
    Decimal(str(value)) — never bare strings, never floats.

Field Registry sources (frontend/src/config/):
  - Producten   : productFields/fields.ts   (parentFields + variantFields)
  - Members     : memberFields/fields/*     (personalFields, membershipFields — incl. `regio`)
  - Events      : eventFields/fields/*       (coreFields, financialFields)
  - Orders      : orderFields/fields/*       (identity/source/status/financial/items)
  - Payments    : NO frontend registry yet (steering: TODO). Minimal realistic
                  keys based on the table key schema (payment_id).
  - Memberships : NO frontend registry yet (steering: TODO). Minimal realistic
                  keys based on the table key schema (membership_id).
  - Counters    : utility table, no frontend config. Atomic counters for
                  order/invoice numbers. PK chosen as `counter_name` (see note
                  in COUNTERS_ITEMS).

Table key schemas (from steering aws-dynamodb):
  Members=member_id(S), Producten=product_id(S), Payments=payment_id(S),
  Events=event_id(S), Memberships=membership_id(S), Orders=order_id(S),
  Counters=(utility; PK `counter_name`(S) chosen here).

Usage:
  backend/.venv/bin/python scripts/local/seed-dynamodb-local.py [--reset]
      [--endpoint-url http://localhost:8000] [--region eu-west-1]
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# Table definitions: name -> primary key attribute (all String, all on-demand)
# ---------------------------------------------------------------------------
TABLES: dict[str, str] = {
    "Producten": "product_id",
    "Members": "member_id",
    "Payments": "payment_id",
    "Events": "event_id",
    "Memberships": "membership_id",
    "Orders": "order_id",
    # Counters is a utility table (atomic counters for order/invoice numbers).
    # No frontend registry exists; we pick `counter_name` as a sane string PK.
    "Counters": "counter_name",
}


def _money(value: str | int | float) -> Decimal:
    """Coerce a value to a DynamoDB Number (Decimal) safely.

    Financial fields MUST be stored as DynamoDB Number type — use
    Decimal(str(value)), never bare strings, never floats.
    """
    return Decimal(str(value))


# ---------------------------------------------------------------------------
# Synthetic fixtures — EXACT Field Registry keys. No PII, obviously-fake values.
# ---------------------------------------------------------------------------

# Producten — parentFields + variantFields (productFields/fields.ts).
# `prijs` is the price; registry stores it as string, but per guardrails +
# task it is seeded here as DynamoDB Number (Decimal).
PRODUCTEN_ITEMS: list[dict[str, Any]] = [
    {
        "product_id": "TEST-PROD-0001",
        "naam": "Test T-Shirt One",
        "artikelcode": "TST-01",
        "prijs": _money("19.95"),  # financial -> Number
        "groep": "Test",
        "subgroep": "T-Shirts",
        "images": [],
        "active": True,
        "is_parent": True,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    },
    {
        "product_id": "TEST-PROD-0001-VAR-M",
        "naam": "Test T-Shirt One",
        "prijs": _money("19.95"),  # financial -> Number
        "active": True,
        "is_parent": False,
        "parent_id": "TEST-PROD-0001",
        "variant_attributes": {"Maat": "M"},
        "stock": 10,
        "sold_count": 0,
        "allow_oversell": True,
    },
    {
        "product_id": "TEST-PROD-0002",
        "naam": "Test Pin Two",
        "artikelcode": "TST-02",
        "prijs": _money("3.50"),  # financial -> Number
        "groep": "Test",
        "subgroep": "Pins",
        "images": [],
        "active": True,
        "is_parent": True,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    },
]

# Members — personalFields + membershipFields. `regio` used for regional
# filtering. Fake, non-PII values only.
MEMBERS_ITEMS: list[dict[str, Any]] = [
    {
        "member_id": "TEST-0001",
        "voornaam": "Test",
        "achternaam": "Member One",
        "email": "test1@example.invalid",
        "geslacht": "X",
        "telefoon": "0600000001",
        "status": "Actief",
        "lidmaatschap": "Gewoon lid",
        "regio": "Utrecht",
        "lidnummer": 90001,
        "ingangsdatum": "2020-01-01",
    },
    {
        "member_id": "TEST-0002",
        "voornaam": "Test",
        "achternaam": "Member Two",
        "email": "test2@example.invalid",
        "geslacht": "X",
        "telefoon": "0600000002",
        "status": "Actief",
        "lidmaatschap": "Gezins lid",
        "regio": "Oost",
        "lidnummer": 90002,
        "ingangsdatum": "2021-06-15",
    },
]

# Events — coreFields + financialFields. `cost`/`revenue` are financial ->
# Number.
EVENTS_ITEMS: list[dict[str, Any]] = [
    {
        "event_id": "TEST-EVT-0001",
        "name": "Test Event One",
        "event_type": "Openingsrit",
        "event_category": "Ritten",
        "participation": "open",
        "linked_regio": "Utrecht",
        "status": "published",
        "location": "Test Location",
        "slug": "test-event-one",
        "description": "Synthetic test event.",
        "start_date": "2026-05-01",
        "end_date": "2026-05-01",
        "participants": 0,
        "cost": _money("0"),  # financial -> Number
        "revenue": _money("0"),  # financial -> Number
    },
    {
        "event_id": "TEST-EVT-0002",
        "name": "Test Event Two",
        "event_type": "ALV",
        "event_category": "Vergaderingen",
        "participation": "leden",
        "linked_regio": "Oost",
        "status": "draft",
        "location": "Test Hall",
        "slug": "test-event-two",
        "description": "Synthetic test event two.",
        "start_date": "2026-09-10",
        "end_date": "2026-09-10",
        "participants": 0,
        "cost": _money("125.00"),  # financial -> Number
        "revenue": _money("0"),  # financial -> Number
    },
]

# Orders — identity/source/status/financial/items. Financial fields
# (total_amount, total_paid, unit_price, line_total) -> Number.
ORDERS_ITEMS: list[dict[str, Any]] = [
    {
        "order_id": "TEST-ORD-0001",
        "order_number": "ORD-2026-0001",
        "member_id": "TEST-0001",
        "user_email": "test1@example.invalid",
        "source_id": "webshop",
        "status": "submitted",
        "payment_status": "unpaid",
        "version": 1,
        "total_amount": _money("23.45"),  # financial -> Number
        "total_paid": _money("0"),  # financial -> Number
        "items": [
            {
                "product_id": "TEST-PROD-0001",
                "variant_id": "TEST-PROD-0001-VAR-M",
                "quantity": 1,
                "unit_price": _money("19.95"),  # financial -> Number
                "line_total": _money("19.95"),  # financial -> Number
                "item_fields_data": {},
                "variant_attributes": {"Maat": "M"},
            },
            {
                "product_id": "TEST-PROD-0002",
                "variant_id": None,
                "quantity": 1,
                "unit_price": _money("3.50"),  # financial -> Number
                "line_total": _money("3.50"),  # financial -> Number
                "item_fields_data": {},
                "variant_attributes": {},
            },
        ],
    },
    {
        "order_id": "TEST-ORD-0002",
        "order_number": "ORD-2026-0002",
        "member_id": "TEST-0002",
        "user_email": "test2@example.invalid",
        "source_id": "webshop",
        "status": "draft",
        "payment_status": "unpaid",
        "version": 1,
        "total_amount": _money("3.50"),  # financial -> Number
        "total_paid": _money("0"),  # financial -> Number
        "items": [
            {
                "product_id": "TEST-PROD-0002",
                "variant_id": None,
                "quantity": 1,
                "unit_price": _money("3.50"),  # financial -> Number
                "line_total": _money("3.50"),  # financial -> Number
                "item_fields_data": {},
                "variant_attributes": {},
            },
        ],
    },
]

# Payments — NO frontend Field Registry yet (steering: TODO). Minimal realistic
# keys based on the payment_id PK. `amount` is financial -> Number.
PAYMENTS_ITEMS: list[dict[str, Any]] = [
    {
        "payment_id": "TEST-PAY-0001",
        "order_id": "TEST-ORD-0001",
        "member_id": "TEST-0001",
        "amount": _money("23.45"),  # financial -> Number
        "status": "pending",
        "created_at": "2026-01-02T00:00:00Z",
    },
    {
        "payment_id": "TEST-PAY-0002",
        "order_id": "TEST-ORD-0002",
        "member_id": "TEST-0002",
        "amount": _money("3.50"),  # financial -> Number
        "status": "pending",
        "created_at": "2026-01-02T00:00:00Z",
    },
]

# Memberships — NO frontend Field Registry yet (steering: TODO). Minimal
# realistic keys based on the membership_id PK.
MEMBERSHIPS_ITEMS: list[dict[str, Any]] = [
    {
        "membership_id": "TEST-MSHIP-0001",
        "name": "Gewoon lid",
        "active": True,
    },
    {
        "membership_id": "TEST-MSHIP-0002",
        "name": "Gezins lid",
        "active": True,
    },
]

# Counters — utility table, no frontend config. Atomic counters for
# order/invoice numbers. PK `counter_name` (chosen here). `value` is a plain
# integer counter (Number), not a financial amount.
COUNTERS_ITEMS: list[dict[str, Any]] = [
    {"counter_name": "order_number", "value": 2},
    {"counter_name": "invoice_number", "value": 0},
]

FIXTURES: dict[str, list[dict[str, Any]]] = {
    "Producten": PRODUCTEN_ITEMS,
    "Members": MEMBERS_ITEMS,
    "Payments": PAYMENTS_ITEMS,
    "Events": EVENTS_ITEMS,
    "Memberships": MEMBERSHIPS_ITEMS,
    "Orders": ORDERS_ITEMS,
    "Counters": COUNTERS_ITEMS,
}


def _dynamodb_resource(endpoint_url: str, region: str):
    """Build a boto3 DynamoDB resource pointing at DynamoDB Local.

    Dummy credentials are supplied so botocore can sign requests; DynamoDB
    Local ignores the signature. This never reaches real AWS.
    """
    return boto3.resource(
        "dynamodb",
        endpoint_url=endpoint_url,
        region_name=region,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
        aws_session_token="testing",
    )


def _table_exists(client, name: str) -> bool:
    try:
        client.describe_table(TableName=name)
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceNotFoundException":
            return False
        raise


def _delete_table(dynamodb, client, name: str) -> None:
    table = dynamodb.Table(name)
    table.delete()
    client.get_waiter("table_not_exists").wait(TableName=name)


def _create_table(dynamodb, client, name: str, pk: str) -> None:
    dynamodb.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": pk, "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": pk, "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",  # on-demand, matching prod conventions
    )
    client.get_waiter("table_exists").wait(TableName=name)


def seed(endpoint_url: str, region: str, reset: bool) -> int:
    dynamodb = _dynamodb_resource(endpoint_url, region)
    client = dynamodb.meta.client

    print(f"Seeding DynamoDB Local at {endpoint_url} (region {region})")
    print(f"  reset = {reset}\n")

    summary: list[tuple[str, str, int]] = []

    for name, pk in TABLES.items():
        exists = _table_exists(client, name)

        if exists and reset:
            print(f"[{name}] exists — deleting (reset)...")
            _delete_table(dynamodb, client, name)
            exists = False

        if not exists:
            print(f"[{name}] creating (PK={pk}, on-demand)...")
            _create_table(dynamodb, client, name, pk)
            created = "created"
        else:
            print(f"[{name}] already exists — skipping create.")
            created = "existed"

        table = dynamodb.Table(name)
        items = FIXTURES.get(name, [])
        for item in items:
            table.put_item(Item=item)

        summary.append((name, created, len(items)))
        print(f"[{name}] inserted {len(items)} synthetic item(s).\n")

    print("=" * 52)
    print("Seed summary")
    print("=" * 52)
    print(f"{'Table':<14}{'Status':<10}{'Items':>6}")
    print("-" * 52)
    for name, status, count in summary:
        print(f"{name:<14}{status:<10}{count:>6}")
    print("=" * 52)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create tables + insert synthetic fixtures in DynamoDB Local."
    )
    parser.add_argument(
        "--endpoint-url",
        default="http://localhost:8000",
        help="DynamoDB Local endpoint (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--region",
        default="eu-west-1",
        help="AWS region name (default: eu-west-1)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate tables if they already exist.",
    )
    args = parser.parse_args(argv)

    try:
        return seed(args.endpoint_url, args.region, args.reset)
    except Exception as exc:  # noqa: BLE001 — surface any failure to the CLI
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
