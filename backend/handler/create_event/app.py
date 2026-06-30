import json
import boto3
import bcrypt
import uuid
import os
from datetime import datetime
from decimal import Decimal

# Import from shared auth layer (REQUIRED)
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
    from shared.price_validation import validate_price_field
    print("Using shared auth layer")
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("create_event")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('EVENTS_TABLE_NAME', 'Events')
table = dynamodb.Table(table_name)

# Valid event statuses and counting rules
VALID_STATUSES = {'draft', 'open', 'closed', 'archived'}
VALID_COUNTING_RULES = {'count_items_by_product', 'count_distinct_clubs', 'sum_field'}
REQUIRED_FIELDS = ['name', 'event_type', 'start_date', 'end_date', 'linked_regio']


def validate_dates(body):
    """
    Validate date ordering: registration_open < registration_close <= start_date <= end_date.
    Only validates relationships between dates that are actually provided.
    Compares date portions only (first 10 chars: yyyy-mm-dd) to handle mixed
    date-only and datetime-local formats correctly.

    Returns list of error strings (empty if valid).
    """
    errors = []
    reg_open = body.get('registration_open')
    reg_close = body.get('registration_close')
    start = body.get('start_date')
    end = body.get('end_date')

    # Normalize to comparable strings (full datetime for same-type, date portion for cross-type)
    def to_date(val: str) -> str:
        """Extract date portion (yyyy-mm-dd) for comparison."""
        return val[:10] if val else ''

    if reg_open and reg_close and reg_open >= reg_close:
        errors.append('registration_open must be before registration_close')
    if reg_close and end and to_date(reg_close) > to_date(end):
        errors.append('registration_close must be before or equal to end_date')
    if start and end and start > end:
        errors.append('start_date must be before or equal to end_date')

    return errors


def validate_required_fields(body):
    """
    Validate that all required fields are present and non-empty.

    Returns list of missing field names.
    """
    missing = []
    for field in REQUIRED_FIELDS:
        value = body.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    return missing


def validate_constraints(constraints):
    """
    Validate constraints array:
    - Each constraint must have a unique key
    - max must be > 0
    - counting_rule must be one of the valid rules

    Returns list of error strings.
    """
    if not constraints:
        return []

    if not isinstance(constraints, list):
        return ['constraints must be an array']

    errors = []
    seen_keys = set()

    for i, constraint in enumerate(constraints):
        if not isinstance(constraint, dict):
            errors.append(f'constraints[{i}] must be an object')
            continue

        key = constraint.get('key')
        if not key:
            errors.append(f'constraints[{i}]: key is required')
        elif key in seen_keys:
            errors.append(f'constraints[{i}]: duplicate key "{key}"')
        else:
            seen_keys.add(key)

        max_val = constraint.get('max')
        if max_val is None:
            errors.append(f'constraints[{i}]: max is required')
        elif not isinstance(max_val, (int, float)) or max_val <= 0:
            errors.append(f'constraints[{i}]: max must be greater than 0')

        counting_rule = constraint.get('counting_rule')
        if not counting_rule:
            errors.append(f'constraints[{i}]: counting_rule is required')
        elif counting_rule not in VALID_COUNTING_RULES:
            errors.append(
                f'constraints[{i}]: invalid counting_rule "{counting_rule}". '
                f'Must be one of: {", ".join(sorted(VALID_COUNTING_RULES))}'
            )

    return errors


def _check_slug_uniqueness(slug, exclude_event_id=None):
    """
    Check if a landing_page slug is already used by another event.
    Returns an error response if a collision is found, None otherwise.
    """
    response = table.scan(
        FilterExpression='landing_page.slug = :slug AND landing_page.enabled = :enabled',
        ExpressionAttributeValues={
            ':slug': slug,
            ':enabled': True,
        },
        ProjectionExpression='event_id',
    )
    for item in response.get('Items', []):
        if item['event_id'] != exclude_event_id:
            return create_error_response(
                409,
                f'Slug "{slug}" is already in use by another event'
            )
    return None


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Check for events create permission
        required_permissions = ['events_create']

        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response

        # Log successful access
        log_successful_access(user_email, user_roles, 'create_event')

        # Parse request body
        body = json.loads(event['body']) if event.get('body') else {}

        if not isinstance(body, dict):
            return create_error_response(400, 'Request body must be a JSON object')

        # Check if this is a clone operation
        clone_from = body.pop('clone_from', None)
        if clone_from:
            return _handle_clone(clone_from, user_email)

        # Validate required fields
        missing = validate_required_fields(body)
        if missing:
            return create_error_response(400, f'Missing required fields: {", ".join(missing)}')

        # Validate name length
        name = body.get('name', '')
        if len(name) > 200:
            return create_error_response(400, 'name must be at most 200 characters')

        # Validate location length
        location = body.get('location', '')
        if location and len(location) > 300:
            return create_error_response(400, 'location must be at most 300 characters')

        # Validate dates
        date_errors = validate_dates(body)
        if date_errors:
            return create_error_response(400, 'Invalid date ordering', {'date_errors': date_errors})

        # Validate constraints if provided
        constraints = body.get('constraints')
        if constraints is not None:
            constraint_errors = validate_constraints(constraints)
            if constraint_errors:
                return create_error_response(400, 'Invalid constraints', {'constraint_errors': constraint_errors})

        # Validate landing_page slug uniqueness if provided
        landing_page = body.get('landing_page')
        if isinstance(landing_page, dict) and landing_page.get('enabled') and landing_page.get('slug'):
            slug = landing_page['slug']
            slug_error = _check_slug_uniqueness(slug)
            if slug_error:
                return slug_error

        # Validate and coerce financial fields
        for field in ['cost', 'revenue']:
            if field in body and body[field] is not None:
                decimal_value, error = validate_price_field(body[field], field)
                if error:
                    return create_error_response(400, error)
                body[field] = decimal_value

        # Validate participants as non-negative integer
        if 'participants' in body and body['participants'] is not None:
            try:
                body['participants'] = int(body['participants'])
                if body['participants'] < 0:
                    return create_error_response(400, 'participants must be non-negative')
            except (ValueError, TypeError):
                return create_error_response(400, 'participants must be an integer')

        # Hash event_password if provided (store as bcrypt hash, never plaintext)
        if 'event_password' in body:
            raw_password = body['event_password']
            if raw_password and isinstance(raw_password, str):
                if len(raw_password) < 4:
                    return create_error_response(400, 'event_password must be at least 4 characters')
                password_bytes = raw_password.encode('utf-8')[:72]
                body['event_password'] = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')
            else:
                body.pop('event_password', None)

        # Generate event ID and create event item
        event_id = str(uuid.uuid4())
        event_item = {
            'event_id': event_id,
            'status': 'draft',
            'created_at': datetime.utcnow().isoformat(),
            'created_by': user_email,
        }

        # Copy allowed fields from body
        allowed_fields = [
            # core
            'name', 'event_type', 'event_category', 'participation',
            'linked_regio', 'location', 'slug', 'poster_url',
            # dates
            'start_date', 'end_date', 'registration_open', 'registration_close', 'payment_deadline',
            # config
            'constraints', 'product_ids', 'landing_page',
            # booking
            'event_password', 'registry_config',
            # financial
            'participants', 'cost', 'revenue', 'notes',
        ]
        for field in allowed_fields:
            if field in body:
                event_item[field] = body[field]

        # Store event in DynamoDB
        table.put_item(Item=event_item)

        print(f"Event {event_id} created by {user_email} with roles {user_roles}")

        return create_success_response({
            'event_id': event_id,
            'message': 'Event created successfully'
        }, 201)

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Unexpected error in create_event: {str(e)}")
        return create_error_response(500, 'Internal server error')


def _handle_clone(source_event_id, user_email):
    """
    Clone an existing event: copy event_type, product_ids, constraints, location.
    Create a new event in draft status with dates cleared.
    """
    try:
        # Fetch source event
        response = table.get_item(Key={'event_id': source_event_id})
        source = response.get('Item')

        if not source:
            return create_error_response(404, f'Source event not found: {source_event_id}')

        # Create cloned event
        new_event_id = str(uuid.uuid4())
        cloned_event = {
            'event_id': new_event_id,
            'status': 'draft',
            'created_at': datetime.utcnow().isoformat(),
            'created_by': user_email,
        }

        # Copy specific fields from source
        clone_fields = ['event_type', 'product_ids', 'constraints', 'location']
        for field in clone_fields:
            if field in source:
                cloned_event[field] = source[field]

        # Store cloned event (dates intentionally left empty)
        table.put_item(Item=cloned_event)

        print(f"Event {new_event_id} cloned from {source_event_id} by {user_email}")

        return create_success_response({
            'event_id': new_event_id,
            'cloned_from': source_event_id,
            'message': 'Event cloned successfully'
        }, 201)

    except Exception as e:
        print(f"Error cloning event: {str(e)}")
        return create_error_response(500, 'Error cloning event')
