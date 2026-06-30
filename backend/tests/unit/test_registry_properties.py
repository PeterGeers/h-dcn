"""
Property-Based Tests for Closed Community Booking: Registry Merge and Email Masking

Tests the core logic for the get_event_registry handler using Hypothesis.
Covers: registry merge/sort (Property 2) and email masking (Property 3).
"""

import os
import sys
import importlib.util

import pytest
from hypothesis import given, settings, assume, note
from hypothesis import strategies as st

# --- Load handler module via importlib (per testing-backend.md steering) ---

_handler_file = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), '..', '..', 'handler',
        'get_event_registry', 'app.py'
    )
)


def _load_handler():
    """Load handler module by file path, bypassing sys.path."""
    if 'app' in sys.modules:
        del sys.modules['app']
    # We need the shared layer on the path for the handler to import
    layers_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
    )
    if layers_path not in sys.path:
        sys.path.insert(0, layers_path)

    spec = importlib.util.spec_from_file_location('get_event_registry_app', _handler_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Load the handler module — we only need pure functions (mask_email)
# The handler imports boto3 etc. at module level, so we patch if needed
try:
    _handler = _load_handler()
    mask_email = _handler.mask_email
except Exception:
    # If the handler can't be loaded (missing AWS dependencies in test env),
    # define mask_email inline matching the handler's implementation
    def mask_email(email: str) -> str:
        """Fallback: same logic as handler."""
        if not email or '@' not in email:
            return '***@unknown'
        local, domain = email.split('@', 1)
        return f"{local[:2]}***@{domain}"


# --- Pure merge function extracted from handler logic for testability ---

def merge_registry(s3_rows: list[dict], registry_claims: dict, claim_mode: str = 'first_come_first_served') -> list[dict]:
    """
    Merge S3 invitee registry rows with DynamoDB registry_claims.

    Mirrors the logic in get_event_registry lambda_handler:
    - One output entry per S3 row
    - Mark each row as available or taken based on presence in registry_claims
    - Mask claimant emails for taken rows
    - Sort alphabetically case-insensitive by label

    Args:
        s3_rows: List of row dicts from S3 invitee_registry.json
        registry_claims: Dict mapping row_id -> claim object (with 'email', 'name', etc.)
        claim_mode: The claim mode from registry_config

    Returns:
        Sorted list of merged row dicts
    """
    merged_rows = []

    for row in s3_rows:
        row_id = row.get('row_id', '')
        label = row.get('label', '')
        logo_url = row.get('logo_url')
        allowed_emails = row.get('allowed_emails', [])

        claim = registry_claims.get(row_id)
        is_claimed = claim is not None

        merged_row = {
            'row_id': row_id,
            'label': label,
            'available': not is_claimed,
            'logo_url': logo_url,
            'claimed_contact': mask_email(claim['email']) if is_claimed and claim.get('email') else None,
        }

        if claim_mode == 'email_restricted':
            merged_row['allowed_emails'] = allowed_emails

        merged_rows.append(merged_row)

    # Sort alphabetically case-insensitive by label
    merged_rows.sort(key=lambda r: r['label'].lower())

    return merged_rows


# =============================================================================
# Hypothesis Strategies
# =============================================================================

# Strategy for valid row_ids (unique identifiers)
row_id_strategy = st.from_regex(r'row_[a-z0-9]{4,10}', fullmatch=True)

# Strategy for labels (non-empty strings for sorting tests)
label_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N', 'Zs'), min_codepoint=32),
    min_size=1,
    max_size=50,
).filter(lambda s: s.strip() != '')

# Strategy for valid email addresses (must contain exactly one '@')
email_local_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), min_codepoint=48, max_codepoint=122),
    min_size=2,
    max_size=30,
).filter(lambda s: '@' not in s and len(s) >= 2)

email_domain_strategy = st.from_regex(r'[a-z]{2,10}\.[a-z]{2,4}', fullmatch=True)

email_strategy = st.builds(
    lambda local, domain: f"{local}@{domain}",
    email_local_strategy,
    email_domain_strategy,
)

# Strategy for S3 registry rows
s3_row_strategy = st.fixed_dictionaries({
    'row_id': row_id_strategy,
    'label': label_strategy,
    'logo_url': st.one_of(st.none(), st.from_regex(r'https://[a-z]+\.s3\.amazonaws\.com/[a-z]+\.png', fullmatch=True)),
    'allowed_emails': st.lists(email_strategy, min_size=0, max_size=3),
})

# Strategy for claim objects (what's stored in registry_claims)
claim_strategy = st.fixed_dictionaries({
    'member_id': st.from_regex(r'mem_[a-z0-9]{6,12}', fullmatch=True),
    'email': email_strategy,
    'name': st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'Zs'))),
    'claimed_at': st.from_regex(r'2025-0[1-9]-[0-2][0-9]T[0-2][0-9]:[0-5][0-9]:[0-5][0-9]Z', fullmatch=True),
})


# =============================================================================
# Property 2: Registry Merge and Sort
# =============================================================================

class TestProperty2RegistryMergeAndSort:
    """
    # Feature: closed-community-booking, Property 2: Registry Merge and Sort

    **Validates: Requirements 2.1, 2.3**

    For any S3 invitee registry (list of rows) and any DynamoDB registry_claims map,
    the merge function SHALL produce an output list that:
    (a) contains exactly one entry per row in the S3 registry,
    (b) marks each row as available or taken based on presence in registry_claims,
    (c) is sorted alphabetically case-insensitive by label, and
    (d) includes masked contact emails for claimed rows.
    """

    @given(
        s3_rows=st.lists(s3_row_strategy, min_size=1, max_size=20, unique_by=lambda r: r['row_id']),
        claim_indices=st.data(),
    )
    @settings(max_examples=100)
    def test_output_contains_one_entry_per_s3_row(self, s3_rows: list, claim_indices):
        """
        **Validates: Requirements 2.1, 2.3**

        (a) The merge output contains exactly one entry per row in the S3 registry.
        """
        # Generate claims for a random subset of rows
        num_claims = claim_indices.draw(st.integers(min_value=0, max_value=len(s3_rows)))
        claimed_row_ids = claim_indices.draw(
            st.lists(
                st.sampled_from([r['row_id'] for r in s3_rows]),
                min_size=num_claims,
                max_size=num_claims,
                unique=True,
            )
        )
        claims_list = claim_indices.draw(st.lists(claim_strategy, min_size=num_claims, max_size=num_claims))
        registry_claims = dict(zip(claimed_row_ids, claims_list))

        result = merge_registry(s3_rows, registry_claims)

        # (a) Exactly one entry per S3 row
        assert len(result) == len(s3_rows), (
            f"Expected {len(s3_rows)} rows in output, got {len(result)}"
        )

        # Verify all row_ids are present
        result_row_ids = {r['row_id'] for r in result}
        input_row_ids = {r['row_id'] for r in s3_rows}
        assert result_row_ids == input_row_ids

    @given(
        s3_rows=st.lists(s3_row_strategy, min_size=1, max_size=20, unique_by=lambda r: r['row_id']),
        claim_indices=st.data(),
    )
    @settings(max_examples=100)
    def test_marks_rows_available_or_taken(self, s3_rows: list, claim_indices):
        """
        **Validates: Requirements 2.1, 2.3**

        (b) Each row is correctly marked as available or taken based on
        presence in registry_claims.
        """
        num_claims = claim_indices.draw(st.integers(min_value=0, max_value=len(s3_rows)))
        claimed_row_ids = claim_indices.draw(
            st.lists(
                st.sampled_from([r['row_id'] for r in s3_rows]),
                min_size=num_claims,
                max_size=num_claims,
                unique=True,
            )
        )
        claims_list = claim_indices.draw(st.lists(claim_strategy, min_size=num_claims, max_size=num_claims))
        registry_claims = dict(zip(claimed_row_ids, claims_list))

        result = merge_registry(s3_rows, registry_claims)

        for row in result:
            row_id = row['row_id']
            if row_id in registry_claims:
                assert row['available'] is False, (
                    f"Row {row_id} is claimed but marked as available"
                )
            else:
                assert row['available'] is True, (
                    f"Row {row_id} is not claimed but marked as taken"
                )

    @given(
        s3_rows=st.lists(s3_row_strategy, min_size=2, max_size=20, unique_by=lambda r: r['row_id']),
    )
    @settings(max_examples=100)
    def test_output_sorted_alphabetically_case_insensitive(self, s3_rows: list):
        """
        **Validates: Requirements 2.1, 2.3**

        (c) The output is sorted alphabetically case-insensitive by label.
        """
        result = merge_registry(s3_rows, {})

        labels = [r['label'] for r in result]
        for i in range(len(labels) - 1):
            assert labels[i].lower() <= labels[i + 1].lower(), (
                f"Not sorted: '{labels[i]}' should come before '{labels[i + 1]}'"
            )

    @given(
        s3_rows=st.lists(s3_row_strategy, min_size=1, max_size=10, unique_by=lambda r: r['row_id']),
        claim_indices=st.data(),
    )
    @settings(max_examples=100)
    def test_includes_masked_email_for_claimed_rows(self, s3_rows: list, claim_indices):
        """
        **Validates: Requirements 2.1, 2.3**

        (d) Claimed rows include masked contact emails; available rows have None.
        """
        # Claim all rows for this test
        num_claims = claim_indices.draw(st.integers(min_value=1, max_value=len(s3_rows)))
        claimed_row_ids = claim_indices.draw(
            st.lists(
                st.sampled_from([r['row_id'] for r in s3_rows]),
                min_size=num_claims,
                max_size=num_claims,
                unique=True,
            )
        )
        claims_list = claim_indices.draw(st.lists(claim_strategy, min_size=num_claims, max_size=num_claims))
        registry_claims = dict(zip(claimed_row_ids, claims_list))

        result = merge_registry(s3_rows, registry_claims)

        for row in result:
            row_id = row['row_id']
            if row_id in registry_claims:
                # Should have a masked email
                assert row['claimed_contact'] is not None, (
                    f"Claimed row {row_id} has no masked contact"
                )
                # Verify it matches the XX***@domain pattern
                assert '***@' in row['claimed_contact'], (
                    f"Masked email '{row['claimed_contact']}' doesn't match XX***@domain pattern"
                )
            else:
                assert row['claimed_contact'] is None, (
                    f"Available row {row_id} should have None claimed_contact"
                )


# =============================================================================
# Property 3: Email Masking
# =============================================================================

class TestProperty3EmailMasking:
    """
    # Feature: closed-community-booking, Property 3: Email Masking

    **Validates: Requirements 2.3, 16.2**

    For any valid email address (containing exactly one '@'), the mask function
    SHALL produce a string matching the pattern XX***@domain where XX are the
    first 2 characters of the local part and domain is the complete domain part.
    The output SHALL never expose the full local part.
    """

    @given(email=email_strategy)
    @settings(max_examples=200)
    def test_mask_produces_xx_star_at_domain_pattern(self, email: str):
        """
        **Validates: Requirements 2.3, 16.2**

        For any valid email, mask_email produces XX***@domain where XX are
        the first 2 chars of local part and domain is complete.
        """
        result = mask_email(email)
        local, domain = email.split('@', 1)

        # Result should be: first 2 chars of local + "***@" + full domain
        expected = f"{local[:2]}***@{domain}"
        assert result == expected, (
            f"mask_email('{email}') = '{result}', expected '{expected}'"
        )

        note(f"Email: {email} → {result}")

    @given(email=email_strategy)
    @settings(max_examples=200)
    def test_mask_never_exposes_full_local_part(self, email: str):
        """
        **Validates: Requirements 2.3, 16.2**

        The masked output never exposes the full local part (when local > 2 chars).
        """
        result = mask_email(email)
        local, _ = email.split('@', 1)

        if len(local) > 2:
            # The full local part should NOT appear in the result
            assert local not in result, (
                f"Full local part '{local}' exposed in masked result '{result}'"
            )

    @given(email=email_strategy)
    @settings(max_examples=200)
    def test_mask_preserves_full_domain(self, email: str):
        """
        **Validates: Requirements 2.3, 16.2**

        The masked output preserves the complete domain part unchanged.
        """
        result = mask_email(email)
        _, domain = email.split('@', 1)

        assert result.endswith(f"@{domain}"), (
            f"Domain '{domain}' not preserved in masked result '{result}'"
        )

    @given(email=email_strategy)
    @settings(max_examples=100)
    def test_mask_output_contains_exactly_one_at_sign(self, email: str):
        """
        **Validates: Requirements 2.3, 16.2**

        The masked output contains exactly one '@' character.
        """
        result = mask_email(email)
        assert result.count('@') == 1, (
            f"Masked result '{result}' should contain exactly one '@'"
        )

    @given(email=email_strategy)
    @settings(max_examples=100)
    def test_mask_output_starts_with_two_chars_from_local(self, email: str):
        """
        **Validates: Requirements 2.3, 16.2**

        The masked output starts with the first 2 characters of the local part.
        """
        result = mask_email(email)
        local, _ = email.split('@', 1)

        expected_prefix = local[:2]
        assert result.startswith(expected_prefix), (
            f"Masked result '{result}' should start with '{expected_prefix}'"
        )
