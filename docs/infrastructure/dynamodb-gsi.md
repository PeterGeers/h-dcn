# DynamoDB Global Secondary Indexes

## Orders Table GSIs

### event-club-index

| Property   | Value                                             |
| ---------- | ------------------------------------------------- |
| Table      | Orders                                            |
| GSI Name   | `event-club-index`                                |
| PK         | `event_id` (String)                               |
| SK         | `club_id` (String)                                |
| Projection | ALL                                               |
| Billing    | PAY_PER_REQUEST (on-demand, inherited from table) |
| Region     | eu-west-1                                         |

**Purpose:** Enables efficient queries for event-based order lookups without full table scans.

**Access patterns supported:**

1. **Find order by club + event** — Query with `event_id = X AND club_id = Y`  
   Used by: `presmeet_get_order` handler (check if a club already has an order for an event)

2. **List all orders for an event** — Query with `event_id = X`  
   Used by: `presmeet_submit_order` (capacity validation across all event orders), `presmeet_generate_report` (event reporting)

3. **Count distinct clubs per event** — Query with `event_id = X`, count unique `club_id` values  
   Used by: event constraint validation (`count_distinct_clubs` rule)

**Creation script:** `backend/scripts/create_event_club_gsi.py`

```bash
# Preview changes
python backend/scripts/create_event_club_gsi.py --dry-run

# Create the GSI
python backend/scripts/create_event_club_gsi.py

# Create and wait for ACTIVE status
python backend/scripts/create_event_club_gsi.py --wait

# Check status
python backend/scripts/create_event_club_gsi.py --status
```

**Note:** DynamoDB tables are managed outside CloudFormation. This GSI must be created via the script, not added to the SAM template. See the [AWS DynamoDB steering rules](../../.kiro/steering/aws-dynamodb.md) for context.

---

## Producten Table GSIs

### parent_id-index

| Property   | Value                |
| ---------- | -------------------- |
| Table      | Producten            |
| GSI Name   | `parent_id-index`    |
| PK         | `parent_id` (String) |
| Projection | ALL                  |

**Purpose:** Query variant records by their parent product ID.

**Used by:** Product variant lookups, cart migration scripts.
