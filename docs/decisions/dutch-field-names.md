# Decision: Dutch Field Names in DynamoDB

**Date:** 2026-06-16  
**Amended:** 2026-09-12 (clarified that the `status` attribute *name* is English but its *values* are Dutch)  
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

## Exceptions (attribute *names* that stay English)

These are about the DynamoDB **key names**, not the values they hold:

- `product_id`, `member_id`, `event_id`, `order_id` — primary keys stay English (AWS convention for IDs)
- `created_at`, `updated_at` — timestamps stay English (universal convention)
- `active` — boolean state field; the attribute name is English and its values are `true`/`false`
- `status` — the attribute **name** is English, but its **values are Dutch** (see below)

## Clarification: `status` values are Dutch (amended 2026-09-12)

The earlier wording ("`active`, `status` — state fields stay English") was
misleading for `status`. The `status` **attribute name** is English, but the
**values stored in it are Dutch** and come from the member field registry enum:

`Actief`, `Opgezegd`, `wachtRegio`, `wachtBetaling`, `Aangemeld`, `Geschorst`,
`HdcnAccount`, `Club`, `Sponsor`, `Overig`.

Verified against production (Members table, 1229 records): `Actief` (1097),
`HdcnAccount` (62), `Sponsor` (52), `Club` (18) — and **zero** `active`/`approved`
records. Handlers and tests MUST compare against the Dutch values (e.g.
`status == 'Actief'`), never English strings like `'active'` or `'approved'`.
This applies to the `cognito_post_authentication` role-assignment logic and any
membership status checks.

The field registry (`frontend/src/config/memberFields/`) is the source of truth
for the allowed status values.
