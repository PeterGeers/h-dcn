# Spec Work Guidelines

Rules for all spec-driven work (features and bugfixes) in this project.

## Definition of Done

A spec task is only complete when ALL of the following are satisfied:

1. **Code** — Implementation matches requirements, no dead code left behind
2. **Tests** — Unit tests and property tests pass for changed code
3. **Lint** — `npx eslint` passes on all modified files (CI fails on lint errors)
4. **Type check** — `npx tsc --noEmit` passes (frontend)
5. **Translations** — All user-facing strings use `useTranslation()` with keys in all 8 locales (nl, en, de, fr, es, it, da, sv)
6. **Migration** — If DynamoDB data changed: migration script in `scripts/`, run with `--dry-run` first
7. **Documentation** — ADR in `docs/decisions/` for architectural changes
8. **Commit** — Committed on the current feature branch (never create a new branch unless asked)
9. **Push + Deploy** — Push and trigger both workflows:
   ```bash
   git push
   gh workflow run deploy-backend.yml --ref {branch} -f stage=test
   gh workflow run deploy-frontend.yml --ref {branch} -f stage=test
   ```

## Branch Convention

- Work on the current feature branch (check `git branch` first)
- Never push directly to `main`
- Commit with `--no-verify` (Kiro hook handles secret scanning)

## Dead Code

After removing or refactoring code, always verify:

- No unused imports remain (ESLint `no-unused-vars`)
- No orphaned files (deleted components still imported elsewhere)
- No references to removed fields in types, handlers, or tests
- `grep` for the removed symbol across the codebase (exclude `.kiro/specs/`, `node_modules/`, `.git/`)

## Translations (i18n)

- All user-facing text must use `useTranslation('{namespace}')` — never hardcode Dutch strings
- Namespace per module: `products`, `webshop`, `common`, `auth`, `eventBooking`, `dashboard`, etc.
- Locale files at `frontend/src/locales/{lang}/{namespace}.json`
- **IMPORTANT**: The app loads translations from `frontend/public/locales/` at runtime (HttpBackend). Always update BOTH `src/locales/` AND `public/locales/` when adding translation keys.
- When adding keys: add to ALL 8 languages in one commit

## Migration Scripts

- Place in `scripts/migrate_*.py`
- Always support `--dry-run` flag
- Always support `--profile` flag (default: `nonprofit-deploy`)
- Log what would be changed before making changes
- Handle pagination (DynamoDB scan returns max 1MB per call)
- Skip presmeet-specific data unless the spec explicitly targets presmeet

## Out of Scope (leave alone)

- **PresMeet module** (`frontend/src/modules/presmeet/`) — uses its own types and patterns. Will be unified in a future spec. Do not modify unless the task explicitly targets it.
- **Legacy field names** — do not rename existing DynamoDB attributes. Use the field registry as source of truth.
- **Cognito configuration** — managed outside CloudFormation. Never modify the user pool or app client.

## Commit Messages

Follow conventional commits:

- `feat:` — new feature or capability
- `fix:` — bug fix
- `refactor:` — code change that neither fixes a bug nor adds a feature
- `test:` — adding or updating tests
- `docs:` — documentation only
- `chore:` — maintenance (deps, CI config, scripts)

Keep the subject line under 70 chars. Use the body for details.

## DynamoDB Field Safety (CRITICAL)

DynamoDB fields are often absent, null, undefined, or stored as unexpected types (string vs number). Never use truthy/falsy checks on DynamoDB fields.

### Rules

1. **Boolean fields** (`active`, `is_parent`, `allow_oversell`): ALWAYS compare with strict equality
   - ✅ `item.active === false` / `item.active !== false`
   - ❌ `!item.active` / `if (item.active)`
   - Use helpers: `isActive(item)`, `isDeactivated(item)`, `canHaveVariants(product)`

2. **Numeric fields** (`prijs`, `price`, `stock`): ALWAYS convert before math/formatting
   - ✅ `formatPrice(item.prijs)` or `Number(item.prijs || 0)`
   - ❌ `item.prijs.toFixed(2)`
   - Use helper: `formatPrice()`, `toPrice()`

3. **Utilities first**: Before writing feature code that reads DynamoDB data, check if a helper exists in `frontend/src/utils/`. If not, CREATE IT FIRST.

### Available helpers

| Helper                     | Location                  | Use for                  |
| -------------------------- | ------------------------- | ------------------------ |
| `canHaveVariants(product)` | `utils/productHelpers.ts` | Show variant UI          |
| `isVariantRecord(product)` | `utils/productHelpers.ts` | Filter out child records |
| `isActive(item)`           | `utils/productHelpers.ts` | Active status checks     |
| `isDeactivated(item)`      | `utils/productHelpers.ts` | Inactive filtering       |
| `formatPrice(value)`       | `utils/formatPrice.ts`    | Display €X.XX safely     |
| `formatPriceEuro(value)`   | `utils/formatPrice.ts`    | Alias for formatPrice    |
| `toPrice(value)`           | `utils/formatPrice.ts`    | Convert to number safely |
