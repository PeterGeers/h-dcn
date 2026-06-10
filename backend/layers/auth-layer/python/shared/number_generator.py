"""
Number generator module for order numbers and invoice numbers.

Uses DynamoDB atomic counters (UpdateItem with ADD operation) to guarantee
unique sequential numbers without race conditions. The ADD operation is
atomic — concurrent Lambda invocations never get the same sequence value.
Counters auto-create on first use (ADD to a non-existent attribute
initializes to 0 + increment).

Order number format: H-YYMMDD-NNN (daily sequence, zero-padded to 3 digits)
Invoice number format: F-YYYY-NNNN (yearly sequence, zero-padded to 4 digits)
"""

import time
import logging
from datetime import date
from typing import Optional

from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)

# Retry configuration for transient DynamoDB failures
MAX_RETRIES = 3
BASE_DELAY_SECONDS = 0.1  # 100ms base delay for exponential backoff


class CounterWriteError(Exception):
    """Raised when DynamoDB UpdateItem fails for a counter after all retries.

    This indicates a transient DynamoDB failure (throttling, service error)
    that persisted through retry attempts with exponential backoff.
    """

    def __init__(self, counter_id: str, original_error: Optional[Exception] = None):
        self.counter_id = counter_id
        self.original_error = original_error
        message = f"Failed to update counter '{counter_id}' after {MAX_RETRIES} attempts"
        if original_error:
            message += f": {original_error}"
        super().__init__(message)


def _increment_counter(counters_table, counter_id: str) -> int:
    """
    Atomically increment a counter in DynamoDB and return the new value.

    Uses UpdateItem with ADD operation which is atomic and auto-creates
    the item if it doesn't exist (initializes to 0 + increment = 1).

    Retries up to MAX_RETRIES times with exponential backoff for transient
    DynamoDB errors (throttling, internal server errors).

    Args:
        counters_table: boto3 DynamoDB Table resource for the counters table.
        counter_id: The partition key value identifying the counter.

    Returns:
        The new counter value after incrementing.

    Raises:
        CounterWriteError: If all retry attempts fail.
    """
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            response = counters_table.update_item(
                Key={'counter_id': counter_id},
                UpdateExpression='ADD current_value :inc',
                ExpressionAttributeValues={':inc': 1},
                ReturnValues='UPDATED_NEW',
            )
            sequence = int(response['Attributes']['current_value'])
            return sequence

        except ClientError as e:
            last_error = e
            error_code = e.response['Error']['Code']

            # Retryable errors: throttling and internal server errors
            if error_code in (
                'ProvisionedThroughputExceededException',
                'ThrottlingException',
                'InternalServerError',
                'ServiceUnavailable',
            ):
                if attempt < MAX_RETRIES - 1:
                    delay = BASE_DELAY_SECONDS * (2 ** attempt)
                    logger.warning(
                        "Counter update attempt %d/%d failed for '%s' (%s), "
                        "retrying in %.2fs",
                        attempt + 1,
                        MAX_RETRIES,
                        counter_id,
                        error_code,
                        delay,
                    )
                    time.sleep(delay)
                    continue

            # Non-retryable error or final attempt — raise immediately
            logger.error(
                "Counter update failed for '%s': %s", counter_id, e
            )
            raise CounterWriteError(counter_id, e) from e

    # All retries exhausted
    raise CounterWriteError(counter_id, last_error)


def generate_order_number(counters_table, today: Optional[date] = None) -> str:
    """
    Generate a unique order number in format H-YYMMDD-NNN.

    Uses a DynamoDB atomic counter keyed by date to produce sequential
    daily order numbers. The counter auto-creates on first use each day.

    Args:
        counters_table: boto3 DynamoDB Table resource for the counters table.
        today: Optional date override (defaults to today). Useful for testing.

    Returns:
        Order number string like "H-250115-001".

    Raises:
        CounterWriteError: If DynamoDB update fails after retries.
    """
    if today is None:
        today = date.today()

    today_str = today.strftime('%y%m%d')
    counter_id = f'order_counter#{today_str}'

    sequence = _increment_counter(counters_table, counter_id)
    order_number = f"H-{today_str}-{sequence:03d}"

    logger.info("Generated order number: %s", order_number)
    return order_number


def generate_invoice_number(counters_table, year: Optional[int] = None) -> str:
    """
    Generate a unique invoice number in format F-YYYY-NNNN.

    Uses a DynamoDB atomic counter keyed by calendar year to produce
    sequential gapless invoice numbers. The counter auto-creates on
    first use each year.

    Args:
        counters_table: boto3 DynamoDB Table resource for the counters table.
        year: Optional year override (defaults to current year). Useful for testing.

    Returns:
        Invoice number string like "F-2025-0042".

    Raises:
        CounterWriteError: If DynamoDB update fails after retries.
    """
    if year is None:
        year = date.today().year

    counter_id = f'invoice_counter#{year}'

    sequence = _increment_counter(counters_table, counter_id)
    invoice_number = f"F-{year}-{sequence:04d}"

    logger.info("Generated invoice number: %s", invoice_number)
    return invoice_number
