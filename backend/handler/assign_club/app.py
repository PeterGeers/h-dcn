"""
POST /presmeet/clubs/assign — Assign a club to the authenticated member.
Updates both the Member record (club_id) and the Club_Registry (assigned_member_id).
Admin can reassign clubs for other members.
"""

import json
import os
from datetime import datetime, timezone
import boto3
from boto3.dynamodb.conditions import Attr

# Import shared authentication utilities with fallback support
try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    )
    from shared.club_identity import get_club_id, is_presmeet_admin, has_presmeet_access
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("assign_club")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
members_table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))
BUCKET = os.environ.get('REPORTS_BUCKET_NAME', 'h-dcn-reports')
CLUB_REGISTRY_KEY = 'presmeet/club_registry.json'


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Validate permissions - Club_User level access
        required_permissions = ['events_read']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response

        # Gate: check Regio_Pressmeet access
        if not has_presmeet_access(user_roles):
            return create_error_response(403, 'PresMeet access required')

        # Log successful access
        log_successful_access(user_email, user_roles, 'assign_club')

        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
        except (json.JSONDecodeError, TypeError):
            return create_error_response(400, 'Invalid JSON in request body')

        club_id = body.get('club_id')
        target_member_email = body.get('member_email')  # Only for admin reassignment

        if not club_id:
            return create_error_response(400, 'club_id is required')

        # Determine target member
        is_admin = is_presmeet_admin(user_roles)
        if target_member_email and is_admin:
            member_email = target_member_email
        else:
            member_email = user_email

        # Load Club_Registry from S3
        try:
            obj = s3.get_object(Bucket=BUCKET, Key=CLUB_REGISTRY_KEY)
            registry = json.loads(obj['Body'].read().decode('utf-8'))
        except Exception as e:
            print(f"Error reading club registry: {e}")
            return create_error_response(500, 'Failed to read club registry')

        # Find the requested club
        clubs = registry.get('clubs', [])
        club_entry = next((c for c in clubs if c['club_id'] == club_id), None)
        if not club_entry:
            return create_error_response(404, f"Club '{club_id}' not found in registry")

        # Check if club already assigned (unless admin reassigning)
        assigned = club_entry.get('assigned_member_id')
        if assigned and not is_admin:
            return create_error_response(
                409,
                'Club already assigned',
                {'assigned_contact': club_entry.get('assigned_contact', 'Contact admin')}
            )

        # Find member record
        response = members_table.scan(
            FilterExpression=Attr('email').eq(member_email) & Attr('status').eq('presmeet')
        )
        members = response.get('Items', [])
        if not members:
            return create_error_response(404, 'PresMeet member record not found')

        member = members[0]
        member_id = member['member_id']
        now = datetime.now(timezone.utc).isoformat()

        # If admin is reassigning, clear previous assignment
        if assigned and is_admin:
            # Clear club_id from previous member(s) who had this club
            prev_response = members_table.scan(
                FilterExpression=Attr('club_id').eq(club_id) & Attr('status').eq('presmeet')
            )
            for prev_member in prev_response.get('Items', []):
                members_table.update_item(
                    Key={'member_id': prev_member['member_id']},
                    UpdateExpression='REMOVE club_id SET updated_at = :now',
                    ExpressionAttributeValues={':now': now}
                )

        # Update Member record with club_id
        members_table.update_item(
            Key={'member_id': member_id},
            UpdateExpression='SET club_id = :cid, updated_at = :now',
            ExpressionAttributeValues={':cid': club_id, ':now': now}
        )

        # Update Club_Registry in S3
        club_entry['assigned_member_id'] = member_id
        club_entry['assigned_contact'] = member_email
        club_entry['assigned_at'] = now

        s3.put_object(
            Bucket=BUCKET,
            Key=CLUB_REGISTRY_KEY,
            Body=json.dumps(registry, indent=2),
            ContentType='application/json'
        )

        return create_success_response({
            'message': f"Club '{club_id}' assigned to {member_email}",
            'club_id': club_id,
            'member_id': member_id
        })

    except Exception as e:
        print(f"Error in assign_club handler: {str(e)}")
        return create_error_response(500, 'Internal server error')
