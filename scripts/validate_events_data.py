"""
Validate existing events in the DynamoDB Events table.

Scans the Events table and reports data quality issues:
- Missing slug fields
- Missing poster_url fields
- Invalid date formats (not YYYY-MM-DD) in start_date or end_date
- Duplicate candidates (events that might be duplicates based on fuzzy matching)

Read-only script — no mutations are performed.

Usage:
    python scripts/validate_events_data.py
    python scripts/validate_events_data.py --profile nonprofit-deploy
    python scripts/validate_events_data.py --table Events-Test
    python scripts/validate_events_data.py --dry-run  (same behavior — always read-only)
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Any

import boto3

from shared.event_dedup import fuzzy_name_match, fuzzy_location_match

# YYYY-MM-DD date pattern (strict: 4-digit year, 2-digit month, 2-digit day)
DATE_PATTERN: re.Pattern[str] = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate existing events in DynamoDB Events table.",
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
        default=True,
        help="Read-only mode (default: True — script never mutates data)",
    )
    return parser.parse_args()


def scan_all_events(table: Any) -> list[dict[str, Any]]:
    """Scan entire Events table with pagination handling."""
    items: list[dict[str, Any]] = []
    response: dict[str, Any] = table.scan()
    items.extend(response.get("Items", []))

    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    return items


def is_valid_date(value: str) -> bool:
    """Check if a string matches YYYY-MM-DD format."""
    return bool(DATE_PATTERN.match(value))


def find_missing_slugs(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find events with missing or empty slug field."""
    results: list[dict[str, Any]] = []
    for event in events:
        slug: str = event.get("slug", "")
        if not slug or not str(slug).strip():
            results.append(event)
    return results


def find_missing_poster_urls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find events with missing or empty poster_url field."""
    results: list[dict[str, Any]] = []
    for event in events:
        poster_url: str = event.get("poster_url", "")
        if not poster_url or not str(poster_url).strip():
            results.append(event)
    return results


def find_invalid_dates(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find events with invalid date formats in start_date or end_date."""
    results: list[dict[str, Any]] = []
    for event in events:
        issues: list[str] = []

        start_date: str = event.get("start_date", "")
        end_date: str = event.get("end_date", "")

        if start_date and not is_valid_date(str(start_date)):
            issues.append(f"start_date='{start_date}'")
        if end_date and not is_valid_date(str(end_date)):
            issues.append(f"end_date='{end_date}'")

        # Also flag if start_date is completely missing (required field)
        if not start_date:
            issues.append("start_date missing")

        if issues:
            results.append({**event, "_date_issues": issues})
    return results


def find_duplicate_candidates(
    events: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """
    Find pairs of events that are potential duplicates.

    Uses fuzzy matching on name + exact date + location.
    Only compares each pair once (i < j).
    """
    duplicates: list[tuple[dict[str, Any], dict[str, Any]]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for i, event_a in enumerate(events):
        name_a: str = event_a.get("name", event_a.get("title", ""))
        date_a: str = event_a.get("start_date", "")
        location_a: str = event_a.get("location", "")
        id_a: str = event_a.get("event_id", "")

        if not name_a or not date_a:
            continue

        for j in range(i + 1, len(events)):
            event_b = events[j]
            name_b: str = event_b.get("name", event_b.get("title", ""))
            date_b: str = event_b.get("start_date", "")
            location_b: str = event_b.get("location", "")
            id_b: str = event_b.get("event_id", "")

            if not name_b or not date_b:
                continue

            # Exact date match is prerequisite
            if date_a != date_b:
                continue

            # Check fuzzy name match
            if not fuzzy_name_match(name_a, name_b):
                continue

            # If both have locations, check location match for stronger confidence
            # But name + date match is already sufficient to flag as candidate
            pair_key: tuple[str, str] = (
                min(id_a, id_b),
                max(id_a, id_b),
            )
            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                duplicates.append((event_a, event_b))

    return duplicates


def format_event_ref(event: dict[str, Any]) -> str:
    """Format a short reference string for an event."""
    event_id: str = event.get("event_id", "?")
    name: str = event.get("name", event.get("title", "(no name)"))
    start_date: str = event.get("start_date", "(no date)")
    return f"'{name}' ({start_date}) [id: {event_id}]"


def print_report(
    events: list[dict[str, Any]],
    missing_slugs: list[dict[str, Any]],
    missing_posters: list[dict[str, Any]],
    invalid_dates: list[dict[str, Any]],
    duplicate_pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    table_name: str,
) -> None:
    """Print the validation report to stdout."""
    print(f"\n{'='*70}")
    print(f"  EVENTS DATA VALIDATION REPORT — Table: {table_name}")
    print(f"{'='*70}")
    print(f"\n  Total events scanned: {len(events)}\n")

    # Missing slugs
    print(f"{'─'*70}")
    print(f"  ❶ Missing slug: {len(missing_slugs)} event(s)")
    print(f"{'─'*70}")
    if missing_slugs:
        for event in missing_slugs:
            print(f"    • {format_event_ref(event)}")
    else:
        print("    ✓ All events have a slug")

    # Missing poster_url
    print(f"\n{'─'*70}")
    print(f"  ❷ Missing poster_url: {len(missing_posters)} event(s)")
    print(f"{'─'*70}")
    if missing_posters:
        for event in missing_posters:
            print(f"    • {format_event_ref(event)}")
    else:
        print("    ✓ All events have a poster_url")

    # Invalid dates
    print(f"\n{'─'*70}")
    print(f"  ❸ Invalid dates: {len(invalid_dates)} event(s)")
    print(f"{'─'*70}")
    if invalid_dates:
        for event in invalid_dates:
            issues: list[str] = event.get("_date_issues", [])
            print(f"    • {format_event_ref(event)}")
            print(f"      Issues: {', '.join(issues)}")
    else:
        print("    ✓ All dates are valid (YYYY-MM-DD format)")

    # Duplicate candidates
    print(f"\n{'─'*70}")
    print(f"  ❹ Duplicate candidates: {len(duplicate_pairs)} pair(s)")
    print(f"{'─'*70}")
    if duplicate_pairs:
        for event_a, event_b in duplicate_pairs:
            print(f"    • {format_event_ref(event_a)}")
            print(f"      ↔ {format_event_ref(event_b)}")
            loc_a: str = event_a.get("location", "(no location)")
            loc_b: str = event_b.get("location", "(no location)")
            if loc_a or loc_b:
                print(f"      Locations: '{loc_a}' / '{loc_b}'")
            print()
    else:
        print("    ✓ No duplicate candidates found")

    # Summary
    total_issues: int = (
        len(missing_slugs)
        + len(missing_posters)
        + len(invalid_dates)
        + len(duplicate_pairs)
    )
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"  Total events:          {len(events)}")
    print(f"  Missing slug:          {len(missing_slugs)}")
    print(f"  Missing poster_url:    {len(missing_posters)}")
    print(f"  Invalid dates:         {len(invalid_dates)}")
    print(f"  Duplicate candidates:  {len(duplicate_pairs)}")
    print(f"  {'─'*40}")
    print(f"  Total issues:          {total_issues}")
    if total_issues == 0:
        print("\n  ✅ All events pass validation!")
    else:
        print(f"\n  ⚠️  {total_issues} issue(s) found — review above for details")
    print(f"{'='*70}\n")


def main() -> None:
    """Main entry point."""
    args: argparse.Namespace = parse_args()

    print(f"\n[validate_events_data] Connecting to DynamoDB...")
    print(f"  Profile: {args.profile}")
    print(f"  Table:   {args.table}")
    print(f"  Mode:    {'dry-run (read-only)' if args.dry_run else 'read-only'}")

    try:
        session = boto3.Session(
            profile_name=args.profile,
            region_name="eu-west-1",
        )
        dynamodb = session.resource("dynamodb")
        table = dynamodb.Table(args.table)

        # Verify table exists by checking item count
        table.load()
        print(f"  Status:  {table.table_status}")
    except Exception as e:
        print(f"\n  ✗ Failed to connect to DynamoDB: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\n[validate_events_data] Scanning table...")
    events: list[dict[str, Any]] = scan_all_events(table)
    print(f"  Fetched {len(events)} events")

    if not events:
        print("\n  No events found in table. Nothing to validate.")
        sys.exit(0)

    # Run validations
    print(f"[validate_events_data] Running validations...")
    missing_slugs: list[dict[str, Any]] = find_missing_slugs(events)
    missing_posters: list[dict[str, Any]] = find_missing_poster_urls(events)
    invalid_dates: list[dict[str, Any]] = find_invalid_dates(events)
    duplicate_pairs: list[tuple[dict[str, Any], dict[str, Any]]] = find_duplicate_candidates(events)

    # Print report
    print_report(
        events=events,
        missing_slugs=missing_slugs,
        missing_posters=missing_posters,
        invalid_dates=invalid_dates,
        duplicate_pairs=duplicate_pairs,
        table_name=args.table,
    )


if __name__ == "__main__":
    main()
