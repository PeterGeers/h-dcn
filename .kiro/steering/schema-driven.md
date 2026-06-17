# Schema-Driven Development

## Core Principle

Every DynamoDB table has a **Field Registry** — a single source of truth for field names, types, validation, and permissions. All code (frontend, backend, specs, migrations) MUST reference this registry. Never invent new field names.

## Existing Field Registries

| Table          | Registry Location                          | Status                                                    |
| -------------- | ------------------------------------------ | --------------------------------------------------------- |
| Members        | `frontend/src/config/memberFields/`        | ✅ Complete                                               |
| Producten      | `frontend/src/config/productFields/`       | ✅ TODO                                                   |
| Events         | `frontend/src/config/eventFields/`         | ❌ TODO                                                   |
| Orders         | `frontend/src/config/orderFields/`         | ❌ TODO                                                   |
| StockMovements | `frontend/src/config/stockMovementFields/` | ❌ TODO                                                   |
| Memberships    | `frontend/src/config/membershipFields/`    | ❌ TODO                                                   |
| Payments       | `frontend/src/config/paymentFields/`       | ❌ TODO                                                   |
| Counters       | (no frontend config needed)                | Utility table — atomic counters for order/invoice numbers |

> **Decision (2026-06):** Carts are NOT a separate table. Orders use a `status` field to represent the cart→order lifecycle. The Carts table is deprecated — do not use for new code.

## Rules for ALL Code Generation

### 1. Never create new field names

Before using any field in code, check the Field Registry for that table. If the field doesn't exist in the registry, ASK the user — don't invent one.

### 2. Field names come from DynamoDB, not translations

The field `key` in the registry matches the DynamoDB attribute name exactly. If DynamoDB stores `prijs`, the code uses `prijs` — never normalize to `price` in handlers or API responses.

### 3. No dual-field patterns

Never store the same data under two names (e.g. both `naam` AND `name`). Pick one. The registry is authoritative.

### 4. Validation lives in the registry

Validation rules are defined in the Field Registry, not scattered across Yup schemas, backend handlers, or individual components. Components read validation FROM the registry.

### 5. Backend handlers must respect the registry

- `UPDATABLE_FIELDS` lists must match registry keys exactly
- Scan/query handlers return fields using registry keys (no renaming)
- Validation in handlers references the same rules as the registry

## Field Registry Structure (follow Members pattern)

```
frontend/src/config/{table}Fields/
├── types.ts          # FieldDefinition interface
├── fields/           # Field definitions grouped by domain
│   ├── index.ts      # Re-exports all field groups
│   └── {group}Fields.ts  # e.g. personalFields, productFields
├── index.ts          # Central registry export
├── permissions.ts    # Permission configuration helpers
├── tableConfig.ts    # Table column configurations
└── modalConfig.ts    # Modal/form configurations
```

## When Creating Specs

Every spec that touches a DynamoDB table MUST:

1. Reference the Field Registry in the design doc
2. Use only fields that exist in the registry
3. If new fields are needed, add them to the registry FIRST
4. Include the registry file in spec context (#[[file:...]])

## Migration Path for Existing Data

When DynamoDB has inconsistent field names (some records use `naam`, others `name`):

1. Decide the canonical name (check the registry, or most common in DB)
2. Write a migration script to normalize existing data
3. Update handlers to use only the canonical name
4. Never add "compatibility" code that reads both — fix the data instead

## Architecture Decision Records

Architectural decisions are documented in `docs/decisions/`. Before proposing alternatives to existing patterns, check this folder for prior decisions and rationale. Key decisions:

- `orders-replace-carts.md` — Orders table replaces Carts (status field lifecycle)
- `defer-lambda-edge-og.md` — Lambda@Edge deferred for OG pre-rendering

When making new architectural decisions with the user, document them in `docs/decisions/` following the same format.
