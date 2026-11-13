# Implementation Plan: Variant Bulk Generator (single axis)

## Overview

Add a single-axis bulk variant generator on top of the `product-variant-simplification`
architecture. Correct `MAX_AXES` to 1, add pure frontend helpers, rewrite the broken
`admin_bulk_create_variants` handler to the new body contract, update the `BulkVariantCreator` modal
and admin API client, and wire everything into the product variant area. Tasks are ordered:
constant + pure helpers first, then backend, then UI, then integration.

## Tasks

- [x] 1. Correct MAX_AXES to single axis
  - [x] 1.1 Set `MAX_AXES = 1` in `frontend/src/config/constants.ts`
    - Update the constant and its doc comment to reflect the single-axis decision
    - _Requirements: 1.1, 1.3_
  - [x] 1.2 Update existing tests that assume MAX_AXES=2
    - Fix `variantFormHelpers.test.ts` and `VariantEditModal.property.test.ts` expectations so that
      1 existing axis → `at-max`
    - Add `frontend/src/config/__tests__/constants.test.ts` asserting `MAX_AXES === 1`
    - _Requirements: 1.1, 1.2_

- [x] 2. Add pure frontend helpers
  - [x] 2.1 Create `variantBulkHelpers.ts`
    - `normalizeValues(raw: string[]): string[]` — trim, drop empty/whitespace, de-dup (case-sensitive), first-seen order
    - `previewCreateCount(requested: string[], existing: string[]): number`
    - Place in `frontend/src/modules/products/utils/variantBulkHelpers.ts`
    - _Requirements: 3.4, 3.5, 3.7_
  - [x] 2.2 Property tests for helpers
    - **Property 1** (normalization) and **Property 2** (preview count)
    - `frontend/src/modules/products/utils/__tests__/variantBulkHelpers.property.test.ts`
    - _Requirements: 3.4, 3.5, 3.7, 5.2_

- [x] 3. Checkpoint — constant + helpers green
  - Run `npx tsc --noEmit` and the new/updated test files (targeted `--testPathPattern`)

- [x] 4. Rewrite backend handler `admin_bulk_create_variants`
  - [x] 4.1 Replace the body contract and logic
    - Auth: `extract_user_credentials` → `validate_permissions_with_regions(['Products_CRUD'])`
    - Read `{ axis_name, values, prijs?, stock?, allow_oversell? }` from body
    - Load parent (`PRODUCTEN_TABLE_NAME` env with `Producten` fallback); 404/400 guards
    - Normalize values server-side; validate non-empty axis, non-empty values, ≤ 20 values
    - Derive existing axis from existing variant records; reject differing axis with 400
    - Skip values whose `variant_attributes` already exist (active or inactive)
    - Build records identical in shape to `admin_create_variant`; `prijs` via `validate_price_field`
      or inherit from parent; defaults `stock=0`, `allow_oversell=False`, `active=True`
    - Reuse `should_remove_default_variant`; delete `var_{product_id}_default` when applicable
    - Return `{ created, skipped, default_variant_removed, message }` (Decimal-safe serialization)
    - Do NOT import or call `generate_variant_combinations`; do NOT reference `required_attributes`/`variant_schema`
    - _Requirements: 4.1–4.6, 5.1–5.4, 6.1–6.3, 7.1, 7.2, 9.1–9.4_
  - [x] 4.2 Confirm template passes PRODUCTEN_TABLE_NAME
    - Ensure `AdminBulkCreateVariantsFunction.Environment.Variables.PRODUCTEN_TABLE_NAME` is set
      (match `admin_create_variant`); add if missing
    - _Requirements: 9.2_
  - [x] 4.3 Backend property tests
    - **P3** non-duplicate create, **P4** record shape, **P5** single-axis, **P6** idempotence
    - `backend/tests/unit/test_admin_bulk_create_variants_properties.py`
    - _Requirements: 4.1–4.5, 5.1, 5.4, 6.2_
  - [x] 4.4 Backend unit tests
    - Skips existing values; rejects differing axis (400); rejects > 20 values (400); removes
      Default_Variant; prijs inherits parent when no override
    - `backend/tests/unit/test_admin_bulk_create_variants.py`
    - _Requirements: 5.1, 6.2, 6.3, 7.1, 4.3_

- [x] 5. Checkpoint — backend green
  - Run only the two new backend test files (never the full suite)

- [x] 6. Update frontend admin API client
  - [x] 6.1 Extend `bulkCreateVariants` with request body + typed result
    - Add `BulkCreateVariantsBody` and `BulkCreateVariantsResult` types; post the body; return `res.data`
    - `frontend/src/modules/webshop-management/services/adminApi.ts`
    - _Requirements: 8.2_

- [x] 7. Update BulkVariantCreator modal
  - [x] 7.1 New inputs + preview
    - Add `existingVariants` prop; derive locked axis via `deriveAxesFromVariants` (lock when 1 axis
      exists, free text when zero)
    - Multi-value entry (one-per-line or tag input); live "N varianten" preview via `previewCreateCount`
    - Disable submit when axis empty or zero values after `normalizeValues`
    - Post `{ axis_name, values, ...optional overrides }`; on success close + `onSuccess()`
    - On 400/5xx keep modal open with values preserved; toast backend message
    - Dark theme tokens; all strings via `useTranslation('products')`
    - _Requirements: 2.3, 3.1, 3.2, 3.3, 3.6, 3.7, 8.1, 8.2, 8.3, 10.1_
  - [x] 7.2 Unit tests for BulkVariantCreator
    - Locks axis when one exists; disables submit on empty; posts normalized values; shows preview count
    - `frontend/src/modules/webshop-management/__tests__/BulkVariantCreator.test.tsx`
    - _Requirements: 3.1, 3.2, 3.6, 3.7_

- [x] 8. Wire generator into the product variant area
  - [x] 8.1 Render the generator trigger near VariantSubTable / Add-variant
    - Pass `productId`, `productName`, current `existingVariants`, and an `onSuccess` that re-fetches
    - Disable when admin lacks `Products_CRUD`; only for `is_parent` products
    - _Requirements: 2.1, 2.2, 2.3, 8.1_

- [x] 9. Translations
  - [x] 9.1 Add `products` namespace keys in all 8 locales
    - Keys for modal title, axis label, values label/placeholder, preview text, validation messages,
      success/skip/error toasts
    - Update BOTH `frontend/src/locales/products.json` AND `frontend/public/locales/{lang}/products.json`
      for nl, en, de, fr, es, it, da, sv
    - _Requirements: 10.1, 10.2_

- [x] 10. Final checkpoint — integration verification
  - `npx tsc --noEmit`; run the targeted new/updated frontend test files; run the two backend test files
  - Smoke: grep confirms handler does not import `generate_variant_combinations` and reintroduces no
    `variant_schema` / `required_attributes`; `MAX_AXES` resolves to 1 everywhere
  - Verify dark-theme compliance (Chakra UI v2 tokens only)

## Notes

- Scope guard: do NOT revive `variant_schema`, `variant_sync.py`, `VariantSchemaEditor`, or two-axis
  generation. Cleaning up the now-unused `generate_variant_combinations` / `validate_variant_schema`
  dead code is out of scope unless explicitly requested.
- No new product field registry fields; no SKU-code string.

### Steering Documents (follow during implementation)

| Steering file                        | Applies to                | Key points                                                            |
| ------------------------------------ | ------------------------- | --------------------------------------------------------------------- |
| `.kiro/steering/look-and-feel.md`    | All frontend UI tasks     | Dark theme tokens, modal/table patterns                               |
| `.kiro/steering/testing-frontend.md` | Frontend test tasks       | `--watchAll=false` + `--testPathPattern`, `npx tsc --noEmit`          |
| `.kiro/steering/testing-backend.md`  | Backend test tasks        | `importlib.util` handler load, `mock_aws`, patch auth as `'app'`      |
| `.kiro/steering/schema-driven.md`    | Field usage               | Registry is source of truth; no new/renamed fields; financial = Number |
| `.kiro/steering/aws-dynamodb.md`     | Backend tasks             | Table name via env var; `--profile nonprofit-deploy`                  |
| `.kiro/steering/authentication.md`   | Backend handler           | `extract_user_credentials` → `validate_permissions_with_regions`      |
| `.kiro/steering/guardrails.md`       | All tasks                 | Only fix what's asked; no dangerous fallbacks                         |
| `.kiro/steering/tech.md` / `structure.md` | All tasks            | Stack, commands, handler/file conventions                             |

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "2.1"] },
    { "id": 1, "tasks": ["2.2", "4.1"] },
    { "id": 2, "tasks": ["4.2", "4.3", "4.4", "6.1"] },
    { "id": 3, "tasks": ["7.1"] },
    { "id": 4, "tasks": ["7.2", "8.1", "9.1"] },
    { "id": 5, "tasks": ["10"] }
  ]
}
```
