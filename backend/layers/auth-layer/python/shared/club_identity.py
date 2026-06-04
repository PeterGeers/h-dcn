"""
Club identity resolution for PresMeet v2.
Replaces the v1 pattern of extracting club_id from Cognito groups.
Club identity is now stored on the Member record.
"""

import os
import boto3
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource('dynamodb')
members_table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))


def get_club_id(user_email: str) -> str | None:
    """
    Look up club_id from the Member record matching the given email.
    Returns club_id for any member who has one assigned (regardless of status),
    since Regio_Pressmeet Cognito group already gates access.

    Args:
        user_email: The authenticated user's email address.

    Returns:
        str | None: The club_id or None if not found / not assigned.
    """
    response = members_table.scan(
        FilterExpression=Attr('email').eq(user_email),
        ProjectionExpression='club_id, member_id'
    )
    items = response.get('Items', [])
    if not items:
        return None
    return items[0].get('club_id')


def is_presmeet_admin(user_roles: list) -> bool:
    """
    Check if user has PresMeet admin access.
    Requires: (Products_CRUD OR Products_Read OR Webshop_Management)
              AND (Regio_Pressmeet OR Regio_All)

    Args:
        user_roles: List of Cognito group names.

    Returns:
        bool: True if user has PresMeet admin access.
    """
    has_management_role = any(
        role in ('Products_CRUD', 'Products_Read', 'Webshop_Management')
        for role in user_roles
    )
    has_region_role = any(
        role in ('Regio_Pressmeet', 'Regio_All')
        for role in user_roles
    )
    return has_management_role and has_region_role


def is_presmeet_admin_write(user_roles: list) -> bool:
    """
    Check if user has PresMeet admin WRITE access (lock, unlock, manual payment).
    Requires: Products_CRUD AND (Regio_Pressmeet OR Regio_All)

    Args:
        user_roles: List of Cognito group names.

    Returns:
        bool: True if user has full PresMeet admin access.
    """
    has_crud_role = 'Products_CRUD' in user_roles
    has_region_role = any(
        role in ('Regio_Pressmeet', 'Regio_All')
        for role in user_roles
    )
    return has_crud_role and has_region_role


def has_presmeet_access(user_roles: list) -> bool:
    """
    Check if user has access to PresMeet booking form.
    Requires: Regio_Pressmeet OR Regio_All in Cognito groups.

    Args:
        user_roles: List of Cognito group names.

    Returns:
        bool: True if user can access the booking form.
    """
    return any(
        role in ('Regio_Pressmeet', 'Regio_All')
        for role in user_roles
    )
