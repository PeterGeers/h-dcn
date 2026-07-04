# Webshop Order Fulfilment — Design

## 1. Order Data Model (uitgebreid)

### Nieuwe velden op Orders table

| Veld               | Type         | Gezet door             | Wanneer                              |
| ------------------ | ------------ | ---------------------- | ------------------------------------ |
| `customer_name`    | String       | Backend (submit_order) | Bij submit                           |
| `customer_email`   | String       | Backend (submit_order) | Bij submit                           |
| `customer_phone`   | String       | Backend (submit_order) | Bij submit (optioneel)               |
| `shipping_address` | Map          | Backend (submit_order) | Bij submit (webshop only)            |
| `pickup_location`  | String       | Backend (submit_order) | Bij submit (event only, uit event)   |
| `delivery_option`  | String       | Frontend → Backend     | Bij submit                           |
| `delivery_cost`    | Number       | Frontend → Backend     | Bij submit (0 voor events)           |
| `tracking_number`  | String       | Admin                  | Bij transitie naar shipped (webshop) |
| `shipping_carrier` | String       | Admin                  | Bij transitie naar shipped (webshop) |
| `shipped_at`       | String (ISO) | Backend                | Auto bij shipped transitie           |
| `picked_up_at`     | String (ISO) | Backend                | Auto bij picked_up transitie (event) |
| `picked_up_by`     | String       | Admin                  | Wie heeft uitgereikt (event)         |

### shipping_address Map structuur

```json
{
  "straat": "Dorpsstraat 12",
  "postcode": "1234AB",
  "woonplaats": "Amsterdam",
  "land": "Nederland"
}
```

### Voorbeeld compleet order record (na betaling)

```json
{
  "order_id": "aaf66465-11f7-4026-9935-b97a21443560",
  "order_number": "ORD-2026-0042",
  "source_id": "webshop",
  "status": "paid",
  "payment_status": "paid",
  "member_id": "mem-uuid",
  "user_email": "lid@example.nl",
  "customer_name": "Jan de Vries",
  "customer_email": "lid@example.nl",
  "customer_phone": "06-12345678",
  "shipping_address": {
    "straat": "Dorpsstraat 12",
    "postcode": "1234AB",
    "woonplaats": "Amsterdam",
    "land": "Nederland"
  },
  "delivery_option": "Verzenden (PostNL)",
  "delivery_cost": 6.95,
  "items": [
    {
      "product_id": "prod-001",
      "variant_id": "var-001",
      "name": "H-DCN T-shirt",
      "variant_attributes": { "Maat": "L", "Kleur": "Zwart" },
      "quantity": 2,
      "unit_price": 25.0,
      "line_total": 50.0
    }
  ],
  "total_amount": 56.95,
  "total_paid": 56.95,
  "version": 3,
  "created_at": "2026-07-01T10:00:00Z",
  "submitted_at": "2026-07-01T10:05:00Z",
  "status_history": [
    {
      "from": "draft",
      "to": "submitted",
      "at": "2026-07-01T10:05:00Z",
      "by": "lid@example.nl",
      "source": "customer"
    },
    {
      "from": "submitted",
      "to": "paid",
      "at": "2026-07-01T10:06:30Z",
      "by": "system",
      "source": "mollie_webhook"
    }
  ]
}
```

---

## 2. Status State Machine

### Webshop Flow (verzending)

```
draft → submitted → paid → order_received → picked → packed → shipped → delivered → completed
                      ↓                                                       ↓
               payment_failed                                         return_requested → return_received → completed
                      ↓
               (retry → submitted)
```

### Event Flow (afhalen op locatie)

```
draft → submitted → locked → paid → ready_for_pickup → picked_up → completed
```

### Welke flow geldt?

- `source_id === 'webshop'` → Webshop flow
- `source_id !== 'webshop'` (event UUID) → Event flow

### Transitie-tabel (backend validatie)

```python
VALID_TRANSITIONS = {
    # Shared
    'draft': ['submitted'],
    'submitted': ['paid', 'payment_failed', 'locked'],  # locked = event flow
    'payment_failed': ['submitted'],

    # Webshop fulfilment
    'paid': ['order_received', 'ready_for_pickup'],  # ready_for_pickup = event flow
    'order_received': ['picked'],
    'picked': ['packed'],
    'packed': ['shipped'],
    'shipped': ['delivered'],
    'delivered': ['completed', 'return_requested'],
    'return_requested': ['return_received'],
    'return_received': ['completed'],

    # Event fulfilment (afhalen op locatie)
    'locked': ['paid'],  # event: locked → paid via Mollie/admin
    'ready_for_pickup': ['picked_up'],
    'picked_up': ['completed'],
}

# Wie mag de transitie uitvoeren
TRANSITION_ACTORS = {
    ('draft', 'submitted'): ['customer', 'admin'],
    ('submitted', 'paid'): ['system'],  # Mollie webhook / admin_record_payment
    ('submitted', 'payment_failed'): ['system'],
    ('submitted', 'locked'): ['admin'],  # Event flow
    ('locked', 'paid'): ['system'],
    ('payment_failed', 'submitted'): ['customer'],

    # Webshop
    ('paid', 'order_received'): ['admin'],
    ('order_received', 'picked'): ['admin'],
    ('picked', 'packed'): ['admin'],
    ('packed', 'shipped'): ['admin'],  # Vereist tracking_number
    ('shipped', 'delivered'): ['admin'],
    ('delivered', 'completed'): ['admin'],
    ('delivered', 'return_requested'): ['admin', 'customer'],
    ('return_requested', 'return_received'): ['admin'],
    ('return_received', 'completed'): ['admin'],

    # Event (afhalen)
    ('paid', 'ready_for_pickup'): ['admin'],
    ('ready_for_pickup', 'picked_up'): ['admin'],
    ('picked_up', 'completed'): ['admin'],
}
```

### Context-aware "Next Status"

De frontend bepaalt op basis van `source_id` welke flow geldt:

- `source_id === 'webshop'` → webshop flow (shipped, delivered, etc.)
- `source_id !== 'webshop'` → event flow (ready_for_pickup, picked_up)

---

## 3. Backend Wijzigingen

### 3.1 submit_order handler uitbreiding

Na succesvolle validatie en vóór status update:

1. Fetch member record (already done for member_id)
2. Kopieer `customer_name`, `customer_email`, `customer_phone` uit member
3. Kopieer `shipping_address` uit member (straat, postcode, woonplaats, land)
4. Lees `delivery_option` en `delivery_cost` uit request body
5. Herbereken `total_amount` = sum(line_totals) + delivery_cost
6. Sla alles op als onderdeel van de submit update

### 3.2 update_order_status handler herschrijven

Huidige staat: generieke field updater zonder validatie.
Nieuwe staat: strict status machine.

```python
def lambda_handler(event, context):
    # Auth check (admin only voor fulfilment transities)
    # Parse target_status uit body
    # Fetch order
    # Validate transitie: current_status → target_status in VALID_TRANSITIONS
    # Validate actor: is de gebruiker bevoegd voor deze transitie
    # Validate precondities (shipped vereist tracking_number)
    # Execute: update status + append status_history + set timestamps
    # Return updated order
```

### 3.3 Mollie webhook fix

In `_handle_presmeet_payment` (nu unified flow):

- Bij `paid`: set `total_paid = amount`, `payment_status = 'paid'`, `status = 'paid'`
- Bij `failed`/`expired`: set `payment_status = 'payment_failed'`

### 3.4 Nieuwe endpoint: batch status update

`POST /admin/orders/batch-status`

```json
{
  "order_ids": ["uuid1", "uuid2"],
  "target_status": "picked"
}
```

Valideert elke order individueel, retourneert success/failure per order.

---

## 4. Frontend Wijzigingen

### 4.1 CheckoutModal → submit_order request body uitbreiden

```typescript
// Stap 1: submitOrder met delivery info
const submitResponse = await orderService.submitOrder(activeOrderId, {
  delivery_option: selectedDelivery,
  delivery_cost: deliveryCost,
});
```

### 4.2 OrdersTab kolom "Klant/Club"

Toon `order.customer_name` in de tabel. Fallback naar `order.user_email` als customer_name ontbreekt.

### 4.3 PaymentsTab verbeteringen

- Toon `total_paid` ipv hardcoded 0
- Klikbare order_id → opent OrderDetailDrawer
- Toon `customer_name` in klant-kolom

### 4.4 OrderDetailDrawer uitbreiden

Nieuwe secties:

- **Klant & Verzending** (customer_name, email, phone, shipping_address)
- **Verzendinfo** (tracking_number input, carrier select, shipped_at)
- **Documenten** (download knoppen: orderbevestiging, pakbon, label)

### 4.5 Fulfilment workflow knoppen

Per status specifieke acties:

- `paid` → "Markeer als ontvangen" knop
- `order_received` → "Markeer als gepickt" knop
- `picked` → "Markeer als ingepakt" knop
- `packed` → "Verzenden" knop (opent tracking_number input)
- `shipped` → "Markeer als bezorgd" knop

---

## 5. PDF Documenten

### 5.1 Pakbon (nieuw endpoint: GET /orders/{id}/packing-slip)

Template:

```
┌─────────────────────────────────────────────┐
│ H-DCN PAKBON                    [logo]      │
│                                             │
│ Order: ORD-2026-0042                        │
│ Datum: 01-07-2026                           │
│                                             │
│ Verzendadres:                               │
│ Jan de Vries                                │
│ Dorpsstraat 12                              │
│ 1234AB Amsterdam                            │
│                                             │
│ ┌───┬────────────────────┬────────┬────┐    │
│ │ ☐ │ Product            │ Variant│ Qty│    │
│ ├───┼────────────────────┼────────┼────┤    │
│ │ ☐ │ H-DCN T-shirt      │ L/Zwart│  2 │    │
│ │ ☐ │ H-DCN Pet          │ —      │  1 │    │
│ └───┴────────────────────┴────────┴────┘    │
│                                             │
│ Leveroptie: Verzenden (PostNL)              │
└─────────────────────────────────────────────┘
```

### 5.2 Adressticker (nieuw endpoint: GET /orders/{id}/shipping-label)

Formaat: 10×15cm (standaard verzendlabel)

```
┌──────────────────────────────┐
│                              │
│  Jan de Vries                │
│  Dorpsstraat 12              │
│  1234AB Amsterdam            │
│  Nederland                   │
│                              │
│  Ref: ORD-2026-0042         │
│                              │
└──────────────────────────────┘
```

### 5.3 Batch PDF

`POST /admin/orders/batch-pdf`

```json
{
  "order_ids": ["uuid1", "uuid2"],
  "document_type": "packing_slip" | "shipping_label"
}
```

Retourneert één PDF met alle documenten (één per pagina).

---

## 6. Order Field Registry Update

Nieuwe groep `'shipping'` toevoegen:

```typescript
export const shippingFields: Record<string, OrderFieldDefinition> = {
  customer_name: { key: 'customer_name', label: 'Klantnaam', dataType: 'string', group: 'shipping', ... },
  customer_email: { key: 'customer_email', label: 'E-mail klant', dataType: 'string', group: 'shipping', ... },
  customer_phone: { key: 'customer_phone', label: 'Telefoon klant', dataType: 'string', group: 'shipping', ... },
  shipping_address: { key: 'shipping_address', label: 'Verzendadres', dataType: 'map', group: 'shipping', ... },
  pickup_location: { key: 'pickup_location', label: 'Afhaallocatie', dataType: 'string', group: 'shipping', ... },
  delivery_option: { key: 'delivery_option', label: 'Leveroptie', dataType: 'string', group: 'shipping', ... },
  delivery_cost: { key: 'delivery_cost', label: 'Verzendkosten', dataType: 'number', group: 'shipping', ... },
  tracking_number: { key: 'tracking_number', label: 'Track & Trace', dataType: 'string', group: 'shipping', ... },
  shipping_carrier: { key: 'shipping_carrier', label: 'Vervoerder', dataType: 'enum', group: 'shipping', enumOptions: ['PostNL', 'DHL', 'DPD', 'Anders'], ... },
  shipped_at: { key: 'shipped_at', label: 'Verzonden op', dataType: 'datetime', group: 'shipping', ... },
  picked_up_at: { key: 'picked_up_at', label: 'Afgehaald op', dataType: 'datetime', group: 'shipping', ... },
  picked_up_by: { key: 'picked_up_by', label: 'Uitgereikt door', dataType: 'string', group: 'shipping', ... },
};
```

Status types uitbreiden:

```typescript
export const ALL_ORDER_STATUSES = [
  "draft",
  "submitted",
  "locked",
  "order_received",
  "payment_pending",
  "payment_failed",
  "paid",
  "picked",
  "packed",
  "shipped",
  "delivered",
  "ready_for_pickup",
  "picked_up", // Event fulfilment
  "return_requested",
  "return_received",
  "completed",
] as const;
```

FieldGroup type uitbreiden: `'identity' | 'source' | 'status' | 'financial' | 'items' | 'delegates' | 'metadata' | 'shipping'`

---

## 7. Fasering

### Fase 1: Data & Backend (quick wins)

- source_id fix (done)
- submit_order: customer_name, shipping_address, delivery_cost opslaan
- Mollie webhook: total_paid correct bijwerken
- Field Registry uitbreiden met shipping groep
- Frontend: klant-kolom vullen in OrdersTab/PaymentsTab

### Fase 2: Status Machine & Admin UI

- update_order_status herschrijven met transitie-validatie
- status_history append logica
- OrderDetailDrawer uitbreiden (klant, verzending, documenten)
- Fulfilment workflow knoppen

### Fase 3: PDF Documenten

- Pakbon PDF endpoint
- Adressticker PDF endpoint
- Download knoppen in OrderDetailDrawer
- Batch PDF voor meerdere orders

### Fase 4: Batch Operaties & Polish

- Batch status update endpoint
- Multi-select in OrdersTab
- Filter op status
- Tracking number input bij shipped transitie
