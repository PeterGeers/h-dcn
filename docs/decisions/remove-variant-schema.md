# ADR: Remove variant_schema from Product Records

**Date:** 2026-06-17  
**Status:** Accepted  
**Context:** Product variant simplification spec

## Decision

Remove the `variant_schema` field from parent product records and all code that reads, writes, or syncs it. Variant axes and values are now derived at runtime from the variant records themselves.

## Context

The old approach stored a `variant_schema` map on each parent product (e.g., `{"Maat": ["S","M","L"], "Kleur": ["Rood","Blauw"]}`). A sync module (`variant_sync.py`) rebuilt this schema whenever variants were created/deleted. The admin UI had a `VariantSchemaEditor` for manual editing. This led to:

- Sync bugs (schema out of date when variants were modified directly)
- Confusion about source of truth (schema vs. actual variant records)
- Extra complexity in the create-variant flow (validation against schema)
- Dead code maintaining two-way synchronization

## New Approach

1. **Frontend admin (VariantEditModal)**: Derives existing axes from `existingVariants` array using `determineFormMode()`. The three-state logic (zero-axes / under-max / at-max) restricts axis creation based on `MAX_AXES = 2`.

2. **Webshop (VariantSelector)**: Uses `deriveAxesFromVariants(variants)` to compute axis→values map from active variant records at display time.

3. **Backend (admin_create_variant)**: No longer validates against a schema. Only checks for duplicate `variant_attributes` (409 response).

4. **Database**: The `variant_schema` field is stripped from existing records via migration script (`scripts/migrate_remove_variant_schema.py`).

## Consequences

- Variant records are the single source of truth for axes/values
- No sync logic needed — removing a variant automatically removes its values from the derived axes
- `MAX_AXES` constant enforces the 2-axis limit in the frontend UI
- The backend does not enforce MAX_AXES (frontend-only constraint) — see tech.md for rationale

## Migration

Run `python scripts/migrate_remove_variant_schema.py` to strip the field from existing Producten records. The field is already ignored by all handlers.

## Exceptions

The PresMeet module uses a different `variant_schema` format (`VariantAxis[]` array instead of `Record<string, string[]>` map) on its own Product type. This is scoped to `modules/presmeet/` and will be addressed in the unified event booking form refactor (see `.kiro/specs/todo/BookingForm.md`).
