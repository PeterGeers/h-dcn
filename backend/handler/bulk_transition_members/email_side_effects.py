"""Email side effect actions for membership workflow transitions.

Each action builds context variables from member data and calls
send_membership_email(). These are side effects — they MUST NOT raise
exceptions that block the transition. All errors are caught and logged.

Registration:
    Call register_email_side_effects(dispatcher) during handler init
    to register all email actions with the ActionDispatcher.

Side effect actions:
    - send_application_email: Confirmation to new applicant (Req 4.1)
    - send_payment_request: Payment instructions after approval (Req 4.3)
    - send_welcome_email: Welcome after activation (Req 4.4)
    - send_cancellation_email: Cancellation confirmation (Req 4.5)
    - send_suspension_notice: Suspension notice (Req 4.6)
    - notify_admin: Admin notification on new application (Req 4.2)
"""

import logging
import os
from datetime import date, datetime, timedelta
from typing import Any

from shared.workflows import ActionDispatcher

from email_actions import send_membership_email

logger = logging.getLogger(__name__)

# --- Configuration ---

ADMIN_EMAIL: str = 'webmaster@h-dcn.nl'
ORGANIZATION_IBAN: str = os.environ.get('ORGANIZATION_IBAN', 'NL00INGB0000000000')
PORTAL_URL: str = os.environ.get('PORTAL_BASE_URL', 'https://portal.h-dcn.nl')

# Contribution amounts per membership type (fallback)
CONTRIBUTION_AMOUNTS: dict[str, str] = {
    'Regulier': '50,00',
    'Gezinslid': '25,00',
    'Jeugdlid': '15,00',
    'Erelid': '0,00',
}

DEFAULT_CONTRIBUTION: str = '50,00'


# --- Helpers ---


def _get_member_name(member: dict[str, Any]) -> str:
    """Build full display name from member record fields."""
    parts: list[str] = []
    voornaam = member.get('voornaam', '')
    tussenvoegsel = member.get('tussenvoegsel', '')
    achternaam = member.get('achternaam', '')

    if voornaam:
        parts.append(voornaam)
    if tussenvoegsel:
        parts.append(tussenvoegsel)
    if achternaam:
        parts.append(achternaam)

    return ' '.join(parts) or member.get('email', 'Lid')


def _get_locale(member: dict[str, Any]) -> str:
    """Determine email locale from member record. Default: nl."""
    return member.get('taal') or member.get('preferred_locale') or 'nl'


def _format_date(iso_str: str | None = None) -> str:
    """Format a date for display. Uses today if no date provided."""
    if iso_str:
        try:
            dt = datetime.fromisoformat(iso_str)
            return dt.strftime('%d-%m-%Y')
        except (ValueError, TypeError):
            pass
    return date.today().strftime('%d-%m-%Y')


def _get_contribution_amount(membership_type: str) -> str:
    """Get contribution amount for a membership type."""
    return CONTRIBUTION_AMOUNTS.get(membership_type, DEFAULT_CONTRIBUTION)


def _payment_deadline() -> str:
    """Calculate payment deadline (30 days from now)."""
    deadline = date.today() + timedelta(days=30)
    return deadline.strftime('%d-%m-%Y')


# --- Side effect actions ---


def send_application_email(ctx: dict[str, Any]) -> None:
    """Send application confirmation to the new applicant.

    Template: membership-application-confirmation
    Variables: MEMBER_NAME, APPLICATION_DATE, MEMBERSHIP_TYPE
    Validates: Requirements 4.1
    """
    try:
        member: dict[str, Any] = ctx.get('member', {})
        recipient: str = member.get('email', '')
        if not recipient:
            logger.warning(f"No email for member {ctx.get('member_id')} — skipping application email")
            return

        variables: dict[str, str] = {
            'MEMBER_NAME': _get_member_name(member),
            'APPLICATION_DATE': _format_date(member.get('created')),
            'MEMBERSHIP_TYPE': member.get('lidmaatschap', 'Regulier'),
        }

        send_membership_email(
            template_name='membership-application-confirmation',
            recipient=recipient,
            variables=variables,
            locale=_get_locale(member),
        )
    except Exception as e:
        logger.error(f"send_application_email failed for {ctx.get('member_id')}: {e}")


def send_payment_request(ctx: dict[str, Any]) -> None:
    """Send payment request after member approval.

    Template: membership-approved-payment-request
    Variables: MEMBER_NAME, MEMBERSHIP_TYPE, CONTRIBUTION_AMOUNT,
              PAYMENT_INSTRUCTIONS, PAYMENT_DEADLINE, IBAN, REFERENCE
    Validates: Requirements 4.3
    """
    try:
        member: dict[str, Any] = ctx.get('member', {})
        recipient: str = member.get('email', '')
        if not recipient:
            logger.warning(f"No email for member {ctx.get('member_id')} — skipping payment request")
            return

        membership_type: str = member.get('lidmaatschap', 'Regulier')
        # Use short reference: achternaam + first 8 chars of member_id
        member_id_short: str = ctx.get('member_id', '')[:8]
        achternaam: str = member.get('achternaam', '')
        reference: str = f"HDCN-{achternaam}-{member_id_short}" if achternaam else f"HDCN-{member_id_short}"

        variables: dict[str, str] = {
            'MEMBER_NAME': _get_member_name(member),
            'MEMBERSHIP_TYPE': membership_type,
            'CONTRIBUTION_AMOUNT': _get_contribution_amount(membership_type),
            'PAYMENT_INSTRUCTIONS': 'Maak het bedrag over naar onderstaand rekeningnummer',
            'PAYMENT_DEADLINE': _payment_deadline(),
            'IBAN': ORGANIZATION_IBAN,
            'REFERENCE': reference,
        }

        send_membership_email(
            template_name='membership-approved-payment-request',
            recipient=recipient,
            variables=variables,
            locale=_get_locale(member),
        )
    except Exception as e:
        logger.error(f"send_payment_request failed for {ctx.get('member_id')}: {e}")


def send_welcome_email(ctx: dict[str, Any]) -> None:
    """Send welcome email after payment received and activation.

    Template: membership-welcome
    Variables: MEMBER_NAME, MEMBER_NUMBER, REGIO, REGIO_CONTACT_NAME,
              REGIO_CONTACT_EMAIL, PORTAL_URL, WELCOME_PACK_NOTE
    Validates: Requirements 4.4
    """
    try:
        member: dict[str, Any] = ctx.get('member', {})
        recipient: str = member.get('email', '')
        if not recipient:
            logger.warning(f"No email for member {ctx.get('member_id')} — skipping welcome email")
            return

        regio: str = member.get('regio', '')
        lidnummer = str(member.get('lidnummer', ctx.get('lidnummer', '')))

        # Look up regio secretary (HdcnAccount member in same regio)
        regio_contact_name: str = ''
        regio_contact_email: str = ''
        if regio:
            try:
                import boto3
                import os
                ddb = boto3.resource('dynamodb', region_name='eu-west-1')
                members_tbl = ddb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))
                scan_resp = members_tbl.scan(
                    FilterExpression='#s = :status AND regio = :regio',
                    ExpressionAttributeNames={'#s': 'status'},
                    ExpressionAttributeValues={':status': 'HdcnAccount', ':regio': regio},
                    ProjectionExpression='voornaam, tussenvoegsel, achternaam, email',
                    Limit=1,
                )
                if scan_resp.get('Items'):
                    secretary = scan_resp['Items'][0]
                    parts = [secretary.get('voornaam', ''), secretary.get('tussenvoegsel', ''), secretary.get('achternaam', '')]
                    regio_contact_name = ' '.join(p for p in parts if p)
                    regio_contact_email = secretary.get('email', '')
            except Exception as e:
                logger.warning(f"Failed to look up regio secretary for {regio}: {e}")

        variables: dict[str, str] = {
            'MEMBER_NAME': _get_member_name(member),
            'MEMBER_NUMBER': lidnummer,
            'REGIO': regio,
            'REGIO_CONTACT_NAME': regio_contact_name,
            'REGIO_CONTACT_EMAIL': regio_contact_email,
            'PORTAL_URL': PORTAL_URL,
            'WELCOME_PACK_NOTE': 'Je welkomstpakket wordt per post verstuurd.',
        }

        send_membership_email(
            template_name='membership-welcome',
            recipient=recipient,
            variables=variables,
            locale=_get_locale(member),
        )
    except Exception as e:
        logger.error(f"send_welcome_email failed for {ctx.get('member_id')}: {e}")


def send_cancellation_email(ctx: dict[str, Any]) -> None:
    """Send cancellation confirmation to the member.

    Template: membership-cancellation-confirmation
    Variables: MEMBER_NAME, CANCELLATION_DATE, MEMBERSHIP_END_DATE, MEMBER_SINCE
    Validates: Requirements 4.5
    """
    try:
        member: dict[str, Any] = ctx.get('member', {})
        recipient: str = member.get('email', '')
        if not recipient:
            logger.warning(f"No email for member {ctx.get('member_id')} — skipping cancellation email")
            return

        today_str: str = date.today().strftime('%d-%m-%Y')
        # End of current year as membership end date
        end_of_year: str = f'31-12-{date.today().year}'

        variables: dict[str, str] = {
            'MEMBER_NAME': _get_member_name(member),
            'CANCELLATION_DATE': today_str,
            'MEMBERSHIP_END_DATE': end_of_year,
            'MEMBER_SINCE': _format_date(member.get('ingangsdatum')),
        }

        send_membership_email(
            template_name='membership-cancellation-confirmation',
            recipient=recipient,
            variables=variables,
            locale=_get_locale(member),
        )
    except Exception as e:
        logger.error(f"send_cancellation_email failed for {ctx.get('member_id')}: {e}")


def send_suspension_notice(ctx: dict[str, Any]) -> None:
    """Send suspension notice to the member.

    Template: membership-suspension-notice
    Variables: MEMBER_NAME, SUSPENSION_DATE, REASON, CONTACT_EMAIL
    Validates: Requirements 4.6
    """
    try:
        member: dict[str, Any] = ctx.get('member', {})
        recipient: str = member.get('email', '')
        if not recipient:
            logger.warning(f"No email for member {ctx.get('member_id')} — skipping suspension notice")
            return

        variables: dict[str, str] = {
            'MEMBER_NAME': _get_member_name(member),
            'SUSPENSION_DATE': date.today().strftime('%d-%m-%Y'),
            'REASON': ctx.get('reason', 'Geen reden opgegeven'),
            'CONTACT_EMAIL': ADMIN_EMAIL,
        }

        send_membership_email(
            template_name='membership-suspension-notice',
            recipient=recipient,
            variables=variables,
            locale=_get_locale(member),
        )
    except Exception as e:
        logger.error(f"send_suspension_notice failed for {ctx.get('member_id')}: {e}")


def notify_admin(ctx: dict[str, Any]) -> None:
    """Send admin notification about a new membership application.

    Template: membership-application-admin-notification
    Recipient: ledenadministratie@h-dcn.nl (always)
    Variables: MEMBER_NAME, EMAIL, REGIO, MEMBERSHIP_TYPE, APPLICATION_DATE
    Validates: Requirements 4.2
    """
    try:
        member: dict[str, Any] = ctx.get('member', {})

        variables: dict[str, str] = {
            'MEMBER_NAME': _get_member_name(member),
            'EMAIL': member.get('email', ''),
            'REGIO': member.get('regio', 'Niet toegewezen'),
            'MEMBERSHIP_TYPE': member.get('lidmaatschap', 'Regulier'),
            'APPLICATION_DATE': _format_date(member.get('created')),
        }

        # Admin notifications always go to the admin mailbox in Dutch
        send_membership_email(
            template_name='membership-application-admin-notification',
            recipient=ADMIN_EMAIL,
            variables=variables,
            locale='nl',
        )
    except Exception as e:
        logger.error(f"notify_admin failed for {ctx.get('member_id')}: {e}")


def send_rejection_email(ctx: dict[str, Any]) -> None:
    """Send rejection notification to the applicant.

    Template: membership-rejection
    Variables: MEMBER_NAME, REASON, CONTACT_EMAIL
    """
    try:
        member: dict[str, Any] = ctx.get('member', {})
        recipient: str = member.get('email', '')
        if not recipient:
            logger.warning(f"No email for member {ctx.get('member_id')} — skipping rejection email")
            return

        variables: dict[str, str] = {
            'MEMBER_NAME': _get_member_name(member),
            'REASON': ctx.get('reason', 'Geen reden opgegeven'),
            'CONTACT_EMAIL': ADMIN_EMAIL,
        }

        send_membership_email(
            template_name='membership-rejection',
            recipient=recipient,
            variables=variables,
            locale=_get_locale(member),
        )
    except Exception as e:
        logger.error(f"send_rejection_email failed for {ctx.get('member_id')}: {e}")


# --- Registration ---


def register_email_side_effects(dispatcher: ActionDispatcher) -> None:
    """Register all email side effect actions with the dispatcher.

    Call this during handler initialization alongside register_actions()
    to make email side effects available for transition execution.
    """
    dispatcher.register_many({
        'send_application_email': send_application_email,
        'send_application_received': send_application_email,  # alias used in membership.py
        'send_payment_request': send_payment_request,
        'send_welcome_email': send_welcome_email,
        'send_cancellation_email': send_cancellation_email,
        'send_suspension_notice': send_suspension_notice,
        'send_rejection_email': send_rejection_email,
        'notify_admin': notify_admin,
    })
