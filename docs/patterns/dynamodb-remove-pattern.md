# DynamoDB Field Clearing Pattern (REMOVE)

## Problem

When a user clears all items from an optional list/map field (e.g., removes all order_item_fields from a product), the field must be removed from DynamoDB — not stored as an empty array or null.

JavaScript's `JSON.stringify` strips properties with value `undefined`, so the backend cannot distinguish "user cleared this field" from "user didn't modify this field" unless the frontend explicitly sends a sentinel value.

## Convention

| Frontend sends         | Meaning              | Backend action     | DynamoDB result     |
| ---------------------- | -------------------- | ------------------ | ------------------- |
| `[]` (empty array)     | User cleared it      | `REMOVE` attribute | Attribute absent    |
| `null`                 | User cleared it      | `REMOVE` attribute | Attribute absent    |
| key absent (undefined) | User didn't touch it | No action          | Attribute unchanged |
| `[{...}]` (non-empty)  | User updated it      | `SET` attribute    | Attribute updated   |

## Frontend Implementation

When all items are removed from a list field, send `[]` — never `undefined`:

```typescript
// ✅ Correct — backend receives the empty array, knows to REMOVE
onChange={(fields) => setFieldValue('order_item_fields', fields)}

// ❌ Wrong — undefined is stripped by JSON.stringify, backend never sees it
onChange={(fields) => setFieldValue('order_item_fields', fields.length > 0 ? fields : undefined)}
```

## Backend Implementation

In update handlers, split fields into SET and REMOVE based on whether the value is empty:

```python
update_parts = []
remove_parts = []
expression_values = {}
expression_names = {}

for field in UPDATABLE_FIELDS:
    if field in body:
        value = body[field]
        # Empty list/None → REMOVE the attribute
        if value is None or (isinstance(value, list) and len(value) == 0):
            remove_parts.append(f'#{field}')
            expression_names[f'#{field}'] = field
        else:
            update_parts.append(f'#{field} = :{field}')
            expression_names[f'#{field}'] = field
            expression_values[f':{field}'] = value

# Build combined expression
update_expression = 'SET ' + ', '.join(update_parts)
if remove_parts:
    update_expression += ' REMOVE ' + ', '.join(remove_parts)
```

## Affected Fields

Any optional list or map attribute that can be fully cleared by the user:

- `order_item_fields` — product order fields
- `purchase_rules` — per-order/event limits
- `variant_schema` — product variant axes
- `images` — product images
- `constraints` — event capacity constraints

## Reference Implementation

- Frontend: `frontend/src/modules/products/components/ProductCard.tsx` (onChange handler)
- Backend: `backend/handler/admin_update_product/app.py` (update expression builder)
