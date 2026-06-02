"""Upload club_registry.json to S3 reports bucket at presmeet/club_registry.json."""
import argparse
import json
import os
import sys

import boto3

PROFILE = 'nonprofit-deploy'
REGION = 'eu-west-1'
BUCKET = 'h-dcn-reports'
S3_KEY = 'presmeet/club_registry.json'

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FILE = os.path.join(SCRIPT_DIR, 'data', 'club_registry.json')


def get_session(profile):
    return boto3.Session(profile_name=profile, region_name=REGION)


def validate_registry(data):
    """Basic validation of the club registry structure."""
    if 'version' not in data:
        raise ValueError("Missing 'version' field")
    if 'clubs' not in data or not isinstance(data['clubs'], list):
        raise ValueError("Missing or invalid 'clubs' array")
    for i, club in enumerate(data['clubs']):
        for field in ('club_id', 'club_name'):
            if field not in club:
                raise ValueError(f"Club at index {i} missing required field '{field}'")
    return True


def main():
    parser = argparse.ArgumentParser(description='Upload club_registry.json to S3')
    parser.add_argument(
        '--file', '-f',
        default=DEFAULT_FILE,
        help=f'Path to club_registry.json (default: {DEFAULT_FILE})'
    )
    parser.add_argument(
        '--profile', '-p',
        default=PROFILE,
        help=f'AWS CLI profile (default: {PROFILE})'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate and show what would be uploaded without actually uploading'
    )
    args = parser.parse_args()

    # Load and validate the registry file
    if not os.path.exists(args.file):
        print(f"ERROR: File not found: {args.file}")
        sys.exit(1)

    with open(args.file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    try:
        validate_registry(data)
    except ValueError as e:
        print(f"ERROR: Invalid registry structure: {e}")
        sys.exit(1)

    club_count = len(data['clubs'])
    print(f"Registry version: {data['version']}")
    print(f"Clubs: {club_count}")
    for club in data['clubs']:
        assigned = club.get('assigned_member_id')
        status = f"assigned to {assigned}" if assigned else "unassigned"
        print(f"  - {club['club_id']}: {club['club_name']} ({status})")

    print(f"\nTarget: s3://{BUCKET}/{S3_KEY}")
    print(f"Profile: {args.profile}")

    if args.dry_run:
        print("\n[DRY RUN] No upload performed.")
        return

    # Upload to S3
    session = get_session(args.profile)
    s3 = session.client('s3')

    body = json.dumps(data, indent=2, ensure_ascii=False)
    s3.put_object(
        Bucket=BUCKET,
        Key=S3_KEY,
        Body=body.encode('utf-8'),
        ContentType='application/json'
    )

    print(f"\nUploaded successfully to s3://{BUCKET}/{S3_KEY}")


if __name__ == '__main__':
    main()
