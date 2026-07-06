"""
Sync event posters to a Google Drive album folder (museum).

Uploads event posters to a shared Google Drive folder named "H-DCN Event Posters".
This serves as a permanent archive (museum) — posters remain in the album
even if the event is deleted from DynamoDB.

Uses Google Drive API with a service account (more reliable than Google Photos API
for service accounts). The shared folder acts as the "album".

Usage:
    python scripts/sync_poster_to_google_photos.py --event-id <id>
    python scripts/sync_poster_to_google_photos.py --all-published
    python scripts/sync_poster_to_google_photos.py --all-published --dry-run
    python scripts/sync_poster_to_google_photos.py --event-id <id> --credentials path/to/creds.json

Trigger:
    - Called after poster_url is set/updated on an event
    - Or run as a periodic batch script with --all-published

Behavior:
    - Idempotent: checks if file with same name already exists before uploading
    - Poster file title: "{event_name} ({start_date}).{ext}"
    - Failure does NOT block event updates (non-critical operation)
    - Poster remains in album permanently (independent of event lifecycle)
"""

from __future__ import annotations

import argparse
import io
import sys
from typing import Any
from urllib.parse import urlparse

import boto3
import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Google Drive API scope — only files created by this app
DRIVE_SCOPES: list[str] = ["https://www.googleapis.com/auth/drive.file"]

# Album folder name in Google Drive
MUSEUM_FOLDER_NAME: str = "H-DCN Event Posters"

# Image extensions recognized as posters
IMAGE_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# Content type mapping for common image extensions
EXTENSION_CONTENT_TYPES: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Sync event posters to Google Drive album (museum).",
    )
    parser.add_argument(
        "--event-id",
        default=None,
        help="Specific event ID to sync poster for",
    )
    parser.add_argument(
        "--all-published",
        action="store_true",
        default=False,
        help="Sync all published events that have a poster_url",
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
        help="Show what would happen without uploading to Google Drive",
    )
    return parser.parse_args()


def get_extension_from_url(url: str) -> str:
    """
    Determine the file extension from a URL path.

    Falls back to '.jpg' if nothing can be determined.
    """
    parsed_path: str = urlparse(url).path
    for ext in IMAGE_EXTENSIONS:
        if parsed_path.lower().endswith(ext):
            return ext
    return ".jpg"


def get_content_type_for_extension(ext: str) -> str:
    """
    Get the MIME content type for a file extension.

    Falls back to 'image/jpeg' for unknown extensions.
    """
    return EXTENSION_CONTENT_TYPES.get(ext.lower(), "image/jpeg")


def build_poster_filename(event_name: str, start_date: str, ext: str) -> str:
    """
    Build the poster filename for the museum album.

    Format: "{event_name} ({start_date}).{ext}"
    Sanitizes the event name to remove characters problematic for filenames.
    """
    # Remove characters that are problematic in filenames
    safe_name: str = event_name.strip()
    for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        safe_name = safe_name.replace(char, '-')

    # Collapse multiple spaces/hyphens
    while '  ' in safe_name:
        safe_name = safe_name.replace('  ', ' ')
    while '--' in safe_name:
        safe_name = safe_name.replace('--', '-')

    safe_name = safe_name.strip(' -')

    return f"{safe_name} ({start_date}){ext}"


def get_drive_service(credentials_path: str) -> Any:
    """
    Build and return a Google Drive API service client.

    Uses a service account from the provided credentials file.

    Raises:
        SystemExit on authentication failure.
    """
    try:
        creds: Credentials = Credentials.from_service_account_file(
            credentials_path,
            scopes=DRIVE_SCOPES,
        )
    except Exception as e:
        print(f"\n  ✗ Failed to load credentials from '{credentials_path}': {e}", file=sys.stderr)
        sys.exit(1)

    try:
        service = build("drive", "v3", credentials=creds)
    except Exception as e:
        print(f"\n  ✗ Failed to build Google Drive service: {e}", file=sys.stderr)
        sys.exit(1)

    return service


def get_or_create_museum_folder(drive_service: Any) -> str:
    """
    Get the museum folder ID, creating it if it doesn't exist.

    Searches for a folder named MUSEUM_FOLDER_NAME owned by the service account.
    If not found, creates it.

    Returns:
        The Google Drive folder ID.
    """
    # Search for existing folder
    query: str = (
        f"name = '{MUSEUM_FOLDER_NAME}' "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )

    results: dict[str, Any] = drive_service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)",
        pageSize=1,
    ).execute()

    files: list[dict[str, Any]] = results.get("files", [])

    if files:
        folder_id: str = files[0]["id"]
        print(f"  📁 Found existing museum folder: {MUSEUM_FOLDER_NAME} (id: {folder_id})")
        return folder_id

    # Create the folder
    folder_metadata: dict[str, str] = {
        "name": MUSEUM_FOLDER_NAME,
        "mimeType": "application/vnd.google-apps.folder",
    }

    folder = drive_service.files().create(
        body=folder_metadata,
        fields="id",
    ).execute()

    folder_id = folder["id"]
    print(f"  📁 Created museum folder: {MUSEUM_FOLDER_NAME} (id: {folder_id})")
    return folder_id


def check_file_exists_in_folder(
    drive_service: Any,
    folder_id: str,
    filename: str,
) -> str | None:
    """
    Check if a file with the given name already exists in the folder.

    Returns the file ID if it exists, None otherwise.
    """
    # Escape single quotes in filename for the query
    escaped_name: str = filename.replace("'", "\\'")

    query: str = (
        f"name = '{escaped_name}' "
        f"and '{folder_id}' in parents "
        f"and trashed = false"
    )

    results: dict[str, Any] = drive_service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)",
        pageSize=1,
    ).execute()

    files: list[dict[str, Any]] = results.get("files", [])

    if files:
        return files[0]["id"]
    return None


def upload_poster_to_museum(
    poster_url: str,
    event_name: str,
    start_date: str,
    drive_service: Any | None = None,
    credentials_path: str = ".googleCredentials.json",
    folder_id: str | None = None,
) -> str | None:
    """
    Upload an event poster to the Google Drive museum folder.

    Downloads the poster from poster_url and uploads it to Google Drive.
    Idempotent: if a file with the same name already exists, returns its ID
    without re-uploading.

    Args:
        poster_url: Public URL of the poster image (typically an S3 URL).
        event_name: Name of the event (used in the filename).
        start_date: Start date of the event (YYYY-MM-DD, used in the filename).
        drive_service: Optional pre-built Drive service client.
        credentials_path: Path to Google service account credentials JSON.
        folder_id: Optional pre-resolved folder ID (avoids repeated lookups).

    Returns:
        The Google Drive file ID of the uploaded (or existing) poster,
        or None on failure.
    """
    # Build Drive service if not provided
    if drive_service is None:
        drive_service = get_drive_service(credentials_path)

    # Get or create the museum folder
    if folder_id is None:
        folder_id = get_or_create_museum_folder(drive_service)

    # Determine file extension and build filename
    ext: str = get_extension_from_url(poster_url)
    filename: str = build_poster_filename(event_name, start_date, ext)

    # Idempotency check: does this file already exist?
    existing_file_id: str | None = check_file_exists_in_folder(
        drive_service, folder_id, filename
    )
    if existing_file_id is not None:
        return existing_file_id

    # Download the poster image
    try:
        response: requests.Response = requests.get(poster_url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"      ⚠ Failed to download poster from '{poster_url}': {e}")
        return None

    image_data: bytes = response.content
    if not image_data:
        print(f"      ⚠ Empty response body from poster URL: {poster_url}")
        return None

    # Determine content type
    content_type: str = get_content_type_for_extension(ext)

    # Upload to Google Drive
    file_metadata: dict[str, Any] = {
        "name": filename,
        "parents": [folder_id],
    }

    media = MediaIoBaseUpload(
        io.BytesIO(image_data),
        mimetype=content_type,
        resumable=True,
    )

    try:
        uploaded_file: dict[str, Any] = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, webViewLink",
        ).execute()
    except Exception as e:
        print(f"      ⚠ Failed to upload poster to Google Drive: {e}")
        return None

    file_id: str = uploaded_file["id"]
    return file_id


def get_events_to_sync(
    table: Any,
    event_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Get events from DynamoDB that need poster syncing.

    If event_id is provided, fetches that single event.
    Otherwise, scans for all published events with a poster_url.

    Returns:
        List of event dicts with at minimum: event_id, name, start_date, poster_url.
    """
    if event_id is not None:
        # Fetch single event
        response: dict[str, Any] = table.get_item(Key={"event_id": event_id})
        item: dict[str, Any] | None = response.get("Item")
        if item is None:
            print(f"  ✗ Event not found: {event_id}", file=sys.stderr)
            return []
        if not item.get("poster_url"):
            print(f"  ⚠ Event '{item.get('name', event_id)}' has no poster_url — nothing to sync")
            return []
        return [item]

    # Scan for all published events with poster_url
    scan_kwargs: dict[str, Any] = {
        "FilterExpression": "#status = :published AND attribute_exists(#poster_url)",
        "ExpressionAttributeNames": {
            "#status": "status",
            "#poster_url": "poster_url",
        },
        "ExpressionAttributeValues": {
            ":published": "published",
        },
    }

    all_items: list[dict[str, Any]] = []
    response = table.scan(**scan_kwargs)
    all_items.extend(response.get("Items", []))

    # Handle pagination
    while "LastEvaluatedKey" in response:
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
        response = table.scan(**scan_kwargs)
        all_items.extend(response.get("Items", []))

    # Filter out events without poster_url (belt and suspenders)
    return [item for item in all_items if item.get("poster_url")]


def main() -> None:
    """Main entry point for Google Drive museum poster sync."""
    args: argparse.Namespace = parse_args()

    # Validate arguments
    if not args.event_id and not args.all_published:
        print(
            "\n  ✗ Must specify either --event-id or --all-published",
            file=sys.stderr,
        )
        sys.exit(1)

    mode_label: str = "DRY-RUN" if args.dry_run else "LIVE"
    print(f"\n[sync_poster_to_google_photos] Museum poster sync ({mode_label})")
    print(f"  Credentials: {args.credentials}")
    print(f"  Profile:     {args.profile}")
    print(f"  Table:       {args.table}")

    # Connect to DynamoDB
    print(f"\n  Connecting to DynamoDB...")
    try:
        session: boto3.Session = boto3.Session(
            profile_name=args.profile,
            region_name="eu-west-1",
        )
        dynamodb = session.resource("dynamodb")
        table = dynamodb.Table(args.table)
        table.load()
        print(f"  Table status: {table.table_status}")
    except Exception as e:
        print(f"\n  ✗ Failed to connect to DynamoDB: {e}", file=sys.stderr)
        sys.exit(1)

    # Get events to sync
    if args.event_id:
        print(f"\n  Fetching event: {args.event_id}")
    else:
        print(f"\n  Scanning for all published events with poster_url...")

    events: list[dict[str, Any]] = get_events_to_sync(table, args.event_id)
    print(f"  Found {len(events)} event(s) to process")

    if not events:
        print("\n  Nothing to sync. Exiting.")
        sys.exit(0)

    # Build Drive service (once for all events)
    drive_service: Any = None
    folder_id: str | None = None

    if not args.dry_run:
        print(f"\n  Connecting to Google Drive...")
        drive_service = get_drive_service(args.credentials)
        folder_id = get_or_create_museum_folder(drive_service)

    # Process events
    print(f"\n  Processing posters...\n")

    uploaded: int = 0
    skipped: int = 0
    errors: int = 0

    for index, event in enumerate(events):
        event_name: str = event.get("name", "(unnamed)")
        event_id: str = event.get("event_id", "?")
        start_date: str = event.get("start_date", "unknown")
        poster_url: str = event.get("poster_url", "")
        prefix: str = f"  [{index + 1}/{len(events)}]"

        if not poster_url:
            print(f"{prefix} ⚠ SKIP: '{event_name}' — no poster_url")
            skipped += 1
            continue

        ext: str = get_extension_from_url(poster_url)
        filename: str = build_poster_filename(event_name, start_date, ext)

        if args.dry_run:
            print(f"{prefix} 🖼 WOULD UPLOAD: '{filename}'")
            print(f"           Source: {poster_url}")
            uploaded += 1
            continue

        # Check if already exists (idempotent)
        existing_id: str | None = check_file_exists_in_folder(
            drive_service, folder_id, filename  # type: ignore[arg-type]
        )
        if existing_id is not None:
            print(f"{prefix} ✓ EXISTS: '{filename}' (id: {existing_id})")
            skipped += 1
            continue

        # Upload
        file_id: str | None = upload_poster_to_museum(
            poster_url=poster_url,
            event_name=event_name,
            start_date=start_date,
            drive_service=drive_service,
            folder_id=folder_id,
        )

        if file_id is not None:
            print(f"{prefix} ✓ UPLOADED: '{filename}' (id: {file_id})")
            uploaded += 1
        else:
            print(f"{prefix} ✗ FAILED: '{event_name}' — upload error")
            errors += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"  MUSEUM SYNC SUMMARY")
    print(f"{'='*60}")
    print(f"  Mode:      {'DRY-RUN (no uploads)' if args.dry_run else 'LIVE'}")
    print(f"  Total:     {len(events)}")
    print(f"  Uploaded:  {uploaded}")
    print(f"  Skipped:   {skipped} (already in museum or no poster)")
    print(f"  Errors:    {errors}")
    print(f"{'='*60}\n")

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
