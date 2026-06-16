# Decision: Orders Table Replaces Separate Carts Table

**Date:** 2026-06  
**Status:** Accepted  
**Supersedes:** Previous decision to use Carts table (early 2026)

## Context

The webshop initially used a separate `Carts` DynamoDB table to hold items before checkout. This was recommended as a cleaner separation between "shopping" and "purchased" states.

## Decision

Use a single `Orders` table with a `status` field to represent the full lifecycle:

- `cart` → items being collected (replaces Carts table)
- `pending` → checkout initiated, awaiting payment
- `paid` → payment confirmed
- `fulfilled` → order delivered/completed
- `cancelled` → order cancelled

## Why

1. **Simpler data model.** One table, one set of handlers, one schema. No need to "move" data from Carts to Orders at checkout — just update the status field.
2. **Fewer failure modes.** The cart→order transition was a multi-step process (copy to Orders, delete from Carts) that could fail midway, leaving orphaned records.
3. **Consistent querying.** Admins can see the full order lifecycle in one place. No need to query two tables to understand a customer's state.
4. **Fewer DynamoDB tables to manage.** Reduces operational overhead, IAM policies, and SAM template complexity.

## What this means

- The `Carts` table is **deprecated**. Do not write new code that reads from or writes to it.
- Existing cart data should be migrated to Orders with `status: 'cart'` (or left to expire).
- The `Carts` table remains in the SAM template for now (referencing existing data) but will be removed once migration is confirmed complete.
- Frontend cart logic should use the Orders API with status filtering, not a separate cart API.

## When to reconsider

- If order table scan performance degrades significantly due to volume of abandoned carts
- If a clear domain boundary emerges between "browsing intent" and "purchase intent" that requires different access patterns or TTL behavior
