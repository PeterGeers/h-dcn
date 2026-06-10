#!/usr/bin/env python3
"""
Seed Test Data for H-DCN Test/Staging Environment

Creates test users in the shared Cognito pool and seeds DynamoDB test tables
with representative data.

Usage:
    python scripts/seed-test-data.py
    python scripts/seed-test-data.py --clear
    python scripts/seed-test-data.py --profile nonprofit-deploy

Requirements:
    - boto3 installed
    - AWS credentials configured (nonprofit-deploy profile)
    - Access to Cognito User Pool eu-west-1_fcUkvwjH5
    - DynamoDB test tables must already exist
"""

import argparse
import sys

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

COGNITO_USER_POOL_ID = "eu-west-1_fcUkvwjH5"
AWS_REGION = "eu-west-1"
TEST_PASSWORD = "Test1234!"

# Test user definitions — emails are HARD-CODED per user (not generated)
TEST_USERS = [
    {
        "username": "test-admin",
        "email": "webmaster+testadmin@h-dcn.nl",
        "groups": [
            "Products_CRUD",
            "Products_Export",
            "Products_Read",
            "Webshop_Management",
            "Members_Read",
            "Members_CRUD",
            "Members_Export",
            "Members_Status_Approve",
            "System_CRUD",
            "System_Logs_Read",
            "System_User_Management",
            "Communication_CRUD",
            "Communication_Read",
            "Communication_Export",
            "Events_CRUD",
            "Events_Read",
            "Events_Export",
            "Regio_All",
            "Regio_Pressmeet",
            "hdcnLeden",
        ],
    },
    {
        "username": "test-lid",
        "email": "peter+testlid@pgeers.nl",
        "groups": [
            "hdcnLeden",
            "Regio_Pressmeet",
            "club_test_presmeet",
        ],
    },
    {
        "username": "test-treasurer",
        "email": "peter+testtreasurer@jabaki.nl",
        "groups": [
            "Finance_CRUD",
            "Finance_Read",
            "hdcnLeden",
        ],
    },
    {
        "username": "test-presmeet",
        "email": "pjageers+testpresmeet@gmail.com",
        "groups": [
            "Regio_Pressmeet",
            "hdcnLeden",
        ],
    },
    {
        "username": "test-readonly",
        "email": "pjageers+testreadonly@gmail.com",
        "groups": [
            "Products_Read",
            "hdcnLeden",
        ],
    },
]


# DynamoDB test table definitions
# Each entry: table name, partition key field name
TEST_TABLES = [
    ("Members-Test", "member_id"),
    ("Producten-Test", "product_id"),
    ("Orders-Test", "order_id"),
    ("Payments-Test", "payment_id"),
    ("Events-Test", "event_id"),
    ("Memberships-Test", "membership_type_id"),
    ("Carts-Test", "cart_id"),
    ("Counters-Test", "counter_id"),
    ("StockMovements-Test", "movement_id"),
]


def generate_seed_data() -> dict:
    """
    Generate deterministic seed data for all test DynamoDB tables.

    Returns a dict mapping table name -> list of item dicts.
    All partition keys use format SEED-{table}-{index}.
    All identifiers use test- or SEED- prefixes.
    Each table with a status field has at least 2 distinct status values.

    This function is pure (no side effects) and can be imported for testing.
    """
    data = {}

    # --- Members-Test ---
    data["Members-Test"] = [
        {
            "member_id": "SEED-members-001",
            "email": "test-member-001@example.com",
            "first_name": "test-Jan",
            "last_name": "test-Jansen",
            "regio": "test-noord",
            "status": "active",
            "membership_type": "regular",
            "phone": "+31600000001",
        },
        {
            "member_id": "SEED-members-002",
            "email": "test-member-002@example.com",
            "first_name": "test-Piet",
            "last_name": "test-Pietersen",
            "regio": "test-zuid",
            "status": "active",
            "membership_type": "regular",
            "phone": "+31600000002",
        },
        {
            "member_id": "SEED-members-003",
            "email": "test-member-003@example.com",
            "first_name": "test-Klaas",
            "last_name": "test-Kansen",
            "regio": "test-oost",
            "status": "inactive",
            "membership_type": "honorary",
            "phone": "+31600000003",
        },
        {
            "member_id": "SEED-members-004",
            "email": "test-member-004@example.com",
            "first_name": "test-Marie",
            "last_name": "test-Mulder",
            "regio": "test-west",
            "status": "inactive",
            "membership_type": "regular",
            "phone": "+31600000004",
        },
        {
            "member_id": "SEED-members-005",
            "email": "test-member-005@example.com",
            "first_name": "test-Anna",
            "last_name": "test-Bakker",
            "regio": "test-noord",
            "status": "active",
            "membership_type": "regular",
            "phone": "+31600000005",
        },
    ]

    # --- Producten-Test ---
    data["Producten-Test"] = [
        {
            "product_id": "SEED-producten-001",
            "name": "test-T-shirt H-DCN Logo",
            "description": "Test product - black t-shirt",
            "price": "29.95",
            "category": "clothing",
            "status": "active",
            "stock": 100,
        },
        {
            "product_id": "SEED-producten-002",
            "name": "test-Pet H-DCN",
            "description": "Test product - cap with logo",
            "price": "19.95",
            "category": "clothing",
            "status": "active",
            "stock": 50,
        },
        {
            "product_id": "SEED-producten-003",
            "name": "test-Sticker Set",
            "description": "Test product - set of 5 stickers",
            "price": "7.50",
            "category": "accessories",
            "status": "inactive",
            "stock": 200,
        },
        {
            "product_id": "SEED-producten-004",
            "name": "test-Sleutelhanger",
            "description": "Test product - metal keychain",
            "price": "12.50",
            "category": "accessories",
            "status": "active",
            "stock": 75,
        },
        {
            "product_id": "SEED-producten-005",
            "name": "test-Jas H-DCN",
            "description": "Test product - club jacket",
            "price": "149.95",
            "category": "clothing",
            "status": "inactive",
            "stock": 0,
        },
    ]

    # --- Orders-Test ---
    data["Orders-Test"] = [
        {
            "order_id": "SEED-orders-001",
            "member_id": "SEED-members-001",
            "items": [{"product_id": "SEED-producten-001", "quantity": 2}],
            "total": "59.90",
            "status": "completed",
            "created_at": "2024-01-15T10:00:00Z",
        },
        {
            "order_id": "SEED-orders-002",
            "member_id": "SEED-members-002",
            "items": [{"product_id": "SEED-producten-002", "quantity": 1}],
            "total": "19.95",
            "status": "pending",
            "created_at": "2024-01-16T11:30:00Z",
        },
        {
            "order_id": "SEED-orders-003",
            "member_id": "SEED-members-003",
            "items": [
                {"product_id": "SEED-producten-003", "quantity": 3},
                {"product_id": "SEED-producten-004", "quantity": 1},
            ],
            "total": "35.00",
            "status": "completed",
            "created_at": "2024-01-17T09:15:00Z",
        },
        {
            "order_id": "SEED-orders-004",
            "member_id": "SEED-members-004",
            "items": [{"product_id": "SEED-producten-005", "quantity": 1}],
            "total": "149.95",
            "status": "cancelled",
            "created_at": "2024-01-18T14:00:00Z",
        },
        {
            "order_id": "SEED-orders-005",
            "member_id": "SEED-members-005",
            "items": [{"product_id": "SEED-producten-001", "quantity": 1}],
            "total": "29.95",
            "status": "pending",
            "created_at": "2024-01-19T16:45:00Z",
        },
    ]

    # --- Payments-Test ---
    data["Payments-Test"] = [
        {
            "payment_id": "SEED-payments-001",
            "order_id": "SEED-orders-001",
            "member_id": "SEED-members-001",
            "amount": "59.90",
            "currency": "EUR",
            "status": "succeeded",
            "stripe_id": "test-pi_001",
            "created_at": "2024-01-15T10:05:00Z",
        },
        {
            "payment_id": "SEED-payments-002",
            "order_id": "SEED-orders-002",
            "member_id": "SEED-members-002",
            "amount": "19.95",
            "currency": "EUR",
            "status": "pending",
            "stripe_id": "test-pi_002",
            "created_at": "2024-01-16T11:35:00Z",
        },
        {
            "payment_id": "SEED-payments-003",
            "order_id": "SEED-orders-003",
            "member_id": "SEED-members-003",
            "amount": "35.00",
            "currency": "EUR",
            "status": "succeeded",
            "stripe_id": "test-pi_003",
            "created_at": "2024-01-17T09:20:00Z",
        },
        {
            "payment_id": "SEED-payments-004",
            "order_id": "SEED-orders-004",
            "member_id": "SEED-members-004",
            "amount": "149.95",
            "currency": "EUR",
            "status": "refunded",
            "stripe_id": "test-pi_004",
            "created_at": "2024-01-18T14:05:00Z",
        },
        {
            "payment_id": "SEED-payments-005",
            "order_id": "SEED-orders-005",
            "member_id": "SEED-members-005",
            "amount": "29.95",
            "currency": "EUR",
            "status": "pending",
            "stripe_id": "test-pi_005",
            "created_at": "2024-01-19T16:50:00Z",
        },
    ]

    # --- Events-Test ---
    data["Events-Test"] = [
        {
            "event_id": "SEED-events-001",
            "title": "test-Nieuwjaarsrit 2024",
            "description": "Test event - new year ride",
            "date": "2024-01-06",
            "location": "test-Amsterdam",
            "status": "published",
            "max_participants": 50,
        },
        {
            "event_id": "SEED-events-002",
            "title": "test-Voorjaarsmeeting",
            "description": "Test event - spring meeting",
            "date": "2024-03-15",
            "location": "test-Utrecht",
            "status": "draft",
            "max_participants": 100,
        },
        {
            "event_id": "SEED-events-003",
            "title": "test-Zomerrit Zuid",
            "description": "Test event - summer ride south",
            "date": "2024-06-20",
            "location": "test-Maastricht",
            "status": "published",
            "max_participants": 30,
        },
        {
            "event_id": "SEED-events-004",
            "title": "test-Herfstdag Oost",
            "description": "Test event - autumn day east",
            "date": "2024-09-28",
            "location": "test-Arnhem",
            "status": "cancelled",
            "max_participants": 40,
        },
        {
            "event_id": "SEED-events-005",
            "title": "test-Kerstdiner",
            "description": "Test event - christmas dinner",
            "date": "2024-12-21",
            "location": "test-Den Haag",
            "status": "draft",
            "max_participants": 80,
        },
    ]

    # --- Memberships-Test ---
    data["Memberships-Test"] = [
        {
            "membership_type_id": "SEED-memberships-001",
            "name": "test-Regulier Lid",
            "description": "Test membership type - regular member",
            "fee": "50.00",
            "duration_months": 12,
            "status": "active",
        },
        {
            "membership_type_id": "SEED-memberships-002",
            "name": "test-Erelid",
            "description": "Test membership type - honorary member",
            "fee": "0.00",
            "duration_months": 0,
            "status": "active",
        },
        {
            "membership_type_id": "SEED-memberships-003",
            "name": "test-Gezinslid",
            "description": "Test membership type - family member",
            "fee": "25.00",
            "duration_months": 12,
            "status": "active",
        },
        {
            "membership_type_id": "SEED-memberships-004",
            "name": "test-Proeflidmaatschap",
            "description": "Test membership type - trial membership",
            "fee": "10.00",
            "duration_months": 3,
            "status": "inactive",
        },
        {
            "membership_type_id": "SEED-memberships-005",
            "name": "test-Jeugdlid",
            "description": "Test membership type - youth member",
            "fee": "20.00",
            "duration_months": 12,
            "status": "inactive",
        },
    ]

    # --- Carts-Test ---
    data["Carts-Test"] = [
        {
            "cart_id": "SEED-carts-001",
            "member_id": "SEED-members-001",
            "items": [{"product_id": "SEED-producten-001", "quantity": 1}],
            "status": "active",
            "created_at": "2024-01-20T08:00:00Z",
        },
        {
            "cart_id": "SEED-carts-002",
            "member_id": "SEED-members-002",
            "items": [
                {"product_id": "SEED-producten-002", "quantity": 2},
                {"product_id": "SEED-producten-003", "quantity": 1},
            ],
            "status": "active",
            "created_at": "2024-01-20T09:00:00Z",
        },
        {
            "cart_id": "SEED-carts-003",
            "member_id": "SEED-members-003",
            "items": [{"product_id": "SEED-producten-004", "quantity": 1}],
            "status": "abandoned",
            "created_at": "2024-01-18T12:00:00Z",
        },
        {
            "cart_id": "SEED-carts-004",
            "member_id": "SEED-members-004",
            "items": [],
            "status": "abandoned",
            "created_at": "2024-01-15T14:00:00Z",
        },
        {
            "cart_id": "SEED-carts-005",
            "member_id": "SEED-members-005",
            "items": [{"product_id": "SEED-producten-005", "quantity": 1}],
            "status": "active",
            "created_at": "2024-01-21T10:30:00Z",
        },
    ]

    # --- Counters-Test (≥2 items) ---
    data["Counters-Test"] = [
        {
            "counter_id": "SEED-counters-001",
            "name": "test-order-number",
            "value": 1000,
        },
        {
            "counter_id": "SEED-counters-002",
            "name": "test-member-number",
            "value": 5000,
        },
    ]

    # --- StockMovements-Test ---
    data["StockMovements-Test"] = [
        {
            "movement_id": "SEED-stockmovements-001",
            "product_id": "SEED-producten-001",
            "quantity": 50,
            "type": "inbound",
            "reason": "test-initial stock",
            "created_at": "2024-01-01T08:00:00Z",
        },
        {
            "movement_id": "SEED-stockmovements-002",
            "product_id": "SEED-producten-001",
            "quantity": -2,
            "type": "outbound",
            "reason": "test-order SEED-orders-001",
            "created_at": "2024-01-15T10:05:00Z",
        },
        {
            "movement_id": "SEED-stockmovements-003",
            "product_id": "SEED-producten-002",
            "quantity": 30,
            "type": "inbound",
            "reason": "test-restock",
            "created_at": "2024-01-10T09:00:00Z",
        },
        {
            "movement_id": "SEED-stockmovements-004",
            "product_id": "SEED-producten-003",
            "quantity": -3,
            "type": "outbound",
            "reason": "test-order SEED-orders-003",
            "created_at": "2024-01-17T09:20:00Z",
        },
        {
            "movement_id": "SEED-stockmovements-005",
            "product_id": "SEED-producten-004",
            "quantity": 20,
            "type": "inbound",
            "reason": "test-initial stock",
            "created_at": "2024-01-02T08:00:00Z",
        },
    ]

    return data


# ---------------------------------------------------------------------------
# CognitoSeeder
# ---------------------------------------------------------------------------


class CognitoSeeder:
    """Creates test users in the shared Cognito pool, sets passwords, and assigns groups."""

    def __init__(self, session: boto3.Session):
        self.client = session.client("cognito-idp", region_name=AWS_REGION)
        self.user_pool_id = COGNITO_USER_POOL_ID
        self.created = 0
        self.skipped = 0

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def seed(self, clear: bool = False) -> None:
        """Create all test users. If *clear* is True, delete them first."""
        if clear:
            self._clear_users()

        for user_cfg in TEST_USERS:
            self._ensure_user(user_cfg)

    def print_summary(self) -> None:
        """Print a summary of seeding results."""
        print("\n--- Cognito seeding summary ---")
        print(f"  Users created: {self.created}")
        print(f"  Users skipped (already exist): {self.skipped}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _user_exists(self, username: str) -> bool:
        try:
            self.client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=username,
            )
            return True
        except self.client.exceptions.UserNotFoundException:
            return False

    def _ensure_user(self, user_cfg: dict) -> None:
        username = user_cfg["username"]
        email = user_cfg["email"]
        groups = user_cfg["groups"]

        # Pool uses UsernameAttributes=["email"], so we must use email as username
        # The "username" field is kept for display/logging purposes
        if self._user_exists(email):
            print(f"  [skip] {username} ({email}) already exists")
            self.skipped += 1
            return

        # Create user — use email as Username (required by pool config)
        self.client.admin_create_user(
            UserPoolId=self.user_pool_id,
            Username=email,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "preferred_username", "Value": username},
            ],
            MessageAction="SUPPRESS",
        )

        # Set permanent password (avoids FORCE_CHANGE_PASSWORD state)
        self.client.admin_set_user_password(
            UserPoolId=self.user_pool_id,
            Username=email,
            Password=TEST_PASSWORD,
            Permanent=True,
        )

        # Assign groups
        for group in groups:
            try:
                self.client.admin_add_user_to_group(
                    UserPoolId=self.user_pool_id,
                    Username=email,
                    GroupName=group,
                )
            except ClientError as exc:
                # Group might not exist yet — log and continue
                print(f"  [warn] Could not add {username} to group {group}: {exc}")

        print(f"  [created] {username} ({email}) -> {len(groups)} groups")
        self.created += 1

    def _clear_users(self) -> None:
        """Delete all test users so they can be recreated cleanly."""
        print("Clearing existing test users...")
        for user_cfg in TEST_USERS:
            username = user_cfg["username"]
            email = user_cfg["email"]
            try:
                self.client.admin_delete_user(
                    UserPoolId=self.user_pool_id,
                    Username=email,
                )
                print(f"  [deleted] {username} ({email})")
            except self.client.exceptions.UserNotFoundException:
                pass
            except ClientError as exc:
                print(f"  [warn] Could not delete {username}: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# DynamoDBSeeder
# ---------------------------------------------------------------------------


class DynamoDBSeeder:
    """Seeds DynamoDB test tables with deterministic data."""

    def __init__(self, session: boto3.Session):
        self.dynamodb = session.resource("dynamodb", region_name=AWS_REGION)
        self.results: list[dict] = []  # {table, items_written, skipped, error}

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def seed(self, clear: bool = False) -> None:
        """Seed all test tables. If *clear* is True, delete existing items first."""
        seed_data = generate_seed_data()

        for table_name, partition_key in TEST_TABLES:
            items = seed_data.get(table_name, [])
            self._seed_table(table_name, partition_key, items, clear)

    def print_summary(self) -> None:
        """Print a summary of DynamoDB seeding results."""
        print("\n--- DynamoDB seeding summary ---")
        for result in self.results:
            if result.get("error"):
                print(f"  {result['table']}: SKIPPED ({result['error']})")
            else:
                print(f"  {result['table']}: {result['items_written']} items written")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _table_exists(self, table_name: str):
        """Check if a table exists and return the Table resource, or None."""
        table = self.dynamodb.Table(table_name)
        try:
            table.load()
            return table
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ResourceNotFoundException":
                return None
            raise

    def _seed_table(
        self, table_name: str, partition_key: str, items: list, clear: bool
    ) -> None:
        """Seed a single table, handling missing tables gracefully."""
        table = self._table_exists(table_name)

        if table is None:
            msg = f"Table '{table_name}' does not exist"
            if clear:
                print(f"  [warn] --clear: {msg}, skipping", file=sys.stderr)
            else:
                print(f"  [error] {msg}, skipping", file=sys.stderr)
            self.results.append(
                {"table": table_name, "items_written": 0, "skipped": True, "error": msg}
            )
            return

        if clear:
            self._clear_table(table, partition_key)

        # Write items
        items_written = 0
        with table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=item)
                items_written += 1

        self.results.append(
            {"table": table_name, "items_written": items_written, "skipped": False, "error": None}
        )
        print(f"  [seeded] {table_name}: {items_written} items")

    def _clear_table(self, table, partition_key: str) -> None:
        """Scan all items from a table and delete them in batches."""
        print(f"  [clear] Scanning {table.name}...")
        # Determine key schema for deletion
        key_names = [k["AttributeName"] for k in table.key_schema]

        deleted = 0
        scan_kwargs = {}
        while True:
            response = table.scan(**scan_kwargs)
            items = response.get("Items", [])
            if not items:
                break

            with table.batch_writer() as batch:
                for item in items:
                    key = {k: item[k] for k in key_names if k in item}
                    batch.delete_item(Key=key)
                    deleted += 1

            # Handle pagination
            if "LastEvaluatedKey" in response:
                scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            else:
                break

        print(f"  [clear] Deleted {deleted} items from {table.name}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed test data for the H-DCN test/staging environment."
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete existing test users/data before seeding",
    )
    parser.add_argument(
        "--profile",
        default="nonprofit-deploy",
        help="AWS profile to use (default: nonprofit-deploy)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Create boto3 session with the specified profile
    try:
        session = boto3.Session(profile_name=args.profile, region_name=AWS_REGION)
    except NoCredentialsError:
        print(
            f"ERROR: AWS credentials not found for profile '{args.profile}'.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Using AWS profile: {args.profile}")
    print(f"Cognito User Pool: {COGNITO_USER_POOL_ID}")
    print()

    # --- Cognito seeding ---
    print("=== Seeding Cognito test users ===")
    cognito_seeder = CognitoSeeder(session)
    try:
        cognito_seeder.seed(clear=args.clear)
    except NoCredentialsError:
        print("ERROR: AWS credentials expired or invalid.", file=sys.stderr)
        sys.exit(1)
    except ClientError as exc:
        print(f"ERROR: AWS API error: {exc}", file=sys.stderr)
        sys.exit(1)

    cognito_seeder.print_summary()

    # --- DynamoDB seeding ---
    print("\n=== Seeding DynamoDB test tables ===")
    dynamo_seeder = DynamoDBSeeder(session)
    try:
        dynamo_seeder.seed(clear=args.clear)
    except NoCredentialsError:
        print("ERROR: AWS credentials expired or invalid.", file=sys.stderr)
        sys.exit(1)
    except ClientError as exc:
        print(f"ERROR: AWS API error during DynamoDB seeding: {exc}", file=sys.stderr)
        sys.exit(1)

    dynamo_seeder.print_summary()

    print("\nDone.")


if __name__ == "__main__":
    main()
