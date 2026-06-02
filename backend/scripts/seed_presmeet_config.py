#!/usr/bin/env python3
"""
Seed Product_Type_Config records for PresMeet into the Producten table.

Inserts 4 config records with product_id prefix 'config_presmeet_*' and source 'presmeet_config'.
Safe to run multiple times — put_item overwrites existing records with the same key.

Usage:
    python backend/scripts/seed_presmeet_config.py
    python backend/scripts/seed_presmeet_config.py --profile nonprofit-deploy
"""

import argparse
from decimal import Decimal

import boto3


REGION = "eu-west-1"
TABLE_NAME = "Producten"

CONFIG_RECORDS = [
    {
        "product_id": "config_presmeet_meeting_ticket",
        "product_type": "meeting_ticket",
        "source": "presmeet_config",
        "max_per_club": 3,
        "min_per_club": 1,
        "unit_price": Decimal("50.00"),
        "required_attributes": {
            "name": {
                "type": "string",
                "required": True,
                "min_length": 1,
                "max_length": 100,
            },
            "role": {
                "type": "string",
                "required": True,
                "min_length": 1,
                "max_length": 100,
            },
        },
    },
    {
        "product_id": "config_presmeet_party_ticket",
        "product_type": "party_ticket",
        "source": "presmeet_config",
        "max_per_club": 13,
        "min_per_club": 0,
        "unit_price": Decimal("99.50"),
        "required_attributes": {
            "name": {
                "type": "string",
                "required": True,
                "min_length": 1,
                "max_length": 100,
            },
            "person_type": {
                "type": "string",
                "required": True,
                "enum": ["delegate", "guest"],
            },
        },
    },
    {
        "product_id": "config_presmeet_tshirt",
        "product_type": "tshirt",
        "source": "presmeet_config",
        "max_per_club": 13,
        "min_per_club": 0,
        "unit_price": Decimal("25.00"),
        "required_attributes": {
            "name": {
                "type": "string",
                "required": True,
                "min_length": 1,
                "max_length": 100,
            },
            "gender": {
                "type": "string",
                "required": True,
                "enum": ["male", "female"],
            },
            "size": {
                "type": "string",
                "required": True,
                "enum": ["S", "M", "L", "XL", "XXL", "3XL", "4XL"],
            },
        },
    },
    {
        "product_id": "config_presmeet_airport_transfer",
        "product_type": "airport_transfer",
        "source": "presmeet_config",
        "max_per_club": 20,
        "min_per_club": 0,
        "unit_price": Decimal("5.00"),
        "required_attributes": {
            "direction": {
                "type": "string",
                "required": True,
                "enum": ["pickup", "dropoff"],
            },
            "airport": {
                "type": "string",
                "required": True,
                "enum": ["AMS", "RTM", "EIN"],
            },
            "flight": {
                "type": "string",
                "required": True,
                "min_length": 2,
                "max_length": 10,
            },
            "date": {
                "type": "string",
                "required": True,
            },
            "time": {
                "type": "string",
                "required": True,
            },
            "persons": {
                "type": "integer",
                "required": True,
                "minimum": 1,
                "maximum": 50,
            },
        },
    },
]


def seed_presmeet_config(profile: str | None = None) -> None:
    """Insert PresMeet Product_Type_Config records into the Producten table."""
    session_kwargs = {"region_name": REGION}
    if profile:
        session_kwargs["profile_name"] = profile

    session = boto3.Session(**session_kwargs)
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    print(f"🔧 Seeding PresMeet config into '{TABLE_NAME}' table (region: {REGION})")
    if profile:
        print(f"   Using profile: {profile}")
    print()

    for record in CONFIG_RECORDS:
        product_id = record["product_id"]
        product_type = record["product_type"]

        table.put_item(Item=record)
        print(
            f"  ✅ {product_id} "
            f"(type={product_type}, "
            f"max={record['max_per_club']}, "
            f"min={record['min_per_club']}, "
            f"price=€{record['unit_price']})"
        )

    print()
    print(f"🎉 Done! Inserted {len(CONFIG_RECORDS)} config records.")
    print("   Records are idempotent — re-running this script is safe.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed PresMeet Product_Type_Config records into Producten table"
    )
    parser.add_argument(
        "--profile",
        default="nonprofit-deploy",
        help="AWS CLI profile to use (default: nonprofit-deploy)",
    )
    args = parser.parse_args()

    seed_presmeet_config(profile=args.profile)
