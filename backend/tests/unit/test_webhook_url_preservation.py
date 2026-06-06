"""
Preservation Property Tests for Webhook URL Construction

These tests verify that the runtime webhook URL construction helper produces
valid, reachable URLs that match the expected API Gateway endpoint pattern.

**Validates: Requirements 3.1, 3.3**

Property 2: Preservation - Webhook URL Construction Produces Valid Reachable URLs

For all valid API Gateway request contexts, the runtime webhook URL construction
function SHALL produce a URL matching:
  https://{apiId}.execute-api.eu-west-1.amazonaws.com/{stage}/mollie-webhook

Approach: Property-based testing with hypothesis to verify URL construction
across many random but valid inputs. The helper is a pure function testable
in isolation, independent of the SAM template fix.
"""

import os
import sys
import re
import pytest
from hypothesis import given, settings, assume, note
from hypothesis import strategies as st
from urllib.parse import urlparse

# Add the create_order handler directory to sys.path so we can import the helper
_handler_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "handler", "create_order"
)
sys.path.insert(0, _handler_dir)

from app import _build_webhook_url  # noqa: E402


# --- Strategies ---

# API Gateway apiId: 10 lowercase alphanumeric characters
api_id_strategy = st.from_regex(r"[a-z0-9]{10}", fullmatch=True)

# Stage name: 1-128 alphanumeric, hyphen, underscore characters
stage_name_strategy = st.from_regex(r"[a-zA-Z0-9_\-]{1,30}", fullmatch=True)


def build_event(api_id, stage):
    """Build a minimal Lambda event with the given requestContext."""
    return {
        "requestContext": {
            "apiId": api_id,
            "stage": stage,
        }
    }


# --- Property Tests ---

class TestWebhookUrlConstruction:
    """
    **Validates: Requirements 3.1, 3.3**

    Property 2: Preservation - Webhook URL Construction Produces Valid Reachable URLs

    For all valid API Gateway request contexts (random apiId strings matching
    [a-z0-9]{10}, random stage names from [a-zA-Z0-9_-]+), the runtime webhook
    URL construction function SHALL produce a URL matching:
      https://{apiId}.execute-api.eu-west-1.amazonaws.com/{stage}/mollie-webhook
    """

    @given(api_id=api_id_strategy, stage=stage_name_strategy)
    @settings(max_examples=200)
    def test_url_matches_expected_pattern(self, api_id, stage):
        """For all valid request contexts, the constructed URL matches the
        expected API Gateway webhook endpoint pattern.

        **Validates: Requirements 3.1, 3.3**
        """
        # Ensure AWS_REGION is set to the expected region
        os.environ['AWS_REGION'] = 'eu-west-1'
        # Clear any MOLLIE_WEBHOOK_URL override so the helper constructs from event
        os.environ.pop('MOLLIE_WEBHOOK_URL', None)

        event = build_event(api_id, stage)
        url = _build_webhook_url(event)

        expected = f"https://{api_id}.execute-api.eu-west-1.amazonaws.com/{stage}/mollie-webhook"
        note(f"Generated URL: {url}")
        note(f"Expected URL: {expected}")

        assert url == expected, (
            f"URL mismatch.\n"
            f"  Got:      {url}\n"
            f"  Expected: {expected}"
        )

    @given(api_id=api_id_strategy, stage=stage_name_strategy)
    @settings(max_examples=200)
    def test_url_always_ends_with_mollie_webhook(self, api_id, stage):
        """For all valid request contexts, the constructed URL always ends
        with /mollie-webhook.

        **Validates: Requirements 3.1, 3.3**
        """
        os.environ['AWS_REGION'] = 'eu-west-1'
        os.environ.pop('MOLLIE_WEBHOOK_URL', None)

        event = build_event(api_id, stage)
        url = _build_webhook_url(event)

        note(f"Generated URL: {url}")
        assert url.endswith("/mollie-webhook"), (
            f"URL does not end with /mollie-webhook: {url}"
        )

    @given(api_id=api_id_strategy, stage=stage_name_strategy)
    @settings(max_examples=200)
    def test_url_is_valid_https(self, api_id, stage):
        """For all valid request contexts, the constructed URL is a valid
        HTTPS URL.

        **Validates: Requirements 3.1, 3.3**
        """
        os.environ['AWS_REGION'] = 'eu-west-1'
        os.environ.pop('MOLLIE_WEBHOOK_URL', None)

        event = build_event(api_id, stage)
        url = _build_webhook_url(event)

        parsed = urlparse(url)
        note(f"Parsed URL: scheme={parsed.scheme}, netloc={parsed.netloc}, path={parsed.path}")

        assert parsed.scheme == "https", f"URL scheme is not https: {parsed.scheme}"
        assert parsed.netloc, f"URL has no netloc (hostname): {url}"
        assert "execute-api" in parsed.netloc, f"URL netloc missing execute-api: {parsed.netloc}"
        assert parsed.path, f"URL has no path: {url}"


class TestWebhookUrlEnvVarOverride:
    """
    **Validates: Requirements 3.3**

    Unit test: When MOLLIE_WEBHOOK_URL env var is set, it takes precedence
    over runtime construction (fallback/override for testing).
    """

    def test_env_var_takes_precedence_when_set(self):
        """When MOLLIE_WEBHOOK_URL is set, it should be used as the webhook URL
        instead of the runtime-constructed URL.

        This tests the fallback/override pattern:
          webhook_url = os.environ.get('MOLLIE_WEBHOOK_URL') or _build_webhook_url(event)
        """
        override_url = "https://custom-override.example.com/mollie-webhook"
        os.environ['MOLLIE_WEBHOOK_URL'] = override_url

        event = build_event("abc1234567", "prod")

        # Simulate the fallback logic that will be used in the handler
        webhook_url = os.environ.get('MOLLIE_WEBHOOK_URL') or _build_webhook_url(event)

        assert webhook_url == override_url, (
            f"Expected env var override to take precedence.\n"
            f"  Got:      {webhook_url}\n"
            f"  Expected: {override_url}"
        )

        # Clean up
        del os.environ['MOLLIE_WEBHOOK_URL']

    def test_runtime_construction_used_when_env_var_empty(self):
        """When MOLLIE_WEBHOOK_URL is empty string, runtime construction is used."""
        os.environ['MOLLIE_WEBHOOK_URL'] = ''
        os.environ['AWS_REGION'] = 'eu-west-1'

        event = build_event("xyz9876543", "staging")

        # Empty string is falsy, so the or-fallback kicks in
        webhook_url = os.environ.get('MOLLIE_WEBHOOK_URL') or _build_webhook_url(event)

        expected = "https://xyz9876543.execute-api.eu-west-1.amazonaws.com/staging/mollie-webhook"
        assert webhook_url == expected

        # Clean up
        del os.environ['MOLLIE_WEBHOOK_URL']

    def test_runtime_construction_used_when_env_var_not_set(self):
        """When MOLLIE_WEBHOOK_URL is not set at all, runtime construction is used."""
        os.environ.pop('MOLLIE_WEBHOOK_URL', None)
        os.environ['AWS_REGION'] = 'eu-west-1'

        event = build_event("def4567890", "dev")

        webhook_url = os.environ.get('MOLLIE_WEBHOOK_URL') or _build_webhook_url(event)

        expected = "https://def4567890.execute-api.eu-west-1.amazonaws.com/dev/mollie-webhook"
        assert webhook_url == expected
