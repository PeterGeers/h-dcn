"""
Verify Google Service Account Connectivity

Tests all local Google integrations using the consolidated service account
(.googleCredentials.json). Run during key rotation to confirm the new key
works for all integrations before deleting the old one.

Feature: risk-management
Requirements: 2b.6

Usage:
    python scripts/verify_google_sa.py
"""

import json
import os
import sys
from pathlib import Path

# Find credentials file
CREDENTIALS_PATH = Path(__file__).parent.parent / '.googleCredentials.json'


def _load_credentials():
    """Load service account credentials from .googleCredentials.json."""
    if not CREDENTIALS_PATH.exists():
        print(f"ERROR: Credentials file not found: {CREDENTIALS_PATH}")
        sys.exit(1)

    from google.oauth2.service_account import Credentials
    return Credentials.from_service_account_file(
        str(CREDENTIALS_PATH),
        scopes=[
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/calendar.readonly',
        ],
    )


def test_gspread() -> bool:
    """Test gspread: read one row from a spreadsheet."""
    print("\n[1/4] Testing gspread (spreadsheets.readonly)...")
    try:
        import gspread
        credentials = _load_credentials()
        gc = gspread.authorize(credentials)
        # List spreadsheets to verify access (doesn't require a specific sheet)
        sheets = gc.openall()
        print(f"  OK — Found {len(sheets)} accessible spreadsheet(s)")
        if sheets:
            first = sheets[0]
            print(f"  First sheet: '{first.title}'")
            ws = first.sheet1
            row = ws.row_values(1)
            print(f"  First row: {row[:5]}{'...' if len(row) > 5 else ''}")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_calendar() -> bool:
    """Test Calendar API: list upcoming events."""
    print("\n[2/4] Testing Calendar API (calendar.readonly)...")
    try:
        from googleapiclient.discovery import build
        credentials = _load_credentials()
        service = build('calendar', 'v3', credentials=credentials, cache_discovery=False)
        events_result = service.events().list(
            calendarId='primary',
            maxResults=5,
            singleEvents=True,
            orderBy='startTime',
        ).execute()
        events = events_result.get('items', [])
        print(f"  OK — Found {len(events)} upcoming event(s)")
        for event in events[:3]:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(f"  - {start}: {event.get('summary', '(no title)')}")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_drive_list() -> bool:
    """Test Drive API: list files."""
    print("\n[3/4] Testing Drive API (drive.readonly)...")
    try:
        from googleapiclient.discovery import build
        credentials = _load_credentials()
        service = build('drive', 'v3', credentials=credentials, cache_discovery=False)
        results = service.files().list(
            pageSize=5,
            fields="files(id, name, mimeType)",
        ).execute()
        files = results.get('files', [])
        print(f"  OK — Found {len(files)} file(s)")
        for f in files[:3]:
            print(f"  - {f['name']} ({f['mimeType']})")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def test_drive_upload() -> bool:
    """Test Drive upload: create and delete a test file (drive.file)."""
    print("\n[4/4] Testing Drive upload (drive.file)...")
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaInMemoryUpload
        credentials = _load_credentials()
        service = build('drive', 'v3', credentials=credentials, cache_discovery=False)

        # Create a test file
        file_metadata = {
            'name': '_test_sa_verification.txt',
            'mimeType': 'text/plain',
        }
        media = MediaInMemoryUpload(
            b'Service account verification test file. Safe to delete.',
            mimetype='text/plain',
        )
        created = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,name',
        ).execute()
        file_id = created['id']
        print(f"  Created test file: {created['name']} (id: {file_id})")

        # Delete the test file
        service.files().delete(fileId=file_id).execute()
        print(f"  Deleted test file: {file_id}")
        print("  OK — Upload and delete succeeded")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


def main():
    print("=" * 60)
    print("Google Service Account Connectivity Verification")
    print(f"Credentials: {CREDENTIALS_PATH}")
    print("=" * 60)

    # Verify credentials file exists and is valid JSON
    try:
        with open(CREDENTIALS_PATH) as f:
            creds = json.load(f)
        print(f"Service account: {creds.get('client_email', 'unknown')}")
        print(f"Project: {creds.get('project_id', 'unknown')}")
    except Exception as e:
        print(f"ERROR: Cannot read credentials file: {e}")
        sys.exit(1)

    results = {
        'gspread': test_gspread(),
        'calendar': test_calendar(),
        'drive_list': test_drive_list(),
        'drive_upload': test_drive_upload(),
    }

    print("\n" + "=" * 60)
    print("RESULTS:")
    all_passed = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        icon = "+" if passed else "X"
        print(f"  [{icon}] {name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("All integrations verified successfully!")
    else:
        print("Some integrations FAILED. Check output above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
