"""
Send delegate invitation email handler.
Endpoint: POST /booking/{id}/invite-email

Sends an SES email to the pending_secondary_email on an order with
an invitation link to the event landing page. Supports initial send
and resend actions from the delegate management UI.

Requirements: 5.3 (delegate invite flow steps 3-4)
"""

import json
import os
import re
import logging
from typing import TypedDict, NotRequired

import boto3
from botocore.exceptions import ClientError

try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        create_success_response,
        create_error_response,
        handle_options_request,
        log_successful_access,
    )
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("send_delegate_invitation")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# AWS resources
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
ses_client = boto3.client('ses', region_name='eu-west-1')
s3_client = boto3.client('s3', region_name='eu-west-1')

orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
events_table = dynamodb.Table(os.environ.get('EVENTS_TABLE_NAME', 'Events'))
members_table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))

# Configuration
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@h-dcn.nl')
PORTAL_BASE_URL = os.environ.get('PORTAL_BASE_URL', 'https://portal.h-dcn.nl')
EMAIL_TEMPLATES_BUCKET = os.environ.get('EMAIL_TEMPLATES_BUCKET', 'hdcn-email-templates')
ORGANIZATION_NAME = os.environ.get('ORGANIZATION_NAME', 'Harley-Davidson Club Nederland')
ORGANIZATION_WEBSITE = os.environ.get('ORGANIZATION_WEBSITE', 'https://portal.h-dcn.nl')
ORGANIZATION_EMAIL = os.environ.get('ORGANIZATION_EMAIL', 'webhulpje@h-dcn.nl')
ORGANIZATION_SHORT_NAME = os.environ.get('ORGANIZATION_SHORT_NAME', 'H-DCN')

# Default locale
DEFAULT_LOCALE = 'nl'
SUPPORTED_LOCALES = ('nl', 'en', 'de', 'fr', 'es', 'it', 'da', 'sv')


# --- Types ---

class InviteEmailRequest(TypedDict):
    locale: NotRequired[str]


# --- Template Loading ---

def _load_template(locale: str) -> str | None:
    """Load the delegate-invitation email template from S3 for the given locale."""
    # Try requested locale first
    if locale and locale != DEFAULT_LOCALE:
        template = _load_s3_template(f'templates/{locale}/delegate-invitation.html')
        if template:
            return template

    # Fallback to Dutch
    template = _load_s3_template(f'templates/{DEFAULT_LOCALE}/delegate-invitation.html')
    if template:
        return template

    return None


def _load_s3_template(key: str) -> str | None:
    """Attempt to load a template from S3. Returns None if not found."""
    try:
        response = s3_client.get_object(
            Bucket=EMAIL_TEMPLATES_BUCKET,
            Key=key,
        )
        return response['Body'].read().decode('utf-8')
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'NoSuchKey':
            return None
        logger.warning(f"Error loading template {key} from S3: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error loading template {key}: {e}")
        return None


def _render_template(template_html: str, context: dict) -> str:
    """Replace {{VARIABLE}} placeholders in the template with context values."""
    rendered = template_html
    for key, value in context.items():
        placeholder = f"{{{{{key}}}}}"
        rendered = rendered.replace(placeholder, str(value))
    return rendered


def _extract_subject(html: str) -> str:
    """Extract subject from HTML <title> tag."""
    match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return f"{ORGANIZATION_SHORT_NAME} — Uitnodiging"


def _get_fallback_html(context: dict) -> str:
    """Generate a minimal fallback HTML email if S3 template is unavailable."""
    row_label = context.get('ROW_LABEL', 'group')
    row_name = context.get('ROW_NAME', '')
    row_display = f"{row_label}: {row_name}" if row_name else row_label
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>{ORGANIZATION_SHORT_NAME} — Uitnodiging voor {context.get('EVENT_NAME', 'evenement')}</title></head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<div style="max-width: 600px; margin: 0 auto; padding: 20px;">
<h2 style="color: #d2691e;">Je bent uitgenodigd voor {context.get('EVENT_NAME', 'een evenement')}</h2>
<p><strong>{context.get('INVITER_NAME', '')}</strong> heeft je uitgenodigd als mede-delegatie voor
<strong>{row_display}</strong>.</p>
<p><a href="{context.get('REGISTRATION_LINK', '#')}">Registreren</a></p>
<p>Met vriendelijke groet,<br>Het {ORGANIZATION_SHORT_NAME} Team</p>
</div>
</body>
</html>"""


# --- Helpers ---

def _resolve_member_by_email(email: str) -> dict | None:
    """Find a member by email (case-insensitive scan)."""
    from boto3.dynamodb.conditions import Attr
    try:
        response = members_table.scan(
            FilterExpression=Attr('email').eq(email.lower()),
            ProjectionExpression='member_id, email, #n, registry_row_id',
            ExpressionAttributeNames={'#n': 'name'},
        )
        items = response.get('Items', [])
        return items[0] if items else None
    except Exception as e:
        logger.error(f"Error resolving member by email: {e}")
        return None


def _get_event(event_id: str) -> dict | None:
    """Load event record."""
    try:
        response = events_table.get_item(Key={'event_id': event_id})
        return response.get('Item')
    except Exception as e:
        logger.error(f"Error fetching event {event_id}: {e}")
        return None


def _resolve_row_label(event: dict) -> str:
    """
    Resolve the row type label from event.registry_config.row_label.
    Fallback: "group".
    """
    registry_config = event.get('registry_config') or {}
    row_label = registry_config.get('row_label', '')
    return row_label if row_label else 'group'


def _resolve_row_name(order: dict, event: dict) -> str:
    """
    Resolve the row name (instance label) for the email template.
    Priority: order.registry_row_label → event.registry_claims[row_id].label → registry_row_id.
    """
    # Try order's stored label first
    row_name = order.get('registry_row_label', '')
    if row_name:
        return row_name

    # Fallback: check event registry_claims
    registry_row_id = order.get('registry_row_id', '')
    if registry_row_id and event:
        registry_claims = event.get('registry_claims', {})
        claim = registry_claims.get(registry_row_id, {})
        if claim and claim.get('label'):
            return claim['label']

    # Final fallback: registry_row_id itself
    return registry_row_id if registry_row_id else ''


def _build_registration_link(event: dict) -> str:
    """Build the registration link for the event landing page."""
    slug = event.get('slug', '')
    if slug:
        return f"{PORTAL_BASE_URL}/events/{slug}/register"
    # Fallback: use event_id-based URL
    event_id = event.get('event_id', '')
    return f"{PORTAL_BASE_URL}/events/{event_id}/register"


def _resolve_locale(body: dict) -> str:
    """Resolve locale from request body, default to Dutch."""
    locale = body.get('locale', DEFAULT_LOCALE)
    if locale not in SUPPORTED_LOCALES:
        return DEFAULT_LOCALE
    return locale


# --- Main Handler ---

def lambda_handler(event, context):
    """POST /booking/{id}/invite-email"""
    try:
        # Handle OPTIONS (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # 1. Auth
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # 2. Get order_id from path
        path_params = event.get('pathParameters') or {}
        order_id = path_params.get('id')
        if not order_id:
            return create_error_response(400, 'Order ID is required in path')

        # 3. Parse body (optional locale)
        try:
            body = json.loads(event.get('body') or '{}')
        except (json.JSONDecodeError, TypeError):
            body = {}

        locale = _resolve_locale(body)

        # 4. Load order
        response = orders_table.get_item(Key={'order_id': order_id})
        order = response.get('Item')
        if not order:
            return create_error_response(404, 'Order not found')

        # 5. Verify order has delegates and pending_secondary_email
        delegates = order.get('delegates')
        if not delegates:
            return create_error_response(
                400, 'This order does not support delegate management'
            )

        pending_email = delegates.get('pending_secondary_email')
        if not pending_email:
            return create_error_response(
                400, 'No pending invitation found on this order. '
                     'Invite a delegate first via the delegate management endpoint.'
            )

        # 6. Verify requester is primary delegate or admin
        requester_member = _resolve_member_by_email(user_email)
        if not requester_member:
            return create_error_response(404, 'Requester member record not found')

        requester_member_id = requester_member['member_id']
        primary_member_id = delegates.get('primary_member_id')
        is_primary = (requester_member_id == primary_member_id)

        is_admin = False
        try:
            is_authorized, _, _ = validate_permissions_with_regions(
                user_roles, ['events_crud'], user_email, None
            )
            is_admin = is_authorized
        except Exception:
            pass

        if not is_primary and not is_admin:
            return create_error_response(
                403, 'Only the primary delegate or an admin can send invitation emails'
            )

        log_successful_access(user_email, user_roles, 'send_delegate_invitation')

        # 7. Gather context for the email
        event_id = order.get('event_id')

        event_record = _get_event(event_id) if event_id else None
        event_name = event_record.get('name', 'Evenement') if event_record else 'Evenement'

        # Resolve ROW_LABEL (type of unit) and ROW_NAME (instance name)
        row_label = _resolve_row_label(event_record) if event_record else 'group'
        row_name = _resolve_row_name(order, event_record) if event_record else order.get('registry_row_id', '')

        # Inviter name: from the requester's member record
        inviter_name = requester_member.get('name', user_email)

        # Registration link
        registration_link = _build_registration_link(event_record) if event_record else PORTAL_BASE_URL

        # 8. Build email
        template_context = {
            'EVENT_NAME': event_name,
            'INVITER_NAME': inviter_name,
            'ROW_LABEL': row_label,
            'ROW_NAME': row_name,
            'REGISTRATION_LINK': registration_link,
            'ORGANIZATION_NAME': ORGANIZATION_NAME,
            'ORGANIZATION_WEBSITE': ORGANIZATION_WEBSITE,
            'ORGANIZATION_EMAIL': ORGANIZATION_EMAIL,
            'ORGANIZATION_SHORT_NAME': ORGANIZATION_SHORT_NAME,
        }

        template_html = _load_template(locale)
        if not template_html:
            template_html = _get_fallback_html(template_context)

        rendered_html = _render_template(template_html, template_context)
        subject = _extract_subject(rendered_html)

        # 9. Send email via SES
        try:
            ses_client.send_email(
                Source=SENDER_EMAIL,
                Destination={
                    'ToAddresses': [pending_email],
                },
                Message={
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8',
                    },
                    'Body': {
                        'Html': {
                            'Data': rendered_html,
                            'Charset': 'UTF-8',
                        },
                    },
                },
            )
        except ClientError as e:
            logger.error(f"SES send_email failed: {e}")
            return create_error_response(
                500, 'Failed to send invitation email. Please try again later.'
            )

        logger.info(
            f"Delegate invitation email sent to {pending_email} "
            f"for order {order_id} (event: {event_id}, row: {row_label}/{row_name})"
        )

        return create_success_response({
            'message': f'Invitation email sent to {pending_email}',
            'recipient': pending_email,
        })

    except Exception as e:
        logger.error(f"Error in send_delegate_invitation handler: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')
