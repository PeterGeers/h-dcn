# Requirements Document

## Introduction

This feature improves the **public webshop product table** so that members can find products
faster. Today the public table (`frontend/src/modules/webshop/components/ProductTable.tsx`) uses
plain, static `<Th>` headers with no per-column sorting or filtering, and discovery relies on a
left-side filter panel (`FilterPanel`) in `WebshopPage.tsx` that offers group and subgroup
dropdowns. The table also carries an "Opties" column that only labels a product as "Varianten" or
"Standaard", and it shows no product imagery.

This spec makes three scoped changes to the public table and adds one new column:

1. Apply the reusable filter/sort framework (`FilterableHeader` + `useTableSort`) to the public
   product table, giving each relevant column an inline text filter and a sort toggle.
2. Remove the left-side group/subgroup filter panel entirely. Group and Subgroup remain as
   table columns that are filterable and sortable in-column via `FilterableHeader`.
3. Remove the "Opties"/variants column (the "Varianten"/"Standaard" label) entirely.
4. Add a small, fixed-size product thumbnail as the leading column, using the first product image,
   normalized the same way `ProductCard` already does.

### Scope

- **In scope:** the public webshop product table only — `ProductTable.tsx` and the parts of
  `WebshopPage.tsx` that feed it (the left-side `FilterPanel` and its group/subgroup state).
- **Out of scope:** the "Webshop Beheer" admin product table and its components. This spec does not
  touch the admin product management UI.
- **Out of scope:** any backend / DynamoDB change. The webshop product list already returns
  `images`, `groep`, and `subgroep` (confirmed in `WebshopPage.loadProducts` →
  `productService.getWebshopProducts`), so no handler or schema change is expected. If a backend
  change turns out to be required, that is a signal to revisit this scope.

### Decision: remove the left-side filters, do not convert them

Per an explicit product decision, the left-side group and subgroup selectors are **removed
entirely**, not re-expressed as a `FilterPanel` above the table. Discovery of group and subgroup is
handled by the in-column `FilterableHeader` search and sort on the Group and Subgroup columns.

### Decision: no image means no image

When a product has no usable image, the thumbnail cell renders nothing (an empty / minimal
placeholder cell). No broken-image icon and no stand-in graphic are shown.

## Glossary

- **Public_Product_Table**: The member-facing product table rendered by
  `frontend/src/modules/webshop/components/ProductTable.tsx`. Distinct from the admin "Webshop
  Beheer" product table, which is out of scope.
- **Webshop_Page**: The page component `frontend/src/modules/webshop/WebshopPage.tsx` that loads
  products, applies the active-product filter, and renders the Public_Product_Table.
- **Table_Framework**: The reusable filter/sort components in `frontend/src/components/filters/`
  (`FilterableHeader`, `FilterPanel`, `GenericFilter`, `YearFilter`) and the hook
  `frontend/src/hooks/useTableSort.ts`, described in `.kiro/steering/table-framework.md`.
- **FilterableHeader**: The Table_Framework component that replaces a `<Th>` with an inline text
  filter input plus a 3-state sort toggle (asc → desc → none).
- **useTableSort**: The Table_Framework hook that provides `sortField`, `sortDirection`,
  `handleSort`, and `sortData` (immutable, locale-aware, nulls sorted to end).
- **Group_Filter_Panel**: The existing left-side `FilterPanel` in Webshop_Page configured with
  group and subgroup single-select filters, together with the `selectedGroep` / `selectedSubgroep`
  state and the `groepOptions` / `subgroepOptions` / `filteredProducts` `useMemo` computations that
  support it.
- **Product_Thumbnail**: The small, fixed-size image rendered as the leading table column for each
  product row, derived from the product's first image.
- **Image_Url_Helper**: A shared utility that normalizes a product's image value into a usable URL
  (handling `images` vs legacy `image`, array vs string, and the
  `my-hdcn-bucke` → `my-hdcn-bucket.s3.eu-west-1.amazonaws.com` URL fix), extracted from the
  logic currently inline in `ProductCard.tsx`.
- **Active_Product**: A product record where `active !== false` (strict comparison, per the
  DynamoDB field-safety rules — a missing or `undefined` `active` value counts as active).

## Requirements

### Requirement 1: Apply the filter/sort framework to the public product table

**User Story:** As a webshop member, I want to search and sort the product table by column, so that
I can find a product quickly without using separate filter controls.

#### Acceptance Criteria

1. THE Public_Product_Table SHALL use the Table_Framework (`FilterableHeader` + `useTableSort`) for
   its column headers instead of plain `<Th>` elements, per `.kiro/steering/table-framework.md`.
2. THE Public_Product_Table SHALL provide a `FilterableHeader` with an inline text filter and a sort
   toggle for the Name column (field `naam`), the Group column (field `groep`), and the Subgroup
   column (field `subgroep`).
3. THE Public_Product_Table SHALL provide a sort toggle for the Price column (field `prijs`).
4. WHEN a member types text into a column's `FilterableHeader` filter, THE Public_Product_Table
   SHALL show only the rows whose corresponding field contains that text, matched
   case-insensitively.
5. WHEN a member activates a column's sort toggle, THE Public_Product_Table SHALL order the rows by
   that column, cycling asc → desc → none on repeated activation, using `useTableSort`.
6. WHILE multiple column filters contain text, THE Public_Product_Table SHALL show only the rows
   that satisfy every active column filter.
7. WHERE a field value is absent, null, or undefined for a row, THE Public_Product_Table SHALL sort
   that row to the end and SHALL treat the row as non-matching for a non-empty text filter on that
   field, without raising an error.
8. THE Public_Product_Table SHALL keep each row clickable to open the product detail view, as it is
   today, when filtering and sorting are applied.

### Requirement 2: Remove the left-side group/subgroup filter panel

**User Story:** As a webshop member, I want product discovery handled directly in the table, so that
the page is not cluttered with a separate filter panel that duplicates the column controls.

#### Acceptance Criteria

1. THE Webshop_Page SHALL NOT render the Group_Filter_Panel (the left-side group and subgroup
   filter controls).
2. THE Webshop_Page SHALL remove the `selectedGroep` and `selectedSubgroep` state and the
   `groepOptions` / `subgroepOptions` option-building computation, as these become unused once the
   Group_Filter_Panel is removed.
3. WHEN the Webshop_Page passes products to the Public_Product_Table, THE Webshop_Page SHALL include
   only Active_Products (`active !== false`), preserving the active-product filter that currently
   lives in the `filteredProducts` computation.
4. THE Webshop_Page SHALL continue to pass products to the Public_Product_Table ordered by no
   group/subgroup pre-filter, relying on the Public_Product_Table's in-column `FilterableHeader`
   for group and subgroup filtering.
5. THE Group column and the Subgroup column SHALL remain present in the Public_Product_Table as
   filterable and sortable columns (per Requirement 1).
6. THE Webshop_Page SHALL remove any imports and helpers that become unused after the
   Group_Filter_Panel removal (for example the `FilterPanel` / `FilterConfig` imports if no longer
   referenced), leaving no dead code.

### Requirement 3: Remove the Opties/variants column

**User Story:** As a webshop member, I want the table to show only columns that help me decide, so
that I do not spend reading time on a label that carries no useful information.

#### Acceptance Criteria

1. THE Public_Product_Table SHALL NOT render the "Opties" column that currently displays
   "Varianten" or "Standaard" based on `is_parent`.
2. THE Public_Product_Table SHALL NOT render the header cell for the removed Opties column.
3. THE Public_Product_Table SHALL NOT introduce a replacement column that shows variant values in
   place of the removed Opties column.
4. THE removal of the Opties column SHALL leave no unused translation key reference in the
   Public_Product_Table (the `table.options` key SHALL no longer be referenced by the component).

### Requirement 4: Add a product thumbnail column

**User Story:** As a webshop member, I want to see a small image of each product in the table, so
that I can recognize products at a glance.

#### Acceptance Criteria

1. THE Public_Product_Table SHALL render a Product_Thumbnail as the leading column, positioned
   before the Name column.
2. THE Product_Thumbnail SHALL use the first usable image for the product, derived from
   `product.images?.[0]` (falling back to the legacy `image` value) via the Image_Url_Helper.
3. THE Product_Thumbnail SHALL be rendered at a fixed box size with `objectFit: cover` and styling
   consistent with the dark theme (`.kiro/steering/look-and-feel.md`), using Chakra UI v2.
4. IF a product has no usable image, THEN THE Public_Product_Table SHALL render an empty or minimal
   placeholder cell for that row and SHALL NOT render an image element or a broken-image indicator.
5. WHERE the product's image data is absent, null, a non-string entry, or an empty array, THE
   Image_Url_Helper SHALL return no URL, and the Public_Product_Table SHALL treat the row as having
   no usable image (per criterion 4), without raising an error.
6. THE Product_Thumbnail column SHALL NOT be sortable or filterable.

### Requirement 5: Shared image URL helper

**User Story:** As a frontend maintainer, I want the image-URL normalization logic in one shared
place, so that the table and the product card stay consistent and the logic is testable.

#### Acceptance Criteria

1. THE Image_Url_Helper SHALL accept a product (or its image fields) and return the first usable,
   fully-qualified image URL, or an empty result when none exists.
2. THE Image_Url_Helper SHALL handle the `images` array, the legacy `image` string, an array value,
   and a single string value, mirroring the normalization currently inline in `ProductCard.tsx`.
3. THE Image_Url_Helper SHALL apply the
   `my-hdcn-bucke` → `my-hdcn-bucket.s3.eu-west-1.amazonaws.com` URL correction, consistent with the
   existing `ProductCard.tsx` behaviour.
4. THE Image_Url_Helper SHALL discard entries that are not non-empty strings before selecting a URL.
5. THE Public_Product_Table SHALL obtain its Product_Thumbnail URL from the Image_Url_Helper rather
   than re-implementing normalization inline.

### Requirement 6: Schema and data-safety conventions

**User Story:** As a platform maintainer, I want the table to use the established field names and
defensive data handling, so that the change is consistent and safe against sparse DynamoDB data.

#### Acceptance Criteria

1. THE Public_Product_Table SHALL read product data using the existing field names `naam`, `groep`,
   `subgroep`, `prijs`, `images`, and `is_parent`, and SHALL NOT introduce new or renamed fields.
2. THE Public_Product_Table SHALL format the price using the safe price helper
   (`formatPrice` / `toPrice`) rather than calling `.toFixed()` directly on a DynamoDB field, per
   the DynamoDB field-safety rules in `.kiro/steering/aws-dynamodb.md`.
3. THE Webshop_Page SHALL determine Active_Product status using strict comparison (`active !== false`)
   and SHALL NOT use a truthy/falsy check on the `active` field.
4. THE change SHALL be frontend-only, with no modification to backend handlers or DynamoDB schema.

### Requirement 7: Translations

**User Story:** As a user of the portal in any supported language, I want the product table labels
in my language, so that the webshop is usable regardless of locale.

#### Acceptance Criteria

1. ALL user-facing strings in the Public_Product_Table (column labels, filter placeholders, and any
   image alt text) SHALL use `useTranslation` keys, with no hardcoded display strings.
2. New or changed translation keys SHALL be added to all 8 locales (nl, en, de, fr, es, it, da, sv).
3. New or changed translation keys SHALL be added to both `frontend/src/locales/{lang}/` and
   `frontend/public/locales/{lang}/` for the relevant namespace (`products` and/or `webshop`),
   consistent with the current `useTranslation('products')` / `table.*` usage.
4. THE removed "Opties" column's `table.options` key MAY remain defined in the locale files, but
   SHALL no longer be referenced by the Public_Product_Table.
