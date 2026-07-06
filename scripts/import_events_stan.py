"""
Import events from a Stan export (CSV) into the DynamoDB Events table.

Reads a CSV file (semicolon or comma-delimited), auto-detects columns using
common Dutch/English header names, maps them to the Events schema, performs
duplicate detection, and writes new events to DynamoDB.

Usage:
    python scripts/import_events_stan.py --input-file stan_export.csv
    python scripts/import_events_stan.py --input-file stan_export.csv --dry-run
    python scripts/import_events_stan.py --input-file stan_export.csv --profile nonprofit-deploy
    python scripts/import_events_stan.py --input-file stan_export.csv --force
    python scripts/import_events_stan.py --input-file stan_export.csv --column-mapping "titel=name,datum=start_date"
    python scripts/import_events_stan.py --input-file stan_export.csv --delimiter ";"

Stan CSV format:
    - Delimiter: auto-detected (semicolon or comma — semicolons common in Dutch exports)
    - Encoding: UTF-8 (with or without BOM)
    - Headers: first row contains column names
    - Column mapping: auto-detected from Dutch/English names, or explicit via --column-mapping

Required mapped fields: name, start_date
Optional mapped fields: end_date, location, description, event_type, linked_regio
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3

from shared.event_dedup import check_duplicate, format_dry_run_result

# --- Column mapping: CSV header → Events schema field ---
# Each key is a lowercase CSV column name that maps to the Events field (value).
DEFAULT_COLUMN_MAP: dict[str, str] = {
    # name
    "naam": "name",
    "name": "name",
    "titel": "name",
    "title": "name",
    "evenement": "name",
    # start_date
    "datum": "start_date",
    "date": "start_date",
    "start_date": "start_date",
    "startdatum": "start_date",
    "start": "start_date",
    # end_date
    "einddatum": "end_date",
    "end_date": "end_date",
    "end": "end_date",
    "eind": "end_date",
    # location
    "locatie": "location",
    "location": "location",
    "plaats": "location",
    # description
    "beschrijving": "description",
    "description": "description",
    "omschrijving": "description",
    # event_type
    "type": "event_type",
    "event_type": "event_type",
    "soort": "event_type",
    # linked_regio
    "regio": "linked_regio",
    "region": "linked_regio",
    "linked_regio": "linked_regio",
}

# Date formats to try when parsing dates (order: most specific first)
DATE_FORMATS: list[str] = [
    "%Y-%m-%d",    # 2026-05-15
    "%d-%m-%Y",    # 15-05-2026
    "%d/%m/%Y",    # 15/05/2026
    "%d-%m-%y",    # 15-05-26
    "%d/%m/%y",    # 15/05/26
]

# Slug generation patterns
SLUG_STRIP_PATTERN: re.Pattern[str] = re.compile(r"[^a-z0-9\-]")
SLUG_MULTI_HYPHEN: re.Pattern[str] = re.compile(r"-{2,}")

VALID_STATUSES: list[str] = ["draft", "published", "archived"]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Import events from a Stan CSV export into the DynamoDB Events table.",
    )
    parser.add_argument(
        "--input-file",
        required=True,
        help="Path to CSV file (Stan export)",
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
    parser.add_argument(
        "--column-mapping",
        default=None,
        help=(
            "Explicit column mapping (overrides auto-detection). "
            'Format: "csv_col=field,csv_col=field" '
            'Example: "titel=name,datum=start_date,locatie=location"'
        ),
    )
    parser.add_argument(
        "--delimiter",
        default=None,
        help="CSV delimiter (default: auto-detect between comma and semicolon)",
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


def parse_date(value: str) -> str | None:
    """
    Parse a date string in various formats and normalize to YYYY-MM-DD.

    Tries multiple date formats common in Dutch and international exports.

    Returns:
        Normalized date string (YYYY-MM-DD) or None if unparseable.
    """
    cleaned: str = value.strip()
    if not cleaned:
        return None

    for fmt in DATE_FORMATS:
        try:
            dt: datetime = datetime.strptime(cleaned, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def detect_delimiter(content: str) -> str:
    """
    Auto-detect CSV delimiter by checking the first line for semicolons vs commas.

    Dutch Excel exports commonly use semicolons. Falls back to comma.
    """
    first_line: str = content.split("\n", maxsplit=1)[0]
    semicolons: int = first_line.count(";")
    commas: int = first_line.count(",")

    if semicolons > commas:
        return ";"
    return ","


def parse_column_mapping(mapping_str: str) -> dict[str, str]:
    """
    Parse an explicit column mapping string into a dict.

    Format: "csv_col=field,csv_col=field"
    Example: "titel=name,datum=start_date,locatie=location"

    Returns:
        Dict mapping lowercase CSV column → Events schema field.
    """
    result: dict[str, str] = {}
    pairs: list[str] = mapping_str.split(",")

    for pair in pairs:
        pair = pair.strip()
        if "=" not in pair:
            print(f"  ⚠ Invalid mapping pair (no '='): '{pair}' — skipping", file=sys.stderr)
            continue

        csv_col, field = pair.split("=", maxsplit=1)
        csv_col = csv_col.strip().lower()
        field = field.strip()

        if not csv_col or not field:
            print(f"  ⚠ Empty key or value in mapping: '{pair}' — skipping", file=sys.stderr)
            continue

        result[csv_col] = field

    return result


def build_column_map(
    headers: list[str],
    explicit_mapping: dict[str, str] | None,
) -> dict[int, str]:
    """
    Build a mapping from column index → Events schema field.

    Uses explicit mapping if provided, otherwise auto-detects from DEFAULT_COLUMN_MAP.

    Returns:
        Dict mapping column index → Events field name.
    """
    lookup: dict[str, str] = explicit_mapping if explicit_mapping else DEFAULT_COLUMN_MAP
    index_map: dict[int, str] = {}

    for i, header in enumerate(headers):
        normalized: str = header.lower().strip()
        if normalized in lookup:
            index_map[i] = lookup[normalized]

    return index_map


def load_csv_file(file_path: str, delimiter: str | None) -> tuple[list[str], list[list[str]], str]:
    """
    Load and parse the CSV input file.

    Handles UTF-8 BOM, auto-detects delimiter.

    Returns:
        Tuple of (headers, rows, detected_delimiter).

    Raises:
        SystemExit on file not found or read errors.
    """
    path: Path = Path(file_path)

    if not path.exists():
        print(f"\n  ✗ File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    try:
        # Read with utf-8-sig to handle BOM (common in Excel exports)
        content: str = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        # Fallback to latin-1 for older exports
        try:
            content = path.read_text(encoding="latin-1")
        except Exception as e:
            print(f"\n  ✗ Cannot read file '{file_path}': {e}", file=sys.stderr)
            sys.exit(1)

    if not content.strip():
        print(f"\n  ✗ File is empty: {file_path}", file=sys.stderr)
        sys.exit(1)

    # Detect or use provided delimiter
    detected_delimiter: str = delimiter if delimiter else detect_delimiter(content)

    # Parse CSV
    reader = csv.reader(io.StringIO(content), delimiter=detected_delimiter)
    rows: list[list[str]] = list(reader)

    if len(rows) < 2:
        print(f"\n  ✗ CSV has no data rows (only header or empty): {file_path}", file=sys.stderr)
        sys.exit(1)

    headers: list[str] = rows[0]
    data_rows: list[list[str]] = rows[1:]

    return headers, data_rows, detected_delimiter


def map_row_to_event(
    row: list[str],
    column_map: dict[int, str],
) -> dict[str, str]:
    """
    Map a single CSV row to an event dict using the column mapping.

    Returns:
        Dict with Events schema field names as keys.
    """
    event: dict[str, str] = {}
    for col_index, field_name in column_map.items():
        if col_index < len(row):
            value: str = row[col_index].strip()
            if value:
                event[field_name] = value
    return event


def validate_event(event: dict[str, str], row_num: int) -> tuple[bool, list[str]]:
    """
    Validate a mapped event dict.

    Required: name, start_date (must parse to valid date).

    Returns:
        Tuple of (is_valid, list of error messages).
    """
    errors: list[str] = []

    # Check required: name
    name: str = event.get("name", "").strip()
    if not name:
        errors.append("Missing required field: 'name'")

    # Check required: start_date (raw value — will be parsed later)
    raw_start: str = event.get("start_date", "").strip()
    if not raw_start:
        errors.append("Missing required field: 'start_date'")
    else:
        parsed: str | None = parse_date(raw_start)
        if parsed is None:
            errors.append(f"Cannot parse start_date: '{raw_start}'")

    # Validate end_date if provided
    raw_end: str = event.get("end_date", "").strip()
    if raw_end:
        parsed_end: str | None = parse_date(raw_end)
        if parsed_end is None:
            errors.append(f"Cannot parse end_date: '{raw_end}'")

    is_valid: bool = len(errors) == 0
    return is_valid, errors


def build_event_item(
    event: dict[str, str],
    status: str,
) -> dict[str, Any]:
    """
    Build a complete DynamoDB item from the mapped event data.

    Generates: event_id (UUID), slug, status, import_source, created_at.
    Normalizes dates to YYYY-MM-DD format.
    """
    name: str = event["name"].strip()

    # Parse and normalize dates
    start_date: str = parse_date(event["start_date"]) or event["start_date"]
    end_date: str | None = None
    if event.get("end_date"):
        end_date = parse_date(event["end_date"])

    item: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "name": name,
        "slug": generate_slug(name),
        "start_date": start_date,
        "status": status,
        "import_source": "stan",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if end_date:
        item["end_date"] = end_date

    # Add optional fields (location, description, event_type, linked_regio)
    optional_fields: list[str] = ["location", "description", "event_type", "linked_regio"]
    for field in optional_fields:
        value: str = event.get(field, "").strip()
        if value:
            item[field] = value

    return item


def main() -> None:
    """Main entry point for Stan CSV event import."""
    args: argparse.Namespace = parse_args()

    # Load input file
    print(f"\n[import_events_stan] Loading '{args.input_file}'...")
    headers, data_rows, detected_delimiter = load_csv_file(args.input_file, args.delimiter)
    print(f"  Found {len(data_rows)} data row(s)")
    print(f"  Delimiter: '{detected_delimiter}' ({'auto-detected' if not args.delimiter else 'user-specified'})")
    print(f"  Headers:   {headers}")

    # Build column mapping
    explicit_mapping: dict[str, str] | None = None
    if args.column_mapping:
        explicit_mapping = parse_column_mapping(args.column_mapping)
        print(f"\n  Explicit column mapping: {explicit_mapping}")

    column_map: dict[int, str] = build_column_map(headers, explicit_mapping)

    if not column_map:
        print(
            "\n  ✗ No columns could be mapped to Events schema fields.",
            file=sys.stderr,
        )
        print("    Headers found: " + ", ".join(headers), file=sys.stderr)
        print(
            "    Use --column-mapping to specify explicit mappings.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Show resolved mapping
    print(f"\n  Column mapping (index → field):")
    for col_idx, field_name in sorted(column_map.items()):
        print(f"    [{col_idx}] '{headers[col_idx]}' → {field_name}")

    # Check that required fields are mapped
    mapped_fields: set[str] = set(column_map.values())
    if "name" not in mapped_fields:
        print("\n  ✗ No column mapped to 'name' (required).", file=sys.stderr)
        print(
            "    Use --column-mapping to specify which column is the event name.",
            file=sys.stderr,
        )
        sys.exit(1)
    if "start_date" not in mapped_fields:
        print("\n  ✗ No column mapped to 'start_date' (required).", file=sys.stderr)
        print(
            "    Use --column-mapping to specify which column is the start date.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Connect to DynamoDB (skip in dry-run + force mode)
    table: Any = None
    if not args.dry_run or not args.force:
        print(f"\n[import_events_stan] Connecting to DynamoDB...")
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

    # Process rows
    mode_label: str = "DRY-RUN" if args.dry_run else "LIVE"
    print(f"\n[import_events_stan] Processing rows ({mode_label})...")
    print(f"  Status:  {args.status}")
    print(f"  Force:   {args.force}")
    print()

    created: int = 0
    skipped: int = 0
    errors: int = 0
    total: int = len(data_rows)

    for index, row in enumerate(data_rows):
        row_num: int = index + 2  # 1-based, accounting for header row

        # Map CSV row to event dict
        event_data: dict[str, str] = map_row_to_event(row, column_map)
        event_name: str = event_data.get("name", "(unnamed)").strip()
        prefix: str = f"  [{index + 1}/{total}]"

        # Validate
        is_valid, validation_errors = validate_event(event_data, row_num)
        if not is_valid:
            print(f"{prefix} ✗ INVALID (row {row_num}): '{event_name}'")
            for err in validation_errors:
                print(f"           {err}")
            errors += 1
            continue

        # Build the DynamoDB item
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
    print(f"  Source:    {args.input_file}")
    print(f"  Format:    CSV (delimiter: '{detected_delimiter}')")
    print(f"  Total:     {total}")
    print(f"  Created:   {created}")
    print(f"  Skipped:   {skipped} (duplicates)")
    print(f"  Errors:    {errors} (validation/write failures)")
    print(f"{'='*60}\n")

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
