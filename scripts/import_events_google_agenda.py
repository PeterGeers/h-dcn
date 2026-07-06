"""
Import events from Google Calendar into the DynamoDB Events table.

Reads events via Google Calendar API v3 using a service account,
maps Google Calendar fields to the Events schema, performs duplicate
detection, and writes new events to DynamoDB.

Usage:
    python scripts/import_events_google_agenda.py
    python scripts/import_events_google_agenda.py --dry-run
    python scripts/import_events_google_agenda.py --calendar-id my-calendar@group.calendar.google.com
    python scripts/import_events_google_agenda.py --profile nonprofit-deploy --status published
    python scripts/import_events_google_agenda.py --force --max-results 50
    python scripts/import_events_google_agenda.py --credentials path/to/creds.json

Field mapping (Google Calendar → DynamoDB Events):
    summary         → name
    start.dateTime  → start_date (normalized to YYYY-MM-DD)
    start.date      → start_date (all-day events, already YYYY-MM-DD)
    end.dateTime    → end_date (normalized to YYYY-MM-DD)
    end.date        → end_date (all-day events, already YYYY-MM-DD)
    location        → location
    description     → description
    id              → google_calendar_event_id

Generated fields: event_id (UUID), slug, created_at, import_source='google'
"""

from __future__ import annotations

import argparse
import mimetypes
import re
import sys
import uuid
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urlparse

import boto3
import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from shared.event_dedup import check_duplicate, format_dry_run_result

# Characters allowed in slugs (lowercase alphanumeric + hyphens)
SLUG_STRIP_PATTERN: re.Pattern[str] = re.compile(r"[^a-z0-9\-]")
SLUG_MULTI_HYPHEN: re.Pattern[str] = re.compile(r"-{2,}")

VALID_STATUSES: list[str] = ["draft", "published", "archived"]

# Google Calendar API scope (read-only)
CALENDAR_SCOPES: list[str] = ["https://www.googleapis.com/auth/calendar.readonly"]

# Image extensions recognized as posters
IMAGE_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# Regex to find image URLs in event descriptions
IMAGE_URL_PATTERN: re.Pattern[str] = re.compile(
    r"https?://[^\s<>\"']+\.(?:jpg|jpeg|png|webp|gif)",
    re.IGNORECASE,
)

# S3 bucket and URL prefix for event posters
S3_POSTER_BUCKET: str = "h-dcn-data-506221081911"
S3_POSTER_PREFIX: str = "event-posters"
S3_POSTER_URL_BASE: str = (
    f"https://{S3_POSTER_BUCKET}.s3.eu-west-1.amazonaws.com/{S3_POSTER_PREFIX}"
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Import events from Google Calendar into the DynamoDB Events table.",
    )
    parser.add_argument(
        "--calendar-id",
        default="primary",
        help="Google Calendar ID to import from (default: primary)",
    )
    parser.add_argument(
        "--credentials",
        default=".googleCredentials.json",
        help="Path to Google service account credentials JSON (default: .googleCredentials.json)",
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
        "--time-min",
        default=None,
        help="Only import events after this date (ISO format YYYY-MM-DD, default: today)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=100,
        help="Maximum number of events to fetch from Google Calendar (default: 100)",
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


def normalize_date(date_field: dict[str, str]) -> str:
    """
    Normalize a Google Calendar date field to YYYY-MM-DD.

    Google Calendar events have either:
    - 'dateTime': ISO 8601 with timezone (e.g. '2026-05-15T10:00:00+02:00')
    - 'date': date only for all-day events (e.g. '2026-05-15')

    Returns the date portion as YYYY-MM-DD string.
    """
    if "date" in date_field:
        # All-day event: already in YYYY-MM-DD format
        return date_field["date"]

    if "dateTime" in date_field:
        # Timed event: extract date portion from ISO datetime
        dt_str: str = date_field["dateTime"]
        # Parse ISO 8601 datetime — take the date part (first 10 chars)
        return dt_str[:10]

    # Fallback: should not happen with valid Google Calendar data
    return ""


def extract_poster_url(google_event: dict[str, Any]) -> str | None:
    """
    Extract a poster image URL from a Google Calendar event.

    Checks two sources in order of priority:
    1. Event attachments (prefer image/* mimeType)
    2. Image URL embedded in the description field (regex for common extensions)

    Returns the poster URL or None if no poster is found.
    """
    # Priority 1: Check attachments array for image files
    attachments: list[dict[str, Any]] = google_event.get("attachments", [])
    for attachment in attachments:
        mime_type: str = attachment.get("mimeType", "")
        file_url: str = attachment.get("fileUrl", "")
        if mime_type.startswith("image/") and file_url:
            return file_url

    # Priority 2: Regex in description for image URLs
    description: str | None = google_event.get("description")
    if description:
        match: re.Match[str] | None = IMAGE_URL_PATTERN.search(description)
        if match:
            return match.group(0)

    return None


def _get_extension_from_url(url: str, content_type: str | None = None) -> str:
    """
    Determine the file extension from a URL path or Content-Type header.

    Falls back to '.jpg' if nothing can be determined.
    """
    # Try URL path first
    parsed_path: str = urlparse(url).path
    for ext in IMAGE_EXTENSIONS:
        if parsed_path.lower().endswith(ext):
            return ext

    # Try Content-Type header
    if content_type:
        ext_guess: str | None = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext_guess and ext_guess in IMAGE_EXTENSIONS:
            return ext_guess
        # Map common content types manually
        ct_lower: str = content_type.lower()
        if "jpeg" in ct_lower or "jpg" in ct_lower:
            return ".jpg"
        if "png" in ct_lower:
            return ".png"
        if "webp" in ct_lower:
            return ".webp"
        if "gif" in ct_lower:
            return ".gif"

    # Default fallback
    return ".jpg"


def download_and_upload_poster(
    url: str,
    slug: str,
    session: boto3.Session,
) -> str | None:
    """
    Download a poster image from a URL and upload it to S3.

    Args:
        url: The poster image URL to download.
        slug: The event slug (used as the S3 object key basename).
        session: boto3 Session with appropriate credentials.

    Returns:
        The public S3 URL of the uploaded poster, or None on failure.
    """
    try:
        response: requests.Response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"      ⚠ Failed to download poster from '{url}': {e}")
        return None

    content_type: str = response.headers.get("Content-Type", "image/jpeg")
    ext: str = _get_extension_from_url(url, content_type)
    image_data: bytes = response.content

    if not image_data:
        print(f"      ⚠ Empty response body from poster URL: {url}")
        return None

    s3_key: str = f"{S3_POSTER_PREFIX}/{slug}{ext}"
    # Use the actual content type for S3, default to jpeg if unknown
    s3_content_type: str = content_type.split(";")[0].strip()
    if not s3_content_type.startswith("image/"):
        s3_content_type = f"image/{ext.lstrip('.')}"

    try:
        s3_client = session.client("s3")
        s3_client.put_object(
            Bucket=S3_POSTER_BUCKET,
            Key=s3_key,
            Body=image_data,
            ContentType=s3_content_type,
            CacheControl="public, max-age=86400",
        )
    except Exception as e:
        print(f"      ⚠ Failed to upload poster to S3 (key: {s3_key}): {e}")
        return None

    s3_url: str = f"{S3_POSTER_URL_BASE}/{slug}{ext}"
    return s3_url


def fetch_google_calendar_events(
    credentials_path: str,
    calendar_id: str,
    time_min: str | None,
    max_results: int,
) -> list[dict[str, Any]]:
    """
    Fetch events from Google Calendar API.

    Args:
        credentials_path: Path to service account JSON file.
        calendar_id: Google Calendar ID.
        time_min: Only events after this date (ISO format), or None for today.
        max_results: Maximum number of events to return.

    Returns:
        List of Google Calendar event objects.

    Raises:
        SystemExit on authentication or API errors.
    """
    # Determine time_min (default: today at 00:00 UTC)
    if time_min is None:
        time_min_dt: str = date.today().isoformat() + "T00:00:00Z"
    else:
        time_min_dt = time_min + "T00:00:00Z"

    try:
        creds: Credentials = Credentials.from_service_account_file(
            credentials_path,
            scopes=CALENDAR_SCOPES,
        )
    except Exception as e:
        print(f"\n  ✗ Failed to load credentials from '{credentials_path}': {e}", file=sys.stderr)
        sys.exit(1)

    try:
        service = build("calendar", "v3", credentials=creds)
    except Exception as e:
        print(f"\n  ✗ Failed to build Google Calendar service: {e}", file=sys.stderr)
        sys.exit(1)

    all_events: list[dict[str, Any]] = []
    page_token: str | None = None

    try:
        while True:
            request_kwargs: dict[str, Any] = {
                "calendarId": calendar_id,
                "timeMin": time_min_dt,
                "maxResults": min(max_results - len(all_events), 250),
                "singleEvents": True,
                "orderBy": "startTime",
                # Include attachments in response (required for poster detection)
                "supportsAttachments": True,
            }
            if page_token:
                request_kwargs["pageToken"] = page_token

            response: dict[str, Any] = (
                service.events().list(**request_kwargs).execute()
            )

            items: list[dict[str, Any]] = response.get("items", [])
            all_events.extend(items)

            # Stop if we have enough or no more pages
            if len(all_events) >= max_results:
                all_events = all_events[:max_results]
                break

            page_token = response.get("nextPageToken")
            if not page_token:
                break

    except Exception as e:
        print(f"\n  ✗ Failed to fetch events from Google Calendar: {e}", file=sys.stderr)
        sys.exit(1)

    return all_events


def validate_google_event(event: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate a Google Calendar event has the minimum required fields.

    Required: summary (name) and start (date).

    Returns:
        Tuple of (is_valid, list of error messages).
    """
    errors: list[str] = []

    summary: str | None = event.get("summary")
    if not summary or not summary.strip():
        errors.append("Missing 'summary' (event name)")

    start: dict[str, str] | None = event.get("start")
    if not start:
        errors.append("Missing 'start' field")
    elif not start.get("dateTime") and not start.get("date"):
        errors.append("'start' has neither 'dateTime' nor 'date'")

    is_valid: bool = len(errors) == 0
    return is_valid, errors


def build_event_item(
    google_event: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    """
    Build a DynamoDB Events item from a Google Calendar event.

    Maps Google Calendar fields to the Events schema and generates
    required fields (event_id, slug, created_at).
    """
    name: str = google_event["summary"].strip()
    start_date: str = normalize_date(google_event["start"])
    google_event_id: str = google_event["id"]

    item: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "name": name,
        "slug": generate_slug(name),
        "start_date": start_date,
        "status": status,
        "import_source": "google",
        "google_calendar_event_id": google_event_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # end_date (optional — may not be present for single-moment events)
    end_field: dict[str, str] | None = google_event.get("end")
    if end_field:
        end_date: str = normalize_date(end_field)
        if end_date:
            item["end_date"] = end_date

    # location (optional)
    location: str | None = google_event.get("location")
    if location and location.strip():
        item["location"] = location.strip()

    # description (optional)
    description: str | None = google_event.get("description")
    if description and description.strip():
        item["description"] = description.strip()

    return item


def check_existing_google_event(
    google_event_id: str,
    table: Any,
) -> dict[str, Any] | None:
    """
    Check if an event with this google_calendar_event_id already exists.

    Scans the table for an exact match on the google_calendar_event_id field.
    This prevents re-importing the same Google Calendar event.

    Returns the existing event dict if found, None otherwise.
    """
    scan_kwargs: dict[str, Any] = {
        "FilterExpression": "#gceid = :gceid_val",
        "ExpressionAttributeNames": {"#gceid": "google_calendar_event_id"},
        "ExpressionAttributeValues": {":gceid_val": google_event_id},
    }

    response: dict[str, Any] = table.scan(**scan_kwargs)
    items: list[dict[str, Any]] = response.get("Items", [])

    # Handle pagination (unlikely for single ID match, but correct)
    while "LastEvaluatedKey" in response:
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))

    if items:
        return items[0]
    return None


def main() -> None:
    """Main entry point for Google Calendar event import."""
    args: argparse.Namespace = parse_args()

    # Fetch events from Google Calendar
    print(f"\n[import_events_google_agenda] Fetching events from Google Calendar...")
    print(f"  Calendar ID:  {args.calendar_id}")
    print(f"  Credentials:  {args.credentials}")
    print(f"  Time min:     {args.time_min or '(today)'}")
    print(f"  Max results:  {args.max_results}")

    google_events: list[dict[str, Any]] = fetch_google_calendar_events(
        credentials_path=args.credentials,
        calendar_id=args.calendar_id,
        time_min=args.time_min,
        max_results=args.max_results,
    )
    print(f"  Fetched {len(google_events)} event(s) from Google Calendar")

    if not google_events:
        print("\n  No events to import. Exiting.")
        sys.exit(0)

    # Connect to DynamoDB
    session: boto3.Session | None = None
    table: Any = None
    if not args.dry_run or not args.force:
        print(f"\n[import_events_google_agenda] Connecting to DynamoDB...")
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
    print(f"\n[import_events_google_agenda] Processing events ({mode_label})...")
    print(f"  Status:  {args.status}")
    print(f"  Force:   {args.force}")
    print()

    created: int = 0
    skipped: int = 0
    errors: int = 0

    for index, google_event in enumerate(google_events):
        event_name: str = google_event.get("summary", "(unnamed)").strip()
        google_id: str = google_event.get("id", "?")
        prefix: str = f"  [{index + 1}/{len(google_events)}]"

        # Validate
        is_valid, validation_errors = validate_google_event(google_event)
        if not is_valid:
            print(f"{prefix} ✗ INVALID: '{event_name}' (Google ID: {google_id})")
            for err in validation_errors:
                print(f"           {err}")
            errors += 1
            continue

        # Build the DynamoDB item
        item: dict[str, Any] = build_event_item(google_event, args.status)

        # Poster detection
        poster_source_url: str | None = extract_poster_url(google_event)
        if poster_source_url:
            if args.dry_run:
                print(f"           🖼 Poster found: {poster_source_url}")
            else:
                # Download and upload poster to S3
                if session is not None:
                    s3_poster_url: str | None = download_and_upload_poster(
                        url=poster_source_url,
                        slug=item["slug"],
                        session=session,
                    )
                    if s3_poster_url:
                        item["poster_url"] = s3_poster_url
                        print(f"           🖼 Poster uploaded: {s3_poster_url}")
                    # Failure is logged inside download_and_upload_poster — continue without poster

        # Duplicate check (unless --force)
        if not args.force and table is not None:
            # First: check by google_calendar_event_id (exact re-import detection)
            existing_by_google_id: dict[str, Any] | None = check_existing_google_event(
                google_event_id=google_id,
                table=table,
            )

            if existing_by_google_id is not None:
                existing_name: str = existing_by_google_id.get("name", "?")
                existing_id: str = existing_by_google_id.get("event_id", "?")
                if args.dry_run:
                    print(
                        f"{prefix} ⚠ DUPLICATE (Google ID): '{event_name}' "
                        f"already imported as '{existing_name}' (id: {existing_id})"
                    )
                else:
                    print(
                        f"{prefix} ⚠ SKIPPED (Google ID match): '{event_name}' "
                        f"matches '{existing_name}' (id: {existing_id})"
                    )
                skipped += 1
                continue

            # Second: fuzzy duplicate check (name + date + location)
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
                existing_name = match.get("name", "?")
                existing_id = match.get("event_id", "?")
                print(
                    f"{prefix} ⚠ SKIPPED (fuzzy duplicate): '{event_name}' "
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
            print(
                f"{prefix} ✓ CREATED: '{event_name}' "
                f"(id: {item['event_id']}, google_id: {google_id})"
            )
            created += 1
        except Exception as e:
            print(f"{prefix} ✗ ERROR writing '{event_name}': {e}")
            errors += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"  IMPORT SUMMARY")
    print(f"{'='*60}")
    print(f"  Mode:        {'DRY-RUN (no writes)' if args.dry_run else 'LIVE'}")
    print(f"  Source:      Google Calendar ({args.calendar_id})")
    print(f"  Total:       {len(google_events)}")
    print(f"  Created:     {created}")
    print(f"  Skipped:     {skipped} (duplicates)")
    print(f"  Errors:      {errors} (validation/write failures)")
    print(f"{'='*60}\n")

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
