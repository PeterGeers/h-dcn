"""
Event-scoped access control for generic event booking.
Checks member access via the allowed_events field on the Members record.
No Cognito group logic — access is purely data-driven.
"""

import os
import boto3

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
members_table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))


def get_member_allowed_events(member_id: str) -> list[str]:
    """
    Read the member's allowed_events list from the Members table.

    Args:
        member_id: The member's unique identifier.

    Returns:
        list[str]: List of event_id UUIDs the member can access,
                   or empty list if member not found or field is missing.
    """
    try:
        response = members_table.get_item(
            Key={'member_id': member_id},
            ProjectionExpression='allowed_events'
        )
    except Exception:
        return []

    item = response.get('Item')
    if not item:
        return []

    return item.get('allowed_events', [])


def has_event_access(member_id: str, event_id: str) -> bool:
    """
    Check if a member has access to a specific event.
    Access is granted purely via the allowed_events list on the Members record.
    No Cognito group checks, no legacy mappings.

    Args:
        member_id: The member's unique identifier.
        event_id: The event UUID to check access for.

    Returns:
        bool: True if event_id is in the member's allowed_events, False otherwise.
    """
    allowed_events = get_member_allowed_events(member_id)
    return event_id in allowed_events
