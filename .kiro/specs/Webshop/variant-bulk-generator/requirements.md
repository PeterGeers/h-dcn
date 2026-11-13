# Requirements Document

## Introduction

This feature adds a **bulk variant generator** to the product management UI. Today, an admin
creating a sized product (e.g. a T-shirt in XS, S, M, L, XL, XXL) must open the
`VariantEditModal` once per size and submit six separate variant records by hand. The generator
lets the admin enter a single axis (name + a list of values) once and create all corresponding
variant records in one action.

This spec builds on the **leading** variant architecture established by
`product-variant-simplification`: variant records are the single source of truth, there is no
`variant_schema` on the parent product, and the webshop derives axes directly from active variant
records via `deriveAxesFromVariants`. The generator therefore creates records only — it does not
persist any schema on the parent.

### Decision: single axis (1 as) for now

Per an explicit product decision, a product supports **one variant axis at a time** (either sizes
*or* colours, not a size×colour matrix). The generator reflects this: it accepts exactly one axis
and produces one variant record per value (no cartesian product). The existing `MAX_AXES = 2`
constant in the frontend does not match this decision and is corrected to `1` as part of this spec.

### Out of scope

- **SKU code strings.** No human-readable per-variant article code (e.g. `HDCN-SHIRT-M`) is
  generated. A variant's identity remains its machine-generated `product_id` (`var_<uuid>`) plus
  its `variant_attributes`. Adding a readable SKU field is explicitly deferred.
- **Two-axis / matrix generation.** Deferred while the 1-axis decision stands.
- **Reviving `variant_schema`, `variant_sync.py`, or `VariantSchemaEditor`.** These were removed by
  `product-variant-simplification` and must stay removed.

## Glossary

- **Variant_Generator**: The frontend UI (a modal launched from the product's variant area) that
  collects one axis name and a list of values and triggers bulk creation.
- **Variant_API**: The backend Lambda `admin_bulk_create_variants`, reached via
  `POST /admin/products/{id}/variants/bulk`.
- **Parent_Product**: A product record with `is_parent = true`.
- **Variant_Record**: A product record with `is_parent = false` and a `parent_id` linking it to a
  Parent_Product. Contains `variant_attributes`, `prijs`, `stock`, `sold_count`, `allow_oversell`,
  `active` — all existing fields in the product field registry. No new fields are introduced.
- **Axis**: A single variant dimension, e.g. `Maat` or `Kleur`. Represented as one key in a
  Variant_Record's `variant_attributes` map.
- **Default_Variant**: The placeholder variant (`var_<parent>_default`, empty `variant_attributes`)
  that simple products carry. It is removed when real variants are added.
- **MAX_AXES**: The maximum number of distinct variant axes a product may have. Set to `1` by this
  spec (frontend `config/constants.ts`).

## Requirements

### Requirement 1: Correct MAX_AXES to a single axis

**User Story:** As a product owner, I want the system to enforce the current single-axis decision,
so that the admin UI and the generator cannot produce multi-axis products.

#### Acceptance Criteria

1. THE frontend `MAX_AXES` constant SHALL equal `1`.
2. WHEN a product already has one distinct axis across its active and inactive variant records, THE
   `VariantEditModal` create mode SHALL be in the `at-max` state (axis restricted to the existing
   axis, no free-text axis-name input).
3. THE change to `MAX_AXES` SHALL NOT alter `determineFormMode`'s logic (it already derives its
   states from `MAX_AXES`); only the constant value changes.

### Requirement 2: Open the generator from the product variant area

**User Story:** As a webshop admin, I want a clearly labelled action to open the bulk generator from
the product's variant area, so that I can create many sizes at once instead of one by one.

#### Acceptance Criteria

1. THE Variant_Generator SHALL be launchable from the product's variant management area (near the
   variant sub-table / "Add variant" action) for admins with `Products_CRUD` permission.
2. WHILE the admin lacks `Products_CRUD` permission, THE Variant_Generator trigger SHALL be disabled.
3. THE Variant_Generator SHALL only be offered for Parent_Products (`is_parent = true`).

### Requirement 3: Enter one axis and a list of values

**User Story:** As a webshop admin, I want to type one axis name and a list of values, so that each
value becomes its own variant.

#### Acceptance Criteria

1. WHEN the product has no existing axis, THE Variant_Generator SHALL accept a free-text axis name.
2. WHEN the product already has one existing axis, THE Variant_Generator SHALL pre-fill and lock the
   axis name to that existing axis (new values are added to the same axis; a second axis cannot be
   introduced).
3. THE Variant_Generator SHALL accept a list of values entered as distinct entries (e.g. one per
   line or as removable tags).
4. THE Variant_Generator SHALL trim each value and discard empty or whitespace-only entries before
   submission.
5. THE Variant_Generator SHALL de-duplicate values case-sensitively before submission, so the same
   value is not submitted twice in one request.
6. IF, after trimming and de-duplication, zero values remain OR the axis name is empty/whitespace,
   THEN THE Variant_Generator SHALL prevent submission and display a validation message.
7. THE Variant_Generator SHALL display a live preview of how many variants will be created (the
   count of remaining distinct values).

### Requirement 4: Per-variant defaults at generation time

**User Story:** As a webshop admin, I want sensible defaults for each generated variant, so that I
can fine-tune stock and price afterwards per variant.

#### Acceptance Criteria

1. FOR EACH generated Variant_Record, THE Variant_API SHALL set `stock = 0`.
2. FOR EACH generated Variant_Record, THE Variant_API SHALL set `allow_oversell = false`.
3. FOR EACH generated Variant_Record, THE Variant_API SHALL set `prijs` to inherit from the
   Parent_Product (store `null` / absent so the variant inherits, consistent with
   `admin_create_variant`).
4. FOR EACH generated Variant_Record, THE Variant_API SHALL set `active = true`, `sold_count = 0`,
   `is_parent = false`, and `parent_id` equal to the Parent_Product's `product_id`.
5. FOR EACH generated Variant_Record, THE Variant_API SHALL set `variant_attributes` to exactly one
   key-value pair: `{ <axis name>: <value> }`.
6. THE optional request body MAY override the default `prijs`, `stock`, and `allow_oversell` applied
   to all generated variants; WHEN an override is absent, the defaults in criteria 1–3 apply.

### Requirement 5: Idempotent, duplicate-safe generation

**User Story:** As a webshop admin, I want re-running the generator to be safe, so that existing
variants are never overwritten or duplicated.

#### Acceptance Criteria

1. WHEN a requested value matches the `variant_attributes` of an existing Variant_Record for the
   same parent (active or inactive), THE Variant_API SHALL skip that value and SHALL NOT create a
   duplicate.
2. THE Variant_API SHALL create records only for values that do not already exist.
3. THE Variant_API SHALL return a summary containing the number of variants created and the list of
   values skipped as duplicates.
4. IF all requested values already exist, THEN THE Variant_API SHALL create nothing and SHALL return
   a success response reporting zero created and the skipped values (it SHALL NOT return an error).

### Requirement 6: Single-axis enforcement on the backend

**User Story:** As a product owner, I want the backend to enforce the single-axis rule, so that the
decision holds even if a client sends unexpected input.

#### Acceptance Criteria

1. THE Variant_API SHALL accept exactly one axis name and a list of values in the request body.
2. IF the requested axis name differs from the product's existing axis (when one exists), THEN THE
   Variant_API SHALL reject the request with a 400 error indicating the product already uses a
   different axis.
3. THE Variant_API SHALL enforce an upper bound on the number of values per request (reusing the
   existing per-axis maximum, 20 values) and SHALL reject requests exceeding it with a 400 error.

### Requirement 7: Default_Variant cleanup

**User Story:** As a webshop admin, I want the placeholder Default_Variant removed once real variants
exist, so that the product does not show an empty default alongside real options.

#### Acceptance Criteria

1. WHEN the parent's only existing variant is the Default_Variant and the generator creates at least
   one real variant, THE Variant_API SHALL remove the Default_Variant (reusing
   `should_remove_default_variant`).
2. THE Variant_API SHALL report in its response whether the Default_Variant was removed.

### Requirement 8: Refresh after generation

**User Story:** As a webshop admin, I want the variant list to reflect generated variants
immediately, so that I never see stale data.

#### Acceptance Criteria

1. WHEN bulk generation succeeds, THE Variant_Generator SHALL re-fetch the variant list for the
   product and close the modal.
2. THE Variant_Generator SHALL display a success notification reporting the number of variants
   created (and, when relevant, how many values were skipped as duplicates).
3. IF the Variant_API returns an error, THEN THE Variant_Generator SHALL keep the modal open with
   entered values preserved and display an error notification with the failure reason.

### Requirement 9: Authorization and handler conventions

**User Story:** As a platform maintainer, I want the generator endpoint to follow the project's
backend conventions, so that it is secure and consistent.

#### Acceptance Criteria

1. THE Variant_API SHALL require authentication and `Products_CRUD` permission via
   `extract_user_credentials` → `validate_permissions_with_regions`.
2. THE Variant_API SHALL read the Producten table name from an environment variable with a `Producten`
   fallback, consistent with the existing handlers.
3. THE Variant_API SHALL coerce and validate `prijs` using the shared `validate_price_field` helper
   before writing, rejecting non-numeric values with a 400 error.
4. THE Variant_API SHALL store `prijs` as a DynamoDB Number (or inherit from parent via `null`),
   never as a bare string.

### Requirement 10: Translations

**User Story:** As a user of the portal in any supported language, I want the generator UI in my
language.

#### Acceptance Criteria

1. ALL user-facing strings in the Variant_Generator SHALL use `useTranslation('products')` keys.
2. New keys SHALL be added to all 8 locales (nl, en, de, fr, es, it, da, sv) in both
   `frontend/src/locales/products.json` and `frontend/public/locales/{lang}/products.json`.
