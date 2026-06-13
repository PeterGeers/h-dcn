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


def get_club_id(user_email: str) -> str | None:
    """
    Look up a member's club_id by their email address.

    Scans the Members table for a record with a matching email,
    then returns the club_id field.

    Args:
        user_email: The member's email address.

    Returns:
        str or None: The member's club_id, or None if not found.
    """
    from boto3.dynamodb.conditions import Attr

    try:
        response = members_table.scan(
            FilterExpression=Attr('email').eq(user_email.lower()),
            ProjectionExpression='club_id'
        )
    except Exception:
        return None

    items = response.get('Items', [])
    if not items:
        return None

    return items[0].get('club_id')


def has_presmeet_access(user_roles: list[str]) -> bool:
    """
    Legacy compatibility: check if user has event booking access.
    In the new system, all authenticated members with event_participant or
    hdcnLeden access can use event booking features.
    This replaces the old Regio_Pressmeet group check.

    Args:
        user_roles: List of Cognito group names.

    Returns:
        bool: True if user has any event-related or member access.
    """
    # In the new system, any logged-in member has booking access
    # (actual event-level access is controlled via allowed_events)
    event_roles = {'Regio_Pressmeet', 'hdcnLeden', 'event_participant'}
    return bool(set(user_roles) & event_roles)


def is_presmeet_admin(user_roles: list[str]) -> bool:
    """
    Legacy compatibility: check if user is an event booking admin.
    Replaces the old is_presmeet_admin from club_identity.

    Args:
        user_roles: List of Cognito group names.

    Returns:
        bool: True if user has admin-level roles.
    """
    admin_roles = {'Products_CRUD', 'Products_Read', 'Webshop_Management', 'Regio_All'}
    return bool(set(user_roles) & admin_roles)
