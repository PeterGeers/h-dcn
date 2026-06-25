# Design Document: Remove event_id from Products

## Overview

This design removes the `event_id` and `event_ids` fields from the Product domain, making `event.product_ids[]` the single source of truth for event-product associations. The change spans the Field Registry, TypeScript interfaces, backend handlers (create, update, get, scan, PDF generation), frontend admin UI, and a DynamoDB migration script.

## Architecture

### Current State

```
Event ──event_id──► Product  (product.event_id = event_id)
Event ──product_ids[]──► Product  (event.product_ids = [product_id, ...])
```

Two sources of truth cause conflicts when they disagree. The `get_products` handler scans by `event_id`, and the admin UI exposes an event selector on products.

### Target State

```
Event ──product_ids[]──► Product  (only association path)
```

Products have no knowledge of which events they belong to. Callers that need "products for event X" read `event.product_ids` and batch-get those IDs from the Producten table.

## Components and Interfaces

### 1. Field Registry (Frontend)

**File:** `frontend/src/config/productFields/fields.ts`

Remove the `event_ids` entry from `parentFields`. No `event_id` entry exists in the registry (only `event_ids` is registered).

```typescript
// REMOVE this entire block from parentFields:
// event_ids: {
//   key: 'event_ids',
//   label: 'Evenementen',
//   ...
// },
```

### 2. TypeScript Interfaces

**Files:**

- `frontend/src/types/index.ts` — Remove `event_ids?: string[]` from `Product`
- `frontend/src/modules/eventBooking/types/eventBooking.types.ts` — Remove `event_id?: string | null` from `Product`

### 3. Create Product Handler

**File:** `backend/handler/admin_create_product/app.py`

Strip `event_id` and `event_ids` from the request body before building the product record. Currently the handler reads `body.get('event_id')` and stores it directly.

```python
# Before building the product dict, strip deprecated fields:
body.pop('event_id', None)
body.pop('event_ids', None)
```

Remove the line `'event_id': event_id,` from the product dict construction.

### 4. Update Product Handler

**File:** `backend/handler/admin_update_product/app.py`

Remove `'event_ids'` from the `UPDATABLE_FIELDS` list. The handler already ignores fields not in this list, so removing it is sufficient. No `event_id` entry exists in the list (only `event_ids`).

```python
UPDATABLE_FIELDS = [
    'naam',
    'artikelcode',
    'prijs',
    'groep',
    'subgroep',
    # 'event_ids',  ← REMOVED
    'images',
    'active',
    'order_item_fields',
    'purchase_rules',
]
```

### 5. Get Products Handler (Batch-Get-by-IDs)

**File:** `backend/handler/get_products/app.py`

Complete rewrite. The handler changes from a scan-by-event_id to a batch-get-by-IDs pattern.

**New interface:**

- Query param: `product_ids` (comma-separated list of product IDs)
- No longer accepts `event_id` param
- Returns only the requested products

**DynamoDB BatchGetItem constraints:**

- Maximum 100 items per call
- Must chunk larger lists into batches of 100

```python
from typing import TypedDict, NotRequired

class GetProductsParams(TypedDict):
    product_ids: list[str]

def _chunk_list(items: list, chunk_size: int = 100) -> list[list]:
    """Split list into chunks of chunk_size for DynamoDB batch limits."""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

def _batch_get_products(product_ids: list[str]) -> list[dict]:
    """Fetch products by ID using DynamoDB BatchGetItem, handling 100-item limit."""
    if not product_ids:
        return []

    all_products = []
    for chunk in _chunk_list(product_ids):
        keys = [{'product_id': pid} for pid in chunk]
        response = dynamodb.batch_get_item(
            RequestItems={
                table_name: {'Keys': keys}
            }
        )
        items = response.get('Responses', {}).get(table_name, [])
        all_products.extend(items)

        # Handle unprocessed keys (DynamoDB throttling)
        unprocessed = response.get('UnprocessedKeys', {})
        while unprocessed.get(table_name):
            response = dynamodb.batch_get_item(RequestItems=unprocessed)
            items = response.get('Responses', {}).get(table_name, [])
            all_products.extend(items)
            unprocessed = response.get('UnprocessedKeys', {})

    return all_products
```

**Auth:** Retains existing role check (`hdcnLeden` or event-related roles).

### 6. Scan Product Handler

**File:** `backend/handler/scan_product/app.py`

Remove `event_ids` from the response normalization dict. Currently it includes `'event_ids': item.get('event_ids', [])`.

```python
# REMOVE from normalized dict:
# 'event_ids': item.get('event_ids', []),
```

### 7. Preparation PDF Generator

**File:** `backend/handler/generate_preparation_pdf/app.py`

Replace `_fetch_products_map(event_id)` — which scans by `event_id` filter — with a batch-get using the event's `product_ids` array.

```python
def _fetch_products_map(product_ids: list[str]) -> dict[str, dict]:
    """Fetch products by ID list using BatchGetItem."""
    if not product_ids:
        return {}

    products_map = {}
    for chunk in _chunk_list(product_ids):
        keys = [{'product_id': pid} for pid in chunk]
        response = dynamodb_resource.batch_get_item(
            RequestItems={
                products_table_name: {
                    'Keys': keys,
                    'ProjectionExpression': 'product_id, #n',
                    'ExpressionAttributeNames': {'#n': 'naam'},
                }
            }
        )
        for item in response.get('Responses', {}).get(products_table_name, []):
            products_map[item['product_id']] = item

        # Handle unprocessed keys
        unprocessed = response.get('UnprocessedKeys', {})
        while unprocessed.get(products_table_name):
            response = dynamodb_resource.batch_get_item(RequestItems=unprocessed)
            for item in response.get('Responses', {}).get(products_table_name, []):
                products_map[item['product_id']] = item
            unprocessed = response.get('UnprocessedKeys', {})

    return products_map
```

**Caller change:** In `lambda_handler`, replace:

```python
products_map = _fetch_products_map(event_id)
```

with:

```python
product_ids = event_record.get('product_ids', [])
products_map = _fetch_products_map(product_ids)
```

### 8. Admin Product Form (Frontend)

**File:** `frontend/src/modules/webshop-management/` (or the ProductCard component)

Remove any event selector (`event_ids` multiselect) from the product edit form. Since `event_ids` is removed from the Field Registry, any form driven by the registry will automatically stop rendering it.

### 9. Event Filter Removal (Frontend)

**Files:**

- `frontend/src/modules/webshop-management/hooks/useEventFilter.ts` — Delete file
- `frontend/src/modules/webshop-management/components/EventFilter.tsx` — Delete file
- `frontend/src/modules/webshop-management/WebshopManagementPage.tsx` — Remove `useEventFilter` import and usage
- `frontend/src/modules/webshop-management/components/ReportsTab.tsx` — Remove `useEventFilter` import and usage

The event filter was passing `event_id` to `get_products`. With the new batch-get pattern, the frontend calls `get_products` with explicit `product_ids` obtained from the event record.

### 10. Migration Script

**File:** `scripts/migrate_remove_event_id_from_products.py`

Follows the established pattern from `migrate_remove_variant_schema.py`:

- `argparse` with `--dry-run` and `--profile` (default: `nonprofit-deploy`)
- Scans for records with `attribute_exists(event_id) OR attribute_exists(event_ids)`
- Removes both attributes with `REMOVE event_id, event_ids`
- Handles DynamoDB pagination
- Logs counts

```python
def main():
    parser = argparse.ArgumentParser(
        description='Remove event_id and event_ids from Producten table'
    )
    parser.add_argument('--profile', default='nonprofit-deploy')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    # Scan with filter: attribute_exists(event_id) OR attribute_exists(event_ids)
    # For each matching record: REMOVE event_id, event_ids
    # Log: total scanned, matching, modified
```

## Data Models

### Producten Table (DynamoDB)

| Attribute   | Before          | After                             |
| ----------- | --------------- | --------------------------------- |
| `event_id`  | Optional string | **Removed** (migration strips it) |
| `event_ids` | Optional list   | **Removed** (migration strips it) |

All other attributes unchanged.

### Events Table (DynamoDB)

No change. `product_ids: string[]` already exists and becomes the sole association mechanism.

## Error Handling

| Scenario                             | Handler                     | Response                                 |
| ------------------------------------ | --------------------------- | ---------------------------------------- |
| Empty `product_ids` param            | get_products                | 200, empty list                          |
| Non-existent IDs in `product_ids`    | get_products                | 200, returns only existing products      |
| Missing `product_ids` param entirely | get_products                | 400, "product_ids parameter is required" |
| DynamoDB throttling on BatchGetItem  | get_products, PDF generator | Retry unprocessed keys                   |
| Event has no `product_ids` array     | PDF generator               | Generate PDF without product data        |

## Shared Utility: Chunk Helper

Both `get_products` and `generate_preparation_pdf` need a chunking utility for the 100-item BatchGetItem limit. Add to the auth layer or as a local helper in each handler (since it's 2 lines):

```python
def _chunk_list(items: list, chunk_size: int = 100) -> list[list]:
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
```

Given the project's "one Lambda per endpoint" architecture and the simplicity of this utility, duplicating it in both handlers is acceptable (avoids adding to the shared layer for a 2-line function).

## Testing Strategy

### Backend (pytest + moto + hypothesis)

- **Property tests** (hypothesis): Validate handlers strip/ignore deprecated fields across randomized payloads. Validate migration correctness. Validate batch-get returns correct subsets.
- **Unit tests** (pytest + moto): Verify specific scenarios — empty product_ids, non-existent IDs, UPDATABLE_FIELDS list contents, migration --dry-run behavior.
- **Pattern**: Use `importlib.util` to load handlers, `mock_aws()` for DynamoDB mocking, patch auth layer.

### Frontend (Jest)

- **Unit tests**: Verify Field Registry no longer exports `event_id`/`event_ids`. Verify removed imports don't cause build failures.
- **Type check**: `tsc --noEmit` confirms no type errors after interface changes.
- **Lint**: `eslint` confirms no unused imports remain after removing event filter hook and EventFilter component.

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property 1: Create handler never persists event_id or event_ids

_For any_ valid product creation payload that includes `event_id` and/or `event_ids` fields, the resulting DynamoDB record SHALL NOT contain an `event_id` or `event_ids` attribute.

**Validates: Requirements 3.1, 3.2**

### Property 2: Update handler ignores event_id and event_ids

_For any_ valid product update payload that includes `event_id` and/or `event_ids` fields, the updated DynamoDB record SHALL NOT have `event_id` or `event_ids` modified or added.

**Validates: Requirements 4.3**

### Property 3: Batch-get returns exactly the existing subset

_For any_ list of product IDs passed to `get_products`, the response SHALL contain exactly the set of products whose IDs both appear in the request AND exist in DynamoDB — no more, no less.

**Validates: Requirements 6.1, 6.4**

### Property 4: Migration dry-run preserves all data

_For any_ set of product records in DynamoDB (some with `event_id`/`event_ids`, some without), running the migration script with `--dry-run` SHALL leave all records completely unchanged.

**Validates: Requirements 8.1**

### Property 5: Migration removes event_id and event_ids from all records

_For any_ set of product records in DynamoDB that contain `event_id` and/or `event_ids` attributes, running the migration script (without `--dry-run`) SHALL result in zero records containing either attribute, regardless of table size or pagination boundaries.

**Validates: Requirements 8.2, 8.4**

### Property 6: Scan response excludes event_id and event_ids

_For any_ product record in DynamoDB (whether or not it has legacy `event_id`/`event_ids` attributes), the `scan_product` API response SHALL NOT include `event_id` or `event_ids` fields in any returned item.

**Validates: Requirements 9.1, 9.2**

### Property 7: PDF generator fetches products via event.product_ids

_For any_ event record with a `product_ids` array, the preparation PDF generator SHALL fetch exactly those product IDs via batch-get and SHALL NOT scan the Producten table by `event_id`.

**Validates: Requirements 7.1, 7.2**
