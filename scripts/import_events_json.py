"""
Import events from a JSON file into the DynamoDB Events table.

Reads a JSON file containing an array of event objects, validates required fields,
performs duplicate detection, and writes new events to DynamoDB.

Usage:
    python scripts/import_events_json.py --input-file events.json
    python scripts/import_events_json.py --input-file events.json --dry-run
    python scripts/import_events_json.py --input-file events.json --profile nonprofit-deploy
    python scripts/import_events_json.py --input-file events.json --status published
    python scripts/import_events_json.py --input-file events.json --force

JSON format (array of event objects):
    [
        {
            "name": "Toerweekend 2026",
            "start_date": "2026-05-15",
            "end_date": "2026-05-17",
            "location": "Amsterdam",
            "description": "Annual touring weekend",
            "event_type": "nationaal",
            "linked_regio": "noord",
            "poster_url": "https://example.com/poster.jpg"
        },
        ...
    ]

Required fields: name, start_date (YYYY-MM-DD)
Optional fields: end_date, location, description, event_type, linked_regio, poster_url
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3

from shared.event_dedup import check_duplicate, format_dry_run_result

# YYYY-MM-DD date pattern (strict: 4-digit year, 2-digit month, 2-digit day)
DATE_PATTERN: re.Pattern[str] = re.compile(
    r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$"
)

# Characters allowed in slugs (lowercase alphanumeric + hyphens)
SLUG_STRIP_PATTERN: re.Pattern[str] = re.compile(r"[^a-z0-9\-]")
SLUG_MULTI_HYPHEN: re.Pattern[str] = re.compile(r"-{2,}")

REQUIRED_FIELDS: list[str] = ["name", "start_date"]
OPTIONAL_FIELDS: list[str] = [
    "end_date",
    "location",
    "description",
    "event_type",
    "linked_regio",
    "poster_url",
]
VALID_STATUSES: list[str] = ["draft", "published", "archived"]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Import events from a JSON file into the DynamoDB Events table.",
    )
    parser.add_argument(
        "--input-file",
        required=True,
        help="Path to JSON file containing array of event objects",
    )
    parser.add_argument(
        "--profile",
        default="nonprofit-deploy",
        help="AWS CLI profile to use (default: nonprofit-deploy)",
    )
    parser.add_argument(
        "--table",
        default="Events",
        help="DynamoDB table name (default: Events)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show what would happen without writing to DynamoDB",
    )
    parser.add_argument(
        "--status",
        default="draft",
        choices=VALID_STATUSES,
        help="Status to assign to imported events (default: draft)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Skip duplicate check and insert even if duplicate detected",
    )
    return parser.parse_args()


def generate_slug(name: str) -> str:
    """
    Generate a URL-friendly slug from an event name.

    Rules:
    - Convert to lowercase
    - Replace spaces with hyphens
    - Strip special characters (keep only alphanumeric + hyphens)
    - Collapse multiple consecutive hyphens
    - Strip leading/trailing hyphens
    """
    slug: str = name.lower().strip()
    slug = slug.replace(" ", "-")
    slug = SLUG_STRIP_PATTERN.sub("", slug)
    slug = SLUG_MULTI_HYPHEN.sub("-", slug)
    slug = slug.strip("-")
    return slug


def validate_event(event: dict[str, Any], index: int) -> tuple[bool, list[str]]:
    """
    Validate a single event object from the JSON input.

    Returns:
        Tuple of (is_valid, list of error messages).
    """
    errors: list[str] = []

    # Check required fields
    for field in REQUIRED_FIELDS:
        value: Any = event.get(field)
        if not value or not str(value).strip():
            errors.append(f"Missing required field: '{field}'")

    # Validate start_date format
    start_date: str = str(event.get("start_date", "")).strip()
    if start_date and not DATE_PATTERN.match(start_date):
        errors.append(f"Invalid start_date format: '{start_date}' (expected YYYY-MM-DD)")

    # Validate end_date format if provided
    end_date: str = str(event.get("end_date", "")).strip()
    if end_date and not DATE_PATTERN.match(end_date):
        errors.append(f"Invalid end_date format: '{end_date}' (expected YYYY-MM-DD)")

    # Validate end_date >= start_date if both provided
    if start_date and end_date and DATE_PATTERN.match(start_date) and DATE_PATTERN.match(end_date):
        if end_date < start_date:
            errors.append(f"end_date '{end_date}' is before start_date '{start_date}'")

    is_valid: bool = len(errors) == 0
    return is_valid, errors


def build_event_item(
    event: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    """
    Build a complete DynamoDB item from the input event data.

    Generates: event_id (UUID), slug, status, import_source, created_at.
    """
    name: str = str(event["name"]).strip()
    start_date: str = str(event["start_date"]).strip()

    item: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "name": name,
        "slug": generate_slug(name),
        "start_date": start_date,
        "status": status,
        "import_source": "json",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Add optional fields if present and non-empty
    for field in OPTIONAL_FIELDS:
        value: Any = event.get(field)
        if value and str(value).strip():
            item[field] = str(value).strip()

    return item


def load_json_file(file_path: str) -> list[dict[str, Any]]:
    """
    Load and parse the JSON input file.

    Expects an array of event objects at the top level.

    Raises:
        SystemExit on file not found, invalid JSON, or wrong structure.
    """
    path: Path = Path(file_path)

    if not path.exists():
        print(f"\n  ✗ File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    try:
        content: str = path.read_text(encoding="utf-8")
        data: Any = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"\n  ✗ Invalid JSON in '{file_path}': {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, list):
        print(
            f"\n  ✗ Expected JSON array at top level, got {type(data).__name__}",
            file=sys.stderr,
        )
        sys.exit(1)

    return data


def main() -> None:
    """Main entry point for JSON event import."""
    args: argparse.Namespace = parse_args()

    # Load input file
    print(f"\n[import_events_json] Loading '{args.input_file}'...")
    events: list[dict[str, Any]] = load_json_file(args.input_file)
    print(f"  Found {len(events)} event(s) in file")

    if not events:
        print("\n  No events to import. Exiting.")
        sys.exit(0)

    # Connect to DynamoDB (skip in dry-run if we want pure local mode,
    # but we still need the table for duplicate checks unless --force)
    table: Any = None
    if not args.dry_run or not args.force:
        print(f"\n[import_events_json] Connecting to DynamoDB...")
        print(f"  Profile: {args.profile}")
        print(f"  Table:   {args.table}")
        print(f"  Region:  eu-west-1")

        try:
            session = boto3.Session(
                profile_name=args.profile,
                region_name="eu-west-1",
            )
            dynamodb = session.resource("dynamodb")
            table = dynamodb.Table(args.table)
            table.load()
            print(f"  Status:  {table.table_status}")
        except Exception as e:
            print(f"\n  ✗ Failed to connect to DynamoDB: {e}", file=sys.stderr)
            sys.exit(1)

    # Process events
    mode_label: str = "DRY-RUN" if args.dry_run else "LIVE"
    print(f"\n[import_events_json] Processing events ({mode_label})...")
    print(f"  Status:  {args.status}")
    print(f"  Force:   {args.force}")
    print()

    created: int = 0
    skipped: int = 0
    errors: int = 0

    for index, event_data in enumerate(events):
        event_name: str = str(event_data.get("name", "(unnamed)")).strip()
        prefix: str = f"  [{index + 1}/{len(events)}]"

        # Validate
        is_valid, validation_errors = validate_event(event_data, index)
        if not is_valid:
            print(f"{prefix} ✗ INVALID: '{event_name}'")
            for err in validation_errors:
                print(f"           {err}")
            errors += 1
            continue

        # Build the item
        item: dict[str, Any] = build_event_item(event_data, args.status)

        # Duplicate check (unless --force)
        if not args.force and table is not None:
            start_date: str = item["start_date"]
            location: str = item.get("location", "")

            match: dict[str, Any] | None = check_duplicate(
                name=event_name,
                start_date=start_date,
                location=location,
                table=table,
            )

            if args.dry_run:
                result_str: str = format_dry_run_result(event_name, start_date, match)
                print(f"{prefix} {result_str.strip()}")
                if match:
                    skipped += 1
                else:
                    created += 1
                continue

            if match is not None:
                existing_name: str = match.get("name", "?")
                existing_id: str = match.get("event_id", "?")
                print(
                    f"{prefix} ⚠ SKIPPED (duplicate): '{event_name}' "
                    f"matches '{existing_name}' (id: {existing_id})"
                )
                skipped += 1
                continue
        elif args.dry_run:
            # --force + --dry-run: show what would be created
            print(f"{prefix} ✓ WOULD CREATE: '{event_name}' (force=True, skip dedup)")
            created += 1
            continue

        # Write to DynamoDB
        try:
            table.put_item(Item=item)
            print(f"{prefix} ✓ CREATED: '{event_name}' (id: {item['event_id']})")
            created += 1
        except Exception as e:
            print(f"{prefix} ✗ ERROR writing '{event_name}': {e}")
            errors += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"  IMPORT SUMMARY")
    print(f"{'='*60}")
    print(f"  Mode:      {'DRY-RUN (no writes)' if args.dry_run else 'LIVE'}")
    print(f"  Input:     {args.input_file}")
    print(f"  Total:     {len(events)}")
    print(f"  Created:   {created}")
    print(f"  Skipped:   {skipped} (duplicates)")
    print(f"  Errors:    {errors} (validation/write failures)")
    print(f"{'='*60}\n")

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
