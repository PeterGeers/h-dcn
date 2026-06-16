# Decision: Bidirectional Variant Sync

**Date:** 2026-06  
**Status:** Accepted  
**Affects:** Producten table (parent + variant records), variant management UI

## Context

Products can have variants (e.g. T-Shirt in sizes S, M, L). There are two ways to manage them:

1. Define the schema first, generate variants from it
2. Add/remove variants individually, derive the schema from them

## Decision

**Support both directions. Keep `variant_schema` and variant records always in sync.**

### Top-down (schema → variants)

User defines or edits `variant_schema` on the parent product:

```json
{ "Maat": ["S", "M", "L"], "Gender": ["Male", "Female"] }
```

The app automatically:

- Creates variant records for all combinations (S-Male, S-Female, M-Male, etc.)
- Preserves existing variants that still match
- Deactivates variants that no longer match the schema

### Bottom-up (variants → schema)

User adds or removes a variant directly (e.g. adds "XL" variant):

The app automatically:

- Updates `variant_schema` on the parent to reflect the new set of values
- e.g. adds "XL" to the "Maat" array

## Key rules

- `variant_schema` on the parent is always the source of truth for "what axes and values exist"
- Variant records are the source of truth for "what's in stock, what's sold"
- After any change (top-down or bottom-up), both must be consistent
- The UI can show either view — edit the schema directly or manage variants individually

## Implementation

- `sync_schema_to_variants(table, product_id, schema, parent_price)` — top-down
- `sync_variant_to_schema(table, product_id, variant_attributes)` — bottom-up
- Located in: `backend/layers/auth-layer/python/shared/variant_sync.py`
