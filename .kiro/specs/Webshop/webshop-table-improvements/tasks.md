# Implementation Plan: Webshop Table Improvements

## Overview

Frontend-only improvement of the **public webshop product table**. Extract the inline image
normalization from `ProductCard` into a shared, pure `utils/productImage.ts` helper; refactor
`ProductCard` onto that helper (behavior identical); rewrite `ProductTable` to use the
`FilterableHeader` + `useTableSort` framework with a leading thumbnail column, remove the "Opties"
column, and format price via `formatPrice`; slim down `WebshopPage` by removing the left-side
`FilterPanel` and its group/subgroup state; and add the new `products` translation keys to all 8
locales. Tasks are ordered so dependencies come first: shared helper → ProductCard refactor and
ProductTable rewrite → WebshopPage cleanup → translations → final checkpoint. No backend or
DynamoDB change.

## Tasks

- [x] 1. Create the shared image helper
  - [x] 1.1 Implement `normalizeProductImages` and `getPrimaryImageUrl`
    - Create `frontend/src/utils/productImage.ts` exporting `ProductImageFields`,
      `normalizeProductImages(product): string[]`, and
      `getPrimaryImageUrl(product): string | null` (= `normalizeProductImages(product)[0] ?? null`)
    - Pure and defensive: accept `images` array / legacy `image` (string | string[]) / single
      string; drop non-string and empty-string entries; never throw on malformed input
    - Apply the bucket URL fix `https://my-hdcn-bucke` →
      `https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com`; leave already-correct URLs untouched
    - Mirror the existing inline `ProductCard.tsx` normalization exactly
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 4.2_
  - [x] 1.2 Property tests for the image helper
    - Create `frontend/src/utils/__tests__/productImage.property.test.ts` (fast-check, ≥100 iterations each)
    - **Property 1: Helper returns null or a non-empty string** — _Validates: Requirements 5.1, 5.4, 4.5_
    - **Property 2: No usable image yields null** — _Validates: Requirements 4.5, 5.4_
    - **Property 3: Bucket URL correction** — _Validates: Requirements 5.3_
    - _Requirements: 5.1, 5.3, 5.4, 4.5_

- [x] 2. Refactor the webshop ProductCard onto the shared helper
  - [x] 2.1 Replace the inline image block with `normalizeProductImages`
    - In `frontend/src/modules/webshop/components/ProductCard.tsx`, replace the inline
      image-normalization block (~lines 138–168) with a call to `normalizeProductImages`
    - Keep the carousel `images: string[]` behavior byte-for-byte identical; no visual change
    - _Requirements: 5.5, 5.2, 5.3_
  - [x] 2.2 Test image-list parity
    - Create `frontend/src/modules/webshop/components/__tests__/ProductCard.images.test.tsx`
    - Assert `normalizeProductImages` produces the same image list the inline logic produced
      (array input, legacy string, bucket-prefix fix, empty/malformed input)
    - _Requirements: 5.2, 5.3, 5.5_

- [x] 3. Checkpoint — helper and ProductCard refactor green
  - Ensure all tests pass, ask the user if questions arise.
  - Run the targeted test files (`--testPathPattern="productImage.property"` and
    `"ProductCard.images"`), `npx tsc --noEmit`, and `CI=true npm run build` (must be warning-free)

- [x] 4. Rewrite the public ProductTable
  - [x] 4.1 Add the self-contained filter + sort composition
    - In `frontend/src/modules/webshop/components/ProductTable.tsx`, add own filter state
      `{ naam, groep, subgroep }` plus `useTableSort(filtered)`; filter-first (case-insensitive
      substring, AND across active filters) then sort via `sortedData`
    - Export a pure `matchesFilters(product, filters)` helper (and `fieldMatches`): empty filter
      matches all; absent/null/undefined/non-string field is non-matching for any non-empty filter
    - Extend the local `Product` type with `images?: string[]` and `image?: string | string[]`;
      keep existing fields; `is_parent` may remain in the type but is not rendered
    - _Requirements: 1.4, 1.5, 1.6, 1.7, 6.1_
  - [x] 4.2 Build the header row with FilterableHeader
    - Leading plain `<Th>` thumbnail column (not sortable, not filterable)
    - `FilterableHeader` for Name (`naam`), Group (`groep`), Subgroup (`subgroep`) with inline text
      filter + sort toggle; Price (`prijs`) sort-only (omit `filterValue`/`onFilterChange`)
    - Wire `sortDirection={sortField === field ? sortDirection : null}` and `onSort={() => handleSort(field)}`
    - Responsive `display` on Group (`{ base: 'none', md: 'table-cell' }`) and Subgroup
      (`{ base: 'none', lg: 'table-cell' }`) matching the body `<Td>` display; dark theme preserved
    - _Requirements: 1.1, 1.2, 1.3, 3.1, 3.2, 3.3, 3.4_
  - [x] 4.3 Build the body rows with the thumbnail cell
    - Leading `<Td>` renders `<Image>` (boxSize 48px, `objectFit="cover"`, borderRadius) only when
      `getPrimaryImageUrl(product)` is non-null; empty `<Td>` otherwise (no `<img>`, no broken-image icon)
    - Render Name, Group, Subgroup, and Price via `formatPrice(product.prijs)`; no `.toFixed()` on raw fields
    - Remove the Opties column entirely (header and cell); do not reference `table.options`
    - Preserve row click (`onProductSelect`), responsive column display, and dark theme styling
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.6, 1.8, 3.1, 6.2_
  - [x] 4.4 Property tests for the table filter/sort logic
    - Create `frontend/src/modules/webshop/components/__tests__/productTableLogic.property.test.ts`
      (fast-check, ≥100 iterations each)
    - **Property 4: Filter yields an ordered subset** — _Validates: Requirements 1.4, 1.5, 1.6_
    - **Property 5: Absent field never matches a non-empty filter** — _Validates: Requirements 1.7, 4.5_
    - **Property 6: Conjunctive filtering** — _Validates: Requirements 1.4, 1.6_
    - **Property 7: Empty filters, no sort is identity** — _Validates: Requirements 1.6, 2.4_
    - _Requirements: 1.4, 1.5, 1.6, 1.7_
  - [x] 4.5 RTL component tests for ProductTable
    - Create `frontend/src/modules/webshop/components/__tests__/ProductTable.test.tsx`
    - Thumbnail shown when image present / no `<img>` when absent; Name text filter
      (case-insensitive); sort toggle asc → desc → none; multiple filters combine with AND; no
      "Opties" header or cell; row click fires `onProductSelect`; price rendered via `formatPrice`
      (e.g. null `prijs` → `€0.00`)
    - _Requirements: 4.1, 4.4, 1.4, 1.5, 1.6, 3.1, 3.2, 1.8, 6.2_

- [x] 5. Checkpoint — ProductTable green
  - Ensure all tests pass, ask the user if questions arise.
  - Run the targeted ProductTable test files (`--testPathPattern="productTableLogic.property"` and
    `"ProductTable"`), `npx tsc --noEmit`, and `CI=true npm run build` (must be warning-free)

- [x] 6. Clean up WebshopPage
  - [x] 6.1 Remove the FilterPanel and group/subgroup state
    - In `frontend/src/modules/webshop/WebshopPage.tsx`, remove the `FilterPanel` JSX block and its
      300px `<Box>`; collapse the `Stack` to a single full-width table box
    - Remove `selectedGroep` / `selectedSubgroep` state, the `groepOptions` / `subgroepOptions`
      memos, and the group/subgroup branches of `filteredProducts`
    - Add an `activeProducts` memo keeping only `active !== false` (strict comparison); pass it to
      `ProductTable`
    - Remove now-unused imports (`FilterPanel`, `FilterConfig`, and any other orphaned symbols);
      leave no dead code
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 6.3, 6.4_

- [x] 7. Add translation keys
  - [x] 7.1 Add new `products` keys to all 8 locales
    - Add `table.filter_name`, `table.filter_group`, `table.filter_subgroup`, `table.thumbnail_alt`
      to nl, en, de, fr, es, it, da, sv
    - Update BOTH `frontend/src/locales/{lang}/products.json` AND
      `frontend/public/locales/{lang}/products.json` in the same change
    - Leave the now-unreferenced `table.options` key in place
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 8. Final checkpoint — integration verification
  - Ensure all tests pass, ask the user if questions arise.
  - Run the targeted new/updated frontend test files (`productImage.property`, `ProductCard.images`,
    `productTableLogic.property`, `ProductTable`)
  - Run `npx tsc --noEmit`; run `npx eslint` on `utils/productImage.ts`, `ProductCard.tsx`,
    `ProductTable.tsx`, and `WebshopPage.tsx`
  - Run `CI=true npm run build` from `frontend/` — must complete with zero warnings (deploy gate)
  - Smoke: grep confirms `WebshopPage.tsx` no longer imports `FilterPanel` and `ProductTable.tsx`
    no longer references `table.options` or renders the Opties column

## Notes

- Tasks marked with `*` are optional test sub-tasks and can be skipped for a faster MVP.
- Each leaf task references specific requirements for traceability; property sub-tasks also cite the
  design Property number and the requirement clauses it validates.
- Checkpoints (tasks 3, 5, 8) run targeted tests + `npx tsc --noEmit` + the `CI=true npm run build`
  deploy gate (CRA treats ESLint warnings as errors under CI).
- **Scope guards:**
  - Do NOT touch the admin "Webshop Beheer" product table or its components — public table only.
  - No backend handler, DynamoDB, or API change; this feature performs no I/O.
  - No new or renamed product field registry fields; reuse `naam`, `groep`, `subgroep`, `prijs`,
    `images`, `image`, `is_parent`, `active`.

### Steering Documents (follow during implementation)

| Steering file                             | Applies to            | Key points                                                            |
| ----------------------------------------- | --------------------- | --------------------------------------------------------------------- |
| `.kiro/steering/table-framework.md`       | ProductTable rewrite  | `FilterableHeader` + `useTableSort` usage and prop contracts          |
| `.kiro/steering/look-and-feel.md`         | All frontend UI tasks | Dark theme tokens, table/image patterns, Chakra UI v2                 |
| `.kiro/steering/testing-frontend.md`      | Frontend test tasks   | `--watchAll=false` + `--testPathPattern`, `npx tsc --noEmit`, fast-check |
| `.kiro/steering/schema-driven.md`         | Field usage           | Registry is source of truth; no new/renamed fields                    |
| `.kiro/steering/aws-dynamodb.md`          | Data safety           | `formatPrice` not `.toFixed()`; strict `active !== false`             |
| `.kiro/steering/guardrails.md`            | All tasks             | Only fix what's asked; frontend-only; no dead code                    |
| `.kiro/steering/tech.md` / `structure.md` | All tasks             | Stack, commands, file conventions, 8-locale i18n                      |

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "7.1"] },
    { "id": 1, "tasks": ["1.2", "2.1", "4.1"] },
    { "id": 2, "tasks": ["2.2", "4.2"] },
    { "id": 3, "tasks": ["4.3"] },
    { "id": 4, "tasks": ["4.4", "4.5", "6.1"] }
  ]
}
```
