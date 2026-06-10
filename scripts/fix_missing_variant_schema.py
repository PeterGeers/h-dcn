#!/usr/bin/env python3
"""
Fix missing variant_schema on migrated products.

The initial migration assigned UUIDs and set is_parent=True, but did NOT:
- Convert opties → variant_schema on the parent record
- Create proper variant records (only Default_Variants were made)

This script:
1. Finds all parent products with opties but no variant_schema
2. Parses opties into variant_schema ({"Maat": ["S", "M", "L", ...]})
3. Sets variant_schema + legacy_opties on the parent
4. Deletes the existing Default_Variant(s) for that parent
5. Creates proper variant records with variant_attributes: {"Maat": "S"} etc.

Usage:
    python scripts/fix_missing_variant_schema.py --dry-run
    python scripts/fix_missing_variant_schema.py
"""

import argparse
import json
import logging
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Attr

REGION = "eu-west-1"
PROFILE = "nonprofit-deploy"
TABLE_NAME = "Producten"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_opties(opties_raw) -> dict | None:
    """Parse legacy opties into variant_schema.
    
    Returns {"Maat": ["S", "M", ...]} or None if empty/invalid.
    """
    if opties_raw is None:
        return None
    
    # Handle list type (some products have opties as [])
    if isinstance(opties_raw, list):
        if not opties_raw:
            return None
        # If it's a list of strings, treat them as values
        values = [str(v).strip() for v in opties_raw if str(v).strip()]
        if not values:
            return None
        return {"Maat": values}
    
    trimmed = str(opties_raw).strip()
    
    # Skip empty, whitespace-only, or "[]"
    if not trimmed or trimmed == "[]" or trimmed.lower() == "one size":
        return None
    
    values = [v.strip() for v in trimmed.split(",")]
    values = [v for v in values if v]
    
    if not values:
        return None
    
    return {"Maat": values}


def main():
    parser = argparse.ArgumentParser(description="Fix missing variant_schema on migrated products")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    ddb = session.resource('dynamodb')
    table = ddb.Table(TABLE_NAME)

    mode = "DRY RUN" if args.dry_run else "LIVE"
    logger.info(f"{'='*60}")
    logger.info(f"Fix Missing variant_schema [{mode}]")
    logger.info(f"{'='*60}")

    # Find parent products with opties but no variant_schema
    resp = table.scan(
        FilterExpression=(
            Attr('is_parent').eq(True) &
            Attr('opties').exists() &
            Attr('variant_schema').not_exists()
        )
    )
    products = resp['Items']
    
    # Handle pagination
    while 'LastEvaluatedKey' in resp:
        resp = table.scan(
            FilterExpression=(
                Attr('is_parent').eq(True) &
                Attr('opties').exists() &
                Attr('variant_schema').not_exists()
            ),
            ExclusiveStartKey=resp['LastEvaluatedKey']
        )
        products.extend(resp['Items'])

    logger.info(f"Found {len(products)} parent products needing fix")

    stats = {
        "updated": 0,
        "skipped_empty": 0,
        "variants_created": 0,
        "default_variants_deleted": 0,
        "errors": [],
    }

    for product in products:
        product_id = product['product_id']
        name = product.get('naam', product.get('name', 'unnamed'))
        opties_raw = product.get('opties')

        # Parse opties
        variant_schema = parse_opties(opties_raw)

        if variant_schema is None:
            # Empty opties — just mark as legacy, keep Default_Variant
            logger.info(f"  [SKIP] {product_id} ({name}): opties='{opties_raw}' → empty, keeping Default_Variant")
            if not args.dry_run:
                table.update_item(
                    Key={'product_id': product_id},
                    UpdateExpression='SET legacy_opties = :lo REMOVE opties',
                    ExpressionAttributeValues={':lo': str(opties_raw) if opties_raw else ''}
                )
            stats["skipped_empty"] += 1
            continue

        logger.info(f"  [FIX] {product_id} ({name}): opties='{opties_raw}' → {json.dumps(variant_schema)}")

        try:
            if not args.dry_run:
                # 1. Update parent: set variant_schema, legacy_opties, remove opties
                table.update_item(
                    Key={'product_id': product_id},
                    UpdateExpression='SET variant_schema = :vs, legacy_opties = :lo, updated_at = :ua REMOVE opties',
                    ExpressionAttributeValues={
                        ':vs': variant_schema,
                        ':lo': str(opties_raw),
                        ':ua': datetime.now(timezone.utc).isoformat(),
                    }
                )

                # 2. Delete existing Default_Variant(s) for this parent
                existing_variants = table.scan(
                    FilterExpression=Attr('parent_id').eq(product_id) & Attr('is_parent').eq(False)
                )
                for var in existing_variants['Items']:
                    table.delete_item(Key={'product_id': var['product_id']})
                    stats["default_variants_deleted"] += 1
                    logger.info(f"    Deleted Default_Variant: {var['product_id']}")

                # 3. Create proper variant records
                price = product.get('prijs', product.get('price', 0))
                for axis_name, values in variant_schema.items():
                    for value in values:
                        variant_id = str(uuid.uuid4())
                        variant_record = {
                            'product_id': variant_id,
                            'parent_id': product_id,
                            'is_parent': False,
                            'name': f"{name} - {value}",
                            'variant_attributes': {axis_name: value},
                            'price': price,
                            'stock': 0,
                            'sold_count': 0,
                            'allow_oversell': True,
                            'active': True,
                            'source': 'fix_migration',
                            'created_at': datetime.now(timezone.utc).isoformat(),
                        }
                        table.put_item(Item=variant_record)
                        stats["variants_created"] += 1

                logger.info(f"    Created {len(list(variant_schema.values())[0])} variants")

            else:
                # Dry run: just count
                total_values = sum(len(v) for v in variant_schema.values())
                stats["variants_created"] += total_values
                logger.info(f"    Would create {total_values} variants")

            stats["updated"] += 1

        except Exception as e:
            logger.error(f"    [ERR] {product_id}: {e}")
            stats["errors"].append({"product_id": product_id, "error": str(e)})

    logger.info(f"{'='*60}")
    logger.info(f"Results:")
    logger.info(f"  Products updated with variant_schema: {stats['updated']}")
    logger.info(f"  Products skipped (empty opties):      {stats['skipped_empty']}")
    logger.info(f"  Default_Variants deleted:             {stats['default_variants_deleted']}")
    logger.info(f"  New variants created:                 {stats['variants_created']}")
    logger.info(f"  Errors:                               {len(stats['errors'])}")
    logger.info(f"{'='*60}")

    if stats["errors"]:
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
