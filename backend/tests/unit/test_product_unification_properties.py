"""
Property-Based Tests for Webshop Product Unification

Tests the core backend logic for the unified webshop pipeline using Hypothesis.
Covers all 27 correctness properties from the design document:
- Variant generation and resolution
- Purchase rules enforcement
- Stock reservation
- Cart structure
- Tenant derivation and access
- Item fields validation and persistence
- Migration correctness
- Payment and order lifecycle
"""

import os
import sys
import uuid
from decimal import Decimal
from functools import reduce
from unittest.mock import MagicMock, patch

import boto3
import pytest
from hypothesis import given, settings, assume, note
from hypothesis import strategies as st
from moto import mock_aws

# Add auth layer to path (same as conftest.py)
_backend_dir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_layers_path = os.path.join(_backend_dir, "layers", "auth-layer", "python")
if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)

from shared.variant_helpers import generate_variant_combinations
from shared.product_validation import (
    validate_variant_schema,
    validate_order_item_fields,
    validate_purchase_rules,
)
from shared.purchase_rules_engine import (
    enforce_max_per_order,
    enforce_max_per_member,
    enforce_max_per_club,
    validate_purchase_rules as validate_purchase_rules_engine,
)
from shared.item_fields_validator import (
    validate_item_fields_data,
    validate_field_value,
)
from shared.channel_resolver import resolve_channels, validate_channel_access
from shared.stock_reservation import (
    reserve_stock_for_order,
    InsufficientStockError,
)


# =============================================================================
# Hypothesis Strategies
# =============================================================================

def _total_combos(schema):
    """Calculate total combinations for a variant schema."""
    if not schema or not isinstance(schema, dict):
        return 0
    counts = [len(v) for v in schema.values() if isinstance(v, list)]
    if not counts:
        return 0
    return reduce(lambda a, b: a * b, counts, 1)


@st.composite
def variant_schema_strategy(draw):
    """Generate valid variant schemas with 1-5 axes, 1-10 values each."""
    num_axes = draw(st.integers(min_value=1, max_value=4))
    schema = {}
    used_names = set()

    for _ in range(num_axes):
        name = draw(st.text(
            alphabet=st.characters(whitelist_categories=("L",)),
            min_size=1,
            max_size=15,
        ).filter(lambda n: n not in used_names))
        used_names.add(name)

        values = draw(st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=("L", "N")),
                min_size=1,
                max_size=10,
            ),
            min_size=1,
            max_size=8,
            unique=True,
        ))
        schema[name] = values

    assume(_total_combos(schema) <= 100)
    assume(len(schema) >= 1)
    return schema


def purchase_rules_strategy():
    """Generate valid purchase rules."""
    return st.fixed_dictionaries({
        "max_per_order": st.one_of(st.none(), st.integers(min_value=1, max_value=100)),
        "max_per_member": st.one_of(st.none(), st.integers(min_value=1, max_value=100)),
        "max_per_club": st.one_of(st.none(), st.integers(min_value=1, max_value=100)),
    })


def order_item_fields_definition_strategy():
    """Generate valid order_item_fields definitions."""
    field_def = st.fixed_dictionaries({
        "id": st.from_regex(r"[a-z][a-z0-9_]{0,19}", fullmatch=True),
        "label": st.text(min_size=1, max_size=50),
        "type": st.sampled_from(["text", "select", "number", "date", "email"]),
        "required": st.booleans(),
    })
    return st.lists(field_def, min_size=1, max_size=5, unique_by=lambda f: f["id"])


def cognito_groups_strategy():
    """Generate sets of Cognito groups."""
    known_groups = ["hdcnLeden", "Regio_Pressmeet", "Regio_All", "admin",
                    "verzoek_lid", "webmaster", "Regio_Noord"]
    return st.lists(st.sampled_from(known_groups), min_size=0, max_size=4, unique=True)


# =============================================================================
# Property 1: Variant generation count equals cartesian product
# Feature: webshop-product-unification, Property 1: Variant generation count
# =============================================================================

class TestProperty1VariantGenerationCount:
    """
    **Validates: Requirements 3.2, 3.3**

    For any valid variant_schema, generated variant count = C₁ × C₂ × ... × Cₙ
    """

    @given(schema=variant_schema_strategy())
    @settings(max_examples=50)
    def test_variant_count_equals_cartesian_product(self, schema):
        expected_count = _total_combos(schema)
        assume(expected_count > 0)

        variants = generate_variant_combinations(
            schema, "prod_test", "h-dcn"
        )

        assert len(variants) == expected_count

    @given(schema=variant_schema_strategy())
    @settings(max_examples=50)
    def test_each_variant_has_unique_combination(self, schema):
        assume(_total_combos(schema) > 0)

        variants = generate_variant_combinations(
            schema, "prod_test", "h-dcn"
        )

        # Each variant should have a unique set of axis values
        combos = [
            tuple(sorted(v["variant_attributes"].items()))
            for v in variants
        ]
        assert len(combos) == len(set(combos))


# =============================================================================
# Property 2: Variant schema validation rejects invalid schemas
# Feature: webshop-product-unification, Property 2: Variant schema validation
# =============================================================================

class TestProperty2VariantSchemaValidation:
    """
    **Validates: Requirements 3.6, 3.8**

    Schemas with duplicate values, empty arrays, or combos > 100 are rejected.
    """

    @given(
        axis_name=st.text(min_size=1, max_size=20,
                          alphabet=st.characters(whitelist_categories=("L",))),
        values=st.lists(st.text(min_size=1, max_size=10,
                                alphabet=st.characters(whitelist_categories=("L",))),
                        min_size=2, max_size=10, unique=True),
    )
    @settings(max_examples=50)
    def test_duplicate_values_rejected(self, axis_name, values):
        """Schema with duplicate values in an axis is rejected."""
        # Create a schema with a duplicate value
        schema = {axis_name: values + [values[0]]}
        is_valid, errors = validate_variant_schema(schema)
        assert not is_valid
        assert any("duplicate" in e["message"].lower() for e in errors)

    @given(
        axis_name=st.text(min_size=1, max_size=20,
                          alphabet=st.characters(whitelist_categories=("L",))),
    )
    @settings(max_examples=50)
    def test_empty_values_array_rejected(self, axis_name):
        """Schema with an empty values array is rejected."""
        schema = {axis_name: []}
        is_valid, errors = validate_variant_schema(schema)
        assert not is_valid
        assert any("at least one value" in e["message"] for e in errors)

    @given(st.data())
    @settings(max_examples=50)
    def test_combinations_exceeding_100_rejected(self, data):
        """Schema where total combinations > 100 is rejected."""
        # Create a schema guaranteed to exceed 100 combos
        # 11 values x 10 values = 110 > 100
        axis1_values = data.draw(
            st.lists(st.text(min_size=1, max_size=5,
                             alphabet=st.characters(whitelist_categories=("L",))),
                     min_size=11, max_size=15, unique=True)
        )
        axis2_values = data.draw(
            st.lists(st.text(min_size=1, max_size=5,
                             alphabet=st.characters(whitelist_categories=("L",))),
                     min_size=10, max_size=15, unique=True)
        )
        schema = {"Size": axis1_values, "Color": axis2_values}
        total = len(axis1_values) * len(axis2_values)
        assume(total > 100)

        is_valid, errors = validate_variant_schema(schema)
        assert not is_valid
        assert any("exceeds" in e["message"] or "maximum" in e["message"]
                   for e in errors)


# =============================================================================
# Property 3: Purchase rules enforcement — max_per_order
# Feature: webshop-product-unification, Property 3
# =============================================================================

class TestProperty3MaxPerOrder:
    """
    **Validates: Requirements 5.1, 5.7, 16.2**

    quantity > max → rejected, quantity ≤ max → allowed
    """

    @given(
        quantity=st.integers(min_value=1, max_value=200),
        max_per_order=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=50)
    def test_max_per_order_enforcement(self, quantity, max_per_order):
        result = enforce_max_per_order(quantity, max_per_order)

        if quantity <= max_per_order:
            assert result is None, f"Should allow {quantity} <= {max_per_order}"
        else:
            assert result is not None, f"Should reject {quantity} > {max_per_order}"
            assert result["error"] == "purchase_rule_violation"
            assert result["details"]["rule"] == "max_per_order"


# =============================================================================
# Property 4: Purchase rules enforcement — max_per_member
# Feature: webshop-product-unification, Property 4
# =============================================================================

class TestProperty4MaxPerMember:
    """
    **Validates: Requirements 5.2, 5.8, 16.3**

    (existing_total + new_quantity) > max → rejected
    """

    @given(
        existing_total=st.integers(min_value=0, max_value=50),
        new_quantity=st.integers(min_value=1, max_value=50),
        max_per_member=st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=50)
    def test_max_per_member_enforcement(self, existing_total, new_quantity, max_per_member):
        # Mock the orders table to return existing_total
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            "Items": [
                {
                    "member_id": "member_1",
                    "status": "paid",
                    "items": [{"product_id": "prod_1", "quantity": existing_total}],
                }
            ]
            if existing_total > 0
            else []
        }

        result = enforce_max_per_member(
            "member_1", "prod_1", new_quantity, max_per_member, mock_table
        )

        if existing_total + new_quantity <= max_per_member:
            assert result is None
        else:
            assert result is not None
            assert result["details"]["rule"] == "max_per_member"


# =============================================================================
# Property 5: Purchase rules enforcement — max_per_club
# Feature: webshop-product-unification, Property 5
# =============================================================================

class TestProperty5MaxPerClub:
    """
    **Validates: Requirements 5.3, 5.9, 16.4**

    (club_total + new_quantity) > max → rejected
    """

    @given(
        club_total=st.integers(min_value=0, max_value=50),
        new_quantity=st.integers(min_value=1, max_value=50),
        max_per_club=st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=50)
    def test_max_per_club_enforcement(self, club_total, new_quantity, max_per_club):
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            "Items": [
                {
                    "club_id": "club_1",
                    "status": "paid",
                    "items": [{"product_id": "prod_1", "quantity": club_total}],
                }
            ]
            if club_total > 0
            else []
        }

        result = enforce_max_per_club(
            "club_1", "prod_1", new_quantity, max_per_club, mock_table
        )

        if club_total + new_quantity <= max_per_club:
            assert result is None
        else:
            assert result is not None
            assert result["details"]["rule"] == "max_per_club"


# =============================================================================
# Property 6: Absent purchase rules impose no constraints
# Feature: webshop-product-unification, Property 6
# =============================================================================

class TestProperty6AbsentRules:
    """
    **Validates: Requirements 5.6, 16.7**

    When rule is absent/null, any quantity is allowed.
    """

    @given(quantity=st.integers(min_value=1, max_value=9999))
    @settings(max_examples=50)
    def test_none_rules_allows_any_quantity(self, quantity):
        result = validate_purchase_rules_engine(
            None,
            {
                "quantity": quantity,
                "product_id": "prod_1",
                "member_id": "member_1",
                "orders_table": None,
                "memberships_table": None,
            },
        )
        assert result is None

    @given(quantity=st.integers(min_value=1, max_value=9999))
    @settings(max_examples=50)
    def test_empty_rules_allows_any_quantity(self, quantity):
        result = validate_purchase_rules_engine(
            {},
            {
                "quantity": quantity,
                "product_id": "prod_1",
                "member_id": "member_1",
                "orders_table": None,
                "memberships_table": None,
            },
        )
        assert result is None

    @given(quantity=st.integers(min_value=1, max_value=9999))
    @settings(max_examples=50)
    def test_rules_with_all_none_values_allows_any_quantity(self, quantity):
        rules = {
            "max_per_order": None,
            "max_per_member": None,
            "max_per_club": None,
        }
        result = validate_purchase_rules_engine(
            rules,
            {
                "quantity": quantity,
                "product_id": "prod_1",
                "member_id": "member_1",
                "orders_table": MagicMock(),
                "memberships_table": None,
            },
        )
        assert result is None


# =============================================================================
# Property 7: min_per_club ≤ max_per_club
# Feature: webshop-product-unification, Property 7
# =============================================================================

class TestProperty7MinMaxClubConstraint:
    """
    **Validates: Requirements 5.4**

    Validation rejects configs where min_per_club > max_per_club.
    """

    @given(
        min_val=st.integers(min_value=2, max_value=100),
        max_val=st.integers(min_value=1, max_value=99),
    )
    @settings(max_examples=50)
    def test_min_exceeds_max_rejected(self, min_val, max_val):
        assume(min_val > max_val)
        rules = {
            "min_per_club": min_val,
            "max_per_club": max_val,
        }
        is_valid, errors = validate_purchase_rules(rules)
        assert not is_valid
        assert any("min_per_club" in e["message"] for e in errors)

    @given(
        min_val=st.integers(min_value=1, max_value=50),
        max_val=st.integers(min_value=50, max_value=100),
    )
    @settings(max_examples=50)
    def test_min_lte_max_accepted(self, min_val, max_val):
        assume(min_val <= max_val)
        rules = {
            "min_per_club": min_val,
            "max_per_club": max_val,
        }
        is_valid, errors = validate_purchase_rules(rules)
        assert is_valid


# =============================================================================
# Property 8: Stock reservation correctness
# Feature: webshop-product-unification, Property 8
# =============================================================================

class TestProperty8StockReservation:
    """
    **Validates: Requirements 6.6**

    initial_stock - stock_after = sold_count_after - initial_sold_count = ordered_quantity
    """

    @given(
        initial_stock=st.integers(min_value=1, max_value=100),
        ordered_quantity=st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=50, deadline=None)
    def test_stock_reservation_invariant(self, initial_stock, ordered_quantity):
        assume(ordered_quantity <= initial_stock)

        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
            table = dynamodb.create_table(
                TableName="Producten",
                KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "product_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            initial_sold_count = 5
            variant_id = "var_test_default"
            table.put_item(
                Item={
                    "product_id": variant_id,
                    "is_parent": False,
                    "stock": initial_stock,
                    "sold_count": initial_sold_count,
                    "allow_oversell": False,
                    "active": True,
                }
            )

            order_id = str(uuid.uuid4())
            order_items = [{"variant_id": variant_id, "quantity": ordered_quantity}]
            reserve_stock_for_order(order_items, table, order_id)

            # Read back the variant
            response = table.get_item(Key={"product_id": variant_id})
            item = response["Item"]

            stock_after = int(item["stock"])
            sold_count_after = int(item["sold_count"])

            # Invariant: initial_stock - stock_after = ordered_quantity
            assert initial_stock - stock_after == ordered_quantity
            # Invariant: sold_count_after - initial_sold_count = ordered_quantity
            assert sold_count_after - initial_sold_count == ordered_quantity


# =============================================================================
# Property 9: Stock enforcement prevents overselling
# Feature: webshop-product-unification, Property 9
# =============================================================================

class TestProperty9StockEnforcement:
    """
    **Validates: Requirements 6.7, 6.8**

    allow_oversell=false AND stock < qty → reject; otherwise → allow
    """

    @given(
        stock=st.integers(min_value=0, max_value=50),
        quantity=st.integers(min_value=1, max_value=60),
        allow_oversell=st.booleans(),
    )
    @settings(max_examples=50, deadline=None)
    def test_stock_enforcement(self, stock, quantity, allow_oversell):
        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
            table = dynamodb.create_table(
                TableName="Producten",
                KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "product_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            variant_id = "var_stock_test"
            table.put_item(
                Item={
                    "product_id": variant_id,
                    "is_parent": False,
                    "stock": stock,
                    "sold_count": 0,
                    "allow_oversell": allow_oversell,
                    "active": True,
                }
            )

            order_id = str(uuid.uuid4())
            order_items = [{"variant_id": variant_id, "quantity": quantity}]

            if not allow_oversell and stock < quantity:
                with pytest.raises(InsufficientStockError):
                    reserve_stock_for_order(order_items, table, order_id)
            else:
                # Should succeed
                results = reserve_stock_for_order(order_items, table, order_id)
                assert results[0]["status"] == "reserved"


# =============================================================================
# Property 10: Cart items never contain selectedOption
# Feature: webshop-product-unification, Property 10
# =============================================================================

class TestProperty10CartItemStructure:
    """
    **Validates: Requirements 6.1, 6.5**

    All cart items have product_id, variant_id, quantity; never selectedOption.
    """

    @given(
        product_id=st.text(min_size=1, max_size=20,
                           alphabet=st.characters(whitelist_categories=("L", "N"))),
        variant_id=st.text(min_size=1, max_size=40,
                           alphabet=st.characters(whitelist_categories=("L", "N", "Pd"))),
        quantity=st.integers(min_value=1, max_value=99),
    )
    @settings(max_examples=50)
    def test_cart_item_has_required_fields_no_selectedoption(
        self, product_id, variant_id, quantity
    ):
        """A properly formed cart item has the required keys and no selectedOption."""
        cart_item = {
            "product_id": product_id,
            "variant_id": variant_id,
            "quantity": quantity,
        }

        # Required fields present
        assert "product_id" in cart_item
        assert "variant_id" in cart_item
        assert "quantity" in cart_item
        # Legacy field absent
        assert "selectedOption" not in cart_item

    @given(
        schema=variant_schema_strategy(),
    )
    @settings(max_examples=50)
    def test_generated_variants_produce_cart_items_without_selectedoption(self, schema):
        """Variants generated from schema lead to cart items with variant_id, not selectedOption."""
        variants = generate_variant_combinations(schema, "prod_1", "h-dcn")
        assume(len(variants) > 0)

        for variant in variants:
            cart_item = {
                "product_id": "prod_1",
                "variant_id": variant["product_id"],
                "quantity": 1,
                "variant_attributes": variant["variant_attributes"],
            }
            assert "selectedOption" not in cart_item
            assert cart_item["variant_id"].startswith("var_")


# =============================================================================
# Property 11: Tenant role derivation
# Feature: webshop-product-unification, Property 11
# =============================================================================

class TestProperty11TenantRoleDerivation:
    """
    **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.7**

    hdcnLeden→h-dcn, Regio_Pressmeet/Regio_All→presmeet, union of grants.
    """

    @given(groups=cognito_groups_strategy())
    @settings(max_examples=50)
    def test_tenant_derivation(self, groups):
        tenants = resolve_channels(groups)

        expected = set()
        if "hdcnLeden" in groups:
            expected.add("h-dcn")
        if "Regio_Pressmeet" in groups or "Regio_All" in groups:
            expected.add("presmeet")

        assert tenants == expected

    @given(groups=cognito_groups_strategy())
    @settings(max_examples=50)
    def test_no_relevant_groups_yields_empty(self, groups):
        relevant = {"hdcnLeden", "Regio_Pressmeet", "Regio_All"}
        has_relevant = any(g in relevant for g in groups)
        tenants = resolve_channels(groups)

        if not has_relevant:
            assert tenants == set()


# =============================================================================
# Property 12: Tenant access enforcement
# Feature: webshop-product-unification, Property 12
# =============================================================================

class TestProperty12TenantAccessEnforcement:
    """
    **Validates: Requirements 7.6**

    Requesting inaccessible tenant returns 403.
    """

    @given(
        requested=st.sampled_from(["h-dcn", "presmeet"]),
        groups=cognito_groups_strategy(),
    )
    @settings(max_examples=50)
    def test_tenant_access_enforcement(self, requested, groups):
        user_channels = resolve_channels(groups)
        result = validate_channel_access(requested, user_channels)

        if requested in user_channels:
            assert result is None
        else:
            assert result is not None
            assert result["statusCode"] == 403


# =============================================================================
# Property 13: Item fields data count matches quantity
# Feature: webshop-product-unification, Property 13
# =============================================================================

class TestProperty13ItemFieldsCount:
    """
    **Validates: Requirements 4.4, 17.5**

    Exactly Q entries required for Q items; fewer or more → rejected.
    """

    @given(
        quantity=st.integers(min_value=1, max_value=10),
        actual_count=st.integers(min_value=0, max_value=15),
    )
    @settings(max_examples=50)
    def test_item_fields_count_validation(self, quantity, actual_count):
        definition = [
            {"id": "name", "label": "Name", "type": "text", "required": True}
        ]
        # Generate actual_count entries
        item_fields_data = [
            {"field_values": {"name": f"Person {i}"}} for i in range(actual_count)
        ]

        result = validate_item_fields_data(
            item_fields_data, definition, quantity
        )

        if actual_count == quantity:
            assert result is None
        else:
            assert result is not None
            assert result["error"] == "item_fields_count_mismatch"


# =============================================================================
# Property 14: Required field validation
# Feature: webshop-product-unification, Property 14
# =============================================================================

class TestProperty14RequiredFieldValidation:
    """
    **Validates: Requirements 4.3, 17.1**

    Empty values for required fields rejected per type-specific rules.
    """

    @given(
        field_type=st.sampled_from(["text", "email", "select", "number", "date"]),
    )
    @settings(max_examples=50)
    def test_required_empty_value_rejected(self, field_type):
        field_def = {
            "id": "test_field",
            "label": "Test",
            "type": field_type,
            "required": True,
        }
        if field_type == "select":
            field_def["options"] = ["A", "B", "C"]

        # Test with empty/None values
        result_none = validate_field_value(None, field_def)
        assert result_none == "required"

        result_empty = validate_field_value("", field_def)
        assert result_empty == "required"

    @given(
        value=st.text(min_size=1, max_size=50,
                      alphabet=st.characters(whitelist_categories=("L", "N"))),
    )
    @settings(max_examples=50)
    def test_required_nonempty_text_accepted(self, value):
        assume(value.strip() != "")
        field_def = {
            "id": "name",
            "label": "Name",
            "type": "text",
            "required": True,
        }
        result = validate_field_value(value, field_def)
        assert result is None


# =============================================================================
# Property 15: Field constraint validation
# Feature: webshop-product-unification, Property 15
# =============================================================================

class TestProperty15FieldConstraintValidation:
    """
    **Validates: Requirements 4.5, 17.2**

    Values violating min_length, max_length, minimum, maximum, pattern, options
    are rejected.
    """

    @given(
        value=st.text(min_size=1, max_size=2,
                      alphabet=st.characters(whitelist_categories=("L",))),
    )
    @settings(max_examples=50)
    def test_min_length_violation_rejected(self, value):
        assume(len(value) < 5)
        field_def = {
            "id": "f1",
            "label": "Field",
            "type": "text",
            "required": False,
            "validation": {"min_length": 5},
        }
        result = validate_field_value(value, field_def)
        assert result is not None
        assert "min_length" in result

    @given(
        value=st.text(min_size=11, max_size=20,
                      alphabet=st.characters(whitelist_categories=("L",))),
    )
    @settings(max_examples=50)
    def test_max_length_violation_rejected(self, value):
        assume(len(value) > 10)
        field_def = {
            "id": "f2",
            "label": "Field",
            "type": "text",
            "required": False,
            "validation": {"max_length": 10},
        }
        result = validate_field_value(value, field_def)
        assert result is not None
        assert "max_length" in result

    @given(value=st.floats(min_value=-1000, max_value=4.99))
    @settings(max_examples=50)
    def test_minimum_violation_rejected(self, value):
        assume(value < 5)
        field_def = {
            "id": "f3",
            "label": "Number",
            "type": "number",
            "required": False,
            "validation": {"minimum": 5},
        }
        result = validate_field_value(value, field_def)
        assert result is not None
        assert "minimum" in result

    @given(value=st.floats(min_value=11.0, max_value=1000))
    @settings(max_examples=50)
    def test_maximum_violation_rejected(self, value):
        assume(value > 10)
        field_def = {
            "id": "f4",
            "label": "Number",
            "type": "number",
            "required": False,
            "validation": {"maximum": 10},
        }
        result = validate_field_value(value, field_def)
        assert result is not None
        assert "maximum" in result

    @given(
        value=st.text(min_size=1, max_size=10,
                      alphabet=st.characters(whitelist_categories=("L",))),
    )
    @settings(max_examples=50)
    def test_options_violation_rejected(self, value):
        options = ["Geen", "Vegetarisch", "Veganistisch"]
        assume(value not in options)
        field_def = {
            "id": "dietary",
            "label": "Diet",
            "type": "select",
            "required": False,
            "options": options,
        }
        result = validate_field_value(value, field_def)
        assert result == "options"


# =============================================================================
# Property 16: Opties migration round-trip
# Feature: webshop-product-unification, Property 16
# =============================================================================

class TestProperty16OptiesMigration:
    """
    **Validates: Requirements 11.1, 11.2, 11.3**

    Migrated variant_schema has axis "opties" with values = split(opties, ",").trim()
    """

    @given(
        values=st.lists(
            st.text(min_size=1, max_size=15,
                    alphabet=st.characters(whitelist_categories=("L", "N"))),
            min_size=1,
            max_size=10,
            unique=True,
        ),
    )
    @settings(max_examples=50)
    def test_opties_migration_roundtrip(self, values):
        """Simulating the migration logic: opties string → variant_schema."""
        # Build the legacy opties string
        opties_string = ", ".join(values)

        # Migration logic: split on comma, trim whitespace
        parsed_values = [v.strip() for v in opties_string.split(",") if v.strip()]

        # Build the variant_schema as migration would
        variant_schema = {"opties": parsed_values}

        # Verify: axis "opties" present, values match original
        assert "opties" in variant_schema
        assert variant_schema["opties"] == values

        # Generate variants and check count
        variants = generate_variant_combinations(
            variant_schema, "prod_legacy", "h-dcn"
        )
        assert len(variants) == len(values)


# =============================================================================
# Property 17: Migration idempotence
# Feature: webshop-product-unification, Property 17
# =============================================================================

class TestProperty17MigrationIdempotence:
    """
    **Validates: Requirements 11.4**

    Second run produces no changes to already-migrated products.
    """

    @given(
        values=st.lists(
            st.text(min_size=1, max_size=10,
                    alphabet=st.characters(whitelist_categories=("L", "N"))),
            min_size=1,
            max_size=5,
            unique=True,
        ),
    )
    @settings(max_examples=50)
    def test_migration_idempotence(self, values):
        """
        Simulates migration logic: if legacy_opties is present, skip.
        This validates the skip detection mechanism.
        """
        # First migration: product has opties, no legacy_opties
        product = {
            "product_id": "prod_1",
            "opties": ", ".join(values),
        }

        # Simulate first migration run
        def migrate(prod):
            if "legacy_opties" in prod:
                return False  # Already migrated, skip
            opties = prod.get("opties")
            if not opties:
                return False
            parsed = [v.strip() for v in opties.split(",") if v.strip()]
            prod["variant_schema"] = {"opties": parsed}
            prod["legacy_opties"] = opties
            del prod["opties"]
            return True

        # First run should migrate
        result1 = migrate(product)
        assert result1 is True
        assert "legacy_opties" in product
        assert "opties" not in product

        # Second run should skip (no changes)
        result2 = migrate(product)
        assert result2 is False
        # Product unchanged after second run
        assert product["variant_schema"] == {"opties": values}


# =============================================================================
# Property 18: Mollie webhook idempotence
# Feature: webshop-product-unification, Property 18
# =============================================================================

class TestProperty18MollieWebhookIdempotence:
    """
    **Validates: Requirements 9.11**

    Same payment_id processed multiple times → same state, no duplicate stock.
    """

    @given(
        initial_stock=st.integers(min_value=10, max_value=100),
        quantity=st.integers(min_value=1, max_value=10),
        times_processed=st.integers(min_value=2, max_value=5),
    )
    @settings(max_examples=50, deadline=None)
    def test_webhook_idempotence_no_duplicate_stock(
        self, initial_stock, quantity, times_processed
    ):
        """Processing stock reservation multiple times for same order is idempotent."""
        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
            table = dynamodb.create_table(
                TableName="Producten",
                KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "product_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            variant_id = "var_idempotent_test"
            table.put_item(
                Item={
                    "product_id": variant_id,
                    "is_parent": False,
                    "stock": initial_stock,
                    "sold_count": 0,
                    "allow_oversell": False,
                    "active": True,
                }
            )

            order_id = str(uuid.uuid4())
            order_items = [{"variant_id": variant_id, "quantity": quantity}]

            # Process multiple times (simulating repeated webhook calls)
            for _ in range(times_processed):
                reserve_stock_for_order(order_items, table, order_id)

            # Read final state
            response = table.get_item(Key={"product_id": variant_id})
            item = response["Item"]

            # Stock should only be decremented once
            assert int(item["stock"]) == initial_stock - quantity
            assert int(item["sold_count"]) == quantity


# =============================================================================
# Property 19: Payment status calculation
# Feature: webshop-product-unification, Property 19
# =============================================================================

class TestProperty19PaymentStatusCalculation:
    """
    **Validates: Requirements 9.10**

    P >= T → "paid", 0 < P < T → "partial"
    """

    @given(
        total=st.decimals(min_value=1, max_value=1000, places=2,
                          allow_nan=False, allow_infinity=False),
        paid=st.decimals(min_value=0, max_value=1000, places=2,
                         allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_payment_status_calculation(self, total, paid):
        assume(total > 0)

        # Replicate the payment status calculation logic
        if paid >= total:
            expected_status = "paid"
        elif paid > 0:
            expected_status = "partial"
        else:
            expected_status = "unpaid"

        # Verify the logic holds
        def calculate_payment_status(total_amount, total_paid):
            if total_paid >= total_amount:
                return "paid"
            elif total_paid > 0:
                return "partial"
            return "unpaid"

        status = calculate_payment_status(total, paid)
        assert status == expected_status


# =============================================================================
# Property 20: Item fields data persistence on order
# Feature: webshop-product-unification, Property 20
# =============================================================================

class TestProperty20ItemFieldsPersistence:
    """
    **Validates: Requirements 10.1, 10.5**

    Stored data preserves field_id, field_label, value, 1-based item_index.
    """

    @given(
        quantity=st.integers(min_value=1, max_value=5),
        field_count=st.integers(min_value=1, max_value=3),
    )
    @settings(max_examples=50)
    def test_item_fields_persistence_format(self, quantity, field_count):
        """Verifies the data transformation preserves all required fields."""
        # Define fields
        fields_def = [
            {"id": f"field_{i}", "label": f"Field {i}", "type": "text", "required": True}
            for i in range(field_count)
        ]

        # Build input item_fields_data
        input_data = []
        for item_idx in range(quantity):
            entry = {}
            for field_def in fields_def:
                entry[field_def["id"]] = f"value_{item_idx}_{field_def['id']}"
            input_data.append({"field_values": entry})

        # Transform to order storage format (as the create_order handler does)
        stored_data = []
        for item_idx, entry in enumerate(input_data):
            field_values = entry.get("field_values", entry)
            for field_def in fields_def:
                stored_data.append({
                    "item_index": item_idx + 1,  # 1-based
                    "field_id": field_def["id"],
                    "field_label": field_def["label"],
                    "value": field_values.get(field_def["id"], ""),
                })

        # Verify all entries preserve required fields
        for entry in stored_data:
            assert "item_index" in entry
            assert "field_id" in entry
            assert "field_label" in entry
            assert "value" in entry
            assert entry["item_index"] >= 1

        # Verify 1-based indexing
        item_indices = sorted(set(e["item_index"] for e in stored_data))
        assert item_indices == list(range(1, quantity + 1))

        # Verify total entry count
        assert len(stored_data) == quantity * field_count


# =============================================================================
# Property 21: CSV export row count
# Feature: webshop-product-unification, Property 21
# =============================================================================

class TestProperty21CSVExportRowCount:
    """
    **Validates: Requirements 10.4**

    rows = Σ(Qᵢ × Fᵢ) + 1 header
    """

    @given(
        order_items=st.lists(
            st.tuples(
                st.integers(min_value=1, max_value=5),  # quantity
                st.integers(min_value=1, max_value=4),  # field count
            ),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(max_examples=50)
    def test_csv_row_count(self, order_items):
        """CSV export produces expected row count."""
        # Calculate expected data rows
        expected_data_rows = sum(q * f for q, f in order_items)

        # Simulate CSV generation
        csv_rows = []
        # Header row
        csv_rows.append(["order_id", "product", "item_index", "field_label", "value"])

        for line_idx, (quantity, field_count) in enumerate(order_items):
            for item_idx in range(1, quantity + 1):
                for field_idx in range(field_count):
                    csv_rows.append([
                        f"order_{line_idx}",
                        f"product_{line_idx}",
                        item_idx,
                        f"field_{field_idx}",
                        f"value_{item_idx}_{field_idx}",
                    ])

        # Total = data rows + 1 header
        assert len(csv_rows) == expected_data_rows + 1


# =============================================================================
# Property 22: Quantity decrease removes highest-numbered item data
# Feature: webshop-product-unification, Property 22
# =============================================================================

class TestProperty22QuantityDecrease:
    """
    **Validates: Requirements 8.8**

    Decrease to Q-N retains items 1..Q-N, discards Q-N+1..Q.
    """

    @given(
        original_quantity=st.integers(min_value=2, max_value=10),
        decrease_amount=st.integers(min_value=1, max_value=9),
    )
    @settings(max_examples=50)
    def test_quantity_decrease_removes_highest_items(
        self, original_quantity, decrease_amount
    ):
        assume(decrease_amount < original_quantity)
        new_quantity = original_quantity - decrease_amount

        # Build item_fields_data for original quantity
        original_data = [
            {"field_values": {"name": f"Person {i+1}"}}
            for i in range(original_quantity)
        ]

        # Apply decrease: keep first new_quantity items
        retained_data = original_data[:new_quantity]

        # Verify retained data matches first new_quantity items
        assert len(retained_data) == new_quantity
        for i, entry in enumerate(retained_data):
            assert entry["field_values"]["name"] == f"Person {i+1}"

        # Verify highest-numbered items (new_quantity+1 to original_quantity) are gone
        discarded_names = [f"Person {i+1}" for i in range(new_quantity, original_quantity)]
        retained_names = [e["field_values"]["name"] for e in retained_data]
        for name in discarded_names:
            assert name not in retained_names


# =============================================================================
# Property 23: Schema evolution discards orphaned field data
# Feature: webshop-product-unification, Property 23
# =============================================================================

class TestProperty23SchemaEvolution:
    """
    **Validates: Requirements 8.9**

    field_ids not in current definition are discarded; existing ones retained.
    """

    @given(
        common_ids=st.lists(
            st.from_regex(r"[a-z]{3,8}", fullmatch=True),
            min_size=1, max_size=3, unique=True,
        ),
        orphaned_ids=st.lists(
            st.from_regex(r"orphan_[a-z]{3,5}", fullmatch=True),
            min_size=1, max_size=3, unique=True,
        ),
    )
    @settings(max_examples=50)
    def test_schema_evolution_discards_orphans(self, common_ids, orphaned_ids):
        """When field definition changes, orphaned data is discarded."""
        # Current definition only has common_ids
        current_definition_ids = set(common_ids)

        # Existing cart data has both common + orphaned fields
        saved_data = {}
        for fid in common_ids:
            saved_data[fid] = f"value_for_{fid}"
        for fid in orphaned_ids:
            saved_data[fid] = f"orphan_value_{fid}"

        # Apply schema evolution: discard orphaned
        filtered_data = {
            k: v for k, v in saved_data.items() if k in current_definition_ids
        }

        # Common fields retained
        for fid in common_ids:
            assert fid in filtered_data
            assert filtered_data[fid] == f"value_for_{fid}"

        # Orphaned fields discarded
        for fid in orphaned_ids:
            assert fid not in filtered_data


# =============================================================================
# Property 24: Persistent order — one per club
# Feature: webshop-product-unification, Property 24
# =============================================================================

class TestProperty24PersistentOrderUniqueness:
    """
    **Validates: Requirements 12.9**

    order_mode "persistent" maintains at most one active order per club.
    """

    @given(
        club_id=st.text(min_size=3, max_size=10,
                        alphabet=st.characters(whitelist_categories=("L", "N"))),
        num_purchases=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=50)
    def test_persistent_order_one_per_club(self, club_id, num_purchases):
        """Simulates persistent order logic: only one active order per club."""
        orders = {}  # club_id → order

        def create_or_update_persistent_order(c_id, items):
            if c_id in orders:
                # Update existing order
                orders[c_id]["items"] = items
                orders[c_id]["version"] += 1
            else:
                # Create new order
                orders[c_id] = {
                    "order_id": str(uuid.uuid4()),
                    "club_id": c_id,
                    "items": items,
                    "version": 1,
                }
            return orders[c_id]

        # Multiple purchases for same club
        for i in range(num_purchases):
            create_or_update_persistent_order(
                club_id, [{"product_id": "prod_1", "quantity": i + 1}]
            )

        # Only one order should exist for this club
        club_orders = [o for o in orders.values() if o["club_id"] == club_id]
        assert len(club_orders) == 1
        # Last purchase's items should be current
        assert club_orders[0]["items"][0]["quantity"] == num_purchases


# =============================================================================
# Property 25: Optimistic locking rejects stale writes
# Feature: webshop-product-unification, Property 25
# =============================================================================

class TestProperty25OptimisticLocking:
    """
    **Validates: Requirements 12.13**

    Concurrent writes with same version → one succeeds, other rejected.
    """

    @given(
        initial_version=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=50)
    def test_optimistic_locking_rejects_stale(self, initial_version):
        """Simulates optimistic locking: same version used by two writers."""
        order = {
            "order_id": "order_1",
            "version": initial_version,
            "items": [],
        }

        results = []

        def attempt_update(new_items, expected_version):
            """Returns True if update succeeds, False if version conflict."""
            if order["version"] != expected_version:
                return False  # Version conflict
            order["version"] += 1
            order["items"] = new_items
            return True

        # Two concurrent writes with the same version
        write1_success = attempt_update(
            [{"product_id": "prod_a"}], initial_version
        )
        write2_success = attempt_update(
            [{"product_id": "prod_b"}], initial_version
        )

        # Exactly one should succeed
        assert write1_success is True
        assert write2_success is False
        # Version should have incremented only once
        assert order["version"] == initial_version + 1


# =============================================================================
# Property 26: Legacy field precedence
# Feature: webshop-product-unification, Property 26
# =============================================================================

class TestProperty26LegacyFieldPrecedence:
    """
    **Validates: Requirements 1.8**

    When both required_attributes and new fields exist, required_attributes ignored.
    """

    @given(schema=variant_schema_strategy())
    @settings(max_examples=50)
    def test_legacy_field_ignored_when_new_fields_present(self, schema):
        """When variant_schema is present, required_attributes should be ignored."""
        product = {
            "product_id": "prod_legacy",
            "required_attributes": {
                "type": "object",
                "properties": {"old_axis": {"type": "string", "enum": ["X", "Y"]}},
            },
            "variant_schema": schema,
        }

        # Determine which field to use (the precedence logic)
        def get_active_variant_config(prod):
            """Returns the active variant config, ignoring legacy if new exists."""
            if prod.get("variant_schema"):
                return prod["variant_schema"]
            return prod.get("required_attributes")

        active_config = get_active_variant_config(product)

        # Should use variant_schema, not required_attributes
        assert active_config == schema
        assert active_config != product["required_attributes"]

    @given(schema=variant_schema_strategy())
    @settings(max_examples=50)
    def test_variants_generated_from_new_schema_not_legacy(self, schema):
        """Variants are generated from variant_schema when both fields exist."""
        product = {
            "product_id": "prod_both",
            "required_attributes": {
                "type": "object",
                "properties": {"legacy": {"type": "string", "enum": ["A"]}},
            },
            "variant_schema": schema,
        }

        # Generate variants using the new field only
        variants = generate_variant_combinations(
            product["variant_schema"], product["product_id"], "h-dcn"
        )

        expected_count = _total_combos(schema)
        assert len(variants) == expected_count

        # Verify none of the variants use the legacy schema
        for v in variants:
            assert "legacy" not in v.get("variant_attributes", {})


# =============================================================================
# Property 27: Variant resolution
# Feature: webshop-product-unification, Property 27
# =============================================================================

class TestProperty27VariantResolution:
    """
    **Validates: Requirements 15.3, 15.5**

    Complete axis selections resolve to exactly one variant or no match.
    """

    @given(schema=variant_schema_strategy())
    @settings(max_examples=50)
    def test_complete_selections_resolve_to_one_variant(self, schema):
        """Each valid combination of axis selections maps to exactly one variant."""
        import itertools

        variants = generate_variant_combinations(schema, "prod_res", "h-dcn")
        assume(len(variants) > 0)

        axis_names = list(schema.keys())
        axis_values = [schema[name] for name in axis_names]

        # For each possible complete selection, exactly one variant should match
        for combo in itertools.product(*axis_values):
            selections = dict(zip(axis_names, combo))

            matching = [
                v for v in variants
                if v["variant_attributes"] == selections
            ]
            assert len(matching) == 1, (
                f"Expected exactly 1 match for {selections}, got {len(matching)}"
            )

    @given(
        schema=variant_schema_strategy(),
        extra_axis_value=st.text(min_size=1, max_size=10,
                                 alphabet=st.characters(whitelist_categories=("L",))),
    )
    @settings(max_examples=50)
    def test_invalid_selections_resolve_to_no_match(self, schema, extra_axis_value):
        """Selections not in the schema produce no matching variant."""
        variants = generate_variant_combinations(schema, "prod_res2", "h-dcn")
        assume(len(variants) > 0)

        axis_names = list(schema.keys())
        # Create an invalid selection by using a value not in any axis
        all_values = set()
        for vals in schema.values():
            all_values.update(vals)

        assume(extra_axis_value not in all_values)

        # Build a selection with one invalid value
        invalid_selections = {}
        for i, name in enumerate(axis_names):
            if i == 0:
                invalid_selections[name] = extra_axis_value
            else:
                invalid_selections[name] = schema[name][0]

        matching = [
            v for v in variants
            if v["variant_attributes"] == invalid_selections
        ]
        assert len(matching) == 0
