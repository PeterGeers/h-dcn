"""Email sending utility for membership workflow transitions.

Provides a reusable `send_membership_email()` function that:
1. Loads an HTML template from S3 (locale-aware with nl fallback)
2. Merges shared org variables + caller-provided variables
3. Renders {{PLACEHOLDER}} substitution
4. Extracts subject from <title> tag
5. Sends via SES (noreply@h-dcn.nl)

Emails are side effects — failures are logged but never block
the workflow transition.
"""

import json
import logging
import os
import re
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EMAIL_TEMPLATES_BUCKET: str = os.environ.get('EMAIL_TEMPLATES_BUCKET', 'h-dcn-email-templates')
SENDER_EMAIL: str = os.environ.get('SENDER_EMAIL', 'noreply@h-dcn.nl')
DEFAULT_LOCALE: str = 'nl'
SUPPORTED_LOCALES: tuple[str, ...] = ('nl', 'en', 'de', 'fr', 'es', 'it', 'da', 'sv')

# ---------------------------------------------------------------------------
# AWS clients (shared across invocations for connection reuse)
# ---------------------------------------------------------------------------

s3_client = boto3.client('s3', region_name='eu-west-1')
ses_client = boto3.client('ses', region_name='eu-west-1')

# ---------------------------------------------------------------------------
# Shared variables cache (loaded once per Lambda container)
# ---------------------------------------------------------------------------

_variables_cache: dict[str, str] | None = None


def _get_shared_variables() -> dict[str, str]:
    """Load shared organization variables from S3 config/variables.json.

    Cached for the lifetime of the Lambda container.
    Falls back to environment variables if S3 is unreachable.
    """
    global _variables_cache
    if _variables_cache is not None:
        return _variables_cache

    try:
        response = s3_client.get_object(
            Bucket=EMAIL_TEMPLATES_BUCKET,
            Key='config/variables.json',
        )
        _variables_cache = json.loads(response['Body'].read().decode('utf-8'))
    except Exception as e:
        logger.warning(f"Failed to load shared variables from S3: {e}")
        _variables_cache = {
            'ORGANIZATION_NAME': os.environ.get(
                'ORGANIZATION_NAME', 'Harley-Davidson Club Nederland'
            ),
            'ORGANIZATION_WEBSITE': os.environ.get(
                'ORGANIZATION_WEBSITE', 'https://portal.h-dcn.nl'
            ),
            'ORGANIZATION_EMAIL': os.environ.get(
                'ORGANIZATION_EMAIL', 'webhulpje@h-dcn.nl'
            ),
            'ORGANIZATION_SHORT_NAME': os.environ.get(
                'ORGANIZATION_SHORT_NAME', 'H-DCN'
            ),
        }

    return _variables_cache


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------


def _load_template(template_name: str, locale: str) -> str | None:
    """Load an HTML template from S3 with locale fallback.

    Resolution order:
    1. templates/{locale}/{template_name}.html
    2. templates/nl/{template_name}.html  (Dutch fallback)

    Returns None if the template cannot be loaded from any path.
    """
    # Try requested locale first (skip if already nl)
    if locale and locale != DEFAULT_LOCALE:
        html = _load_s3_template(f'templates/{locale}/{template_name}.html')
        if html:
            return html

    # Fallback to Dutch
    return _load_s3_template(f'templates/{DEFAULT_LOCALE}/{template_name}.html')


def _load_s3_template(key: str) -> str | None:
    """Attempt to load a single template file from S3."""
    try:
        response = s3_client.get_object(
            Bucket=EMAIL_TEMPLATES_BUCKET,
            Key=key,
        )
        return response['Body'].read().decode('utf-8')
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code in ('NoSuchKey', '404'):
            return None
        logger.warning(f"S3 error loading template '{key}': {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error loading template '{key}': {e}")
        return None


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_template(template_html: str, variables: dict[str, Any]) -> str:
    """Replace all {{PLACEHOLDER}} tokens with values from variables dict."""
    rendered = template_html
    for key, value in variables.items():
        placeholder = f"{{{{{key}}}}}"
        rendered = rendered.replace(placeholder, str(value) if value is not None else '')
    return rendered


def _extract_subject(rendered_html: str, template_name: str) -> str:
    """Extract the email subject from the <title> tag of the rendered HTML.

    Falls back to a generic subject based on the template name.
    """
    match = re.search(r'<title>(.*?)</title>', rendered_html, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    # Readable fallback from template name: "membership-welcome" → "Membership Welcome"
    fallback = template_name.replace('-', ' ').replace('_', ' ').title()
    return f"H-DCN — {fallback}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def send_membership_email(
    template_name: str,
    recipient: str,
    variables: dict[str, Any],
    locale: str = DEFAULT_LOCALE,
) -> bool:
    """Send a membership workflow email using an S3-hosted HTML template.

    This function is designed to be called as a side effect during workflow
    transitions. It will NEVER raise an exception — all errors are logged
    and the function returns False.

    Args:
        template_name: Template file name without extension and path,
            e.g. 'membership-welcome' → loads templates/{locale}/membership-welcome.html
        recipient: Email address of the recipient.
        variables: Dict of placeholder values specific to this email
            (merged with shared organization variables).
        locale: Two-letter locale code (default: 'nl').
            Falls back to Dutch if the requested locale template is not found.

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    if not recipient:
        logger.warning(
            f"Cannot send email '{template_name}': no recipient address provided"
        )
        return False

    # Normalize locale
    effective_locale = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE

    try:
        # 1. Load template
        template_html = _load_template(template_name, effective_locale)
        if not template_html:
            logger.error(
                f"Template '{template_name}' not found for locale "
                f"'{effective_locale}' or fallback '{DEFAULT_LOCALE}'"
            )
            return False

        # 2. Merge shared variables + caller variables (caller overrides shared)
        shared_vars = _get_shared_variables()
        all_variables: dict[str, Any] = {**shared_vars, **variables}

        # 3. Render template
        rendered_html = _render_template(template_html, all_variables)

        # 4. Extract subject
        subject = _extract_subject(rendered_html, template_name)

        # 5. Send via SES
        ses_client.send_email(
            Source=SENDER_EMAIL,
            Destination={'ToAddresses': [recipient]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {'Html': {'Data': rendered_html, 'Charset': 'UTF-8'}},
            },
        )

        logger.info(
            f"Email '{template_name}' sent to {recipient} (locale={effective_locale})"
        )
        return True

    except ClientError as e:
        logger.error(
            f"SES error sending '{template_name}' to {recipient}: {e}"
        )
        return False
    except Exception as e:
        logger.error(
            f"Unexpected error sending '{template_name}' to {recipient}: {e}"
        )
        return False
