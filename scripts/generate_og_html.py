"""
H-DCN OG HTML Generator

Generates minimal HTML files with Open Graph meta tags for social media sharing.
These static files are served to social media bots by the CloudFront Function.

Usage as script:
    python scripts/generate_og_html.py --slug toerweekend-2026 --profile nonprofit-deploy

Usage as module:
    from scripts.generate_og_html import generate_og_html, upload_og_html
    html = generate_og_html(event)
    upload_og_html(slug, html, session)
"""

import argparse
import html as html_module
import logging
import sys
from typing import Any

import boto3

logger = logging.getLogger(__name__)

# Frontend bucket for OG HTML files (NOT the data bucket)
FRONTEND_BUCKET: str = 'h-dcn-frontend-506221081911'
PORTAL_BASE_URL: str = 'https://portal.h-dcn.nl'


def generate_og_html(event: dict[str, Any]) -> str:
    """
    Generate minimal HTML with OG meta tags for a published event.

    Args:
        event: DynamoDB event record with at least:
            - name (str): Event title
            - slug (str): URL-safe identifier
            - start_date (str): YYYY-MM-DD
            - end_date (str, optional): YYYY-MM-DD
            - location (str, optional): Event location
            - poster_url (str, optional): Full URL to poster image
            - description (str, optional): Short event description

    Returns:
        Complete HTML string with OG and Twitter Card meta tags.
    """
    name: str = event.get('name', 'H-DCN Event')
    slug: str = event.get('slug', '')
    start_date: str = event.get('start_date', '')
    end_date: str = event.get('end_date', start_date)
    location: str = event.get('location', '')
    poster_url: str = event.get('poster_url', '')
    description: str = event.get('description', '')

    # Build OG description from date + location
    og_description: str = _build_og_description(
        start_date=start_date,
        end_date=end_date,
        location=location,
        description=description,
    )

    canonical_url: str = f'{PORTAL_BASE_URL}/events/{slug}/info'

    # Escape all values for safe HTML embedding
    title_escaped: str = html_module.escape(name)
    description_escaped: str = html_module.escape(og_description)
    image_escaped: str = html_module.escape(poster_url)
    url_escaped: str = html_module.escape(canonical_url)

    return f'''<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="utf-8">
    <title>{title_escaped}</title>

    <!-- Open Graph -->
    <meta property="og:title" content="{title_escaped}">
    <meta property="og:description" content="{description_escaped}">
    <meta property="og:image" content="{image_escaped}">
    <meta property="og:url" content="{url_escaped}">
    <meta property="og:type" content="website">

    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title_escaped}">
    <meta name="twitter:description" content="{description_escaped}">
    <meta name="twitter:image" content="{image_escaped}">

    <!-- Redirect browsers to SPA -->
    <meta http-equiv="refresh" content="0;url={url_escaped}">
</head>
<body>
    <p><a href="{url_escaped}">{title_escaped}</a></p>
</body>
</html>'''


def _build_og_description(
    start_date: str,
    end_date: str,
    location: str,
    description: str,
) -> str:
    """
    Build a concise OG description from event date and location.

    Priority: date + location. Falls back to description if both are empty.
    """
    parts: list[str] = []

    if start_date:
        if end_date and end_date != start_date:
            parts.append(f'{_format_date(start_date)} - {_format_date(end_date)}')
        else:
            parts.append(_format_date(start_date))

    if location:
        parts.append(location)

    if parts:
        return ' • '.join(parts)

    # Fallback to description (truncated)
    if description:
        return description[:200]

    return 'H-DCN Event'


def _format_date(date_str: str) -> str:
    """
    Format YYYY-MM-DD to a readable Dutch date string.

    Returns the original string if parsing fails.
    """
    try:
        parts: list[str] = date_str[:10].split('-')
        if len(parts) == 3:
            day: str = parts[2].lstrip('0') or '0'
            months: list[str] = [
                'januari', 'februari', 'maart', 'april', 'mei', 'juni',
                'juli', 'augustus', 'september', 'oktober', 'november', 'december',
            ]
            month_idx: int = int(parts[1]) - 1
            if 0 <= month_idx < 12:
                return f'{day} {months[month_idx]} {parts[0]}'
        return date_str
    except (ValueError, IndexError):
        return date_str


def upload_og_html(slug: str, html_content: str, session: boto3.Session) -> None:
    """
    Upload the OG HTML file to S3 (frontend bucket).

    Path: events/{slug}/og.html

    Args:
        slug: Event URL slug
        html_content: Generated HTML string
        session: boto3 Session (with appropriate profile/credentials)
    """
    s3_client = session.client('s3')
    key: str = f'events/{slug}/og.html'

    s3_client.put_object(
        Bucket=FRONTEND_BUCKET,
        Key=key,
        Body=html_content.encode('utf-8'),
        ContentType='text/html',
        CacheControl='max-age=3600',
    )
    logger.info(f'Uploaded OG HTML to s3://{FRONTEND_BUCKET}/{key}')


def delete_og_html(slug: str, session: boto3.Session) -> None:
    """
    Delete the OG HTML file from S3 when an event is archived/deleted.

    Args:
        slug: Event URL slug
        session: boto3 Session
    """
    s3_client = session.client('s3')
    key: str = f'events/{slug}/og.html'

    try:
        s3_client.delete_object(Bucket=FRONTEND_BUCKET, Key=key)
        logger.info(f'Deleted OG HTML from s3://{FRONTEND_BUCKET}/{key}')
    except Exception as e:
        logger.warning(f'Failed to delete OG HTML for {slug}: {e}')


def generate_and_upload(event: dict[str, Any], session: boto3.Session) -> None:
    """
    Convenience function: generate OG HTML and upload to S3.

    Call this from handlers when an event status changes to 'published'.

    Args:
        event: DynamoDB event record
        session: boto3 Session
    """
    slug: str | None = event.get('slug')
    if not slug:
        logger.warning(f"Cannot generate OG HTML: event has no slug (event_id={event.get('event_id')})")
        return

    html_content: str = generate_og_html(event)
    upload_og_html(slug, html_content, session)


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------

def _fetch_event_from_dynamodb(slug: str, session: boto3.Session) -> dict[str, Any] | None:
    """Fetch a published event from DynamoDB by slug."""
    dynamodb = session.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table('Events')

    # Scan for the slug (Events table uses event_id as key, not slug)
    response = table.scan(
        FilterExpression='slug = :slug',
        ExpressionAttributeValues={':slug': slug},
        Limit=1,
    )
    items: list[dict[str, Any]] = response.get('Items', [])
    return items[0] if items else None


def main() -> None:
    """CLI entry point for generating OG HTML for a specific event."""
    parser = argparse.ArgumentParser(
        description='Generate OG HTML for an event and upload to S3'
    )
    parser.add_argument('--slug', required=True, help='Event slug (e.g., toerweekend-2026)')
    parser.add_argument('--profile', default='nonprofit-deploy', help='AWS profile name')
    parser.add_argument('--dry-run', action='store_true', help='Print HTML without uploading')
    parser.add_argument('--all-published', action='store_true', help='Generate for all published events')

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    session: boto3.Session = boto3.Session(profile_name=args.profile)

    if args.all_published:
        _generate_all_published(session, dry_run=args.dry_run)
        return

    event: dict[str, Any] | None = _fetch_event_from_dynamodb(args.slug, session)
    if not event:
        logger.error(f'Event with slug "{args.slug}" not found in DynamoDB')
        sys.exit(1)

    html_content: str = generate_og_html(event)

    if args.dry_run:
        print(html_content)
        print(f'\n--- Would upload to: s3://{FRONTEND_BUCKET}/events/{args.slug}/og.html ---')
    else:
        upload_og_html(args.slug, html_content, session)
        print(f'✓ Uploaded OG HTML for "{event.get("name")}" to S3')


def _generate_all_published(session: boto3.Session, dry_run: bool = False) -> None:
    """Generate OG HTML for all published events."""
    dynamodb = session.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table('Events')

    response = table.scan(
        FilterExpression='#s = :status',
        ExpressionAttributeNames={'#s': 'status'},
        ExpressionAttributeValues={':status': 'published'},
    )
    items: list[dict[str, Any]] = response.get('Items', [])

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression='#s = :status',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':status': 'published'},
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        items.extend(response.get('Items', []))

    logger.info(f'Found {len(items)} published events')
    generated: int = 0
    skipped: int = 0

    for event in items:
        slug: str | None = event.get('slug')
        if not slug:
            logger.warning(f"Skipping event {event.get('event_id')}: no slug")
            skipped += 1
            continue

        html_content: str = generate_og_html(event)

        if dry_run:
            print(f'  [DRY-RUN] {slug}: would upload {len(html_content)} bytes')
        else:
            upload_og_html(slug, html_content, session)

        generated += 1

    print(f'\n✓ Generated: {generated}, Skipped: {skipped}')


if __name__ == '__main__':
    main()
