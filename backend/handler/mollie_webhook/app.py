import json
import os
import boto3
import requests
from decimal import Decimal
from boto3.dynamodb.conditions import Attr

# Import shared utilities (only cors_headers for response formatting)
try:
    from shared.auth_utils import cors_headers
except ImportError:
    def cors_headers():
        return {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS,GET,POST,PUT,DELETE,PATCH",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Credentials": "false"
        }

dynamodb = boto3.resource('dynamodb')
payments_table = dynamodb.Table(os.environ.get('PAYMENTS_TABLE_NAME', 'Payments'))
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))

MOLLIE_API_KEY = os.environ.get('MOLLIE_API_KEY', '')


def fetch_mollie_payment(mollie_payment_id):
    """
    Fetch payment status from Mollie API.

    Args:
        mollie_payment_id: The Mollie payment ID (e.g., tr_xxx)

    Returns:
        dict: Mollie payment object, or None on error
    """
    try:
        url = f"https://api.mollie.com/v2/payments/{mollie_payment_id}"
        headers = {
            "Authorization": f"Bearer {MOLLIE_API_KEY}",
            "Content-Type": "application/json"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Mollie API error: status={response.status_code}, body={response.text}")
            return None
    except Exception as e:
        print(f"Error fetching Mollie payment {mollie_payment_id}: {str(e)}")
        return None


def find_payment_by_mollie_id(mollie_payment_id):
    """
    Find payment record in Payments table by mollie_payment_id.

    Args:
        mollie_payment_id: The Mollie payment ID to look up

    Returns:
        dict or None: The payment record, or None if not found
    """
    try:
        response = payments_table.scan(
            FilterExpression=Attr('mollie_payment_id').eq(mollie_payment_id)
        )
        items = response.get('Items', [])

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = payments_table.scan(
                FilterExpression=Attr('mollie_payment_id').eq(mollie_payment_id),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get('Items', []))

        if items:
            return items[0]
        return None
    except Exception as e:
        print(f"Error finding payment by mollie_id {mollie_payment_id}: {str(e)}")
        return None


def update_payment_status(payment_id, new_status):
    """
    Update payment record status in Payments table.

    Args:
        payment_id: The internal payment_id (primary key)
        new_status: The new status string
    """
    try:
        payments_table.update_item(
            Key={'payment_id': payment_id},
            UpdateExpression='SET #status = :status, updated_at = :updated_at',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': new_status,
                ':updated_at': _now_iso()
            }
        )
    except Exception as e:
        print(f"Error updating payment {payment_id} status to {new_status}: {str(e)}")
        raise


def recalculate_order_payment_status(order_id):
    """
    Recalculate and update order payment_status based on all paid payments.

    Loads all payments for the order_id, sums amounts where status="paid",
    compares to order total_amount:
    - If outstanding balance = 0 → payment_status = "paid"
    - Else → payment_status = "partial"

    Args:
        order_id: The order_id to recalculate
    """
    try:
        # Load order
        order_response = orders_table.get_item(Key={'order_id': order_id})
        if 'Item' not in order_response:
            print(f"Warning: Order {order_id} not found during payment status recalculation")
            return

        order = order_response['Item']
        order_total = Decimal(str(order.get('total_amount', 0)))

        # Load all payments for this order
        payments_response = payments_table.scan(
            FilterExpression=Attr('order_id').eq(order_id) & Attr('status').eq('paid')
        )
        paid_payments = payments_response.get('Items', [])

        # Handle pagination
        while 'LastEvaluatedKey' in payments_response:
            payments_response = payments_table.scan(
                FilterExpression=Attr('order_id').eq(order_id) & Attr('status').eq('paid'),
                ExclusiveStartKey=payments_response['LastEvaluatedKey']
            )
            paid_payments.extend(payments_response.get('Items', []))

        # Sum paid amounts
        total_paid = Decimal('0.00')
        for payment in paid_payments:
            amount = payment.get('amount', 0)
            if isinstance(amount, Decimal):
                total_paid += amount
            else:
                total_paid += Decimal(str(amount))

        # Determine payment_status
        outstanding = max(Decimal('0.00'), order_total - total_paid)
        if outstanding == Decimal('0.00'):
            new_payment_status = 'paid'
        else:
            new_payment_status = 'partial'

        # Update order payment_status
        orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression='SET payment_status = :ps, updated_at = :updated_at',
            ExpressionAttributeValues={
                ':ps': new_payment_status,
                ':updated_at': _now_iso()
            }
        )
        print(f"Order {order_id} payment_status updated to '{new_payment_status}' "
              f"(total={order_total}, paid={total_paid}, outstanding={outstanding})")

    except Exception as e:
        print(f"Error recalculating payment status for order {order_id}: {str(e)}")
        raise


def _now_iso():
    """Return current UTC timestamp in ISO format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def lambda_handler(event, context):
    """
    Mollie webhook handler.

    - No Cognito auth (public endpoint called by Mollie)
    - Receives Mollie payment ID via form-encoded POST body
    - Fetches payment status from Mollie API
    - Updates payment record and optionally order payment_status
    - Always returns 200 to Mollie
    - Idempotent: re-processing same payment ID is safe
    """
    try:
        # Handle OPTIONS request (unlikely for webhook but good practice)
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': ''
            }

        # Extract Mollie payment ID from request body
        # Mollie sends form-encoded body with 'id' field
        body = event.get('body', '')
        mollie_payment_id = None

        if body:
            # Check if body is base64 encoded (API Gateway may encode it)
            if event.get('isBase64Encoded', False):
                import base64
                body = base64.b64decode(body).decode('utf-8')

            # Parse form-encoded body: "id=tr_xxx"
            try:
                # Try form-encoded first
                from urllib.parse import parse_qs
                parsed = parse_qs(body)
                if 'id' in parsed:
                    mollie_payment_id = parsed['id'][0]
            except Exception:
                pass

            # Fallback: try JSON body
            if not mollie_payment_id:
                try:
                    json_body = json.loads(body)
                    mollie_payment_id = json_body.get('id')
                except (json.JSONDecodeError, TypeError):
                    pass

        if not mollie_payment_id:
            print("Warning: No Mollie payment ID found in webhook request body")
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps({'status': 'ignored', 'reason': 'no payment id'})
            }

        print(f"Processing Mollie webhook for payment: {mollie_payment_id}")

        # Fetch payment status from Mollie API
        mollie_payment = fetch_mollie_payment(mollie_payment_id)
        if not mollie_payment:
            print(f"Warning: Could not fetch Mollie payment {mollie_payment_id}")
            # Return 200 to prevent Mollie from retrying endlessly
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps({'status': 'error', 'reason': 'mollie api unavailable'})
            }

        mollie_status = mollie_payment.get('status', '')
        print(f"Mollie payment {mollie_payment_id} status: {mollie_status}")

        # Find our payment record by mollie_payment_id
        payment_record = find_payment_by_mollie_id(mollie_payment_id)
        if not payment_record:
            print(f"Warning: No payment record found for mollie_payment_id {mollie_payment_id}")
            # Return 200 - don't crash, this might be a duplicate or old webhook
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps({'status': 'ignored', 'reason': 'payment not found'})
            }

        payment_id = payment_record['payment_id']
        order_id = payment_record.get('order_id')
        current_status = payment_record.get('status', '')

        # Idempotency: if payment is already in the target status, skip
        if current_status == mollie_status:
            print(f"Payment {payment_id} already has status '{mollie_status}', skipping")
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps({'status': 'ok', 'message': 'already processed'})
            }

        # Update payment record status
        update_payment_status(payment_id, mollie_status)

        # Handle status-specific logic
        if mollie_status == 'paid':
            # Payment successful: recalculate order payment_status
            if order_id:
                recalculate_order_payment_status(order_id)
            else:
                print(f"Warning: Payment {payment_id} has no order_id, cannot update order status")

        elif mollie_status in ('failed', 'cancelled', 'expired'):
            # Payment failed/cancelled/expired: update payment record only
            # Order payment_status remains unchanged
            print(f"Payment {payment_id} status set to '{mollie_status}', order status unchanged")

        else:
            # Other statuses (open, pending, authorized): update payment record only
            print(f"Payment {payment_id} status set to '{mollie_status}' (intermediate status)")

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'status': 'ok'})
        }

    except Exception as e:
        # Always return 200 to Mollie to prevent retry flooding
        print(f"Error processing Mollie webhook: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'status': 'error', 'reason': 'internal error'})
        }
