# Data Migrations

Tracking which migration scripts need to run when deploying features to production.

## How to Use

1. Before merging a feature branch to `main`, check if it has entries here
2. Run migrations in listed order (top to bottom)
3. Always run with `--dry-run` first
4. After confirmed successful run, mark as completed with date

## Convention

- All migrations support `--dry-run` and `--profile nonprofit-deploy`
- Migrations are idempotent (safe to re-run)
- Run against `--stage test` first, then `--stage prod` (if flag is supported)
- After running in production, move the entry to the "Completed" section below

---

## Pending: `feature/closed-community-booking`

These migrations must run **before or during** production deployment of this feature.
Order matters — run top to bottom.

### 1. `migrate_events_to_new_schema.py`

**What:** Normalizes existing event records to the new Field Registry schema (title→name, date→start_date/end_date, status mapping).

```bash
python scripts/migrate_events_to_new_schema.py --dry-run --profile nonprofit-deploy --stage prod
python scripts/migrate_events_to_new_schema.py --profile nonprofit-deploy --stage prod
```

**Run before:** Deploying updated event handlers (create_event, update_event, get_events).

---

### 2. `migrate_image_urls_to_nonprofit_bucket.py`

**What:** Updates product image URLs from old S3 bucket (`my-hdcn-bucket`) to nonprofit bucket (`h-dcn-data-506221081911`).

```bash
python scripts/migrate_image_urls_to_nonprofit_bucket.py --dry-run --profile nonprofit-deploy
python scripts/migrate_image_urls_to_nonprofit_bucket.py --profile nonprofit-deploy
```

**Run before:** Any code that serves images from the new bucket URL.

---

### 3. `migrate_club_to_registry_row.py`

**What:** Replaces `club_id` with `registry_row_id` across Orders, Members, Payments, Producten, and Events. Resolves label/logo from S3 registry file.

```bash
python scripts/migrate_club_to_registry_row.py --dry-run --stage prod
python scripts/migrate_club_to_registry_row.py --stage prod
python scripts/migrate_club_to_registry_row.py --stage prod --validate
```

**Run before:** Deploying the event booking flow (handlers reference `registry_row_id`).

---

### 4. `migrate_remove_event_id_from_products.py`

**What:** Removes deprecated `event_id` and `event_ids` fields from all products in Producten table (event.product_ids is now sole source of truth).

```bash
python scripts/migrate_remove_event_id_from_products.py --dry-run --profile nonprofit-deploy
python scripts/migrate_remove_event_id_from_products.py --profile nonprofit-deploy
```

**Run after:** Deploying updated `get_products` handler (no longer reads event_id from products).

---

### 5. `migrate_create_default_variants.py`

**What:** Creates Default_Variant records for old products that have zero variants. Ensures all products have at least one variant (stock tracked at variant level only).

```bash
python scripts/migrate_create_default_variants.py --dry-run --profile nonprofit-deploy
python scripts/migrate_create_default_variants.py --profile nonprofit-deploy
```

**Run anytime:** No handler dependency — purely a data consistency fix. Idempotent.

---

## Completed

<!-- Move entries here after running in production, with the date -->
<!-- Example:
### ~~migrate_example.py~~ — completed 2026-06-15
-->
