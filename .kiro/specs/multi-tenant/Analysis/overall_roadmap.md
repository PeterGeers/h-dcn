# Overall Roadmap — Independently Executable Steps

> Top-level breakdown for evolving the two current systems (H-DCN portal +
> myAdmin) toward a unified multi-tenant solution. This is the **index**: each
> step below is a self-contained workstream that can be executed and shipped on
> its own, applied to the live/bespoke solution as it stands at that moment. The
> existing `migration_plan.md` (AWS account move) is just **one** of these steps.
>
> Companion to the other Analysis docs. This is a plan/outline — no code or
> infrastructure changed.

## Design principle for every step

Each step must be:

- **Independently valuable** — worth doing even if the project paused right after.
- **Independently shippable** — leaves both live systems working; no half-broken
  intermediate state.
- **Reversible or low-risk** — or, where irreversible (data moves), gated by
  copy-verify-keep-old.
- **Loosely coupled** — depends only on its stated prerequisites, nothing else.

Steps are ordered by dependency and risk, but several can run in parallel (noted).

## Keeping governance current (cross-cutting rule)

Governance — steering, architecture docs, and ADRs — describes the system, and
the system changes at almost every step. If governance goes stale, Kiro steers by
rules that no longer match reality, which is worse than no steering because it is
confidently wrong. So governance is **not** a one-time S1b task that is then
frozen, and it is **not** a periodic "return to S1" sweep. Instead:

**Definition-of-done clause (applies to every step):**

> A step is not complete until any steering, architecture docs, and ADRs it
> invalidates or introduces have been updated to match — governance must reflect
> the system *as it now is*, not the plan.

**Rules:**

- **Fold the update into the step that causes the change** — the person finishing
  the step has the fresh knowledge; do not defer to a later batch pass.
- **Update at step completion, not mid-flight** — the system is temporarily
  in-between during implementation; refresh governance when the new state is
  stable and shippable, not on every intermediate commit.
- **ADRs are append-only** — record one ADR per material decision; supersede old
  ADRs, never rewrite them. ADRs are the durable decision log; steering is the
  active-rules layer that must track current truth.

**Per-step governance delta (which steps change the model):**

| Step | Governance to update on completion |
| --- | --- |
| S1a | (none — pure layout) |
| S1b | Baseline: steering scoping, initial ADRs |
| S2 | Auth steering — signature-verified tokens, no trusting unverified headers; ADR |
| S3 | Auth/tenant steering — the claim contract; survivor-pool ADR |
| S4 | Architecture steering — entitlement projected into token, not read from MySQL per request; ADR |
| S5 | Schema-driven + DynamoDB steering — `tenant_id` key, isolation, overlay |
| S6 | Infra steering — nonprofit account, bucket separation incl. myAdmin's bucket; update `migration_plan.md` status |
| S7 | `tech.md` + `testing-frontend.md` (portal) — Vite, `import.meta.env` |
| S8 / S9 | `structure.md` / UI steering — merged layout, routing |
| S10 | Cleanup note; ADR closure |

Roughly every step except S1a and S10 carries a governance delta — which is why it
belongs in each step's definition of done, not in a recurring return to S1.

## Dependency at a glance

```
S1a (workspace layout) ── independent, do anytime
S1b (governance)       ── needs S1a
S2 (JWT verify)        ── independent, do anytime  ─┐
S3 (tenant claims)     ── needs S2                  │
S4 (token projection)  ── needs S3                  ├─ identity track
S5 (H-DCN tenant_id)   ── needs S3 (claims exist)   │
S6 (AWS move)          ── needs survivor-pool decision (from S3 planning)
S7 (H-DCN React19+Vite) ── independent, do anytime ─┐
S8 (shared login+nav)  ── needs S2/S3              ├─ frontend track
S9 (unified SPA)       ── needs S7 + S8            ─┘
S10 (decommission)     ── last, needs S6 stable
```

---

## The steps

### S1a — Unify the workspace (mono-repo layout)
- **What:** bring both projects into one workspace as separate top-level folders
  (e.g. `portal/`, `admin/`, `shared/`, `docs/`). Keep both deploy pipelines
  separate.
- **Why independent:** pure code organization; no runtime change.
- **Risk:** very low, fully reversible.
- **Prereq:** none.
- **Ref:** chat history (workspace merge).

### S1b — Reconcile Kiro governance (steering, hooks, skills, docs/ADRs)
- **Why this is its own step:** steering and hooks are **workspace-scoped by
  default**, so merging two `.kiro` trees naively produces contradictory rules and
  hooks firing on the wrong project. This is low-risk (docs/config, reversible)
  but real content work — decisions must be made file by file.
- **What (steering):** both projects have overlapping-but-different files that
  cannot simply coexist —
  `product.md`, `tech.md`, `structure.md`, `specs.md`, `testing-frontend.md`
  exist in **both** with different content (H-DCN: SAM/Lambda/DynamoDB/CRA;
  myAdmin: Flask/MySQL/Vite). Resolve by splitting into:
  - **Shared, always-included:** truly global rules (git safety, secret scanning,
    WSL path handling).
  - **Per-project, `inclusion: fileMatch`:** domain rules scoped to their subtree
    (`portal/**` vs `admin/**`) so H-DCN's SAM/DynamoDB conventions and myAdmin's
    Flask/MySQL conventions each activate only for their own code.
- **What (hooks):** merge the two hook sets and **path-scope each via its
  `matcher`** — H-DCN `sam-template-review` → `portal/**`, myAdmin
  `migration-safety-check` (MySQL) → `admin/**`, `commerce-lint-on-save` →
  `admin/**`, etc. Deduplicate the `ggshield-pre-commit.json` that exists in both;
  keep secret-scanning global.
- **What (skills):** myAdmin has 4 skills (`commands`, `database`, `pr-checklist`,
  `specs-reference`); H-DCN has none. Decide which generalize (likely
  `pr-checklist`, `specs-reference`) and which stay domain-scoped (`database` is
  MySQL-specific).
- **What (docs):** merge `docs/architecture` and `docs/decisions` from both,
  attributing each doc to its domain, and resolve the `Common/` spec-folder
  collision (both projects have one).
- **What (NEW shared context — important):** author steering + ADRs that exist in
  **neither** project today but are needed for the merged reality:
  - New steering: the two-service-plane architecture, the tenant-claim contract,
    which datastore owns what (MySQL vs DynamoDB), verified-JWT requirement.
  - New ADRs in `docs/decisions/`: "unified identity pool", "MySQL
    system-of-record + token projection", "two service planes / Railway stays",
    "one workspace, two datastores". These capture the decisions from this whole
    analysis set.
- **Risk:** low, reversible — but without it Kiro is confused (or wrong) in the
  merged workspace, so it is a prerequisite for productive work after S1a.
- **Prereq:** S1a.
- **Ref:** this analysis set; `myadmin_as_base.md` for the architecture decisions
  to turn into ADRs.

### S2 — Verify JWT signatures on both backends
- **What:** verify tokens against the Cognito pool JWKS on H-DCN
  (`auth_utils.py` currently only base64-decodes) and confirm myAdmin's existing
  `jwt_verifier.py` is applied everywhere. Stop trusting unverified headers
  (`X-Enhanced-Groups`, `X-Tenant`) as the source of truth.
- **Why independent:** a security hardening that improves each system as-is,
  before any multi-tenant work.
- **Risk:** medium (auth path) but scoped; testable per handler.
- **Prereq:** none. **This is the non-negotiable foundation.**
- **Ref:** `myadmin_as_base.md` (auth prerequisite), `first_thoughts.md` §1.

### S3 — Define + populate the shared tenant/role claims
- **What:** decide the survivor Cognito pool; standardize the claim shape
  (`cognito:groups` for roles, `custom:tenants` for tenant access); ensure both
  systems read them identically.
- **Why independent:** establishes the identity contract; each system can adopt
  the claims without the other changing.
- **Risk:** medium; mostly config + provisioning.
- **Prereq:** S2 (verify before trusting claims). Also fixes the survivor-pool
  decision that `migration_plan.md` Gate 1 needs.
- **Ref:** `myadmin_as_base.md` (identity plane, balance section).

### S4 — Project resolved entitlement into the token (Pre-Token-Generation trigger)
- **What:** a Cognito Pre-Token-Generation Lambda that computes each user's
  resolved tenants + effective modules from MySQL once at login and stamps them
  as claims — so the request path never queries MySQL for entitlement.
- **Why independent:** improves both planes' authorization without changing
  business logic; can ship after claims exist.
- **Risk:** medium; one Lambda + a token-lifetime/revocation decision.
- **Prereq:** S3.
- **Ref:** `myadmin_as_base.md` ("The fix: system of record + projection").

### S5 — Add the tenant dimension to the H-DCN (portal) data
- **What:** add `tenant_id` partition key to H-DCN DynamoDB tables, key + IAM
  `LeadingKeys` isolation, and the tenant-field overlay. Migrate existing H-DCN
  data to carry its own `tenant_id` (dry-run first).
- **Why independent:** makes the portal tenant-aware; H-DCN keeps working as a
  single-tenant instance of the new model.
- **Risk:** medium-high (data migration) — gated by dry-run + backup.
- **Prereq:** S3 (claims exist to scope against).
- **Ref:** `tenant_field_config.md`, `rewrite_vs_refactor.md` (DynamoDB tenancy).

### S6 — Move myAdmin's AWS footprint to the nonprofit account
- **What:** the existing detailed plan — recreate SNS/S3/DynamoDB in nonprofit,
  copy data, handle Cognito, repoint Railway `.env`. Railway/MySQL stay put.
- **Why independent:** infra relocation; once repointed, myAdmin runs unchanged
  from nonprofit resources.
- **Risk:** high (production data + Cognito users) — its own gated plan.
- **Prereq:** survivor-pool decision from S3.
- **Ref:** `migration_plan.md` (this is that whole document, as one step here).

### S7 — Upgrade H-DCN frontend to React 19 + Vite
- **What:** upgrade H-DCN from React 18/CRA to React 19 + Vite to match myAdmin;
  map `process.env.REACT_APP_*` → `import.meta.env` with fail-fast checks.
- **Why independent:** modernizes H-DCN's tooling; valuable on its own and the
  pivotal enabler for a single-SPA merge.
- **Risk:** medium; regression-test the H-DCN UI (Chakra v2 runs on React 19).
- **Prereq:** none (can run in parallel with the identity/AWS tracks).
- **Ref:** `frontend_merge.md`.

### S8 — Shared login + shared top navigation (two SPAs, one product feel)
- **What:** both SPAs use the one Cognito pool/token; add a shared top nav so
  crossing domains feels like one product.
- **Why independent:** delivers most of the "one product" experience cheaply,
  without merging code.
- **Risk:** low.
- **Prereq:** S2/S3 (shared verified identity).
- **Ref:** `frontend_merge.md` (Option 3).

### S9 — Merge into one unified SPA
- **What:** combine both frontends into a single React 19 + Vite + Chakra v2 app
  with routing between domains; shared theme/components.
- **Why independent:** the final frontend consolidation; optional if S8 is
  "good enough."
- **Risk:** medium; mostly routing + folder integration once S7 is done.
- **Prereq:** S7 (H-DCN on React 19 + Vite) + S8 (shared identity/nav proven).
- **Ref:** `frontend_merge.md` (Option 1).

### S10 — Decommission the old AWS account resources
- **What:** after a stable soak, tear down the old account's bucket/topic/tables/
  pool. Final backup first.
- **Why independent / last:** the only truly irreversible cleanup.
- **Risk:** high but controlled; only after everything proven.
- **Prereq:** S6 stable in production.
- **Ref:** `migration_plan.md` Phase 6.

---

## Parallel tracks (what can run at once)

- **Identity track:** S2 → S3 → S4 (and S5 after S3).
- **Frontend track:** S7 and S8 can proceed alongside the identity track; S9 after
  both.
- **Infra track:** S6 after the S3 survivor-pool decision; S10 last.
- **S1a/S1b** can happen at any time and make the rest easier; S1b is what keeps
  Kiro coherent in the merged workspace.

## Suggested first moves

1. **S1a** (workspace layout) — free, clarifying.
2. **S1b** (governance reconciliation) — so Kiro's steering/hooks are correct in
   the merged workspace before real work starts; also the place to record the
   architecture decisions from this analysis as ADRs.
3. **S2** (JWT verification) — the security foundation everything else assumes.
4. **S3 survivor-pool decision** — unblocks both S6 (AWS move) and the rest of the
   identity track.

Everything else sequences off those. Each step, when reached, should get its own
requirements/design spec under `.kiro/specs/multi-tenant/` before execution — this
roadmap is the index that ties them together.

## Note on scope

This roadmap deliberately keeps the two datastores separate (MySQL for finance,
DynamoDB for the portal) and Railway in place. "One system" here means one
identity, one workspace, one AWS account, and (optionally) one SPA — **not** one
database. See `rewrite_vs_refactor.md` and `myadmin_as_base.md` for that rationale.
