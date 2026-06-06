"""
Unit tests for the item_fields_validator module.

Tests validate_item_fields_data and validate_field_value against
the order_item_fields definitions (Requirements 4.1–4.6, 17.1–17.5).
"""

import pytest
from shared.item_fields_validator import (
    validate_item_fields_data,
    validate_field_value,
)


# --- Field definitions used in tests ---

TEXT_FIELD_REQUIRED = {
    "id": "name",
    "label": "Name",
    "type": "text",
    "required": True,
    "validation": {"min_length": 2, "max_length": 100},
}

TEXT_FIELD_OPTIONAL = {
    "id": "notes",
    "label": "Notes",
    "type": "text",
    "required": False,
    "validation": {"max_length": 500},
}

EMAIL_FIELD_REQUIRED = {
    "id": "email",
    "label": "Email",
    "type": "email",
    "required": True,
}

SELECT_FIELD_REQUIRED = {
    "id": "dietary",
    "label": "Dietary",
    "type": "select",
    "required": True,
    "options": ["None", "Vegetarian", "Vegan"],
}

NUMBER_FIELD_WITH_RANGE = {
    "id": "age",
    "label": "Age",
    "type": "number",
    "required": True,
    "validation": {"minimum": 18, "maximum": 99},
}

DATE_FIELD_REQUIRED = {
    "id": "arrival_date",
    "label": "Arrival Date",
    "type": "date",
    "required": True,
}

TEXT_FIELD_WITH_PATTERN = {
    "id": "phone",
    "label": "Phone",
    "type": "text",
    "required": False,
    "validation": {"pattern": r"^\+?[0-9\- ]{7,15}$"},
}


# --- Tests for validate_item_fields_data ---

class TestValidateItemFieldsData:
    """Tests for the main validation orchestrator."""

    def test_valid_submission(self):
        """Happy path: correct count and valid values."""
        fields_def = [TEXT_FIELD_REQUIRED, SELECT_FIELD_REQUIRED]
        data = [
            {"field_values": {"name": "Jan", "dietary": "Vegetarian"}},
            {"field_values": {"name": "Piet", "dietary": "None"}},
        ]
        result = validate_item_fields_data(data, fields_def, quantity=2)
        assert result is None

    def test_missing_item_fields_data(self):
        """None item_fields_data returns count mismatch error."""
        fields_def = [TEXT_FIELD_REQUIRED]
        result = validate_item_fields_data(None, fields_def, quantity=2, line_item_index=1)
        assert result is not None
        assert result["error"] == "item_fields_count_mismatch"
        assert result["details"]["line_item_index"] == 1
        assert result["details"]["expected"] == 2
        assert result["details"]["actual"] == 0

    def test_count_too_few(self):
        """Fewer entries than quantity returns count mismatch."""
        fields_def = [TEXT_FIELD_REQUIRED]
        data = [{"field_values": {"name": "Jan"}}]
        result = validate_item_fields_data(data, fields_def, quantity=3, line_item_index=0)
        assert result is not None
        assert result["error"] == "item_fields_count_mismatch"
        assert result["details"]["expected"] == 3
        assert result["details"]["actual"] == 1

    def test_count_too_many(self):
        """More entries than quantity returns count mismatch."""
        fields_def = [TEXT_FIELD_REQUIRED]
        data = [
            {"field_values": {"name": "A"}},
            {"field_values": {"name": "B"}},
            {"field_values": {"name": "C"}},
        ]
        result = validate_item_fields_data(data, fields_def, quantity=2)
        assert result is not None
        assert result["error"] == "item_fields_count_mismatch"
        assert result["details"]["expected"] == 2
        assert result["details"]["actual"] == 3

    def test_required_field_missing_value(self):
        """Required field with empty value returns validation error."""
        fields_def = [TEXT_FIELD_REQUIRED]
        data = [{"field_values": {"name": ""}}]
        result = validate_item_fields_data(data, fields_def, quantity=1)
        assert result is not None
        assert result["error"] == "item_fields_validation_error"
        assert result["details"]["item_index"] == 0
        assert result["details"]["field_id"] == "name"
        assert result["details"]["constraint"] == "required"

    def test_constraint_violation_in_second_item(self):
        """Validation error in second item correctly reports item_index=1."""
        fields_def = [TEXT_FIELD_REQUIRED]
        data = [
            {"field_values": {"name": "Valid Name"}},
            {"field_values": {"name": "X"}},  # Too short (min_length=2 violated... wait, "X" has length 1)
        ]
        result = validate_item_fields_data(data, fields_def, quantity=2)
        assert result is not None
        assert result["details"]["item_index"] == 1
        assert result["details"]["field_id"] == "name"
        assert "min_length" in result["details"]["constraint"]

    def test_direct_dict_format(self):
        """Supports direct dict format (without field_values wrapper)."""
        fields_def = [TEXT_FIELD_REQUIRED]
        data = [{"name": "Jan"}]
        result = validate_item_fields_data(data, fields_def, quantity=1)
        assert result is None

    def test_optional_fields_allow_empty(self):
        """Optional fields can be empty without triggering errors."""
        fields_def = [TEXT_FIELD_OPTIONAL]
        data = [{"field_values": {"notes": ""}}]
        result = validate_item_fields_data(data, fields_def, quantity=1)
        assert result is None

    def test_optional_fields_allow_missing(self):
        """Optional fields can be absent without triggering errors."""
        fields_def = [TEXT_FIELD_OPTIONAL]
        data = [{"field_values": {}}]
        result = validate_item_fields_data(data, fields_def, quantity=1)
        assert result is None


# --- Tests for validate_field_value ---

class TestValidateFieldValueRequired:
    """Tests for required field validation."""

    def test_required_text_empty_string(self):
        assert validate_field_value("", TEXT_FIELD_REQUIRED) == "required"

    def test_required_text_whitespace_only(self):
        assert validate_field_value("   ", TEXT_FIELD_REQUIRED) == "required"

    def test_required_text_none(self):
        assert validate_field_value(None, TEXT_FIELD_REQUIRED) == "required"

    def test_required_text_valid(self):
        assert validate_field_value("Jan", TEXT_FIELD_REQUIRED) is None

    def test_required_select_empty(self):
        assert validate_field_value("", SELECT_FIELD_REQUIRED) == "required"

    def test_required_select_valid(self):
        assert validate_field_value("Vegetarian", SELECT_FIELD_REQUIRED) is None

    def test_required_number_none(self):
        assert validate_field_value(None, NUMBER_FIELD_WITH_RANGE) == "required"

    def test_required_number_zero_is_valid(self):
        """Zero is a valid number value (not empty)."""
        field = {**NUMBER_FIELD_WITH_RANGE, "validation": {}}
        assert validate_field_value(0, field) is None

    def test_required_date_none(self):
        assert validate_field_value(None, DATE_FIELD_REQUIRED) == "required"

    def test_required_date_empty_string(self):
        assert validate_field_value("", DATE_FIELD_REQUIRED) == "required"

    def test_required_date_valid(self):
        assert validate_field_value("2024-01-15", DATE_FIELD_REQUIRED) is None

    def test_required_email_empty(self):
        assert validate_field_value("", EMAIL_FIELD_REQUIRED) == "required"

    def test_required_email_valid(self):
        assert validate_field_value("test@example.com", EMAIL_FIELD_REQUIRED) is None


class TestValidateFieldValueText:
    """Tests for text field validation constraints."""

    def test_min_length_violation(self):
        result = validate_field_value("X", TEXT_FIELD_REQUIRED)
        assert result == "min_length:2"

    def test_max_length_violation(self):
        field = {"id": "t", "label": "T", "type": "text", "required": False, "validation": {"max_length": 5}}
        result = validate_field_value("123456", field)
        assert result == "max_length:5"

    def test_pattern_match(self):
        result = validate_field_value("+31 6 1234567", TEXT_FIELD_WITH_PATTERN)
        assert result is None

    def test_pattern_no_match(self):
        result = validate_field_value("not a phone", TEXT_FIELD_WITH_PATTERN)
        assert result is not None
        assert "pattern" in result


class TestValidateFieldValueEmail:
    """Tests for email field validation."""

    def test_valid_email(self):
        result = validate_field_value("user@example.com", EMAIL_FIELD_REQUIRED)
        assert result is None

    def test_invalid_email_no_at(self):
        result = validate_field_value("notanemail", EMAIL_FIELD_REQUIRED)
        assert result == "email_format"

    def test_invalid_email_no_domain(self):
        result = validate_field_value("user@", EMAIL_FIELD_REQUIRED)
        assert result == "email_format"

    def test_email_with_length_constraint(self):
        field = {
            "id": "email",
            "label": "Email",
            "type": "email",
            "required": False,
            "validation": {"max_length": 10},
        }
        result = validate_field_value("a@very-long-domain.com", field)
        assert result == "max_length:10"


class TestValidateFieldValueSelect:
    """Tests for select field validation."""

    def test_valid_option(self):
        result = validate_field_value("Vegetarian", SELECT_FIELD_REQUIRED)
        assert result is None

    def test_invalid_option(self):
        result = validate_field_value("Paleo", SELECT_FIELD_REQUIRED)
        assert result == "options"

    def test_case_sensitive(self):
        """Select options are case-sensitive."""
        result = validate_field_value("vegetarian", SELECT_FIELD_REQUIRED)
        assert result == "options"


class TestValidateFieldValueNumber:
    """Tests for number field validation constraints."""

    def test_valid_in_range(self):
        result = validate_field_value(25, NUMBER_FIELD_WITH_RANGE)
        assert result is None

    def test_below_minimum(self):
        result = validate_field_value(17, NUMBER_FIELD_WITH_RANGE)
        assert result == "minimum:18"

    def test_above_maximum(self):
        result = validate_field_value(100, NUMBER_FIELD_WITH_RANGE)
        assert result == "maximum:99"

    def test_string_number_valid(self):
        """String numbers are coerced."""
        result = validate_field_value("25", NUMBER_FIELD_WITH_RANGE)
        assert result is None

    def test_non_numeric_string(self):
        result = validate_field_value("abc", NUMBER_FIELD_WITH_RANGE)
        # Required check happens first for required fields
        # but "abc" is not empty for number? Actually it fails _is_empty_for_type
        # because float("abc") raises ValueError, so it's "empty" → "required"
        assert result == "required"
