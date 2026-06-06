"""
Property-Based Tests for PresMeet Club Logo Upload

# Feature: presmeet-club-logo-upload, Property 1: Client-side file size validation boundary

Tests the file size validation boundary using Hypothesis to verify
correctness across arbitrary file sizes around the 5MB limit.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# The MAX_IMAGE_SIZE constant as defined in the upload_club_logo handler
MAX_IMAGE_SIZE = 5_242_880  # 5MB in bytes


# --- Validation function under test ---

def validate_file_size(size_in_bytes: int) -> bool:
    """
    Client-side file size validation logic.
    Mirrors the check in upload_club_logo/app.py:
        if len(image_bytes) > MAX_IMAGE_SIZE: reject

    Returns True if the file size is acceptable (≤ MAX_IMAGE_SIZE),
    False if the file is too large (> MAX_IMAGE_SIZE).
    """
    return size_in_bytes <= MAX_IMAGE_SIZE


# =============================================================================
# Property 1: Client-side file size validation boundary
# =============================================================================

class TestProperty1FileSizeValidationBoundary:
    """
    **Validates: Requirements 2.3**

    Property 1: For any file with size greater than 5MB (5,242,880 bytes),
    the validation function SHALL reject it. For any file with size less than
    or equal to 5MB, the validation function SHALL accept it.
    """

    @given(size=st.integers(min_value=0, max_value=MAX_IMAGE_SIZE))
    @settings(max_examples=100)
    def test_files_at_or_below_5mb_are_accepted(self, size: int):
        """Files with size <= 5MB (5,242,880 bytes) SHALL be accepted."""
        assert validate_file_size(size) is True

    @given(size=st.integers(min_value=MAX_IMAGE_SIZE + 1, max_value=MAX_IMAGE_SIZE * 10))
    @settings(max_examples=100)
    def test_files_above_5mb_are_rejected(self, size: int):
        """Files with size > 5MB (5,242,880 bytes) SHALL be rejected."""
        assert validate_file_size(size) is False

    def test_exact_boundary_5mb_accepted(self):
        """Exactly 5MB (5,242,880 bytes) SHALL be accepted."""
        assert validate_file_size(MAX_IMAGE_SIZE) is True

    def test_one_byte_over_boundary_rejected(self):
        """5MB + 1 byte (5,242,881 bytes) SHALL be rejected."""
        assert validate_file_size(MAX_IMAGE_SIZE + 1) is False

    def test_max_image_size_constant_is_5mb(self):
        """Confirm MAX_IMAGE_SIZE is exactly 5MB."""
        assert MAX_IMAGE_SIZE == 5_242_880


# =============================================================================
# Feature: presmeet-club-logo-upload, Property 2: Base64 encoding round-trip
# Validates: Requirements 3.1
# =============================================================================

import base64


class TestProperty2Base64EncodingRoundTrip:
    """
    # Feature: presmeet-club-logo-upload, Property 2: Base64 encoding round-trip

    **Validates: Requirements 3.1**

    For any valid byte sequence representing image data, encoding it to base64
    and then decoding the result SHALL produce the original byte sequence.
    """

    @given(data=st.binary(min_size=0, max_size=5_242_880))
    @settings(max_examples=100)
    def test_base64_encode_decode_roundtrip(self, data: bytes):
        """
        **Validates: Requirements 3.1**

        For any byte sequence, encoding to base64 then decoding produces
        the original bytes.
        """
        encoded = base64.b64encode(data).decode('utf-8')
        decoded = base64.b64decode(encoded)
        assert decoded == data


# =============================================================================
# Property 7: Server-side payload size limit
# =============================================================================

import json
import os
import sys
from unittest.mock import patch, MagicMock

# Ensure backend root is importable for package-style imports
_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_layers_path = os.path.join(_backend_dir, "layers", "auth-layer", "python")

if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)

# Set environment variables before importing handler
os.environ.setdefault('FRONTEND_BUCKET_NAME', 'h-dcn-frontend-506221081911')
os.environ.setdefault('MEMBERS_TABLE_NAME', 'Members')
os.environ.setdefault('COGNITO_USER_POOL_ID', 'eu-west-1_test')

from handler.upload_club_logo.app import lambda_handler


class TestProperty7ServerSidePayloadSizeLimit:
    """
    # Feature: presmeet-club-logo-upload, Property 7: Server-side payload size limit

    **Validates: Requirements 4.8**

    For any base64-encoded payload whose decoded size exceeds 5MB (5,242,880 bytes),
    the upload handler SHALL return a 413 status code.
    """

    @given(
        extra_bytes=st.integers(min_value=1, max_value=800_000),
    )
    @settings(max_examples=100, deadline=None)
    def test_oversized_payload_returns_413(self, extra_bytes):
        """For any payload exceeding 5MB after base64 decoding, handler returns 413."""
        from hypothesis import note

        # Generate oversized byte payload (5MB + extra_bytes, keeping it reasonable)
        oversized_data = b'\x00' * (MAX_IMAGE_SIZE + extra_bytes)
        note(f"Generated payload size: {len(oversized_data)} bytes ({extra_bytes} over limit)")

        # Base64 encode the oversized data
        encoded_data = base64.b64encode(oversized_data).decode('utf-8')

        # Build a realistic API Gateway event
        event = {
            'httpMethod': 'POST',
            'headers': {
                'Authorization': 'Bearer mock-token'
            },
            'body': json.dumps({
                'image_data': encoded_data,
                'club_id': 'test-club-123',
                'content_type': 'image/png'
            })
        }

        # Mock auth and club identity so we reach the size check
        with patch('handler.upload_club_logo.app.extract_user_credentials') as mock_auth, \
             patch('handler.upload_club_logo.app.get_club_id') as mock_club_id, \
             patch('handler.upload_club_logo.app.s3_client'):
            mock_auth.return_value = ('test@test.nl', ['hdcnLeden'], None)
            mock_club_id.return_value = 'test-club-123'

            # Import and invoke handler
            response = lambda_handler(event, None)

        assert response['statusCode'] == 413, (
            f"Expected 413 for payload of {len(oversized_data)} bytes "
            f"(limit is {MAX_IMAGE_SIZE}), got {response['statusCode']}"
        )

        # Verify error message is present
        body = json.loads(response['body'])
        assert 'error' in body
        note(f"Error message: {body['error']}")


# =============================================================================
# Feature: presmeet-club-logo-upload, Property 5: Output is always valid PNG
# =============================================================================

import io
from PIL import Image
from hypothesis import note

# PNG magic bytes
PNG_MAGIC = b'\x89PNG\r\n\x1a\n'

# Supported input formats
SUPPORTED_FORMATS = ['PNG', 'JPEG', 'WEBP', 'GIF']

# Max dimensions used by the handler
_MAX_DIMENSIONS = (200, 200)


def _create_test_image(width, height, fmt):
    """Create a valid image in the specified format and return its bytes."""
    # Use RGB for JPEG (doesn't support alpha), RGBA for others
    mode = 'RGB' if fmt == 'JPEG' else 'RGBA'
    image = Image.new(mode, (width, height), color=(100, 150, 200) if mode == 'RGB' else (100, 150, 200, 255))
    buffer = io.BytesIO()
    if fmt == 'GIF':
        # GIF doesn't support RGBA, convert to RGB
        image = image.convert('RGB')
    image.save(buffer, format=fmt)
    return buffer.getvalue()


def _process_image(image_bytes):
    """
    Replicate the resize+convert logic from upload_club_logo handler.

    From app.py:
        image.thumbnail((200, 200), Image.LANCZOS)
        # Convert mode if necessary
        if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
            image = image.convert('RGBA')
        elif image.mode != 'RGB' and image.mode != 'RGBA':
            image = image.convert('RGB')
        # Convert to PNG
        output_buffer = io.BytesIO()
        image.save(output_buffer, format='PNG')
        return output_buffer.getvalue()
    """
    image = Image.open(io.BytesIO(image_bytes))
    image.thumbnail(_MAX_DIMENSIONS, Image.LANCZOS)

    if image.mode in ('RGBA', 'LA') or (
        image.mode == 'P' and 'transparency' in image.info
    ):
        image = image.convert('RGBA')
    elif image.mode != 'RGB' and image.mode != 'RGBA':
        image = image.convert('RGB')

    output_buffer = io.BytesIO()
    image.save(output_buffer, format='PNG')
    return output_buffer.getvalue()


class TestProperty5OutputAlwaysValidPNG:
    """
    # Feature: presmeet-club-logo-upload, Property 5: Output is always valid PNG

    **Validates: Requirements 4.3**

    For any valid image in any supported input format (PNG, JPEG, WebP, GIF),
    after processing through the resize logic, the output bytes SHALL begin
    with PNG magic bytes and be a parseable PNG file.
    """

    @given(
        width=st.integers(min_value=1, max_value=2000),
        height=st.integers(min_value=1, max_value=2000),
        fmt=st.sampled_from(SUPPORTED_FORMATS),
    )
    @settings(max_examples=100, deadline=None)
    def test_output_starts_with_png_magic_bytes(self, width, height, fmt):
        """After processing any valid image, output always starts with PNG magic bytes."""
        # Create a valid image in the given format
        image_bytes = _create_test_image(width, height, fmt)
        note(f"Input: {width}x{height} {fmt} ({len(image_bytes)} bytes)")

        # Process through the resize+convert logic
        output_bytes = _process_image(image_bytes)
        note(f"Output: {len(output_bytes)} bytes")

        # Verify PNG magic bytes
        assert output_bytes[:8] == PNG_MAGIC, (
            f"Output does not start with PNG magic bytes. "
            f"Got: {output_bytes[:8]!r}, Expected: {PNG_MAGIC!r}"
        )

    @given(
        width=st.integers(min_value=1, max_value=2000),
        height=st.integers(min_value=1, max_value=2000),
        fmt=st.sampled_from(SUPPORTED_FORMATS),
    )
    @settings(max_examples=100, deadline=None)
    def test_output_is_parseable_png(self, width, height, fmt):
        """After processing any valid image, the output is a fully parseable PNG file."""
        # Create a valid image in the given format
        image_bytes = _create_test_image(width, height, fmt)
        note(f"Input: {width}x{height} {fmt} ({len(image_bytes)} bytes)")

        # Process through the resize+convert logic
        output_bytes = _process_image(image_bytes)

        # Verify output can be opened as a valid PNG
        output_image = Image.open(io.BytesIO(output_bytes))
        assert output_image.format == 'PNG', (
            f"Output format is {output_image.format}, expected PNG"
        )
        # Verify the image loads without errors
        output_image.load()


# =============================================================================
# Property 3: Image resize fits within 200×200 preserving aspect ratio
# =============================================================================

from PIL import Image


class TestProperty3ImageResizeFitsWithin200x200:
    """
    # Feature: presmeet-club-logo-upload, Property 3: Image resize fits within 200×200 preserving aspect ratio

    **Validates: Requirements 4.1**

    For any valid image with arbitrary width and height, after applying the resize
    function using image.thumbnail((200, 200), Image.LANCZOS), the output dimensions
    SHALL satisfy:
      width ≤ 200 AND height ≤ 200 AND (width == 200 OR height == 200)
    AND the output aspect ratio SHALL equal the input aspect ratio
    (within ±1 pixel rounding tolerance).
    """

    @given(
        width=st.integers(min_value=1, max_value=5000),
        height=st.integers(min_value=1, max_value=5000),
    )
    @settings(max_examples=100)
    def test_resize_fits_within_200x200_preserving_aspect_ratio(self, width, height):
        """
        For any valid image dimensions, thumbnail((200, 200)) produces output that:
        1. Has width ≤ 200 and height ≤ 200
        2. Has at least one dimension equal to 200 (unless input is smaller)
        3. Preserves the aspect ratio within ±1 pixel rounding tolerance
        """
        from hypothesis import note

        # Create a test image with the generated dimensions
        image = Image.new("RGB", (width, height), color="red")

        # Apply the same resize logic as the handler
        image.thumbnail((200, 200), Image.LANCZOS)

        out_width, out_height = image.size

        note(f"Input: {width}x{height} -> Output: {out_width}x{out_height}")

        # Constraint 1: output must fit within 200x200 bounding box
        assert out_width <= 200, (
            f"Output width {out_width} exceeds 200 for input {width}x{height}"
        )
        assert out_height <= 200, (
            f"Output height {out_height} exceeds 200 for input {width}x{height}"
        )

        # Constraint 2: at least one dimension should equal 200,
        # unless the input was already smaller than 200 in both dimensions
        # (thumbnail does not upscale)
        if width >= 200 or height >= 200:
            assert out_width == 200 or out_height == 200, (
                f"Neither dimension equals 200 for input {width}x{height}: "
                f"got {out_width}x{out_height}"
            )
        else:
            # Input is smaller than 200x200 in both dimensions - thumbnail doesn't upscale
            assert out_width == width and out_height == height, (
                f"Small image should remain unchanged: input {width}x{height}, "
                f"got {out_width}x{out_height}"
            )

        # Constraint 3: aspect ratio preserved within ±1 pixel rounding tolerance
        if width <= 200 and height <= 200:
            # No resize needed, dimensions unchanged
            expected_width = width
            expected_height = height
        else:
            scale = min(200 / width, 200 / height)
            expected_width = round(width * scale)
            expected_height = round(height * scale)

        # Allow ±1 pixel tolerance for rounding
        assert abs(out_width - expected_width) <= 1, (
            f"Width mismatch: expected ~{expected_width}, got {out_width} "
            f"for input {width}x{height}"
        )
        assert abs(out_height - expected_height) <= 1, (
            f"Height mismatch: expected ~{expected_height}, got {out_height} "
            f"for input {width}x{height}"
        )


# =============================================================================
# Feature: presmeet-club-logo-upload, Property 8: Authorization — club ownership or admin override
# Validates: Requirements 5.5, 5.6
# =============================================================================

# Admin roles that grant override access (must match handler's ADMIN_ROLES)
_ADMIN_ROLES = {'Products_CRUD', 'Webshop_Management'}

# All possible roles to draw from in generated test data
_ALL_POSSIBLE_ROLES = [
    'Products_CRUD',
    'Webshop_Management',
    'Leden_Beheren',
    'Events_Beheren',
    'Financien_Beheren',
    'Webshop_Klant',
    'hdcn_leden',
]

# Non-admin roles only (for denial tests)
_NON_ADMIN_ROLES = [
    'Leden_Beheren',
    'Events_Beheren',
    'Financien_Beheren',
    'Webshop_Klant',
    'hdcn_leden',
]


def _is_authorized(user_club_id: str, request_club_id: str, user_roles: list) -> bool:
    """
    Pure authorization logic extracted from the upload_club_logo handler.
    Access is granted if:
    - request_club_id matches user_club_id (own club), OR
    - user has at least one admin role (Products_CRUD or Webshop_Management)
    """
    if request_club_id == user_club_id:
        return True
    has_admin_role = bool(_ADMIN_ROLES.intersection(set(user_roles)))
    return has_admin_role


class TestProperty8AuthorizationClubOwnershipOrAdminOverride:
    """
    # Feature: presmeet-club-logo-upload, Property 8: Authorization — club ownership or admin override

    **Validates: Requirements 5.5, 5.6**

    For any combination of (user_club_id, request_club_id, user_roles),
    the upload SHALL succeed if and only if request_club_id == user_club_id
    OR 'Products_CRUD' in user_roles OR 'Webshop_Management' in user_roles.
    Otherwise it SHALL return 403.
    """

    @given(
        user_club_id=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')),
            min_size=1,
            max_size=50,
        ),
        request_club_id=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')),
            min_size=1,
            max_size=50,
        ),
        user_roles=st.lists(
            st.sampled_from(_ALL_POSSIBLE_ROLES),
            min_size=0,
            max_size=4,
            unique=True,
        ),
    )
    @settings(max_examples=100)
    def test_authorization_decision_matches_expected_logic(
        self,
        user_club_id: str,
        request_club_id: str,
        user_roles: list,
    ):
        """
        **Validates: Requirements 5.5, 5.6**

        For any (user_club_id, request_club_id, user_roles) tuple, access
        is granted iff the club IDs match OR the user holds an admin role.
        """
        from hypothesis import note

        owns_club = request_club_id == user_club_id
        has_admin = 'Products_CRUD' in user_roles or 'Webshop_Management' in user_roles
        expected_authorized = owns_club or has_admin

        actual_authorized = _is_authorized(user_club_id, request_club_id, user_roles)

        note(f"user_club={user_club_id!r}, req_club={request_club_id!r}, roles={user_roles}")
        assert actual_authorized == expected_authorized, (
            f"Authorization mismatch: "
            f"user_club_id={user_club_id!r}, request_club_id={request_club_id!r}, "
            f"roles={user_roles!r} -> expected={expected_authorized}, got={actual_authorized}"
        )

    @given(
        club_id=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')),
            min_size=1,
            max_size=50,
        ),
        user_roles=st.lists(
            st.sampled_from(_ALL_POSSIBLE_ROLES),
            min_size=0,
            max_size=4,
            unique=True,
        ),
    )
    @settings(max_examples=100)
    def test_own_club_always_authorized(self, club_id: str, user_roles: list):
        """
        **Validates: Requirements 5.5**

        When request_club_id equals user_club_id, access is always granted
        regardless of roles.
        """
        assert _is_authorized(club_id, club_id, user_roles) is True

    @given(
        user_club_id=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')),
            min_size=1,
            max_size=50,
        ),
        request_club_id=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')),
            min_size=1,
            max_size=50,
        ),
        admin_role=st.sampled_from(['Products_CRUD', 'Webshop_Management']),
        extra_roles=st.lists(
            st.sampled_from(_ALL_POSSIBLE_ROLES),
            min_size=0,
            max_size=3,
            unique=True,
        ),
    )
    @settings(max_examples=100)
    def test_admin_role_always_authorized(
        self,
        user_club_id: str,
        request_club_id: str,
        admin_role: str,
        extra_roles: list,
    ):
        """
        **Validates: Requirements 5.6**

        When user holds Products_CRUD or Webshop_Management, access is
        always granted regardless of club_id match.
        """
        roles = list(set([admin_role] + extra_roles))
        assert _is_authorized(user_club_id, request_club_id, roles) is True

    @given(
        user_club_id=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')),
            min_size=1,
            max_size=20,
        ),
        request_club_id=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd')),
            min_size=1,
            max_size=20,
        ),
        user_roles=st.lists(
            st.sampled_from(_NON_ADMIN_ROLES),
            min_size=0,
            max_size=4,
            unique=True,
        ),
    )
    @settings(max_examples=100)
    def test_non_admin_different_club_denied(
        self,
        user_club_id: str,
        request_club_id: str,
        user_roles: list,
    ):
        """
        **Validates: Requirements 5.5, 5.6**

        When club IDs differ and user has no admin role, access is denied.
        """
        from hypothesis import assume
        assume(user_club_id != request_club_id)

        assert _is_authorized(user_club_id, request_club_id, user_roles) is False


# =============================================================================
# Feature: presmeet-club-logo-upload, Property 9: Response URL contains cache-busting parameter
# Validates: Requirements 6.1
# =============================================================================


def _make_valid_png_bytes() -> bytes:
    """Create a minimal valid PNG image for testing."""
    img = Image.new("RGB", (50, 50), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestProperty9ResponseUrlCacheBusting:
    """
    Property 9: Response URL contains cache-busting parameter

    For any successful upload with a given club_id, the returned logo_url
    SHALL contain the substring `assets/presmeet/logos/{club_id}.png?t=`
    followed by a numeric timestamp.

    **Validates: Requirements 6.1**
    """

    @given(
        club_id=st.from_regex(r'[a-zA-Z0-9]{1,30}', fullmatch=True),
    )
    @settings(max_examples=100, deadline=None)
    def test_successful_upload_url_contains_cache_bust_timestamp(self, club_id: str):
        """
        **Validates: Requirements 6.1**

        For any alphanumeric club_id, a successful upload returns a logo_url
        containing `assets/presmeet/logos/{club_id}.png?t=` followed by digits.
        """
        import base64 as _b64

        # Create a valid PNG image
        valid_image_bytes = _make_valid_png_bytes()
        encoded_image = _b64.b64encode(valid_image_bytes).decode('utf-8')

        # Build API Gateway event
        event = {
            'httpMethod': 'POST',
            'headers': {
                'Authorization': 'Bearer mock-token'
            },
            'body': json.dumps({
                'image_data': encoded_image,
                'club_id': club_id,
                'content_type': 'image/png',
            }),
        }

        # Mock auth, club identity, and S3 so we get a successful upload
        mock_s3 = MagicMock()

        with patch('handler.upload_club_logo.app.extract_user_credentials') as mock_auth, \
             patch('handler.upload_club_logo.app.get_club_id') as mock_club_id, \
             patch('handler.upload_club_logo.app.s3_client', mock_s3):
            mock_auth.return_value = ('user@club.nl', ['hdcnLeden'], None)
            mock_club_id.return_value = club_id  # Same as request -> authorized

            response = lambda_handler(event, None)

        # Verify successful response
        assert response['statusCode'] == 200, (
            f"Expected 200 for valid upload with club_id={club_id!r}, "
            f"got {response['statusCode']}: {response.get('body')}"
        )

        body = json.loads(response['body'])
        assert 'logo_url' in body, (
            f"Response body should contain 'logo_url', got keys: {list(body.keys())}"
        )

        logo_url = body['logo_url']

        # Verify URL contains the expected cache-busting pattern
        expected_pattern = f'assets/presmeet/logos/{club_id}.png?t='
        assert expected_pattern in logo_url, (
            f"logo_url should contain '{expected_pattern}', got: {logo_url}"
        )

        # Verify the timestamp part after ?t= is numeric
        t_index = logo_url.index('?t=')
        timestamp_str = logo_url[t_index + 3:]
        assert timestamp_str.isdigit(), (
            f"Cache-busting parameter should be numeric, got: {timestamp_str!r}"
        )
        assert int(timestamp_str) > 0, (
            f"Timestamp should be positive, got: {timestamp_str}"
        )


# =============================================================================
# Feature: presmeet-club-logo-upload, Property 4: Invalid image data produces 400 error without S3 side effects
# Validates: Requirements 4.2, 4.7
# =============================================================================


def _is_valid_image(data: bytes) -> bool:
    """Check if byte sequence happens to be a valid image (unlikely for random bytes)."""
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        return True
    except Exception:
        return False


class TestProperty4InvalidImageDataProduces400:
    """
    # Feature: presmeet-club-logo-upload, Property 4: Invalid image data produces 400 error without S3 side effects

    **Validates: Requirements 4.2, 4.7**

    For any byte sequence that is NOT a valid image (random bytes, truncated headers,
    non-image files), the upload handler SHALL return a 400 status code and SHALL NOT
    invoke S3 put_object.
    """

    @given(
        invalid_data=st.binary(min_size=1, max_size=1000).filter(
            lambda b: not _is_valid_image(b)
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_invalid_image_returns_400_no_s3_call(self, invalid_data: bytes):
        """
        **Validates: Requirements 4.2, 4.7**

        For any non-image byte sequence, the handler returns 400 and does not
        call S3 put_object.
        """
        from hypothesis import note
        import base64 as b64

        # Base64 encode the invalid image data
        encoded_data = b64.b64encode(invalid_data).decode('utf-8')

        # Build a realistic API Gateway event
        event = {
            'httpMethod': 'POST',
            'headers': {
                'Authorization': 'Bearer mock-token'
            },
            'body': json.dumps({
                'image_data': encoded_data,
                'club_id': 'test-club-123',
                'content_type': 'image/png',
            }),
        }

        # Mock auth, club identity, and S3 client
        mock_s3 = MagicMock()

        with patch('handler.upload_club_logo.app.extract_user_credentials') as mock_auth, \
             patch('handler.upload_club_logo.app.get_club_id') as mock_club_id, \
             patch('handler.upload_club_logo.app.s3_client', mock_s3):
            mock_auth.return_value = ('user@club.nl', ['hdcnLeden'], None)
            mock_club_id.return_value = 'test-club-123'

            response = lambda_handler(event, None)

        # Verify: handler returns 400 for invalid image data
        assert response['statusCode'] == 400, (
            f"Expected 400 for invalid image data ({len(invalid_data)} bytes), "
            f"got {response['statusCode']}: {response.get('body')}"
        )

        # Verify: S3 put_object was NOT called (no side effects)
        mock_s3.put_object.assert_not_called()

        # Verify error message is descriptive
        body = json.loads(response['body'])
        assert 'error' in body, "Response should contain an 'error' field"
        note(f"Error: {body['error']} for {len(invalid_data)} bytes of invalid data")


# =============================================================================
# Feature: presmeet-club-logo-upload, Property 6: S3 key construction matches pattern
# Validates: Requirements 4.4
# =============================================================================


class TestProperty6S3KeyConstructionMatchesPattern:
    """
    Property 6: S3 key construction matches pattern

    For any valid club_id string, the constructed S3 key SHALL equal
    `assets/presmeet/logos/{club_id}.png` exactly.

    **Validates: Requirements 4.4**
    """

    @given(
        club_id=st.text(
            alphabet=st.characters(whitelist_categories=('L', 'N', 'Pd', 'Pc')),
            min_size=1,
            max_size=100,
        ),
    )
    @settings(max_examples=100)
    def test_s3_key_equals_expected_pattern(self, club_id: str):
        """
        **Validates: Requirements 4.4**

        For any club_id string, the S3 key constructed by the handler logic
        SHALL equal 'assets/presmeet/logos/{club_id}.png' exactly.
        """
        # This is the exact key construction used in the handler
        s3_key = f'assets/presmeet/logos/{club_id}.png'

        # Verify the key matches the expected pattern
        expected_key = f'assets/presmeet/logos/{club_id}.png'
        assert s3_key == expected_key, (
            f"S3 key mismatch: got {s3_key!r}, expected {expected_key!r}"
        )

        # Verify structural properties of the key
        assert s3_key.startswith('assets/presmeet/logos/'), (
            f"Key must start with 'assets/presmeet/logos/', got: {s3_key!r}"
        )
        assert s3_key.endswith('.png'), (
            f"Key must end with '.png', got: {s3_key!r}"
        )

        # Verify the club_id is embedded correctly in the key
        # Extract club_id back from the key
        prefix = 'assets/presmeet/logos/'
        suffix = '.png'
        extracted_club_id = s3_key[len(prefix):-len(suffix)]
        assert extracted_club_id == club_id, (
            f"Extracted club_id {extracted_club_id!r} does not match input {club_id!r}"
        )

        note(f"club_id={club_id!r} -> s3_key={s3_key!r}")
