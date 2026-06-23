import json
import boto3
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
    lambda_handler = create_smart_fallback_handler("update_event")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('EVENTS_TABLE_NAME', 'Events')
table = dynamodb.Table(table_name)

# Valid event statuses, transitions, and counting rules
VALID_STATUSES = {'draft', 'open', 'closed', 'archived'}
VALID_COUNTING_RULES = {'count_items_by_product', 'count_distinct_clubs', 'sum_field'}
ALLOWED_MANUAL_TRANSITIONS = {
    'draft': {'open'},
    'open': {'closed'},
    'closed': {'open'},
}
REQUIRED_FIELDS = ['name', 'event_type', 'start_date', 'end_date', 'linked_regio']


def validate_dates(body):
    """
    Validate date ordering: registration_open < registration_close <= start_date <= end_date.
    Only validates relationships between dates that are actually provided.

    Returns list of error strings (empty if valid).
    """
    errors = []
    reg_open = body.get('registration_open')
    reg_close = body.get('registration_close')
    start = body.get('start_date')
    end = body.get('end_date')

    if reg_open and reg_close and reg_open >= reg_close:
        errors.append('registration_open must be before registration_close')
    if reg_close and start and reg_close > start:
        errors.append('registration_close must be before or equal to start_date')
    if start and end and start > end:
        errors.append('start_date must be before or equal to end_date')

    return errors


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

        # Check for events update permission
        required_permissions = ['events_update']

        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response

        # Log successful access
        log_successful_access(user_email, user_roles, 'update_event')

        # Get event_id from path
        event_id = event['pathParameters']['event_id']

        # Parse request body
        body = json.loads(event['body']) if event.get('body') else {}

        if not isinstance(body, dict):
            return create_error_response(400, 'Request body must be a JSON object')

        # Check if this is a status override operation
        if 'status' in body and len(body) == 1:
            return _handle_status_override(event_id, body['status'], user_email)

        # Fetch current event for merge validation
        current_response = table.get_item(Key={'event_id': event_id})
        current_event = current_response.get('Item')

        if not current_event:
            return create_error_response(404, f'Event not found: {event_id}')

        # Merge current event with updates for validation
        merged = {**current_event, **body}
        merged.pop('event_id', None)  # Don't validate event_id as a field

        # If updating date fields, validate ordering using merged values
        date_fields = {'registration_open', 'registration_close', 'start_date', 'end_date'}
        if any(f in body for f in date_fields):
            date_errors = validate_dates(merged)
            if date_errors:
                return create_error_response(400, 'Invalid date ordering', {'date_errors': date_errors})

        # If updating constraints, validate them
        if 'constraints' in body:
            constraint_errors = validate_constraints(body['constraints'])
            if constraint_errors:
                return create_error_response(400, 'Invalid constraints', {'constraint_errors': constraint_errors})

        # Validate name length if provided
        if 'name' in body and len(body['name']) > 200:
            return create_error_response(400, 'name must be at most 200 characters')

        # Validate location length if provided
        if 'location' in body and body['location'] and len(body['location']) > 300:
            return create_error_response(400, 'location must be at most 300 characters')

        # Validate landing_page slug uniqueness if provided
        if 'landing_page' in body:
            landing_page = body['landing_page']
            if isinstance(landing_page, dict) and landing_page.get('enabled') and landing_page.get('slug'):
                slug = landing_page['slug']
                slug_error = _check_slug_uniqueness(slug, event_id)
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

        # Regional access control: check if user may edit this event
        event_regio = current_event.get('linked_regio')
        if event_regio:
            # Users with Events_CRUD or Regio_All can edit any event
            has_full_event_access = any(
                role in ['Events_CRUD', 'Regio_All', 'System_CRUD', 'System_User_Management']
                for role in user_roles
            )
            if not has_full_event_access:
                # Regional user: check if their region matches the event's linked_regio
                user_region_roles = [r for r in user_roles if r.startswith('Regio_')]
                user_regions = []
                for role in user_region_roles:
                    # Extract region name from role (e.g., Regio_Noord-Holland → Noord-Holland)
                    region_name = role.replace('Regio_', '', 1)
                    user_regions.append(region_name)

                if event_regio not in user_regions and 'All' not in user_regions:
                    return create_error_response(
                        403,
                        f'Je hebt geen rechten om events in regio "{event_regio}" te bewerken'
                    )

        # Build update expression
        update_expression = "SET updated_at = :updated_at"
        expression_values = {':updated_at': datetime.utcnow().isoformat()}
        expression_names = {}

        # Fields that can be updated
        updatable_fields = [
            # core
            'name', 'event_type', 'event_category', 'participation',
            'linked_regio', 'location', 'slug', 'poster_url',
            # dates
            'start_date', 'end_date', 'registration_open', 'registration_close', 'payment_deadline',
            # config
            'constraints', 'product_ids', 'landing_page',
            # financial
            'participants', 'cost', 'revenue', 'notes',
        ]

        for key, value in body.items():
            if key in updatable_fields:
                attr_name = f"#{key}"
                update_expression += f", {attr_name} = :{key}"
                expression_values[f":{key}"] = value
                expression_names[attr_name] = key

        update_params = {
            'Key': {'event_id': event_id},
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_values,
            'ConditionExpression': 'attribute_exists(event_id)',
        }

        if expression_names:
            update_params['ExpressionAttributeNames'] = expression_names

        try:
            table.update_item(**update_params)
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            return create_error_response(404, f'Event not found: {event_id}')

        print(f"Event {event_id} updated by {user_email} with roles {user_roles}")

        return create_success_response({
            'message': 'Event updated successfully',
            'updated_fields': [k for k in body.keys() if k in updatable_fields]
        })

    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}')
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Unexpected error in update_event: {str(e)}")
        return create_error_response(500, 'Internal server error')


def _handle_status_override(event_id, new_status, user_email):
    """
    Handle manual status override transitions:
    - draft → open
    - open → closed
    - closed → open
    """
    if new_status not in VALID_STATUSES:
        return create_error_response(400, f'Invalid status: {new_status}. Must be one of: {", ".join(sorted(VALID_STATUSES))}')

    # Fetch current event
    response = table.get_item(Key={'event_id': event_id})
    current_event = response.get('Item')

    if not current_event:
        return create_error_response(404, f'Event not found: {event_id}')

    current_status = current_event.get('status', 'draft')

    # Validate transition
    allowed = ALLOWED_MANUAL_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        return create_error_response(
            400,
            f'Invalid status transition from "{current_status}" to "{new_status}". '
            f'Allowed transitions from "{current_status}": {sorted(allowed) if allowed else "none"}'
        )

    # Perform the status update
    now = datetime.utcnow().isoformat()
    table.update_item(
        Key={'event_id': event_id},
        UpdateExpression='SET #status = :new_status, updated_at = :updated_at, status_changed_at = :changed_at, status_changed_by = :changed_by',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={
            ':new_status': new_status,
            ':updated_at': now,
            ':changed_at': now,
            ':changed_by': user_email,
        },
    )

    print(f"Event {event_id} status changed from {current_status} to {new_status} by {user_email}")

    return create_success_response({
        'message': f'Event status changed from {current_status} to {new_status}',
        'event_id': event_id,
        'previous_status': current_status,
        'new_status': new_status,
    })
