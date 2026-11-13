# Migration Plan — Move myAdmin's AWS Footprint to the Nonprofit Account

> Scope: bring the AWS-resident parts of **myAdmin** into the H-DCN **nonprofit
> account (506221081911, eu-west-1)**. The **Railway backend (Flask) and its
> MySQL database stay exactly where they are** — only its AWS resources move and
> its config is repointed. Companion to `myadmin_as_base.md`. This is a plan, not
> an execution; no infrastructure has been changed.

## Guiding rules (from the H-DCN guardrails)

- Never put the Cognito pool, DynamoDB tables, or S3 **data** bucket under
  CloudFormation without `DeletionPolicy: Retain` — a prior deploy deleted prod
  data this way.
- Never use `--delete` or `rm --recursive` against a data bucket. Back up before
  any data move.
- Every data move is **copy → verify → cut over → keep old until proven →
  decommission**. Never move-in-place.
- Use the `nonprofit-deploy` profile for automated ops in 506221081911.

## Scope: what actually has to move (verified)

myAdmin's AWS footprint is small and entirely env-var driven (no hardcoded
account IDs in code — values live in `.env`):

| Service | What | Difficulty |
| --- | --- | --- |
| **Cognito** | User pool + app client | **Hard** — users/passwords/passkeys do not move easily |
| **S3** | One shared bucket (`S3_SHARED_BUCKET`) — invoices, branding, templates | Medium — real tenant data, copy carefully |
| **DynamoDB** | Landing pages, tenant slugs, media assets (small tables) | Medium — copy or recreate + migrate |
| **SNS** | One topic (`myadmin-notifications`) | Trivial — recreate |
| Region | Already `eu-west-1` | None — same region, no cross-region work |

Two facts that make this easier:
- **All AWS resources are `.env`-driven** (`COGNITO_USER_POOL_ID`,
  `COGNITO_CLIENT_ID/SECRET`, `SNS_TOPIC_ARN`, `S3_SHARED_BUCKET`, `AWS_REGION`).
  Repointing Railway is mostly a config change, not a code rewrite.
- **myAdmin already verifies JWT signatures** (`backend/src/auth/jwt_verifier.py`
  checks issuer + app client ID) — it is already closer to the verified-token
  ideal than H-DCN.

## The one hard part: Cognito

Everything except Cognito is "create in nonprofit, copy data, flip the env var."
Cognito is different:

- User pools cannot be exported with passwords (hashes do not come out).
- Passkeys/WebAuthn are bound to the pool (RP ID + pool) and do not transfer.

Two routes:

- **Route 1 — one survivor pool = the H-DCN nonprofit pool** (the unified-identity
  direction from `myadmin_as_base.md`). Add myAdmin's users/groups/`custom:tenants`
  to it. Because passwords/passkeys cannot migrate, myAdmin users likely need a
  **reset or re-registration** flow. Strategic payoff: "one identity."
- **Route 2 — recreate myAdmin's pool separately in nonprofit.** Simpler to reason
  about, but does NOT deliver "one identity" — loses the main point.

**Recommendation: Route 1**, accepting the user-migration cost. This decision is
Gate 1 below and drives everything else.

---

## Phases and gates

Each gate must be satisfied before the next phase starts. You can stop between any
two phases in a working state.

### Gate 1 — Decide the Cognito survivor + inventory (do first, no infra changes)

- [ ] Confirm exact resource names in myAdmin's **current** account: bucket name,
      SNS topic ARN, and the DynamoDB table names (landing pages, tenant slugs,
      media assets).
- [ ] Count myAdmin users; confirm whether passkeys are in active use (drives the
      difficulty of Route 1).
- [ ] **Decide: Route 1 (survivor = H-DCN nonprofit pool) or Route 2 (new pool).**
- [ ] Decide the user story for Route 1: silent re-provision + password reset, or
      re-registration invite.
- [ ] Confirm/define the Railway→nonprofit access identity (least-privilege IAM
      role/user scoped to just myAdmin's bucket, topic, tables, and pool access).

### Phase 2 — Recreate the easy resources in nonprofit (low risk)

- [ ] **SNS**: create `myadmin-notifications` topic in 506221081911; note new ARN.
- [ ] **S3**: create the shared bucket in nonprofit (versioning on). Do NOT reuse
      the H-DCN data bucket `h-dcn-data-506221081911` — keep myAdmin's bucket
      separate (bucket-separation guardrail).
- [ ] **DynamoDB**: create the myAdmin tables in nonprofit (PAY_PER_REQUEST),
      managed outside CloudFormation or with `DeletionPolicy: Retain`.
- [ ] Verify each resource exists and is reachable with the `nonprofit-deploy`
      profile.

### Phase 3 — Copy the data (copy-verify, keep originals)

- [ ] **S3**: copy bucket contents old→new (`aws s3 cp`/`sync` **without**
      `--delete`). Back up first. Verify object counts and a sample of files.
- [ ] **DynamoDB**: copy items old→new (scan-and-write script, or on-demand
      backup/restore). Verify item counts per table.
- [ ] Keep all originals intact — no deletion in this phase.

### Phase 4 — Cognito (per Gate 1 decision)

If Route 1 (survivor = nonprofit H-DCN pool):
- [ ] Provision myAdmin users into the nonprofit pool.
- [ ] Recreate myAdmin's groups/roles and set `custom:tenants` per user.
- [ ] Stand up the reset/re-registration path and comms for myAdmin users.
- [ ] (Ties into `myadmin_as_base.md`) confirm the token claims myAdmin needs are
      present in this pool.

If Route 2 (new separate pool):
- [ ] Create the pool + app client in nonprofit; recreate groups; migrate users
      with reset flow.

### Phase 5 — Repoint Railway (config only, Railway stays put)

- [ ] Update myAdmin's Railway `.env`:
      `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, `COGNITO_CLIENT_SECRET`,
      `SNS_TOPIC_ARN`, `S3_SHARED_BUCKET`, `AWS_REGION`, and the nonprofit AWS
      credentials/role.
- [ ] Deploy on Railway; run smoke tests: login, an S3 read/write, an SNS send,
      and a DynamoDB-backed feature (landing page / tenant slug / media asset).
- [ ] Verify no code still points at the old account.

### Phase 6 — Soak, then decommission (final, irreversible)

- [ ] Run on nonprofit resources for a defined soak period; watch logs/errors.
- [ ] Only after stable: decommission the old account's bucket/topic/tables/pool.
- [ ] Final backup of old data before deletion.

---

## Risk flags

1. **Cognito user migration is the real project risk**, not the S3/SNS/DynamoDB
   moves (those are routine). Passwords and passkeys do not migrate — plan the
   user story in Gate 1, and size it against the actual user count and passkey
   usage (not yet verified).
2. **Railway → nonprofit credentials.** Railway uses the old account today. It
   needs a least-privilege identity in nonprofit scoped to only myAdmin's
   resources. Follow H-DCN profile conventions.
3. **The data-bucket guardrail applies to myAdmin's bucket once in nonprofit** —
   no `--delete`, back up before moves.
4. **Keep myAdmin's bucket separate** from `h-dcn-data-506221081911`. Two distinct
   data buckets in one account; never cross them.
5. **This is production data.** Copy-verify-cutover-keep-old for every resource;
   never move-in-place.

## What this plan explicitly does NOT do

- Does not move or change the Railway Flask backend or MySQL — they stay put.
- Does not merge datastores (finance stays MySQL, portal stays DynamoDB).
- Does not merge the two codebases or workspaces (separate concern; see the
  broader path in the chat history).
- Does not implement the unified token/entitlement projection — that is the
  architectural work in `myadmin_as_base.md`, which can proceed independently once
  the Cognito survivor pool exists.

## Suggested first concrete action

Complete **Gate 1** only: inventory the exact resource names + user/passkey counts
in myAdmin's current account, and decide Route 1 vs Route 2. That single decision
unblocks and de-risks the entire rest of the plan.
