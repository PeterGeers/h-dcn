#!/usr/bin/env python3
"""
Migrate Members table (add member_type, allowed_events) and clean up Cognito groups.

This script performs the member data migration and Cognito cleanup for the generic
event booking system:

1. Backfill `member_type = "hdcn_member"` on all Members records
2. Backfill `allowed_events = []` on all Members records
3. Migrate Regio_Pressmeet users: grant event access + remove from group
4. Create `event_participant` Cognito group
5. Delete `Regio_Pressmeet` Cognito group (remove all users first)

Prerequisites:
    - AWS profile `nonprofit-deploy` configured
    - The Members table must exist in the target account
    - Cognito user pool `eu-west-1_fcUkvwjH5` must exist

Usage:
    # Backfill member_type and allowed_events on test table
    python backend/scripts/migrate_members_and_cognito.py --stage test --backfill-members

    # Migrate Regio_Pressmeet users (requires --event-id)
    python backend/scripts/migrate_members_and_cognito.py --stage test --migrate-pressmeet --event-id <uuid>

    # Create event_participant Cognito group
    python backend/scripts/migrate_members_and_cognito.py --stage test --create-group

    # Delete Regio_Pressmeet group (removes all users first)
    python backend/scripts/migrate_members_and_cognito.py --stage test --delete-pressmeet-group

    # Run all operations
    python backend/scripts/migrate_members_and_cognito.py --stage test --all --event-id <uuid>

    # Dry run (show what would happen)
    python backend/scripts/migrate_members_and_cognito.py --stage test --all --event-id <uuid> --dry-run
"""

import argparse
import sys

import boto3
from botocore.exceptions import ClientError


REGION = "eu-west-1"
PROFILE = "nonprofit-deploy"
COGNITO_POOL_ID = "eu-west-1_fcUkvwjH5"

REGIO_PRESSMEET_GROUP = "Regio_Pressmeet"
EVENT_PARTICIPANT_GROUP = "event_participant"
EVENT_PARTICIPANT_DESCRIPTION = "External event participants with limited portal access"

STAGE_TABLE_MAP = {
    "test": "Members-Test",
    "prod": "Members",
}


def get_table_name(stage: str) -> str:
    """Map stage to DynamoDB table name."""
    if stage not in STAGE_TABLE_MAP:
        print(f"❌ Invalid stage '{stage}'. Must be 'test' or 'prod'.")
        sys.exit(1)
    return STAGE_TABLE_MAP[stage]


def get_session(profile: str = PROFILE) -> boto3.Session:
    """Create a boto3 session with the specified profile."""
    return boto3.Session(profile_name=profile, region_name=REGION)


def confirm_action(message: str) -> bool:
    """Ask the user to confirm a destructive action."""
    response = input(f"\n⚠️  {message}\n   Type 'yes' to confirm: ")
    return response.strip().lower() == "yes"


# --- Operation 1: Backfill member_type ---


def backfill_member_type(session: boto3.Session, table_name: str, dry_run: bool = False) -> None:
    """Set member_type = 'hdcn_member' on all records that don't already have it."""
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}📋 Backfilling member_type on '{table_name}'...")

    # Scan all members
    members = []
    scan_kwargs = {"ProjectionExpression": "member_id, member_type"}

    while True:
        response = table.scan(**scan_kwargs)
        members.extend(response.get("Items", []))
        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    total = len(members)
    already_set = sum(1 for m in members if "member_type" in m)
    to_update = total - already_set

    print(f"   Total members: {total}")
    print(f"   Already have member_type: {already_set}")
    print(f"   To update: {to_update}")

    if to_update == 0:
        print("   ✅ All members already have member_type set.")
        return

    if dry_run:
        print(f"   [DRY RUN] Would set member_type='hdcn_member' on {to_update} records.")
        return

    updated = 0
    failed = 0

    for member in members:
        if "member_type" in member:
            continue

        member_id = member["member_id"]
        try:
            table.update_item(
                Key={"member_id": member_id},
                UpdateExpression="SET member_type = :mt",
                ConditionExpression="attribute_not_exists(member_type)",
                ExpressionAttributeValues={":mt": "hdcn_member"},
            )
            updated += 1
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                # Another process set it — that's fine
                pass
            else:
                failed += 1
                print(f"   ⚠️  Failed to update {member_id}: {e.response['Error']['Message']}")

        if updated % 50 == 0 and updated > 0:
            print(f"   Updated {updated}/{to_update}...")

    print(f"   ✅ Backfill complete. Updated: {updated}, Failed: {failed}")


# --- Operation 2: Backfill allowed_events ---


def backfill_allowed_events(session: boto3.Session, table_name: str, dry_run: bool = False) -> None:
    """Set allowed_events = [] on all records that don't already have it."""
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}📋 Backfilling allowed_events on '{table_name}'...")

    # Scan all members
    members = []
    scan_kwargs = {"ProjectionExpression": "member_id, allowed_events"}

    while True:
        response = table.scan(**scan_kwargs)
        members.extend(response.get("Items", []))
        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    total = len(members)
    already_set = sum(1 for m in members if "allowed_events" in m)
    to_update = total - already_set

    print(f"   Total members: {total}")
    print(f"   Already have allowed_events: {already_set}")
    print(f"   To update: {to_update}")

    if to_update == 0:
        print("   ✅ All members already have allowed_events set.")
        return

    if dry_run:
        print(f"   [DRY RUN] Would set allowed_events=[] on {to_update} records.")
        return

    updated = 0
    failed = 0

    for member in members:
        if "allowed_events" in member:
            continue

        member_id = member["member_id"]
        try:
            table.update_item(
                Key={"member_id": member_id},
                UpdateExpression="SET allowed_events = :ae",
                ConditionExpression="attribute_not_exists(allowed_events)",
                ExpressionAttributeValues={":ae": []},
            )
            updated += 1
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                pass
            else:
                failed += 1
                print(f"   ⚠️  Failed to update {member_id}: {e.response['Error']['Message']}")

        if updated % 50 == 0 and updated > 0:
            print(f"   Updated {updated}/{to_update}...")

    print(f"   ✅ Backfill complete. Updated: {updated}, Failed: {failed}")


# --- Operation 3: Migrate Regio_Pressmeet users ---


def migrate_pressmeet_users(
    session: boto3.Session, table_name: str, event_id: str, dry_run: bool = False
) -> None:
    """
    Migrate Regio_Pressmeet users:
    - Find their Members record by email
    - Add event_id to their allowed_events
    - Remove them from Regio_Pressmeet group
    """
    cognito = session.client("cognito-idp", region_name=REGION)
    dynamodb = session.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(table_name)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}🔄 Migrating Regio_Pressmeet users...")
    print(f"   Event ID to grant: {event_id}")

    # List all users in Regio_Pressmeet group
    users = _list_group_users(cognito, REGIO_PRESSMEET_GROUP)

    if not users:
        print("   ℹ️  No users found in Regio_Pressmeet group.")
        return

    print(f"   Found {len(users)} users in Regio_Pressmeet group.")

    if dry_run:
        print(f"   [DRY RUN] Would migrate {len(users)} users:")
        for user in users:
            email = _get_user_email(user)
            print(f"     - {email or user['Username']}")
        return

    if not confirm_action(
        f"Migrate {len(users)} users from Regio_Pressmeet → allowed_events[{event_id}]?"
    ):
        print("   ⏭️  Skipping Regio_Pressmeet migration.")
        return

    # Build email → member_id lookup from Members table
    print("   📋 Building email → member_id lookup from Members table...")
    email_to_member = _build_email_lookup(table)
    print(f"   Found {len(email_to_member)} members with email addresses.")

    migrated = 0
    not_found = 0
    failed = 0

    for user in users:
        email = _get_user_email(user)
        username = user["Username"]

        if not email:
            print(f"   ⚠️  User '{username}' has no email attribute. Skipping.")
            not_found += 1
            continue

        # Find member record by email
        member_id = email_to_member.get(email.lower())
        if not member_id:
            print(f"   ⚠️  No Members record found for '{email}'. Skipping.")
            not_found += 1
            continue

        # Add event_id to allowed_events (if not already present)
        try:
            table.update_item(
                Key={"member_id": member_id},
                UpdateExpression="SET allowed_events = list_append(if_not_exists(allowed_events, :empty), :evt)",
                ConditionExpression="NOT contains(allowed_events, :eid)",
                ExpressionAttributeValues={
                    ":empty": [],
                    ":evt": [event_id],
                    ":eid": event_id,
                },
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                # Already has this event_id — that's fine
                pass
            else:
                print(f"   ⚠️  Failed to update allowed_events for '{email}': {e.response['Error']['Message']}")
                failed += 1
                continue

        # Remove user from Regio_Pressmeet group
        try:
            cognito.admin_remove_user_from_group(
                UserPoolId=COGNITO_POOL_ID,
                Username=username,
                GroupName=REGIO_PRESSMEET_GROUP,
            )
        except ClientError as e:
            print(f"   ⚠️  Failed to remove '{username}' from group: {e.response['Error']['Message']}")
            failed += 1
            continue

        migrated += 1
        print(f"   ✓ Migrated: {email} (member_id: {member_id})")

    print(f"\n   ✅ Migration complete. Migrated: {migrated}, Not found: {not_found}, Failed: {failed}")


def _list_group_users(cognito, group_name: str) -> list:
    """List all users in a Cognito group (handles pagination)."""
    users = []
    kwargs = {
        "UserPoolId": COGNITO_POOL_ID,
        "GroupName": group_name,
    }

    try:
        while True:
            response = cognito.list_users_in_group(**kwargs)
            users.extend(response.get("Users", []))
            next_token = response.get("NextToken")
            if not next_token:
                break
            kwargs["NextToken"] = next_token
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"   ℹ️  Group '{group_name}' does not exist.")
            return []
        raise

    return users


def _get_user_email(user: dict) -> str | None:
    """Extract email from Cognito user attributes."""
    for attr in user.get("Attributes", []):
        if attr["Name"] == "email":
            return attr["Value"]
    return None


def _build_email_lookup(table) -> dict:
    """Scan Members table and build email → member_id lookup."""
    lookup = {}
    scan_kwargs = {"ProjectionExpression": "member_id, email"}

    while True:
        response = table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            email = item.get("email", "").lower()
            if email:
                lookup[email] = item["member_id"]
        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    return lookup


# --- Operation 4: Create event_participant group ---


def create_event_participant_group(session: boto3.Session, dry_run: bool = False) -> None:
    """Create the event_participant Cognito group."""
    cognito = session.client("cognito-idp", region_name=REGION)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}🏗️  Creating Cognito group '{EVENT_PARTICIPANT_GROUP}'...")
    print(f"   Pool: {COGNITO_POOL_ID}")
    print(f"   Description: {EVENT_PARTICIPANT_DESCRIPTION}")

    if dry_run:
        print(f"   [DRY RUN] Would create group '{EVENT_PARTICIPANT_GROUP}'.")
        return

    try:
        cognito.create_group(
            GroupName=EVENT_PARTICIPANT_GROUP,
            UserPoolId=COGNITO_POOL_ID,
            Description=EVENT_PARTICIPANT_DESCRIPTION,
        )
        print(f"   ✅ Group '{EVENT_PARTICIPANT_GROUP}' created successfully.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "GroupExistsException":
            print(f"   ✅ Group '{EVENT_PARTICIPANT_GROUP}' already exists. Nothing to do.")
        else:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            print(f"   ❌ Failed to create group: [{error_code}] {error_message}")
            sys.exit(1)


# --- Operation 5: Delete Regio_Pressmeet group ---


def delete_pressmeet_group(session: boto3.Session, dry_run: bool = False) -> None:
    """Remove all users from Regio_Pressmeet and delete the group."""
    cognito = session.client("cognito-idp", region_name=REGION)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}🗑️  Deleting Cognito group '{REGIO_PRESSMEET_GROUP}'...")

    # List users still in the group
    users = _list_group_users(cognito, REGIO_PRESSMEET_GROUP)

    if not users and not dry_run:
        # Group might not exist — try to delete anyway
        pass
    elif users:
        print(f"   Found {len(users)} users still in the group.")

        if dry_run:
            print(f"   [DRY RUN] Would remove {len(users)} users and delete the group.")
            return

        if not confirm_action(
            f"Remove {len(users)} users from '{REGIO_PRESSMEET_GROUP}' and delete the group?"
        ):
            print("   ⏭️  Skipping group deletion.")
            return

        # Remove all users from the group
        removed = 0
        for user in users:
            username = user["Username"]
            try:
                cognito.admin_remove_user_from_group(
                    UserPoolId=COGNITO_POOL_ID,
                    Username=username,
                    GroupName=REGIO_PRESSMEET_GROUP,
                )
                removed += 1
            except ClientError as e:
                print(f"   ⚠️  Failed to remove '{username}': {e.response['Error']['Message']}")

        print(f"   Removed {removed}/{len(users)} users from group.")
    elif dry_run:
        print(f"   [DRY RUN] Would delete group '{REGIO_PRESSMEET_GROUP}' (no users in group).")
        return

    # Delete the group
    try:
        cognito.delete_group(
            GroupName=REGIO_PRESSMEET_GROUP,
            UserPoolId=COGNITO_POOL_ID,
        )
        print(f"   ✅ Group '{REGIO_PRESSMEET_GROUP}' deleted successfully.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"   ✅ Group '{REGIO_PRESSMEET_GROUP}' does not exist. Nothing to delete.")
        else:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            print(f"   ❌ Failed to delete group: [{error_code}] {error_message}")
            sys.exit(1)


# --- Main ---


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Migrate Members table (add member_type, allowed_events) and clean up Cognito groups. "
            "Part of the generic event booking system migration."
        )
    )
    parser.add_argument(
        "--stage",
        required=True,
        choices=["test", "prod"],
        help="Target stage: 'test' → Members-Test, 'prod' → Members",
    )
    parser.add_argument(
        "--profile",
        default=PROFILE,
        help=f"AWS CLI profile to use (default: {PROFILE})",
    )
    parser.add_argument(
        "--event-id",
        help="Event UUID to grant to former Regio_Pressmeet users (required for --migrate-pressmeet)",
    )
    parser.add_argument(
        "--backfill-members",
        action="store_true",
        help="Run operations 1 & 2: backfill member_type and allowed_events",
    )
    parser.add_argument(
        "--migrate-pressmeet",
        action="store_true",
        help="Run operation 3: migrate Regio_Pressmeet users to allowed_events",
    )
    parser.add_argument(
        "--create-group",
        action="store_true",
        help="Run operation 4: create event_participant Cognito group",
    )
    parser.add_argument(
        "--delete-pressmeet-group",
        action="store_true",
        help="Run operation 5: remove all users from Regio_Pressmeet and delete the group",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all operations in order (1-5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    args = parser.parse_args()

    # Validate flags
    run_backfill = args.backfill_members or args.all
    run_migrate = args.migrate_pressmeet or args.all
    run_create = args.create_group or args.all
    run_delete = args.delete_pressmeet_group or args.all

    if not any([run_backfill, run_migrate, run_create, run_delete]):
        parser.error(
            "No operation specified. Use --backfill-members, --migrate-pressmeet, "
            "--create-group, --delete-pressmeet-group, or --all."
        )

    if run_migrate and not args.event_id:
        parser.error("--event-id is required when using --migrate-pressmeet or --all.")

    table_name = get_table_name(args.stage)
    session = get_session(args.profile)

    print("=" * 60)
    print("🔧 Members Migration & Cognito Cleanup")
    print("=" * 60)
    print(f"   Stage:      {args.stage}")
    print(f"   Table:      {table_name}")
    print(f"   Profile:    {args.profile}")
    print(f"   Region:     {REGION}")
    print(f"   Pool:       {COGNITO_POOL_ID}")
    if args.event_id:
        print(f"   Event ID:   {args.event_id}")
    if args.dry_run:
        print(f"   Mode:       DRY RUN (no changes will be made)")
    print("=" * 60)

    # Operation 1 & 2: Backfill member_type and allowed_events
    if run_backfill:
        backfill_member_type(session, table_name, dry_run=args.dry_run)
        backfill_allowed_events(session, table_name, dry_run=args.dry_run)

    # Operation 3: Migrate Regio_Pressmeet users
    if run_migrate:
        migrate_pressmeet_users(session, table_name, args.event_id, dry_run=args.dry_run)

    # Operation 4: Create event_participant group
    if run_create:
        create_event_participant_group(session, dry_run=args.dry_run)

    # Operation 5: Delete Regio_Pressmeet group
    if run_delete:
        delete_pressmeet_group(session, dry_run=args.dry_run)

    print("\n" + "=" * 60)
    print("✅ All requested operations complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
