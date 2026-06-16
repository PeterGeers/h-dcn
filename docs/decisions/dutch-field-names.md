# Decision: Dutch Field Names in DynamoDB

**Date:** 2026-06-16  
**Status:** Accepted  
**Supersedes:** Previous informal preference for English field names

## Context

DynamoDB tables evolved organically with Dutch field names (Members: `voornaam`, `achternaam`, `regio`; Producten: `naam`, `prijs`, `groep`, `subgroep`). A previous session recommended normalizing to English (`name`, `price`, `group`), which led to scan handlers translating field names, frontend/backend mismatches, and dual-field storage in DynamoDB.

## Decision

**Keep Dutch field names as the canonical standard.** DynamoDB stores Dutch, handlers return Dutch, frontend uses Dutch. No translation layers.

## Why

1. **Existing data is Dutch.** Members table (complete, working) uses Dutch. Producten has mostly Dutch. Migrating to English means touching every record with zero user-facing benefit.
2. **The Members field registry already uses Dutch.** It's the proven, working pattern. Products should follow the same convention.
3. **Translation causes bugs.** The `naam`/`name` and `prijs`/`price` dual-field problem was directly caused by a "normalize to English" approach in scan handlers.
4. **Domain language is Dutch.** The organization is Dutch, the UI labels are Dutch, the business logic uses Dutch terms. Using Dutch keys means fewer mapping layers.

## Rules

- All DynamoDB attribute names use Dutch (matching the existing Members pattern)
- No handler should rename/normalize fields between DynamoDB and API response
- Frontend code uses the same Dutch keys as DynamoDB
- UI labels are handled by i18n (react-i18next), not by field name choice
- Code variables and function names remain in English (standard practice)

## Exceptions

- `product_id`, `member_id`, `event_id`, `order_id` — primary keys stay English (AWS convention for IDs)
- `created_at`, `updated_at` — timestamps stay English (universal convention)
- `active`, `status` — state fields stay English (already established)
