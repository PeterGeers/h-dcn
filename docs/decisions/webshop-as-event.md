# Decision: Webshop Is an Event

**Date:** 2026-06-16  
**Status:** Accepted  
**Affects:** Producten table, Events table, webshop filtering logic

## Context

Products currently use two fields to control visibility:

- `event_id` (string) — links product to exactly one event
- `nietInWinkel` (boolean) — hides product from the general webshop

This creates awkward logic: "show product if `nietInWinkel` is false OR if `event_id` matches the current event." It also prevents a product from being sold in multiple events simultaneously.

## Decision

**Treat the webshop as a permanent event.** Replace `event_id` and `nietInWinkel` with a single field:

```
event_ids: list of strings
```

- A product with `event_ids: ["evt-webshop"]` appears in the general webshop
- A product with `event_ids: ["evt-pm2027"]` appears only in the PM2027 event shop
- A product with `event_ids: ["evt-webshop", "evt-pm2027"]` appears in both
- A product with `event_ids: []` or missing field is a draft (not shown anywhere)

The webshop is represented as a permanent event record in the Events table (e.g. `event_id: "evt-webshop"`, no end date).

## Migration

- If `nietInWinkel` is false and no `event_id` → `event_ids: ["evt-webshop"]`
- If `event_id` is set → `event_ids: [event_id]`
- If `nietInWinkel` is true and `event_id` is set → `event_ids: [event_id]`
- If `nietInWinkel` is true and no `event_id` → `event_ids: []`

## Benefits

- One field, one concept, no special boolean logic
- Products can be in multiple events simultaneously
- Filtering is uniform: "products for event X" works the same for webshop or any event
- Removes the confusing `nietInWinkel` double-negative naming
