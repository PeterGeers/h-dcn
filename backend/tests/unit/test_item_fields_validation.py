# Feature: order-pipeline-improvements, Property 13: Required item fields validation
"""
Property-Based Test for item fields validation (Property 13).

**Validates: Requirements 6.3, 6.4**

Property 13: Required item fields validation
    For any product with `order_item_fields` containing required fields,
    and any `item_fields_data` submission, if any required field has an
    empty or missing value for any item unit, the validator SHALL return
    an error identifying the `item_index`, `field_id`, and a descriptive
    message. If all required fields have non-empty values, validation
    SHALL pass.
"""

import os
import sys

from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Ensure auth layer is importable
_layers_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'layers', 'auth-layer', 'python')
)
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)

from shared.item_fields_validator import validate_item_fields


# =============================================================================
# Strategies
# =============================================================================

# Valid field types supported by the validator
FIELD_TYPES = ["text", "email", "number", "select", "date"]


def field_id_strategy():
    """Generate valid field IDs (non-empty alphanumeric + underscore)."""
    return st.from_regex(r"[a-z][a-z0-9_]{1,15}", fullmatch=True)


def required_field_definition(field_type=None):
    """Generate a required field definition for a given type."""
    if field_type is None:
        field_type_st = st.sampled_from(FIELD_TYPES)
    else:
        field_type_st = st.just(field_type)

    return st.fixed_dictionaries({
        "id": field_id_strategy(),
        "label": st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N", "Z"))),
        "type": field_type_st,
        "required": st.just(True),
    })


def non_empty_value_for_type(field_type):
    """Generate a non-empty valid value for a given field type."""
    if field_type == "text":
        return st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N")))
    elif field_type == "email":
        # Generate simple valid emails
        local = st.from_regex(r"[a-z]{2,8}", fullmatch=True)
        domain = st.from_regex(r"[a-z]{2,6}", fullmatch=True)
        tld = st.sampled_from(["com", "nl", "org", "net"])
        return st.builds(lambda l, d, t: f"{l}@{d}.{t}", local, domain, tld)
    elif field_type == "number":
        return st.integers(min_value=1, max_value=1000)
    elif field_type == "select":
        # For select, the value must be a non-empty string
        return st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L",)))
    elif field_type == "date":
        # Generate dates in YYYY-MM-DD format
        year = st.integers(min_value=2020, max_value=2030)
        month = st.integers(min_value=1, max_value=12)
        day = st.integers(min_value=1, max_value=28)
        return st.builds(lambda y, m, d: f"{y:04d}-{m:02d}-{d:02d}", year, month, day)
    else:
        return st.text(min_size=1, max_size=20)


def empty_value_for_type(field_type):
    """Generate an empty/missing value for a given field type."""
    if field_type == "text":
        return st.sampled_from([None, "", "   ", "  \t  "])
    elif field_type == "email":
        return st.sampled_from([None, "", "   "])
    elif field_type == "number":
        return st.just(None)
    elif field_type == "select":
        return st.sampled_from([None, "", "   "])
    elif field_type == "date":
        return st.sampled_from([None, "", "   "])
    else:
        return st.sampled_from([None, ""])


# =============================================================================
# Property 13: Required item fields validation
# =============================================================================

class TestProperty13RequiredItemFieldsValidation:
    """
    Property 13: Required item fields validation.

    For any product with order_item_fields containing required fields,
    and any item_fields_data submission:
    - If all required fields have non-empty values → validation SHALL pass
    - If any required field has empty/missing value → SHALL return errors
      with correct item_index, field_id, and descriptive message
    """

    @given(
        field_type=st.sampled_from(FIELD_TYPES),
        quantity=st.integers(min_value=1, max_value=5),
        data=st.data(),
    )
    @settings(max_examples=200)
    def test_all_required_fields_filled_passes_validation(self, field_type, quantity, data):
        """
        When all required fields have non-empty values for all item units,
        validation SHALL pass (return empty error list).

        **Validates: Requirements 6.3, 6.4**
        """
        # Generate a required field definition
        field_id = data.draw(field_id_strategy())
        field_def = {
            "id": field_id,
            "label": "Test Field",
            "type": field_type,
            "required": True,
        }

        # For select fields, define options that include the generated values
        if field_type == "select":
            options = data.draw(st.lists(
                st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=("L",))),
                min_size=2,
                max_size=5,
                unique=True,
            ))
            field_def["options"] = options
            # Generate values from available options
            item_fields_data = [
                {"field_values": {field_id: data.draw(st.sampled_from(options))}}
                for _ in range(quantity)
            ]
        else:
            # Generate non-empty values for each item unit
            item_fields_data = [
                {"field_values": {field_id: data.draw(non_empty_value_for_type(field_type))}}
                for _ in range(quantity)
            ]

        order_item_fields = [field_def]

        errors = validate_item_fields(order_item_fields, item_fields_data, quantity)

        # All required fields filled → no errors
        assert errors == [], (
            f"Expected no errors when all required fields are filled, "
            f"but got: {errors}"
        )

    @given(
        field_type=st.sampled_from(FIELD_TYPES),
        quantity=st.integers(min_value=1, max_value=5),
        target_item_index=st.data(),
        data=st.data(),
    )
    @settings(max_examples=200)
    def test_missing_required_field_returns_error_with_correct_identifiers(
        self, field_type, quantity, target_item_index, data
    ):
        """
        When any required field has an empty or missing value for any item unit,
        the validator SHALL return an error identifying the item_index, field_id,
        and a descriptive message.

        **Validates: Requirements 6.3, 6.4**
        """
        # Pick which item index will have the empty value
        bad_index = data.draw(st.integers(min_value=0, max_value=quantity - 1))

        # Generate a required field definition
        field_id = data.draw(field_id_strategy())
        field_def = {
            "id": field_id,
            "label": "Test Field",
            "type": field_type,
            "required": True,
        }

        # Build item_fields_data with one item having an empty value
        item_fields_data = []
        for i in range(quantity):
            if i == bad_index:
                # Use an empty/missing value for the target item
                empty_val = data.draw(empty_value_for_type(field_type))
                item_fields_data.append({"field_values": {field_id: empty_val}})
            else:
                # Use a valid non-empty value
                if field_type == "select":
                    # For select, we need to provide a value (not in options is OK
                    # for this test since we're testing required-ness, not options validation)
                    valid_val = "ValidOption"
                    field_def["options"] = ["ValidOption", "AnotherOption"]
                    item_fields_data.append({"field_values": {field_id: valid_val}})
                else:
                    valid_val = data.draw(non_empty_value_for_type(field_type))
                    item_fields_data.append({"field_values": {field_id: valid_val}})

        # If select type, ensure options are set
        if field_type == "select" and "options" not in field_def:
            field_def["options"] = ["ValidOption", "AnotherOption"]

        order_item_fields = [field_def]

        errors = validate_item_fields(order_item_fields, item_fields_data, quantity)

        # SHALL return at least one error
        assert len(errors) > 0, (
            f"Expected validation errors when required field is empty/missing "
            f"at item_index={bad_index}, but got no errors. "
            f"field_type={field_type}, value={item_fields_data[bad_index]}"
        )

        # Find the error for our specific bad item
        matching_errors = [
            e for e in errors
            if e["item_index"] == bad_index and e["field_id"] == field_id
        ]
        assert len(matching_errors) >= 1, (
            f"Expected error with item_index={bad_index} and field_id={field_id}, "
            f"but errors were: {errors}"
        )

        # Each error SHALL have a descriptive message
        for error in matching_errors:
            assert "message" in error, f"Error missing 'message' key: {error}"
            assert isinstance(error["message"], str), (
                f"Error message should be a string, got: {type(error['message'])}"
            )
            assert len(error["message"]) > 0, (
                f"Error message should be non-empty: {error}"
            )

    @given(
        num_fields=st.integers(min_value=1, max_value=4),
        quantity=st.integers(min_value=1, max_value=3),
        data=st.data(),
    )
    @settings(max_examples=200)
    def test_multiple_required_fields_all_filled_passes(self, num_fields, quantity, data):
        """
        When multiple required fields are defined and all have non-empty values
        across all item units, validation SHALL pass.

        **Validates: Requirements 6.3, 6.4**
        """
        # Generate unique field definitions
        field_types_drawn = data.draw(
            st.lists(st.sampled_from(["text", "number", "date"]),
                     min_size=num_fields, max_size=num_fields)
        )
        field_ids = [f"field_{i}" for i in range(num_fields)]

        order_item_fields = [
            {"id": fid, "label": f"Field {i}", "type": ftype, "required": True}
            for i, (fid, ftype) in enumerate(zip(field_ids, field_types_drawn))
        ]

        # Generate valid data for all fields in all items
        item_fields_data = []
        for _ in range(quantity):
            field_values = {}
            for fid, ftype in zip(field_ids, field_types_drawn):
                field_values[fid] = data.draw(non_empty_value_for_type(ftype))
            item_fields_data.append({"field_values": field_values})

        errors = validate_item_fields(order_item_fields, item_fields_data, quantity)
        assert errors == [], (
            f"Expected no errors with all required fields filled, but got: {errors}"
        )

    @given(
        quantity=st.integers(min_value=1, max_value=3),
        data=st.data(),
    )
    @settings(max_examples=200)
    def test_missing_field_key_treated_as_empty(self, quantity, data):
        """
        When a required field's key is entirely absent from field_values
        (not just empty but missing), the validator SHALL treat it as empty
        and return an error with the correct item_index and field_id.

        **Validates: Requirements 6.3, 6.4**
        """
        field_id = data.draw(field_id_strategy())
        field_def = {
            "id": field_id,
            "label": "Required Field",
            "type": "text",
            "required": True,
        }

        # Pick which item will be missing the field
        bad_index = data.draw(st.integers(min_value=0, max_value=quantity - 1))

        item_fields_data = []
        for i in range(quantity):
            if i == bad_index:
                # Field key entirely absent
                item_fields_data.append({"field_values": {}})
            else:
                valid_val = data.draw(non_empty_value_for_type("text"))
                item_fields_data.append({"field_values": {field_id: valid_val}})

        order_item_fields = [field_def]

        errors = validate_item_fields(order_item_fields, item_fields_data, quantity)

        # SHALL return error for the missing field
        assert len(errors) > 0, (
            f"Expected error when required field key is absent at item_index={bad_index}"
        )

        matching = [e for e in errors if e["item_index"] == bad_index and e["field_id"] == field_id]
        assert len(matching) >= 1, (
            f"Expected error with item_index={bad_index}, field_id={field_id}, got: {errors}"
        )
        assert matching[0]["message"], "Error should have a non-empty message"
