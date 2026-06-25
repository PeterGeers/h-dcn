# Root Cause Analysis: Variants Not Shown in Event Booking Form

## The Bug

The event booking form's `ProductConfigurator` never shows variant dropdowns. Users cannot select size/color when booking event products. In the normal webshop cart, variants work correctly.

## Root Cause: Two-fold data gap

### 1. `variant_schema` field was removed from DynamoDB

Migration script `scripts/migrate_remove_variant_schema.py` removed `variant_schema` from all parent products. The webshop adapted by fetching variant records separately and deriving axes at runtime via `deriveAxesFromVariants()`. The event booking module was **never updated** to match.

### 2. `getProducts()` in eventBookingApi uses `/scan-product/` which returns NO variant data

The `scan_product` handler (`backend/handler/scan_product/app.py`) returns only parent product metadata:

- `product_id`, `naam`, `prijs`, `images`, `order_item_fields`, `purchase_rules`, etc.
- **No `variant_schema`** — field no longer exists in DB
- **No `variants` array** — handler doesn't fetch child records

## How It Works in the Webshop (Correct)

```
1. ProductCard opens → useEffect calls productService.getVariants(productId)
2. get_variants handler scans Producten table for records with parent_id = productId
3. Returns full variant records (product_id, variant_attributes, price, stock, etc.)
4. VariantSelector derives axes via deriveAxesFromVariants(variants)
5. User selects from dropdowns → resolves to a specific variant_id
```

**Key components:**

- `frontend/src/modules/webshop/components/ProductCard.tsx` — fetches variants on open
- `frontend/src/modules/webshop/components/VariantSelector.tsx` — renders axis dropdowns
- `frontend/src/modules/webshop-management/utils/variantUtils.ts` — `deriveAxesFromVariants()`
- `backend/handler/get_variants/app.py` — returns variant records for a parent

## How It Fails in the Event Booking

```
1. getProducts() fetches /scan-product/ → returns product WITHOUT variant_schema or variants
2. ProductConfigurator checks: product.variant_schema?.length > 0 → FALSE (field is null/undefined)
3. Variant dropdowns never render
4. User sees no way to select a size/color
```

**Affected components:**

- `frontend/src/modules/eventBooking/services/eventBookingApi.ts` — `getProducts()` never fetches variants
- `frontend/src/modules/eventBooking/components/ProductConfigurator.tsx` — expects `product.variant_schema` and `product.variants` (both always empty)
- `frontend/src/modules/eventBooking/types/eventBooking.types.ts` — `Product` type declares fields that are never populated

## The Type Mismatch

`eventBooking.types.ts` Product interface declares:

```typescript
variant_schema: VariantAxis[] | null;    // Always null — removed from DB
variants?: ProductVariant[];              // Never populated — no API call fetches them
```

## Secondary Issue: Missing Variant Combinations (2-axis products)

If a product has two axes (e.g., "Maat" + "Kleur"), there should be a variant record in DynamoDB for **each combination**. Some products are missing combinations — the `VariantSelector` shows "Combinatie niet beschikbaar" for those pairs.

### Real-world example: PM2027 T-Shirt Meeting (test)

This product has two axes:

- **Gender**: Male, Female
- **Maat**: XS, S, M, L, ...

The admin UI (VariantEditModal) creates a separate SKU/variant record for each **individual value** on each axis, but does NOT generate the **cross-product combinations** (Male+XS, Male+S, Female+XS, Female+S, etc.). The UI simply doesn't support creating combined variant records — it treats each axis value independently.

This means:

- Variant records exist for "Male", "Female", "XS", "S", "M", "L" separately
- No variant record exists for "Male + M" or "Female + L"
- The `VariantSelector` can never resolve a match because it needs ALL axes selected simultaneously

### Why this is an admin UI limitation

The `VariantEditModal` generates variants per-axis, not per-combination. For 2 axes with N×M values, it would need to generate N×M variant records (e.g., 2 genders × 6 sizes = 12 SKUs). The current UI doesn't offer this cross-product generation.

### Decision: 1 axis per product, split multi-axis into separate products

The system supports **one variant axis per product**. When a product needs two dimensions (e.g., gender + size), the solution is to split it into separate parent products:

- **"T-Shirt Meeting Male"** → variants: XS, S, M, L, XL, ...
- **"T-Shirt Meeting Female"** → variants: XS, S, M, L, XL, ...

This is the correct workaround given the current data model and admin UI. Each product has a single axis (Maat) with a variant record per size, which the VariantSelector handles perfectly.

**Implication for the fix:** The code only needs to support 1 axis. No cross-product generation needed. The admin workflow is: create separate products when you need a second dimension.

**Action item:** Split PM2027 T-Shirt Meeting into two products (Male/Female), each with size variants only.

## Fix Options

### Option B: Reuse VariantSelector via shared hook (recommended)

The fix creates a **shared `useProductVariants` hook** that encapsulates variant fetching + the `VariantSelector` component can be reused by all channels (webshop, event booking, future channels).

#### Architecture: Shared variant layer

```
frontend/src/hooks/useProductVariants.ts     ← NEW: shared hook (fetch + state)
frontend/src/components/VariantSelector.tsx   ← MOVE from webshop/components/
frontend/src/utils/variantUtils.ts            ← MOVE from webshop-management/utils/

Consumers:
├── webshop/components/ProductCard.tsx         → uses useProductVariants + VariantSelector
├── eventBooking/components/ProductConfigurator.tsx → uses useProductVariants + VariantSelector
└── (future channels)                         → same pattern
```

#### What the shared hook provides

```typescript
// frontend/src/hooks/useProductVariants.ts
interface UseProductVariantsResult {
  variants: VariantRecord[];
  loading: boolean;
  error: boolean;
  hasVariantAxes: boolean; // true if any variant has non-empty variant_attributes
}

function useProductVariants(
  productId: string | null,
  enabled: boolean,
): UseProductVariantsResult;
```

- Calls `GET /products/{id}/variants`
- Filters to active variants
- Returns the raw variant records for `VariantSelector` to consume
- Handles loading/error state

#### Step-by-step implementation

1. **Create `frontend/src/hooks/useProductVariants.ts`**
   - Shared hook that fetches variants for a given product_id
   - Uses the existing `/products/{id}/variants` endpoint
   - Returns `{ variants, loading, error, hasVariantAxes }`

2. **Move `VariantSelector.tsx` to `frontend/src/components/VariantSelector.tsx`**
   - It's already generic — accepts `VariantRecord[]` and returns the selected variant
   - Update imports in `webshop/components/ProductCard.tsx`

3. **Move `variantUtils.ts` to `frontend/src/utils/variantUtils.ts`**
   - `deriveAxesFromVariants()` is already a pure function, no module-specific deps
   - Update imports in VariantSelector and webshop-management

4. **Refactor `ProductCard.tsx` (webshop)**
   - Replace inline `useEffect` + `productService.getVariants()` with `useProductVariants(productId, isOpen)`
   - Keep the rest of the component as-is

5. **Refactor `ProductConfigurator.tsx` (event booking)**
   - Remove `variant_schema` / `variants` props from Product type dependency
   - Add `useProductVariants(product.product_id, true)`
   - Replace custom variant Select elements with `<VariantSelector variants={variants} onVariantSelect={...} />`
   - Bridge `onVariantSelect` callback to the existing `onChange(fields, variantId)` interface

6. **Clean up `eventBooking.types.ts`**
   - Remove `variant_schema` and `variants` from the `Product` interface (they're never populated)
   - Remove `VariantAxis` and `ProductVariant` types (replaced by shared `VariantRecord`)

7. **Remove dead code**
   - `resolveVariantId()` in ProductConfigurator (replaced by VariantSelector's internal logic)
   - `isVariantSelectionIncomplete()` (replaced by `hasVariantAxes && selectedVariant === null`)

#### API call pattern

The shared hook uses the SAME endpoint the webshop already calls:

```
GET /products/{product_id}/variants
→ { product_id, variants: VariantRecord[], total_count }
```

No backend changes needed.

#### Single-axis constraint

Since the decision is 1 axis per product (split multi-axis into separate products), the `VariantSelector` already handles this correctly — it renders one dropdown per derived axis. With proper product data (1 axis only), it just works.

## Recommended Approach

**Shared hook + shared VariantSelector**, reusable by all channels. No backend changes needed. Products with multiple dimensions are split into separate parent products (1 axis each).
