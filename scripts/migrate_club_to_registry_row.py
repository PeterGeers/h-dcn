#!/usr/bin/env python3
"""
Club to Registry Row Migration Script.

Replaces club_id with registry_row_id across Orders, Members, Payments,
Producten, and Events tables. Resolves registry_row_label and
registry_row_logo_url from the S3 registry file for Orders and Payments.

Tables and fields:
  - Orders: club_id → registry_row_id + registry_row_label + registry_row_logo_url
  - Members: club_id → registry_row_id (no label/logo)
  - Payments: club_id → registry_row_id + registry_row_label + registry_row_logo_url
  - Producten: purchase_rules.max_per_club → max_per_order, min_per_club → min_per_order
  - Events: remove order_scope field, rename counting_rule values

Behavior:
  - --dry-run: preview changes without writing to DynamoDB
  - --validate: verify all records have registry_row_id and no club_id remains
  - --remove-old-fields: remove old club_id fields after successful validation
  - Idempotent: records already containing registry_row_id are skipped
  - Handles DynamoDB pagination (LastEvaluatedKey)

Usage:
    # Dry-run
    python scripts/migrate_club_to_registry_row.py --stage test --dry-run

    # Apply changes
    python scripts/migrate_club_to_registry_row.py --stage test

    # Validate migration
    python scripts/migrate_club_to_registry_row.py --stage test --validate

    # Remove old fields after validation
    python scripts/migrate_club_to_registry_row.py --stage test --remove-old-fields
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import TypedDict, NotRequired

import boto3

REGION = "eu-west-1"
DEFAULT_PROFILE = "nonprofit-deploy"
S3_BUCKET = "h-dcn-reports"
S3_REGISTRY_KEY = "presmeet/club_registry.json"

# Table names per stage
TABLE_NAMES = {
    "test": {
        "orders": "Orders-Test",
        "members": "Members-Test",
        "payments": "Payments-Test",
        "producten": "Producten-Test",
        "events": "Events-Test",
    },
    "prod": {
        "orders": "Orders",
        "members": "Members",
        "payments": "Payments",
        "producten": "Producten",
        "events": "Events",
    },
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# --- Types ---

class RegistryRow(TypedDict):
    club_id: str
    club_name: str
    logo_url: NotRequired[str | None]


class MigrationStats(TypedDict):
    scanned: int
    converted: int
    skipped: int
    errored: int


class ValidationResult(TypedDict):
    passed: bool
    total_checked: int
    non_compliant: list[str]


# --- S3 Registry Loading ---

def load_registry_from_s3(session: boto3.Session) -> dict[str, RegistryRow]:
    """Load the club registry from S3 and return a lookup dict keyed by club_id."""
    s3 = session.client("s3", region_name=REGION)
    response = s3.get_object(Bucket=S3_BUCKET, Key=S3_REGISTRY_KEY)
    data = json.loads(response["Body"].read().decode("utf-8"))

    registry: dict[str, RegistryRow] = {}
    for club in data.get("clubs", []):
        club_id = club.get("club_id")
        if club_id:
            registry[str(club_id)] = {
                "club_id": str(club_id),
                "club_name": club.get("club_name", ""),
                "logo_url": club.get("logo_url"),
            }

    logger.info(f"Loaded {len(registry)} entries from S3 registry")
    return registry


# --- DynamoDB Helpers ---

def get_dynamodb_resource(session: boto3.Session):
    """Create a DynamoDB resource from session."""
    return session.resource("dynamodb", region_name=REGION)


def scan_all(table) -> list[dict]:
    """Scan entire table handling pagination."""
    items: list[dict] = []
    scan_kwargs: dict = {}
    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        if "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        else:
            break
    return items


# --- Migration Functions ---

def migrate_orders(table, registry: dict[str, RegistryRow], dry_run: bool) -> MigrationStats:
    """Migrate Orders table: club_id → registry_row_id + label + logo_url."""
    stats: MigrationStats = {"scanned": 0, "converted": 0, "skipped": 0, "errored": 0}

    scan_kwargs: dict = {}
    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])

        for item in items:
            stats["scanned"] += 1
            order_id = item.get("order_id", "unknown")

            # Idempotency: skip if already migrated
            if "registry_row_id" in item:
                stats["skipped"] += 1
                continue

            club_id = item.get("club_id")
            if not club_id:
                stats["skipped"] += 1
                continue

            # Resolve from registry
            club_id_str = str(club_id)
            if club_id_str not in registry:
                logger.warning(
                    f"  SKIP order {order_id}: club_id '{club_id_str}' not found in S3 registry"
                )
                stats["skipped"] += 1
                continue

            row = registry[club_id_str]
            registry_row_label = row["club_name"]
            registry_row_logo_url = row.get("logo_url") or None

            if dry_run:
                logger.info(
                    f"  [DRY RUN] Would migrate order {order_id}: "
                    f"club_id='{club_id_str}' → registry_row_id='{club_id_str}', "
                    f"label='{registry_row_label}'"
                )
            else:
                try:
                    table.update_item(
                        Key={"order_id": order_id},
                        UpdateExpression=(
                            "SET registry_row_id = :row_id, "
                            "registry_row_label = :label, "
                            "registry_row_logo_url = :logo_url"
                        ),
                        ExpressionAttributeValues={
                            ":row_id": club_id_str,
                            ":label": registry_row_label,
                            ":logo_url": registry_row_logo_url,
                        },
                    )
                except Exception as e:
                    logger.error(f"  ERROR migrating order {order_id}: {e}")
                    stats["errored"] += 1
                    continue

            stats["converted"] += 1

        if "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        else:
            break

    return stats


def migrate_members(table, registry: dict[str, RegistryRow], dry_run: bool) -> MigrationStats:
    """Migrate Members table: club_id → registry_row_id (no label/logo)."""
    stats: MigrationStats = {"scanned": 0, "converted": 0, "skipped": 0, "errored": 0}

    scan_kwargs: dict = {}
    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])

        for item in items:
            stats["scanned"] += 1
            member_id = item.get("member_id", "unknown")

            # Idempotency: skip if already migrated
            if "registry_row_id" in item:
                stats["skipped"] += 1
                continue

            club_id = item.get("club_id")
            if not club_id:
                stats["skipped"] += 1
                continue

            # Resolve from registry
            club_id_str = str(club_id)
            if club_id_str not in registry:
                logger.warning(
                    f"  SKIP member {member_id}: club_id '{club_id_str}' not found in S3 registry"
                )
                stats["skipped"] += 1
                continue

            if dry_run:
                logger.info(
                    f"  [DRY RUN] Would migrate member {member_id}: "
                    f"club_id='{club_id_str}' → registry_row_id='{club_id_str}'"
                )
            else:
                try:
                    table.update_item(
                        Key={"member_id": member_id},
                        UpdateExpression="SET registry_row_id = :row_id",
                        ExpressionAttributeValues={":row_id": club_id_str},
                    )
                except Exception as e:
                    logger.error(f"  ERROR migrating member {member_id}: {e}")
                    stats["errored"] += 1
                    continue

            stats["converted"] += 1

        if "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        else:
            break

    return stats


def migrate_payments(table, registry: dict[str, RegistryRow], dry_run: bool) -> MigrationStats:
    """Migrate Payments table: club_id → registry_row_id + label + logo_url."""
    stats: MigrationStats = {"scanned": 0, "converted": 0, "skipped": 0, "errored": 0}

    scan_kwargs: dict = {}
    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])

        for item in items:
            stats["scanned"] += 1
            payment_id = item.get("payment_id", "unknown")

            # Idempotency: skip if already migrated
            if "registry_row_id" in item:
                stats["skipped"] += 1
                continue

            club_id = item.get("club_id")
            if not club_id:
                stats["skipped"] += 1
                continue

            # Resolve from registry
            club_id_str = str(club_id)
            if club_id_str not in registry:
                logger.warning(
                    f"  SKIP payment {payment_id}: club_id '{club_id_str}' not found in S3 registry"
                )
                stats["skipped"] += 1
                continue

            row = registry[club_id_str]
            registry_row_label = row["club_name"]
            registry_row_logo_url = row.get("logo_url") or None

            if dry_run:
                logger.info(
                    f"  [DRY RUN] Would migrate payment {payment_id}: "
                    f"club_id='{club_id_str}' → registry_row_id='{club_id_str}', "
                    f"label='{registry_row_label}'"
                )
            else:
                try:
                    table.update_item(
                        Key={"payment_id": payment_id},
                        UpdateExpression=(
                            "SET registry_row_id = :row_id, "
                            "registry_row_label = :label, "
                            "registry_row_logo_url = :logo_url"
                        ),
                        ExpressionAttributeValues={
                            ":row_id": club_id_str,
                            ":label": registry_row_label,
                            ":logo_url": registry_row_logo_url,
                        },
                    )
                except Exception as e:
                    logger.error(f"  ERROR migrating payment {payment_id}: {e}")
                    stats["errored"] += 1
                    continue

            stats["converted"] += 1

        if "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        else:
            break

    return stats


def migrate_producten(table, dry_run: bool) -> MigrationStats:
    """Migrate Producten: purchase_rules.max_per_club → max_per_order, min_per_club → min_per_order."""
    stats: MigrationStats = {"scanned": 0, "converted": 0, "skipped": 0, "errored": 0}

    scan_kwargs: dict = {}
    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])

        for item in items:
            stats["scanned"] += 1
            product_id = item.get("product_id", "unknown")
            purchase_rules = item.get("purchase_rules")

            if not purchase_rules or not isinstance(purchase_rules, dict):
                stats["skipped"] += 1
                continue

            has_old_max = "max_per_club" in purchase_rules
            has_old_min = "min_per_club" in purchase_rules

            if not has_old_max and not has_old_min:
                stats["skipped"] += 1
                continue

            # Build updated purchase_rules
            new_rules = dict(purchase_rules)
            if has_old_max:
                # max_per_order takes precedence if both exist (Req 5.8)
                if "max_per_order" not in new_rules:
                    new_rules["max_per_order"] = new_rules["max_per_club"]
                del new_rules["max_per_club"]
            if has_old_min:
                if "min_per_order" not in new_rules:
                    new_rules["min_per_order"] = new_rules["min_per_club"]
                del new_rules["min_per_club"]

            if dry_run:
                logger.info(
                    f"  [DRY RUN] Would migrate product {product_id}: "
                    f"purchase_rules updated (max_per_club→max_per_order, min_per_club→min_per_order)"
                )
            else:
                try:
                    table.update_item(
                        Key={"product_id": product_id},
                        UpdateExpression="SET purchase_rules = :rules",
                        ExpressionAttributeValues={":rules": new_rules},
                    )
                except Exception as e:
                    logger.error(f"  ERROR migrating product {product_id}: {e}")
                    stats["errored"] += 1
                    continue

            stats["converted"] += 1

        if "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        else:
            break

    return stats


def migrate_events(table, dry_run: bool) -> MigrationStats:
    """Migrate Events: remove order_scope, rename counting_rule values."""
    stats: MigrationStats = {"scanned": 0, "converted": 0, "skipped": 0, "errored": 0}

    scan_kwargs: dict = {}
    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])

        for item in items:
            stats["scanned"] += 1
            event_id = item.get("event_id", "unknown")

            has_order_scope = "order_scope" in item
            needs_counting_rule_update = False
            updated_constraints = None

            # Check constraints for counting_rule rename
            constraints = item.get("constraints")
            if constraints and isinstance(constraints, list):
                updated_constraints = []
                for constraint in constraints:
                    if isinstance(constraint, dict):
                        counting_rule = constraint.get("counting_rule")
                        if counting_rule == "count_distinct_clubs":
                            new_constraint = dict(constraint)
                            new_constraint["counting_rule"] = "count_distinct_rows"
                            updated_constraints.append(new_constraint)
                            needs_counting_rule_update = True
                        else:
                            updated_constraints.append(constraint)
                    else:
                        updated_constraints.append(constraint)

            if not has_order_scope and not needs_counting_rule_update:
                stats["skipped"] += 1
                continue

            if dry_run:
                changes = []
                if has_order_scope:
                    changes.append("remove order_scope")
                if needs_counting_rule_update:
                    changes.append("rename counting_rule: count_distinct_clubs → count_distinct_rows")
                logger.info(
                    f"  [DRY RUN] Would migrate event {event_id}: {', '.join(changes)}"
                )
            else:
                try:
                    update_parts = []
                    remove_parts = []
                    expr_values: dict = {}
                    expr_names: dict = {}

                    if needs_counting_rule_update and updated_constraints:
                        update_parts.append("#constraints = :constraints")
                        expr_values[":constraints"] = updated_constraints
                        expr_names["#constraints"] = "constraints"

                    if has_order_scope:
                        remove_parts.append("order_scope")

                    update_expr = ""
                    if update_parts:
                        update_expr += "SET " + ", ".join(update_parts)
                    if remove_parts:
                        update_expr += " REMOVE " + ", ".join(remove_parts)

                    update_kwargs: dict = {
                        "Key": {"event_id": event_id},
                        "UpdateExpression": update_expr.strip(),
                    }
                    if expr_values:
                        update_kwargs["ExpressionAttributeValues"] = expr_values
                    if expr_names:
                        update_kwargs["ExpressionAttributeNames"] = expr_names

                    table.update_item(**update_kwargs)
                except Exception as e:
                    logger.error(f"  ERROR migrating event {event_id}: {e}")
                    stats["errored"] += 1
                    continue

            stats["converted"] += 1

        if "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        else:
            break

    return stats


# --- Validation ---

def validate_table(table, key_field: str, table_name: str) -> ValidationResult:
    """Validate that all records have registry_row_id and no club_id remains."""
    result: ValidationResult = {"passed": True, "total_checked": 0, "non_compliant": []}

    scan_kwargs: dict = {}
    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])

        for item in items:
            result["total_checked"] += 1
            record_id = item.get(key_field, "unknown")

            has_registry_row_id = "registry_row_id" in item
            has_club_id = "club_id" in item

            if not has_registry_row_id or has_club_id:
                result["passed"] = False
                reasons = []
                if not has_registry_row_id:
                    reasons.append("missing registry_row_id")
                if has_club_id:
                    reasons.append("still has club_id")
                result["non_compliant"].append(
                    f"{table_name}/{record_id} ({', '.join(reasons)})"
                )

        if "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        else:
            break

    return result


def run_validation(dynamodb, table_names: dict[str, str]) -> bool:
    """Run validation across Orders, Members, and Payments tables."""
    tables_to_validate = [
        ("orders", "order_id", "Orders"),
        ("members", "member_id", "Members"),
        ("payments", "payment_id", "Payments"),
    ]

    all_passed = True
    total_non_compliant: list[str] = []

    for table_key, key_field, display_name in tables_to_validate:
        table = dynamodb.Table(table_names[table_key])
        logger.info(f"Validating {display_name}...")
        result = validate_table(table, key_field, display_name)

        status = "PASS" if result["passed"] else "FAIL"
        logger.info(f"  {display_name}: {status} ({result['total_checked']} records checked)")

        if not result["passed"]:
            all_passed = False
            total_non_compliant.extend(result["non_compliant"])
            for record in result["non_compliant"][:10]:
                logger.warning(f"    Non-compliant: {record}")
            if len(result["non_compliant"]) > 10:
                logger.warning(
                    f"    ... and {len(result['non_compliant']) - 10} more"
                )

    if all_passed:
        logger.info("\n✓ Validation PASSED: all records are migrated")
    else:
        logger.error(
            f"\n✗ Validation FAILED: {len(total_non_compliant)} non-compliant records"
        )

    return all_passed


# --- Remove Old Fields ---

def remove_old_fields_from_table(
    table, key_field: str, table_name: str, dry_run: bool
) -> MigrationStats:
    """Remove club_id field from all records in a table."""
    stats: MigrationStats = {"scanned": 0, "converted": 0, "skipped": 0, "errored": 0}

    scan_kwargs: dict = {}
    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])

        for item in items:
            stats["scanned"] += 1
            record_id = item.get(key_field, "unknown")

            if "club_id" not in item:
                stats["skipped"] += 1
                continue

            if dry_run:
                logger.info(
                    f"  [DRY RUN] Would remove club_id from {table_name}/{record_id}"
                )
            else:
                try:
                    table.update_item(
                        Key={key_field: record_id},
                        UpdateExpression="REMOVE club_id",
                    )
                except Exception as e:
                    logger.error(
                        f"  ERROR removing club_id from {table_name}/{record_id}: {e}"
                    )
                    stats["errored"] += 1
                    continue

            stats["converted"] += 1

        if "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        else:
            break

    return stats


def run_remove_old_fields(dynamodb, table_names: dict[str, str], dry_run: bool) -> bool:
    """Remove old club_id fields from Orders, Members, and Payments after validation passes."""
    # First validate
    logger.info("Running validation before removing old fields...")
    if not run_validation(dynamodb, table_names):
        logger.error("Validation failed — cannot remove old fields until all records are migrated")
        return False

    logger.info("\nValidation passed. Removing old club_id fields...")

    tables_to_clean = [
        ("orders", "order_id", "Orders"),
        ("members", "member_id", "Members"),
        ("payments", "payment_id", "Payments"),
    ]

    for table_key, key_field, display_name in tables_to_clean:
        table = dynamodb.Table(table_names[table_key])
        logger.info(f"\nRemoving old fields from {display_name}...")
        stats = remove_old_fields_from_table(table, key_field, display_name, dry_run)
        print_summary(display_name, stats, dry_run)

    return True


# --- Output ---

def print_summary(table_name: str, stats: MigrationStats, dry_run: bool) -> None:
    """Print a human-readable summary for one table."""
    mode = "DRY RUN" if dry_run else "APPLIED"
    print(f"\n  {table_name} [{mode}]:")
    print(f"    Scanned:    {stats['scanned']}")
    print(f"    Converted:  {stats['converted']}")
    print(f"    Skipped:    {stats['skipped']}")
    print(f"    Errors:     {stats['errored']}")


# --- Main ---

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Migrate club_id to registry_row_id across Orders, Members, "
            "Payments, Producten, and Events tables."
        )
    )
    parser.add_argument(
        "--stage",
        type=str,
        required=True,
        choices=["test", "prod"],
        help="Target stage (test or prod).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Log changes without writing to DynamoDB.",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=DEFAULT_PROFILE,
        help=f"AWS CLI profile (default: {DEFAULT_PROFILE}).",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        default=False,
        help="Validate all records have registry_row_id and no club_id remains.",
    )
    parser.add_argument(
        "--remove-old-fields",
        action="store_true",
        default=False,
        help="Remove old club_id fields after successful validation.",
    )
    args = parser.parse_args()

    table_names = TABLE_NAMES[args.stage]

    # Create session
    session = boto3.Session(profile_name=args.profile, region_name=REGION)
    dynamodb = get_dynamodb_resource(session)

    mode = "DRY RUN" if args.dry_run else "APPLY"
    logger.info(f"{'=' * 60}")
    logger.info(f"Club to Registry Row Migration [{mode}]")
    logger.info(f"Stage: {args.stage} | Profile: {args.profile} | Region: {REGION}")
    logger.info(f"{'=' * 60}")

    # --- Validate mode ---
    if args.validate:
        passed = run_validation(dynamodb, table_names)
        sys.exit(0 if passed else 1)

    # --- Remove old fields mode ---
    if args.remove_old_fields:
        success = run_remove_old_fields(dynamodb, table_names, args.dry_run)
        sys.exit(0 if success else 1)

    # --- Migration mode ---
    # Load registry from S3
    registry = load_registry_from_s3(session)

    # Migrate Orders
    logger.info(f"\nMigrating Orders ({table_names['orders']})...")
    orders_table = dynamodb.Table(table_names["orders"])
    orders_stats = migrate_orders(orders_table, registry, args.dry_run)

    # Migrate Members
    logger.info(f"\nMigrating Members ({table_names['members']})...")
    members_table = dynamodb.Table(table_names["members"])
    members_stats = migrate_members(members_table, registry, args.dry_run)

    # Migrate Payments
    logger.info(f"\nMigrating Payments ({table_names['payments']})...")
    payments_table = dynamodb.Table(table_names["payments"])
    payments_stats = migrate_payments(payments_table, registry, args.dry_run)

    # Migrate Producten
    logger.info(f"\nMigrating Producten ({table_names['producten']})...")
    producten_table = dynamodb.Table(table_names["producten"])
    producten_stats = migrate_producten(producten_table, args.dry_run)

    # Migrate Events
    logger.info(f"\nMigrating Events ({table_names['events']})...")
    events_table = dynamodb.Table(table_names["events"])
    events_stats = migrate_events(events_table, args.dry_run)

    # Print summary
    print(f"\n{'=' * 60}")
    print(f"  Club to Registry Row Migration Summary")
    print(f"{'=' * 60}")
    print_summary("Orders", orders_stats, args.dry_run)
    print_summary("Members", members_stats, args.dry_run)
    print_summary("Payments", payments_stats, args.dry_run)
    print_summary("Producten", producten_stats, args.dry_run)
    print_summary("Events", events_stats, args.dry_run)

    total_errors = (
        orders_stats["errored"]
        + members_stats["errored"]
        + payments_stats["errored"]
        + producten_stats["errored"]
        + events_stats["errored"]
    )
    total_converted = (
        orders_stats["converted"]
        + members_stats["converted"]
        + payments_stats["converted"]
        + producten_stats["converted"]
        + events_stats["converted"]
    )

    if args.dry_run and total_converted > 0:
        print(f"\n  NOTE: This was a dry run. Remove --dry-run to execute the migration.")

    print(f"{'=' * 60}\n")

    if total_errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
