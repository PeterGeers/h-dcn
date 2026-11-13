"""
Import the Federation International Rally Calendar (DOCX) into the DynamoDB Events table.

The document is a plain list of tab-separated lines grouped under month headings:

    March
    27 - 28<TAB>HDC Liberator<TAB>Lieshoutseweg, Aarle-Rixtel, NL

Parsing rules:
    - A month name on its own line sets the current month.
    - A 4-digit year on its own line (e.g. "2028") switches year and resets the month.
    - "27 - 28" is a range in the current month, "24" is a single day.
    - "30 - 1" (end < start) means the range ends in the NEXT month. The calendar
      repeats such a line under the next month; the repeat is dropped.
    - "TBC" locations are stored without a location.

Every imported event gets:
    event_type = internationaal_treffen, event_category = rally,
    participation = open, linked_regio = regio_all

Usage (run from the repo root, requires `pip install python-docx`):
    python scripts/import_events_rally_calendar.py --input-file "INTERNATIONAL RALLY CALENDAR 2027-3.docx" --dry-run
    python scripts/import_events_rally_calendar.py --input-file calendar.docx --profile nonprofit-deploy
    python scripts/import_events_rally_calendar.py --input-file calendar.docx --status published --force
"""

from __future__ import annotations

import argparse
import re
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import boto3

from import_events_stan import generate_slug
from shared.event_dedup import check_duplicate, format_dry_run_result

EVENT_TYPE: str = "internationaal_treffen"
EVENT_CATEGORY: str = "rally"
PARTICIPATION: str = "open"
LINKED_REGIO: str = "regio_all"
# Registry enum for import_source has no docx/calendar value; 'manual' is the closest valid one.
IMPORT_SOURCE: str = "manual"

MONTHS: dict[str, int] = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}

YEAR_PATTERN: re.Pattern[str] = re.compile(r"^\d{4}$")
# Day part at the start of a line: "27 - 28", "30 – 1", "2- 4", "12 -15", "24"
DAY_PATTERN: re.Pattern[str] = re.compile(r"^(\d{1,2})(?:\s*[-–—]\s*(\d{1,2}))?(?!\d)")
# Columns are separated by tabs or by runs of 2+ spaces (a few lines use spaces)
COLUMN_SPLIT: re.Pattern[str] = re.compile(r"\t+|\s{2,}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import the international rally calendar DOCX into the Events table.",
    )
    parser.add_argument("--input-file", required=True, help="Path to the calendar .docx")
    parser.add_argument("--year", type=int, default=2027, help="Starting year (default: 2027)")
    parser.add_argument("--profile", default="nonprofit-deploy", help="AWS profile (default: nonprofit-deploy)")
    parser.add_argument("--table", default="Events", help="DynamoDB table (default: Events)")
    parser.add_argument("--status", default="draft", choices=["draft", "published", "archived"],
                        help="Status for imported events (default: draft)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen, write nothing")
    parser.add_argument("--force", action="store_true", help="Skip duplicate check against existing events")
    return parser.parse_args()


def add_month(year: int, month: int) -> tuple[int, int]:
    """Return (year, month) of the month after the given one."""
    return (year + 1, 1) if month == 12 else (year, month + 1)


def parse_calendar(lines: list[str], start_year: int) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Parse calendar lines into raw rally dicts.

    Returns:
        (rallies, notes). Each rally has name, location, start_date, end_date (optional).
        notes lists lines that were skipped or look suspicious.
    """
    rallies: list[dict[str, Any]] = []
    notes: list[str] = []
    year: int = start_year
    month: int | None = None
    seen_wraps: set[tuple[str, int, int]] = set()

    for raw in lines:
        text: str = raw.strip()
        if not text:
            continue

        if text.lower() in MONTHS:
            month = MONTHS[text.lower()]
            continue

        if YEAR_PATTERN.match(text):
            year = int(text)
            month = None
            continue

        match = DAY_PATTERN.match(text)
        if match is None:
            continue  # title, column header, stray punctuation

        if month is None:
            notes.append(f"No month for line, skipped: {text!r}")
            continue

        start_day: int = int(match.group(1))
        end_day: int | None = int(match.group(2)) if match.group(2) else None
        columns: list[str] = [c.strip() for c in COLUMN_SPLIT.split(text[match.end():].strip()) if c.strip()]
        if not columns:
            notes.append(f"No rally name, skipped: {text!r}")
            continue

        name: str = columns[0]
        location: str = columns[1] if len(columns) > 1 else ""
        if location.upper() == "TBC":
            location = ""

        # Range crossing a month boundary: end day < start day -> ends next month.
        end_year, end_month = year, month
        if end_day is not None and end_day < start_day:
            key = (name.lower(), start_day, end_day)
            if key in seen_wraps:
                notes.append(f"Dropped repeat of cross-month line under {text.split()[0]}: {name}")
                continue
            seen_wraps.add(key)
            end_year, end_month = add_month(year, month)

        try:
            start = date(year, month, start_day)
            end = date(end_year, end_month, end_day) if end_day is not None else None
        except ValueError as e:
            notes.append(f"Invalid date ({e}), skipped: {text!r}")
            continue

        if end is not None and end < start:
            notes.append(f"End before start, skipped: {text!r}")
            continue

        rallies.append({
            "name": name,
            "location": location,
            "start_date": start.isoformat(),
            "end_date": end.isoformat() if end is not None else None,
        })

    return rallies, notes


def build_item(rally: dict[str, Any], status: str) -> dict[str, Any]:
    """Build the DynamoDB item using Events registry field names."""
    item: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "name": rally["name"],
        "slug": f"{generate_slug(rally['name'])}-{rally['start_date'][:4]}",
        "event_type": EVENT_TYPE,
        "event_category": EVENT_CATEGORY,
        "participation": PARTICIPATION,
        "linked_regio": LINKED_REGIO,
        "start_date": rally["start_date"],
        "status": status,
        "import_source": IMPORT_SOURCE,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if rally["end_date"]:
        item["end_date"] = rally["end_date"]
    if rally["location"]:
        item["location"] = rally["location"]
    return item


def main() -> None:
    args: argparse.Namespace = parse_args()

    path: Path = Path(args.input_file)
    if not path.exists():
        print(f"\n  ✗ File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    try:
        import docx  # python-docx
    except ImportError:
        print("\n  ✗ python-docx is required: pip install python-docx", file=sys.stderr)
        sys.exit(1)

    lines: list[str] = [p.text for p in docx.Document(str(path)).paragraphs]
    rallies, notes = parse_calendar(lines, args.year)

    print(f"\n[import_events_rally_calendar] Parsed {len(rallies)} rally(ies) from '{args.input_file}'")
    for note in notes:
        print(f"  ⚠ {note}")
    if not rallies:
        print("  ✗ Nothing to import.", file=sys.stderr)
        sys.exit(1)

    table: Any = None
    if not (args.dry_run and args.force):
        try:
            session = boto3.Session(profile_name=args.profile, region_name="eu-west-1")
            table = session.resource("dynamodb").Table(args.table)
            table.load()
        except Exception as e:
            print(f"\n  ✗ Failed to connect to DynamoDB: {e}", file=sys.stderr)
            sys.exit(1)

    mode: str = "DRY-RUN" if args.dry_run else "LIVE"
    print(f"\n[import_events_rally_calendar] Processing ({mode}), status={args.status}, force={args.force}\n")

    created = skipped = errors = 0
    total: int = len(rallies)

    for index, rally in enumerate(rallies, start=1):
        prefix: str = f"  [{index}/{total}]"
        item: dict[str, Any] = build_item(rally, args.status)
        range_label: str = rally["start_date"] + (f" → {rally['end_date']}" if rally["end_date"] else "")

        if not args.force:
            match = check_duplicate(
                name=rally["name"], start_date=rally["start_date"],
                location=rally["location"], table=table,
            )
            if match is not None:
                print(f"{prefix} ⚠ SKIPPED (duplicate): '{rally['name']}' ({range_label}) "
                      f"matches '{match.get('name', '?')}' (id: {match.get('event_id', '?')})")
                skipped += 1
                continue

        if args.dry_run:
            print(f"{prefix} ✓ WOULD CREATE: '{rally['name']}' | {range_label} | {rally['location'] or '(no location)'}")
            created += 1
            continue

        try:
            table.put_item(Item=item)
            print(f"{prefix} ✓ CREATED: '{rally['name']}' ({range_label}) id: {item['event_id']}")
            created += 1
        except Exception as e:
            print(f"{prefix} ✗ ERROR writing '{rally['name']}': {e}")
            errors += 1

    print(f"\n{'=' * 60}")
    print(f"  Mode: {mode} | Total: {total} | Created: {created} | Skipped: {skipped} | Errors: {errors}")
    print(f"{'=' * 60}\n")

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
