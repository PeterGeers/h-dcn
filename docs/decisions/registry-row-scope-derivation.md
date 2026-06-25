# Decision: Registry Row Scope Derivation (replacing order_scope field)

**Date:** 2026-06  
**Status:** Accepted  
**Context:** Generic Registry Row Refactor spec

## Context

The event booking system originally stored an explicit `order_scope` field on Event records to determine whether orders are scoped per member or per registration unit (club). This required manual configuration and introduced a redundant data point — the presence of `registry_config` on an event already implies row-scoped ordering.

Additionally, the entire codebase used `club_*` naming (fields, variables, components, translations) because the first use case was motorcycle clubs. This made the system unusable for other scenarios: schools, teams, families, or any other registration unit.

## Decision

### 1. Remove `order_scope` field — derive scope from `registry_config`

Instead of reading an explicit `order_scope` field, the system derives order scope at runtime:

```python
def _resolve_order_scope(event_record: dict) -> str:
    if event_record.get('registry_config'):
        return 'registry_row'  # one order per registry row
    return 'member'            # one order per member
```

The `order_scope` field is removed from Event records by the migration script.

### 2. Rename `club_*` to `registry_row_*` across the stack

All field names, function names, component names, and translation keys that reference "club" are renamed to use `registry_row`:

| Layer                                | Old                            | New                                                        |
| ------------------------------------ | ------------------------------ | ---------------------------------------------------------- |
| DynamoDB (Orders, Members, Payments) | `club_id`                      | `registry_row_id`                                          |
| DynamoDB (Orders)                    | —                              | `registry_row_label`, `registry_row_logo_url` (new fields) |
| DynamoDB (Producten)                 | `max_per_club`, `min_per_club` | `max_per_order`, `min_per_order`                           |
| DynamoDB (Events)                    | `order_scope`                  | _(removed)_                                                |
| Backend shared layer                 | `get_club_id()`                | `get_registry_row_id()`                                    |
| Backend handlers                     | `club_id` variables            | `registry_row_id` / `row_id`                               |
| Frontend types                       | `Order.club_id`                | `Order.registry_row_id`                                    |
| Frontend components                  | `ClubLogoUploader`             | `RegistryRowLogo`                                          |
| Translations                         | hardcoded "club"               | `{{rowLabel}}` interpolation                               |
| PDF generation                       | `club-name`, `club-logo` CSS   | `row-name`, `row-logo` CSS                                 |

## Why

1. **Single source of truth for scope.** The `registry_config` field already defines everything needed for row-scoped events (S3 path, row label, claim mode, max delegates). A separate `order_scope` field is redundant and can drift out of sync.

2. **Multi-tenant by design.** Generic naming (`registry_row_*`) enables the same system to serve clubs, teams, schools, families, or any registration unit — without code changes. The `row_label` from `registry_config` (e.g. "club", "team", "school") drives all user-facing text via i18n interpolation.

3. **No dual-field patterns.** The project's schema-driven rules (see `steering/schema-driven.md`) prohibit storing the same data under two names. Renaming in a single migration pass avoids compatibility code.

4. **Reduced cognitive load.** Developers no longer need to understand that "club" is a special case of a generic concept — the naming makes the abstraction explicit.

## Consequences

- **Migration required.** All existing records in Orders, Members, Payments, Producten, and Events must be migrated before deploying new code. Migration is idempotent with `--dry-run` support.
- **No backward compatibility code.** After migration, handlers use only new field names. No fallback reads of `club_id`.
- **Translation interpolation.** All `eventBooking` namespace translations use `{{rowLabel}}` instead of hardcoded "club". The value is resolved from `event.registry_config.row_label` at runtime.
- **S3 resolution at order creation.** Label and logo are resolved from S3 (not stored on the Member) and copied to the Order. This avoids stale data if the registry is updated.
- **Old endpoints removed.** `/presmeet/clubs`, `/presmeet/clubs/assign`, `/presmeet/logo` are replaced by the generic `/events/{event_id}/registry-logo` endpoint.

## When to reconsider

- If a third scope type emerges that cannot be derived from existing event configuration fields
- If performance requirements change and scope derivation needs to be cached/precomputed rather than derived per request
