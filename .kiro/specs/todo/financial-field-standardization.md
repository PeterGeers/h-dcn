# Financial Field Standardization

## Problem

Price/financial fields across the codebase are inconsistently stored (string vs number) and displayed (inline `Number(x).toFixed(2)` patterns instead of helpers). This causes:

- `toFixed is not a function` crashes when DynamoDB returns a string
- Inconsistent price display across components
- No backend enforcement of numeric types

## What's done

- ✅ `formatPrice()` / `formatPriceEuro()` / `toPrice()` helpers created at `frontend/src/utils/formatPrice.ts`
- ✅ Used in: VariantSubTable, ProductManagementPage, ProductTable, webshop/ProductCard, DraftOrderModal
- ✅ Steering rule in `specs.md` documenting the helpers

## What still needs to be done

### Frontend (remaining inline patterns)

| File                                       | Line     | Current                                                  | Replace with                                       |
| ------------------------------------------ | -------- | -------------------------------------------------------- | -------------------------------------------------- |
| `webshop/WebshopPage.tsx`                  | ~674     | `Number(item.price \|\| 0).toFixed(2)`                   | `formatPrice(item.price)`                          |
| `webshop/CheckoutModal.tsx`                | ~439     | `(Number(item.price \|\| 0) * item.quantity).toFixed(2)` | `formatPrice(toPrice(item.price) * item.quantity)` |
| `webshop/OrderConfirmation.tsx`            | ~225-226 | `Number(item.price \|\| 0).toFixed(2)`                   | `formatPrice(item.price)`                          |
| `advanced-exports/AdvancedExportsPage.tsx` | ~152-154 | `productStats.gemiddeldePrijs.toFixed(2)`                | `formatPrice(productStats.gemiddeldePrijs)`        |

### Steering rule (schema-driven.md)

Add to `schema-driven.md`:

```
### 6. Financial fields must be stored as DynamoDB Number type

Financial fields (prijs, price, purchase_price_per_unit, cost, revenue, total_paid)
MUST be stored as DynamoDB Number type, not String. Backend handlers must:
- Coerce string prices to Decimal before writing: `Decimal(str(value))`
- Reject non-numeric values with 400 error
- Never store prices as bare strings like "25"
```

### Backend enforcement

Handlers to update:

- `admin_update_product/app.py` — validate `prijs` is numeric before storing
- `admin_create_variant/app.py` — validate `prijs` if provided
- `admin_create_product/app.py` — validate `price`/`prijs`
- `create_order/app.py` — validate line item prices

### DynamoDB migration

Run a one-time migration to convert existing string prices to Number type:

- Scan Producten table for records where `prijs` is a string
- Convert to Decimal and update
- Same for Orders table `line_items[].price`
