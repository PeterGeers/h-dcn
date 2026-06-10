"""Fix Default_Variants: set allow_oversell=True for products without variant_schema.

These are simple products (pins, badges, stickers) that don't track per-variant stock.
Their Default_Variants were created with allow_oversell=False and stock=0, which blocks
add-to-cart (the system thinks they're out of stock).
"""
import boto3
import json
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

session = boto3.Session(profile_name='nonprofit-deploy', region_name='eu-west-1')
ddb = session.resource('dynamodb')
table = ddb.Table('Producten')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    mode = "DRY RUN" if args.dry_run else "LIVE"
    logger.info(f"Fix Default_Variant allow_oversell [{mode}]")

    # Find all parent products WITHOUT variant_schema (these use Default_Variants)
    resp = table.scan(
        FilterExpression=(
            boto3.dynamodb.conditions.Attr('is_parent').eq(True) &
            boto3.dynamodb.conditions.Attr('variant_schema').not_exists()
        )
    )
    parents = resp['Items']
    while 'LastEvaluatedKey' in resp:
        resp = table.scan(
            FilterExpression=(
                boto3.dynamodb.conditions.Attr('is_parent').eq(True) &
                boto3.dynamodb.conditions.Attr('variant_schema').not_exists()
            ),
            ExclusiveStartKey=resp['LastEvaluatedKey']
        )
        parents.extend(resp['Items'])

    logger.info(f"Found {len(parents)} parent products without variant_schema")

    fixed = 0
    for parent in parents:
        parent_id = parent['product_id']
        name = parent.get('naam', parent.get('name', 'unnamed'))

        # Find Default_Variant(s) for this parent
        var_resp = table.scan(
            FilterExpression=(
                boto3.dynamodb.conditions.Attr('parent_id').eq(parent_id) &
                boto3.dynamodb.conditions.Attr('is_parent').eq(False)
            )
        )

        for variant in var_resp['Items']:
            if not variant.get('allow_oversell', False):
                logger.info(f"  [FIX] {name}: variant {variant['product_id'][:8]}... -> allow_oversell=True")
                if not args.dry_run:
                    table.update_item(
                        Key={'product_id': variant['product_id']},
                        UpdateExpression='SET allow_oversell = :v',
                        ExpressionAttributeValues={':v': True}
                    )
                fixed += 1

    logger.info(f"Fixed {fixed} Default_Variants with allow_oversell=True")


if __name__ == "__main__":
    main()
