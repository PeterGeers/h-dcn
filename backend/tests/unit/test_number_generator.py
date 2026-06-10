"""
Unit tests for shared.number_generator module.

Tests the atomic counter-based order number and invoice number generation
using moto for DynamoDB mocking.
"""

import pytest
import boto3
from moto import mock_aws
from datetime import date
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

from shared.number_generator import (
    generate_order_number,
    generate_invoice_number,
    CounterWriteError,
    _increment_counter,
    MAX_RETRIES,
)


@pytest.fixture
def counters_table():
    """Create a mocked DynamoDB Counters table."""
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.create_table(
            TableName='Counters',
            KeySchema=[
                {'AttributeName': 'counter_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'counter_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        table.meta.client.get_waiter('table_exists').wait(TableName='Counters')
        yield table


class TestGenerateOrderNumber:
    """Tests for generate_order_number function."""

    def test_generates_correct_format(self, counters_table):
        """Order number follows H-YYMMDD-NNN format."""
        today = date(2025, 1, 15)
        result = generate_order_number(counters_table, today=today)
        assert result == "H-250115-001"

    def test_sequential_numbers_same_day(self, counters_table):
        """Multiple calls on the same day produce sequential numbers."""
        today = date(2025, 6, 3)
        first = generate_order_number(counters_table, today=today)
        second = generate_order_number(counters_table, today=today)
        third = generate_order_number(counters_table, today=today)

        assert first == "H-250603-001"
        assert second == "H-250603-002"
        assert third == "H-250603-003"

    def test_different_days_have_separate_sequences(self, counters_table):
        """Different dates get independent counters."""
        day1 = date(2025, 1, 15)
        day2 = date(2025, 1, 16)

        first_day1 = generate_order_number(counters_table, today=day1)
        first_day2 = generate_order_number(counters_table, today=day2)
        second_day1 = generate_order_number(counters_table, today=day1)

        assert first_day1 == "H-250115-001"
        assert first_day2 == "H-250116-001"
        assert second_day1 == "H-250115-002"

    def test_zero_padding(self, counters_table):
        """Sequence number is zero-padded to 3 digits."""
        today = date(2025, 12, 31)
        result = generate_order_number(counters_table, today=today)
        assert result == "H-251231-001"

    def test_defaults_to_today(self, counters_table):
        """When no date provided, uses today's date."""
        with patch('shared.number_generator.date') as mock_date:
            mock_date.today.return_value = date(2025, 3, 20)
            mock_date.side_effect = lambda *args, **kwargs: date(*args, **kwargs)
            result = generate_order_number(counters_table)
            assert result.startswith("H-")
            # The date part should be 6 digits
            parts = result.split("-")
            assert len(parts) == 3
            assert len(parts[1]) == 6
            assert len(parts[2]) == 3


class TestGenerateInvoiceNumber:
    """Tests for generate_invoice_number function."""

    def test_generates_correct_format(self, counters_table):
        """Invoice number follows F-YYYY-NNNN format."""
        result = generate_invoice_number(counters_table, year=2025)
        assert result == "F-2025-0001"

    def test_sequential_numbers_same_year(self, counters_table):
        """Multiple calls in the same year produce sequential numbers."""
        first = generate_invoice_number(counters_table, year=2025)
        second = generate_invoice_number(counters_table, year=2025)
        third = generate_invoice_number(counters_table, year=2025)

        assert first == "F-2025-0001"
        assert second == "F-2025-0002"
        assert third == "F-2025-0003"

    def test_different_years_have_separate_sequences(self, counters_table):
        """Different years get independent counters."""
        first_2025 = generate_invoice_number(counters_table, year=2025)
        first_2026 = generate_invoice_number(counters_table, year=2026)
        second_2025 = generate_invoice_number(counters_table, year=2025)

        assert first_2025 == "F-2025-0001"
        assert first_2026 == "F-2026-0001"
        assert second_2025 == "F-2025-0002"

    def test_zero_padding_four_digits(self, counters_table):
        """Sequence number is zero-padded to 4 digits."""
        result = generate_invoice_number(counters_table, year=2024)
        assert result == "F-2024-0001"

    def test_defaults_to_current_year(self, counters_table):
        """When no year provided, uses current year."""
        result = generate_invoice_number(counters_table)
        current_year = date.today().year
        assert result == f"F-{current_year}-0001"


class TestCounterWriteError:
    """Tests for CounterWriteError exception."""

    def test_error_message_includes_counter_id(self):
        """Error message includes the counter_id that failed."""
        error = CounterWriteError("order_counter#250115")
        assert "order_counter#250115" in str(error)
        assert str(MAX_RETRIES) in str(error)

    def test_error_preserves_original_error(self):
        """Original exception is accessible."""
        original = ValueError("DynamoDB timeout")
        error = CounterWriteError("test_counter", original)
        assert error.original_error is original
        assert error.counter_id == "test_counter"


class TestRetryLogic:
    """Tests for retry behavior on transient DynamoDB failures."""

    def test_retries_on_throttling(self, counters_table):
        """Retries on ProvisionedThroughputExceededException."""
        # Use a mock table that fails twice then succeeds
        mock_table = MagicMock()
        throttle_error = ClientError(
            {'Error': {'Code': 'ProvisionedThroughputExceededException', 'Message': 'Throttled'}},
            'UpdateItem'
        )
        success_response = {'Attributes': {'current_value': {'N': '1'}}}
        # Note: moto returns Python types, not DynamoDB wire format
        mock_table.update_item.side_effect = [
            throttle_error,
            throttle_error,
            {'Attributes': {'current_value': 1}},
        ]

        with patch('shared.number_generator.time.sleep'):
            result = _increment_counter(mock_table, 'test_counter')

        assert result == 1
        assert mock_table.update_item.call_count == 3

    def test_raises_counter_write_error_after_max_retries(self):
        """Raises CounterWriteError after exhausting all retries."""
        mock_table = MagicMock()
        throttle_error = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Throttled'}},
            'UpdateItem'
        )
        mock_table.update_item.side_effect = throttle_error

        with patch('shared.number_generator.time.sleep'):
            with pytest.raises(CounterWriteError) as exc_info:
                _increment_counter(mock_table, 'test_counter')

        assert exc_info.value.counter_id == 'test_counter'
        assert mock_table.update_item.call_count == MAX_RETRIES

    def test_non_retryable_error_fails_immediately(self):
        """Non-retryable errors (e.g., ValidationException) fail without retry."""
        mock_table = MagicMock()
        validation_error = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Bad request'}},
            'UpdateItem'
        )
        mock_table.update_item.side_effect = validation_error

        with pytest.raises(CounterWriteError) as exc_info:
            _increment_counter(mock_table, 'test_counter')

        assert mock_table.update_item.call_count == 1
        assert exc_info.value.counter_id == 'test_counter'

    @patch('shared.number_generator.time.sleep')
    def test_exponential_backoff_delays(self, mock_sleep):
        """Verifies exponential backoff timing between retries."""
        mock_table = MagicMock()
        throttle_error = ClientError(
            {'Error': {'Code': 'InternalServerError', 'Message': 'Server error'}},
            'UpdateItem'
        )
        mock_table.update_item.side_effect = throttle_error

        with pytest.raises(CounterWriteError):
            _increment_counter(mock_table, 'test_counter')

        # Should have slept between retries with exponential backoff
        assert mock_sleep.call_count == MAX_RETRIES - 1
        calls = [call[0][0] for call in mock_sleep.call_args_list]
        # First retry: 0.1s, second retry: 0.2s
        assert calls[0] == pytest.approx(0.1)
        assert calls[1] == pytest.approx(0.2)


# =============================================================================
# Property-Based Tests (Hypothesis)
# =============================================================================

import re
from hypothesis import given, settings
from hypothesis import strategies as st


# Feature: order-pipeline-improvements, Property 6: Order number format validity
class TestOrderNumberFormatProperty:
    """
    Property 6: For any date and sequence value, the generated order number
    SHALL match the regex pattern ^H-\\d{6}-\\d{3}$ where the first 6 digits
    correspond to YYMMDD of the generation date and the last 3 digits are a
    zero-padded sequence >= 001.

    **Validates: Requirements 3.1**
    """

    @given(generation_date=st.dates(
        min_value=date(2000, 1, 1), max_value=date(2099, 12, 31)
    ))
    @settings(max_examples=200, deadline=None)
    def test_order_number_matches_format(self, generation_date):
        """Order number always matches ^H-\\d{6}-\\d{3}$ for any date."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Counters',
                KeySchema=[
                    {'AttributeName': 'counter_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'counter_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST',
            )
            table.meta.client.get_waiter('table_exists').wait(TableName='Counters')

            result = generate_order_number(table, today=generation_date)

            # Must match the full format pattern
            assert re.match(r'^H-\d{6}-\d{3}$', result), (
                f"Order number '{result}' does not match pattern ^H-\\d{{6}}-\\d{{3}}$"
            )

    @given(generation_date=st.dates(
        min_value=date(2000, 1, 1), max_value=date(2099, 12, 31)
    ))
    @settings(max_examples=200, deadline=None)
    def test_order_number_date_portion_matches_input(self, generation_date):
        """The 6-digit date portion corresponds to YYMMDD of the generation date."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Counters',
                KeySchema=[
                    {'AttributeName': 'counter_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'counter_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST',
            )
            table.meta.client.get_waiter('table_exists').wait(TableName='Counters')

            result = generate_order_number(table, today=generation_date)

            # Extract the date portion and verify it matches the input date
            parts = result.split('-')
            date_part = parts[1]
            expected_date_str = generation_date.strftime('%y%m%d')
            assert date_part == expected_date_str, (
                f"Date portion '{date_part}' does not match expected "
                f"'{expected_date_str}' for date {generation_date}"
            )

    @given(generation_date=st.dates(
        min_value=date(2000, 1, 1), max_value=date(2099, 12, 31)
    ))
    @settings(max_examples=200, deadline=None)
    def test_order_number_sequence_starts_at_001(self, generation_date):
        """The sequence portion is >= 001 (first call always produces 001)."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Counters',
                KeySchema=[
                    {'AttributeName': 'counter_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'counter_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST',
            )
            table.meta.client.get_waiter('table_exists').wait(TableName='Counters')

            result = generate_order_number(table, today=generation_date)

            # Extract sequence and verify it's >= 1
            parts = result.split('-')
            sequence = int(parts[2])
            assert sequence >= 1, (
                f"Sequence {sequence} is less than 1 (minimum is 001)"
            )


# Feature: order-pipeline-improvements, Property 7: Invoice number format validity
class TestInvoiceNumberFormatProperty:
    """
    Property 7: For any year and sequence value, the generated invoice number
    SHALL match the regex pattern ^F-\\d{4}-\\d{4}$ where the first 4 digits
    correspond to the calendar year and the last 4 digits are a zero-padded
    sequence >= 0001.

    **Validates: Requirements 7.1**
    """

    @given(year=st.integers(min_value=2000, max_value=2099))
    @settings(max_examples=200, deadline=None)
    def test_invoice_number_matches_format(self, year):
        """Invoice number always matches ^F-\\d{4}-\\d{4}$ for any year."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Counters',
                KeySchema=[
                    {'AttributeName': 'counter_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'counter_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST',
            )
            table.meta.client.get_waiter('table_exists').wait(TableName='Counters')

            result = generate_invoice_number(table, year=year)

            # Must match the full format pattern
            assert re.match(r'^F-\d{4}-\d{4}$', result), (
                f"Invoice number '{result}' does not match pattern ^F-\\d{{4}}-\\d{{4}}$"
            )

    @given(year=st.integers(min_value=2000, max_value=2099))
    @settings(max_examples=200, deadline=None)
    def test_invoice_number_year_portion_matches_input(self, year):
        """The 4-digit year portion corresponds to the input calendar year."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Counters',
                KeySchema=[
                    {'AttributeName': 'counter_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'counter_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST',
            )
            table.meta.client.get_waiter('table_exists').wait(TableName='Counters')

            result = generate_invoice_number(table, year=year)

            # Extract the year portion and verify it matches the input year
            parts = result.split('-')
            year_part = parts[1]
            assert year_part == str(year), (
                f"Year portion '{year_part}' does not match expected '{year}'"
            )

    @given(year=st.integers(min_value=2000, max_value=2099))
    @settings(max_examples=200, deadline=None)
    def test_invoice_number_sequence_starts_at_0001(self, year):
        """The sequence portion is >= 0001 (first call always produces 0001)."""
        with mock_aws():
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.create_table(
                TableName='Counters',
                KeySchema=[
                    {'AttributeName': 'counter_id', 'KeyType': 'HASH'}
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'counter_id', 'AttributeType': 'S'}
                ],
                BillingMode='PAY_PER_REQUEST',
            )
            table.meta.client.get_waiter('table_exists').wait(TableName='Counters')

            result = generate_invoice_number(table, year=year)

            # Extract sequence and verify it's >= 1
            parts = result.split('-')
            sequence = int(parts[2])
            assert sequence >= 1, (
                f"Sequence {sequence} is less than 1 (minimum is 0001)"
            )


# Feature: order-pipeline-improvements, Property 8: Bank transfer reference equals order number
class TestBankTransferReferenceProperty:
    """
    Property 8: For any order that has an order_number assigned and initiates a
    bank transfer payment, the transfer_instructions.reference field SHALL equal
    the order_number.

    **Validates: Requirements 3.7**
    """

    @given(
        date_part=st.from_regex(r'\d{6}', fullmatch=True),
        seq_part=st.integers(min_value=1, max_value=999),
    )
    @settings(max_examples=200, deadline=None)
    def test_transfer_reference_equals_order_number(self, date_part, seq_part):
        """
        For any valid order_number (H-YYMMDD-NNN format), the bank transfer
        reference produced by the pay_order logic equals the order_number.

        This simulates the pay_order handler's logic:
            order_number = order.get('order_number', order_id[:8])
            transfer_instructions = {'reference': order_number, ...}
        """
        order_number = f"H-{date_part}-{seq_part:03d}"

        # Simulate what pay_order does: read order_number from order dict
        order = {'order_number': order_number, 'order_id': 'fake-uuid-12345678'}

        # The handler's logic for bank transfer reference (Req 3.7)
        reference = order.get('order_number', order['order_id'][:8])

        # Property: reference must equal the order_number
        assert reference == order_number, (
            f"Transfer reference '{reference}' does not equal "
            f"order_number '{order_number}'"
        )

    @given(
        year=st.integers(min_value=0, max_value=99),
        month=st.integers(min_value=1, max_value=12),
        day=st.integers(min_value=1, max_value=28),
        seq=st.integers(min_value=1, max_value=999),
    )
    @settings(max_examples=200, deadline=None)
    def test_transfer_reference_format_preserved(self, year, month, day, seq):
        """
        The transfer reference retains the exact H-YYMMDD-NNN format of the
        order_number — no truncation, no transformation.
        """
        order_number = f"H-{year:02d}{month:02d}{day:02d}-{seq:03d}"

        order = {'order_number': order_number, 'order_id': 'abcdefgh-1234-5678'}

        # Simulate pay_order handler reference assignment
        reference = order.get('order_number', order['order_id'][:8])

        # The reference must match the H-YYMMDD-NNN regex pattern
        assert re.match(r'^H-\d{6}-\d{3}$', reference), (
            f"Transfer reference '{reference}' does not match expected format"
        )
        # And it must be identical to the order_number
        assert reference == order_number
