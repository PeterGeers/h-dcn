"""
Verify that the event-member-index GSI on Orders-Test works correctly.

Steps:
1. Put a test item into Orders-Test with order_id, source_id, and member_id
2. Query GSI by source_id + member_id (PK + SK)
3. Query GSI by source_id only (PK-only)
4. Clean up: delete the test item

Usage:
    python backend/scripts/verify_gsi.py
"""

import boto3
from boto3.dynamodb.conditions import Key

TABLE_NAME = "Orders-Test"
GSI_NAME = "event-member-index"
REGION = "eu-west-1"
PROFILE = "nonprofit-deploy"

# Test data
TEST_ITEM = {
    "order_id": "test-verify-gsi-001",
    "source_id": "test-event-uuid-123",
    "member_id": "test-member-uuid-456",
    "status": "draft",
    "items": [],
}


def main():
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    dynamodb = session.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)

    print(f"=== GSI Verification: {GSI_NAME} on {TABLE_NAME} ===\n")

    # Step 1: Put test item
    print("1. Putting test item...")
    table.put_item(Item=TEST_ITEM)
    print(f"   ✓ Item written: order_id={TEST_ITEM['order_id']}")

    success = True

    try:
        # Step 2: Query GSI by source_id + member_id (PK + SK)
        print("\n2. Querying GSI by source_id + member_id (PK + SK)...")
        response = table.query(
            IndexName=GSI_NAME,
            KeyConditionExpression=(
                Key("source_id").eq(TEST_ITEM["source_id"])
                & Key("member_id").eq(TEST_ITEM["member_id"])
            ),
        )
        items = response.get("Items", [])
        if len(items) == 1 and items[0]["order_id"] == TEST_ITEM["order_id"]:
            print(f"   ✓ Found 1 item: order_id={items[0]['order_id']}")
        else:
            print(f"   ✗ UNEXPECTED: got {len(items)} items: {items}")
            success = False

        # Step 3: Query GSI by source_id only (PK-only)
        print("\n3. Querying GSI by source_id only (PK-only)...")
        response = table.query(
            IndexName=GSI_NAME,
            KeyConditionExpression=Key("source_id").eq(TEST_ITEM["source_id"]),
        )
        items = response.get("Items", [])
        if any(item["order_id"] == TEST_ITEM["order_id"] for item in items):
            print(f"   ✓ Found test item among {len(items)} result(s)")
        else:
            print(f"   ✗ UNEXPECTED: test item not found in {len(items)} results")
            success = False

    finally:
        # Step 4: Clean up
        print("\n4. Cleaning up: deleting test item...")
        table.delete_item(Key={"order_id": TEST_ITEM["order_id"]})
        print(f"   ✓ Deleted: order_id={TEST_ITEM['order_id']}")

    # Final result
    print("\n" + "=" * 50)
    if success:
        print("✓ GSI VERIFICATION PASSED — event-member-index works correctly")
    else:
        print("✗ GSI VERIFICATION FAILED — see errors above")

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
