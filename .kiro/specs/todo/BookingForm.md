# Event form Presmeet required

Can have a field name Naam required

- Ticket to access presmeet (max 3 by club)
- Ticket to be at the party (Evt with a fee for drinks notes)
- Ticket for dropdown/ pickup at airports or ??
- Ticket for a nice thing todo around Noordwijkerhout
- Presmeet T-Shirt
- Presmeet Guest t-shirt
  Do not have a field name Naam required, butr cab be added temporary
- H-DCN products like badges, pins, stickers from the webshop

# Flows

## Guest driven in onde order

When the booking form for an event opens the flow should be:

- Club-id/name is given
- Open the order for the bespoke club_id/club_name
- Ask for a name of a guest
- Show a list of orderable items
- Select the items to order for bespoke guest
- Ask for the variances of a product ordered for a guesty
- ask for the fieldnames to be filled (except where the guestname is requested fill in the name of the bespoke guest)
- Quantity per orderline is 1????
- How do you handle products that have no fieldname request for name
- How do you handle validation of rules for products
- Do we need rules for orders/events
- A pdf booking form can be asked for with all details of the order including status, cost, payment status and validation statement
  Pros:
  For each guest you can make a welcome package with all guest ordered products (Tickets, shirst etcetera)

Cons:
Not all standard products require the field name Naam. You have to add the fieldname rwequirement to all products that can be ordered.

## Guest driven with a dedicated order/payment per guest

Pros:
For each guest you can make a welcome package with all guest ordered products (Tickets, shirst etcetera)
Cost/ Payment are clear linked to the visitor.
(??} The issue of declaration of cost in the club is at the visitor

Cons:
The order / payment process needs attention
To allow each guest to make his own booking there is good supervision of who is allowed for a meeting or party (No Club coordination)
Access/Authoriozation each visitor needs a login

## Order driven by club

Alternative flow
When the booking form for an event opens the flow should be:

- Club-id/name is given
- Open the order for the bespoke club_id/club_name
- Show a list of orderable items
- Select a qty for each orderable item
- Press validate and
  -- The app wil ask for the required variances for products with variances
  -- The app will asks for teh requested field names for each unique order line
  -- The app will validate the correct filling of product requirements
  -- The app will calculate the rules defined
- A pdf booking overview can be asked for with all details of the order including status, cost, payment status and validation statement

Pros:
For each club you can make a welcome package with all ordered products (Tickets, shirst etcetera). For some products there is a specfication to which guest it belongs but not for all

Cons:
The distribution of products becomes the responsibility for the club representative (the name of the perdon who chreated the order or his sub)

---

# PresMeet Module Analysis (June 2026)

## Current State

The presmeet module (`frontend/src/modules/presmeet/`) is a **full event booking system** that started as Presidents Meeting-specific but has been partially generalized. It has both presmeet-specific code and generic booking code that should be unified into a single event booking form.

## Frontend Components

| Component                 | Purpose                                                  | PresMeet-specific?                                |
| ------------------------- | -------------------------------------------------------- | ------------------------------------------------- |
| `PresMeetPage.tsx`        | Legacy entry, filters events by `event_type='presmeet'`  | Yes — should be replaced by `EventBookingPage`    |
| `EventBookingPage.tsx`    | Generic entry, reads `eventId` from URL params           | No — already generic                              |
| `BookingWizard.tsx`       | Multi-step booking flow                                  | Partially — uses club concept                     |
| `BookingForm.tsx`         | Product selection per person                             | Partially                                         |
| `ProductConfigurator.tsx` | Renders order_item_fields + variant dropdowns per person | **Uses `variant_schema` (VariantAxis[] format)**  |
| `OnboardingFlow.tsx`      | Club assignment wizard                                   | **Yes — presmeet-only**                           |
| `DelegateManager.tsx`     | Club delegate management                                 | **Yes — presmeet-only**                           |
| `DelegateSection.tsx`     | Delegate UI section                                      | **Yes — presmeet-only**                           |
| `GuestSection.tsx`        | Guest management within club order                       | Partially                                         |
| `ClubLogoUploader.tsx`    | Upload club logos to S3                                  | **Yes — presmeet-only**                           |
| `BookingOverview.tsx`     | Order summary / read-only view                           | Generic                                           |
| `BookingSummaryPdf.tsx`   | PDF generation for booking                               | Generic (references `variant_schema` for display) |
| `PaymentPanel.tsx`        | Mollie payment initiation                                | Generic                                           |
| `PaymentSection.tsx`      | Payment status display                                   | Generic                                           |
| `PersonCard.tsx`          | Person (delegate/guest) card                             | Partially                                         |
| `EffectiveLimits.tsx`     | Purchase rules display                                   | Generic                                           |
| `SubmitPanel.tsx`         | Order submission                                         | Generic                                           |
| `TransferSection.tsx`     | Transfer/hand-over section                               | Partially                                         |
| `EventInfoHeader.tsx`     | Event details header                                     | Generic                                           |
| `ReadOnlyView.tsx`        | Locked order display                                     | Generic                                           |

## Frontend Services & Types

| File                          | Notes                                                                                                  |
| ----------------------------- | ------------------------------------------------------------------------------------------------------ |
| `services/presmeetApi.ts`     | Axios client for all booking endpoints — generic despite the name                                      |
| `types/presmeet.types.ts`     | Defines `VariantAxis`, `Product.variant_schema: VariantAxis[] \| null` — **still uses variant_schema** |
| `types/presmeet.ts`           | Legacy types with `source: "presmeet"` hardcoded                                                       |
| `hooks/usePresMeetBooking.ts` | Booking state hook                                                                                     |
| `hooks/useAutoSave.ts`        | Auto-save draft hook                                                                                   |
| `utils/cartBuilder.ts`        | Cart construction logic                                                                                |
| `utils/orderTransformer.ts`   | Order ↔ form data transformation                                                                       |
| `utils/pdfGenerator.ts`       | PDF export                                                                                             |
| `utils/priceCalculator.ts`    | Price calculation                                                                                      |
| `utils/validation.ts`         | Form validation                                                                                        |

## Backend — PresMeet-Specific Handlers

| Handler                    | Purpose                                              | Specific? |
| -------------------------- | ---------------------------------------------------- | --------- |
| `assign_club/app.py`       | POST /presmeet/clubs/assign — assigns club to member | **Yes**   |
| `get_club_registry/app.py` | Reads `presmeet/club_registry.json` from S3          | **Yes**   |
| `upload_club_logo/app.py`  | Uploads to `assets/presmeet/logos/{club_id}.png`     | **Yes**   |

## Backend — Shared Handlers with PresMeet Gates

These handlers serve both webshop and event orders but have `Regio_Pressmeet` role checks:

| Handler                     | PresMeet-specific code                                                      |
| --------------------------- | --------------------------------------------------------------------------- |
| `admin_lock_orders/app.py`  | Checks `Regio_Pressmeet` for access                                         |
| `admin_unlock_order/app.py` | Checks `Regio_Pressmeet` for access                                         |
| `get_products/app.py`       | Checks `Regio_Pressmeet` in access control                                  |
| `update_order_items/app.py` | Checks `Regio_Pressmeet` in access control                                  |
| `pay_order/app.py`          | Checks `Regio_Pressmeet` in access control                                  |
| `create_order/app.py`       | Checks `Regio_Pressmeet` in access control                                  |
| `mollie_webhook/app.py`     | Has `_handle_presmeet_payment()` — separate payment flow via Payments table |

## Backend — Shared Auth Layer

- `shared/event_access.py` — contains `has_presmeet_access()`, `is_presmeet_admin()`, `get_club_id()`

## Variant Schema in PresMeet

The presmeet module uses a **different variant_schema format** than the admin/webshop system:

```typescript
// PresMeet format (still in use):
interface VariantAxis { name: string; values: string[] }
Product.variant_schema: VariantAxis[] | null
// Example: [{name: "Size", values: ["S","M","L"]}, {name: "Gender", values: ["Male","Female"]}]

// Admin/webshop format (REMOVED):
type VariantSchema = Record<string, string[]>
// Example: {"Maat": ["S","M","L"], "Kleur": ["Rood","Blauw"]}
```

The `ProductConfigurator.tsx` renders a `<Select>` dropdown per axis from `product.variant_schema`. This should eventually be unified to use variant records + `deriveAxesFromVariants()` like the webshop now does.

## S3 Paths (PresMeet-specific)

- `s3://h-dcn-reports/presmeet/club_registry.json` — club registry data
- `s3://h-dcn-frontend-506221081911/assets/presmeet/logos/{club_id}.png` — club logos

## Routing

```
/presmeet                    → PresMeetPage (legacy, auto-detects first open presmeet event)
/events/:eventId/booking     → EventBookingPage (generic, reads event_id from URL)
```

Dashboard shows event cards for all open events → navigates to `/events/{id}/booking`.

## Key Decisions for Unification

1. **Replace `PresMeetPage`** — The `/presmeet` route can redirect to `/events/{first-open-presmeet-event}/booking`
2. **Club concept** — Decide if clubs are presmeet-only or a generic event feature (organizer groups?)
3. **Delegates** — Presmeet-specific or generic "attendee management"?
4. **variant_schema on products** — Replace with variant records + `deriveAxesFromVariants()` in ProductConfigurator
5. **`Regio_Pressmeet` role** — Replace with generic `event_participant` + `allowed_events` on member record
6. **Payment flow** — Mollie webhook has two paths (Payments table vs Orders table) — should be unified
7. **Rename module** — `modules/presmeet/` → `modules/event-booking/` (or keep as-is with clear separation)

## Scripts (reference)

- `backend/scripts/seed_presmeet_2027.py` — seeds PM2027 event + 4 products
- `scripts/upload_club_registry.py` — uploads club registry JSON to S3
- `scripts/upload_logos.py` — uploads club logos to S3
