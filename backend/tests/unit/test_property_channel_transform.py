"""
Property-Based Test for Channel-to-Event_ID Transformation (Property 4)

**Validates: Requirements 1.16, 1.17, 10.12**

Property 4: Channel-to-event_id transformation is correct

For any product record with a `channel` field, the migration SHALL remove the
`channel` and `tenant` fields and set `event_id` to the linked event's `event_id`
when `channel` is "presmeet", or set `event_id` to `null` when `channel` is "h-dcn"
or absent. The `channel` field SHALL also be removed from all cart records.
"""

import os
import sys
import uuid

import boto3
import pytest
from hypothesis import given, settings, assume, note
from hypothesis import strategies as st
from moto import mock_aws

# Add scripts directory to path for importing migrate_products
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts")
)


# =============================================================================
# Hypothesis Strategies
# =============================================================================

def channel_strategy():
    """Generate channel values: 'h-dcn', 'presmeet', empty string, or absent (None)."""
    return st.sampled_from(["h-dcn", "presmeet", "", None])


def product_id_strategy():
    """Generate product IDs (UUID-like strings)."""
    return st.from_regex(r"prod_[a-z0-9]{4,12}", fullmatch=True)


@st.composite
def product_record_strategy(draw):
    """Generate a product record with various channel/tenant combinations."""
    product_id = draw(product_id_strategy())
    channel = draw(channel_strategy())
    has_tenant = draw(st.booleans())

    record = {
        "product_id": product_id,
        "name": f"Product {product_id}",
        "is_parent": True,
        "active": True,
    }

    if channel is not None:
        record["channel"] = channel
    if has_tenant:
        tenant_value = draw(st.sampled_from(["h-dcn", "presmeet", "default"]))
        record["tenant"] = tenant_value

    return record


@st.composite
def cart_record_strategy(draw):
    """Generate a cart record with optional channel field."""
    cart_id = draw(st.from_regex(r"cart_[a-z0-9]{4,8}", fullmatch=True))
    has_channel = draw(st.booleans())
    channel = draw(st.sampled_from(["h-dcn", "presmeet", "other"]))

    record = {"cart_id": cart_id, "items": []}
    if has_channel:
        record["channel"] = channel
    return record


@st.composite
def event_with_products_strategy(draw):
    """Generate an event record with a list of linked product_ids."""
    event_id = draw(st.from_regex(r"evt_[a-z0-9]{4,8}", fullmatch=True))
    num_products = draw(st.integers(min_value=1, max_value=5))
    product_ids = [
        draw(product_id_strategy()) for _ in range(num_products)
    ]
    return {
        "event_id": event_id,
        "name": f"Event {event_id}",
        "product_ids": product_ids,
    }


# =============================================================================
# Property 4: Channel-to-event_id transformation is correct
# =============================================================================

class TestProperty4ChannelToEventIdTransformation:
    """
    **Validates: Requirements 1.16, 1.17, 10.12**

    For any product record with a `channel` field, the migration SHALL:
    - Remove `channel` and `tenant` fields
    - Set `event_id` to the linked event's event_id when channel is "presmeet"
    - Set `event_id` to null when channel is "h-dcn" or absent
    - Remove `channel` from all cart records
    """

    @given(
        products=st.lists(product_record_strategy(), min_size=1, max_size=10, unique_by=lambda p: p["product_id"]),
        carts=st.lists(cart_record_strategy(), min_size=0, max_size=5, unique_by=lambda c: c["cart_id"]),
    )
    @settings(max_examples=100, deadline=None)
    def test_channel_removed_and_event_id_set(self, products, carts):
        """
        For any set of products with various channel values, after transformation:
        - All `channel` fields are removed from products
        - All `tenant` fields are removed from products
        - `event_id` is correctly assigned based on channel value
        - `channel` is removed from all cart records
        """
        if "migrate_products" in sys.modules:
            del sys.modules["migrate_products"]

        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")

            producten = dynamodb.create_table(
                TableName="Producten",
                KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "product_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            events_table = dynamodb.create_table(
                TableName="Events",
                KeySchema=[{"AttributeName": "event_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "event_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            carts_table = dynamodb.create_table(
                TableName="Carts",
                KeySchema=[{"AttributeName": "cart_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "cart_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            # Create an event that links to all presmeet products
            presmeet_product_ids = [
                p["product_id"] for p in products if p.get("channel") == "presmeet"
            ]
            event_id = "evt_test_event"
            if presmeet_product_ids:
                events_table.put_item(
                    Item={
                        "event_id": event_id,
                        "name": "Test Event",
                        "product_ids": presmeet_product_ids,
                    }
                )

            # Seed products
            for product in products:
                producten.put_item(Item=product)

            # Seed carts
            for cart in carts:
                carts_table.put_item(Item=cart)

            from migrate_products import transform_channels_to_event_ids

            result = transform_channels_to_event_ids(
                producten, events_table, dry_run=False, carts_table=carts_table
            )

            # Verify each product
            for product in products:
                pid = product["product_id"]
                item = producten.get_item(Key={"product_id": pid})["Item"]

                had_channel = "channel" in product
                had_tenant = "tenant" in product
                channel_value = product.get("channel", "")

                if had_channel or had_tenant:
                    # channel and tenant MUST be removed
                    assert "channel" not in item, (
                        f"Product {pid}: 'channel' field should be removed"
                    )
                    assert "tenant" not in item, (
                        f"Product {pid}: 'tenant' field should be removed"
                    )

                    # event_id MUST be correctly assigned
                    if channel_value == "presmeet":
                        assert item.get("event_id") == event_id, (
                            f"Product {pid}: channel='presmeet' should get event_id={event_id}"
                        )
                    else:
                        # h-dcn, empty, or absent channel → event_id = None
                        assert item.get("event_id") is None, (
                            f"Product {pid}: channel='{channel_value}' should get event_id=None"
                        )
                else:
                    # Products without channel/tenant should be untouched
                    assert "channel" not in item
                    assert "tenant" not in item

            # Verify carts: channel field must be removed from all carts that had it
            for cart in carts:
                cid = cart["cart_id"]
                cart_item = carts_table.get_item(Key={"cart_id": cid})["Item"]
                assert "channel" not in cart_item, (
                    f"Cart {cid}: 'channel' field should be removed"
                )

    @given(
        channel=st.sampled_from(["h-dcn", "", "unknown_value"]),
    )
    @settings(max_examples=100, deadline=None)
    def test_non_presmeet_channels_get_null_event_id(self, channel):
        """
        Products with channel != "presmeet" (including h-dcn, empty, unknown)
        always get event_id=None.
        """
        if "migrate_products" in sys.modules:
            del sys.modules["migrate_products"]

        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")

            producten = dynamodb.create_table(
                TableName="Producten",
                KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "product_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            events_table = dynamodb.create_table(
                TableName="Events",
                KeySchema=[{"AttributeName": "event_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "event_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            carts_table = dynamodb.create_table(
                TableName="Carts",
                KeySchema=[{"AttributeName": "cart_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "cart_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            product_id = f"prod_{uuid.uuid4().hex[:8]}"
            product = {
                "product_id": product_id,
                "name": "Test Product",
                "channel": channel,
                "tenant": "some_tenant",
                "is_parent": True,
            }
            producten.put_item(Item=product)

            from migrate_products import transform_channels_to_event_ids

            transform_channels_to_event_ids(
                producten, events_table, dry_run=False, carts_table=carts_table
            )

            item = producten.get_item(Key={"product_id": product_id})["Item"]
            assert item.get("event_id") is None
            assert "channel" not in item
            assert "tenant" not in item

    @given(
        num_products=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=100, deadline=None)
    def test_presmeet_products_linked_to_event_get_correct_event_id(self, num_products):
        """
        Products with channel='presmeet' that ARE linked in an event's product_ids
        list get the correct event_id.
        """
        if "migrate_products" in sys.modules:
            del sys.modules["migrate_products"]

        with mock_aws():
            dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")

            producten = dynamodb.create_table(
                TableName="Producten",
                KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "product_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            events_table = dynamodb.create_table(
                TableName="Events",
                KeySchema=[{"AttributeName": "event_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "event_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            carts_table = dynamodb.create_table(
                TableName="Carts",
                KeySchema=[{"AttributeName": "cart_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "cart_id", "AttributeType": "S"}
                ],
                BillingMode="PAY_PER_REQUEST",
            )

            # Create products with presmeet channel
            product_ids = [f"prod_pm_{uuid.uuid4().hex[:6]}" for _ in range(num_products)]
            expected_event_id = "evt_presmeet_2025"

            # Create event linking all products
            events_table.put_item(
                Item={
                    "event_id": expected_event_id,
                    "name": "PresMeet 2025",
                    "product_ids": product_ids,
                }
            )

            # Seed products
            for pid in product_ids:
                producten.put_item(
                    Item={
                        "product_id": pid,
                        "name": f"PM Product {pid}",
                        "channel": "presmeet",
                        "tenant": "presmeet",
                        "is_parent": True,
                        "active": True,
                    }
                )

            from migrate_products import transform_channels_to_event_ids

            result = transform_channels_to_event_ids(
                producten, events_table, dry_run=False, carts_table=carts_table
            )

            assert result["channel_transformations"] == num_products
            assert len(result["errors"]) == 0

            # Verify each product got the correct event_id
            for pid in product_ids:
                item = producten.get_item(Key={"product_id": pid})["Item"]
                assert item["event_id"] == expected_event_id, (
                    f"Product {pid} should have event_id={expected_event_id}"
                )
                assert "channel" not in item
                assert "tenant" not in item
