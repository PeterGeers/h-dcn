"""
Migrate product image URLs from old private bucket to nonprofit bucket.

Replaces:
  https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com/product-images/...
With:
  https://h-dcn-data-506221081911.s3.eu-west-1.amazonaws.com/product-images/...

Usage:
  python scripts/migrate_image_urls_to_nonprofit_bucket.py --dry-run --profile nonprofit-deploy
  python scripts/migrate_image_urls_to_nonprofit_bucket.py --profile nonprofit-deploy

Idempotent: safe to re-run. Only updates records that still reference the old bucket.
"""

import argparse
import boto3
import sys

OLD_PREFIX = "https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com/"
NEW_PREFIX = "https://h-dcn-data-506221081911.s3.eu-west-1.amazonaws.com/"

TABLE_NAME = "Producten"
REGION = "eu-west-1"


def migrate(profile: str, dry_run: bool) -> int:
    session = boto3.Session(profile_name=profile, region_name=REGION)
    dynamodb = session.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)

    # Scan all products (with pagination)
    items = []
    response = table.scan()
    items.extend(response.get("Items", []))
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        items.extend(response.get("Items", []))

    mode = "[DRY-RUN]" if dry_run else "[APPLIED]"
    print(f"\n{mode} Scanning {TABLE_NAME} table...")
    print(f"  Total products scanned: {len(items)}")

    updated = 0
    skipped = 0
    errors = 0

    for item in items:
        product_id = item.get("product_id")
        images = item.get("images", [])

        if not images or not isinstance(images, list):
            skipped += 1
            continue

        # Check if any image URL needs updating
        new_images = []
        needs_update = False
        for img in images:
            if isinstance(img, str) and img.startswith(OLD_PREFIX):
                new_img = img.replace(OLD_PREFIX, NEW_PREFIX)
                new_images.append(new_img)
                needs_update = True
            else:
                new_images.append(img)

        if not needs_update:
            skipped += 1
            continue

        # Show what would change
        naam = item.get("naam", "?")
        print(f"\n  {naam} ({product_id}):")
        for old, new in zip(images, new_images):
            if old != new:
                print(f"    - {old}")
                print(f"    + {new}")

        if not dry_run:
            try:
                table.update_item(
                    Key={"product_id": product_id},
                    UpdateExpression="SET images = :imgs",
                    ExpressionAttributeValues={":imgs": new_images},
                )
                updated += 1
            except Exception as e:
                print(f"    ERROR: {e}")
                errors += 1
        else:
            updated += 1

    print(f"\n{mode} Summary:")
    print(f"  Scanned:  {len(items)}")
    print(f"  Updated:  {updated}")
    print(f"  Skipped:  {skipped}")
    print(f"  Errors:   {errors}")

    if errors > 0:
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Migrate product image URLs from old bucket to nonprofit bucket"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to DynamoDB",
    )
    parser.add_argument(
        "--profile",
        default="nonprofit-deploy",
        help="AWS profile to use (default: nonprofit-deploy)",
    )
    args = parser.parse_args()

    sys.exit(migrate(profile=args.profile, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
