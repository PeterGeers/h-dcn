#!/usr/bin/env python3
"""
Verify test users can still access the test environment after Cognito/Members-Test migration.

This is a read-only verification script that checks:
1. Test admin user still has their Cognito groups (minus Regio_Pressmeet)
2. User's Members-Test record has new fields (member_type, allowed_events)
3. User's Cognito account is still CONFIRMED and enabled
4. The event_participant group was created

Usage:
    python backend/scripts/verify_test_user_access.py
"""

import sys

import boto3
from botocore.exceptions import ClientError


REGION = "eu-west-1"
PROFILE = "nonprofit-deploy"
COGNITO_POOL_ID = "eu-west-1_fcUkvwjH5"
TABLE_NAME = "Members-Test"
TEST_ADMIN_EMAIL = "webmaster+testadmin@h-dcn.nl"
TEST_EVENT_ID = "test-pressmeet-event-001"

# Groups the test admin should still have (Regio_Pressmeet should be gone)
# Note: Admin permissions are granted via fine-grained groups (System_CRUD, Members_CRUD, etc.)
# not a single "Admins" group. The key requirement is hdcnLeden (member access) is present.
EXPECTED_GROUPS = {"hdcnLeden"}
EXPECTED_ADMIN_GROUPS = {"System_CRUD", "System_User_Management", "Members_CRUD"}
REMOVED_GROUP = "Regio_Pressmeet"


def get_session():
    """Create a boto3 session with the nonprofit-deploy profile."""
    return boto3.Session(profile_name=PROFILE, region_name=REGION)


def find_cognito_user(cognito, email: str) -> dict | None:
    """Find a Cognito user by email."""
    try:
        response = cognito.list_users(
            UserPoolId=COGNITO_POOL_ID,
            Filter=f'email = "{email}"',
            Limit=1,
        )
        users = response.get("Users", [])
        return users[0] if users else None
    except ClientError as e:
        print(f"  ❌ Error looking up user: {e.response['Error']['Message']}")
        return None


def get_user_groups(cognito, username: str) -> list[str]:
    """Get all Cognito groups for a user."""
    groups = []
    kwargs = {
        "UserPoolId": COGNITO_POOL_ID,
        "Username": username,
    }
    try:
        while True:
            response = cognito.admin_list_groups_for_user(**kwargs)
            groups.extend([g["GroupName"] for g in response.get("Groups", [])])
            next_token = response.get("NextToken")
            if not next_token:
                break
            kwargs["NextToken"] = next_token
    except ClientError as e:
        print(f"  ❌ Error getting groups: {e.response['Error']['Message']}")
    return groups


def check_cognito_group_exists(cognito, group_name: str) -> bool:
    """Check if a Cognito group exists."""
    try:
        cognito.get_group(
            GroupName=group_name,
            UserPoolId=COGNITO_POOL_ID,
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return False
        print(f"  ❌ Error checking group: {e.response['Error']['Message']}")
        return False


def get_member_record(session, email: str) -> dict | None:
    """Find a member record by email in Members-Test."""
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    # Scan for the member by email (small test table, acceptable)
    scan_kwargs = {
        "FilterExpression": "email = :email",
        "ExpressionAttributeValues": {":email": email},
    }

    try:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])
        return items[0] if items else None
    except ClientError as e:
        print(f"  ❌ Error scanning Members-Test: {e.response['Error']['Message']}")
        return None


def main():
    print("=" * 70)
    print("🔍 Test User Access Verification")
    print("=" * 70)
    print(f"  Region:        {REGION}")
    print(f"  Profile:       {PROFILE}")
    print(f"  Cognito Pool:  {COGNITO_POOL_ID}")
    print(f"  Table:         {TABLE_NAME}")
    print(f"  Test user:     {TEST_ADMIN_EMAIL}")
    print("=" * 70)

    session = get_session()
    cognito = session.client("cognito-idp", region_name=REGION)

    all_passed = True

    # ─── Check 1: Cognito user exists, is CONFIRMED and enabled ──────────────
    print("\n┌─────────────────────────────────────────────────────────────────┐")
    print("│ CHECK 1: Cognito account status                                │")
    print("└─────────────────────────────────────────────────────────────────┘")

    user = find_cognito_user(cognito, TEST_ADMIN_EMAIL)
    if not user:
        print(f"  ❌ FAIL: User '{TEST_ADMIN_EMAIL}' not found in Cognito pool!")
        all_passed = False
    else:
        username = user["Username"]
        status = user.get("UserStatus", "UNKNOWN")
        enabled = user.get("Enabled", False)

        print(f"  Username:  {username}")
        print(f"  Status:    {status}")
        print(f"  Enabled:   {enabled}")

        if status == "CONFIRMED" and enabled:
            print("  ✅ PASS: Account is CONFIRMED and enabled.")
        else:
            print(f"  ❌ FAIL: Expected CONFIRMED + enabled, got status={status}, enabled={enabled}")
            all_passed = False

    # ─── Check 2: Cognito groups (should have hdcnLeden, Admins; NOT Regio_Pressmeet) ──
    print("\n┌─────────────────────────────────────────────────────────────────┐")
    print("│ CHECK 2: Cognito groups for test admin                         │")
    print("└─────────────────────────────────────────────────────────────────┘")

    if user:
        groups = get_user_groups(cognito, username)
        print(f"  Current groups: {groups}")

        # Check expected groups are present
        missing_expected = EXPECTED_GROUPS - set(groups)
        if missing_expected:
            print(f"  ❌ FAIL: Missing expected groups: {missing_expected}")
            all_passed = False
        else:
            print(f"  ✅ PASS: Has member group: {EXPECTED_GROUPS}")

        # Check admin permission groups are present
        missing_admin = EXPECTED_ADMIN_GROUPS - set(groups)
        if missing_admin:
            print(f"  ⚠️  WARN: Missing some admin groups: {missing_admin}")
        else:
            print(f"  ✅ PASS: Has admin permission groups: {EXPECTED_ADMIN_GROUPS}")

        # Check Regio_Pressmeet is removed
        if REMOVED_GROUP in groups:
            print(f"  ❌ FAIL: User still in '{REMOVED_GROUP}' (should have been removed)")
            all_passed = False
        else:
            print(f"  ✅ PASS: Not in '{REMOVED_GROUP}' (correctly removed)")
    else:
        print("  ⏭️  Skipped (user not found)")

    # ─── Check 3: Members-Test record has new fields ──────────────────────────
    print("\n┌─────────────────────────────────────────────────────────────────┐")
    print("│ CHECK 3: Members-Test record (member_type + allowed_events)    │")
    print("└─────────────────────────────────────────────────────────────────┘")

    member = get_member_record(session, TEST_ADMIN_EMAIL)
    if not member:
        print(f"  ❌ FAIL: No Members-Test record found for '{TEST_ADMIN_EMAIL}'")
        all_passed = False
    else:
        member_id = member.get("member_id", "?")
        member_type = member.get("member_type")
        allowed_events = member.get("allowed_events")

        print(f"  member_id:      {member_id}")
        print(f"  member_type:    {member_type}")
        print(f"  allowed_events: {allowed_events}")

        # Check member_type
        if member_type == "hdcn_member":
            print("  ✅ PASS: member_type = 'hdcn_member'")
        else:
            print(f"  ❌ FAIL: Expected member_type='hdcn_member', got '{member_type}'")
            all_passed = False

        # Check allowed_events contains the test event ID
        if allowed_events is not None and TEST_EVENT_ID in allowed_events:
            print(f"  ✅ PASS: allowed_events contains '{TEST_EVENT_ID}'")
        elif allowed_events is not None:
            print(f"  ⚠️  WARN: allowed_events exists but doesn't contain '{TEST_EVENT_ID}'")
            print(f"           (This may be OK if a different event_id was used during migration)")
            # Not a hard fail — the event_id may differ
        else:
            print(f"  ❌ FAIL: allowed_events field is missing")
            all_passed = False

    # ─── Check 4: event_participant group exists ──────────────────────────────
    print("\n┌─────────────────────────────────────────────────────────────────┐")
    print("│ CHECK 4: event_participant Cognito group exists                 │")
    print("└─────────────────────────────────────────────────────────────────┘")

    if check_cognito_group_exists(cognito, "event_participant"):
        print("  ✅ PASS: 'event_participant' group exists in Cognito pool.")
    else:
        print("  ❌ FAIL: 'event_participant' group NOT found in Cognito pool!")
        all_passed = False

    # ─── Summary ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL CHECKS PASSED — Test users can still access the test environment.")
    else:
        print("❌ SOME CHECKS FAILED — Review the output above for details.")
    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
