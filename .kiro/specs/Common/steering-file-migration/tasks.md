# Implementation Plan: Steering File Migration

## Overview

Migrate three steering files from `.kiro/specs/steering/` to `.kiro/steering/`, create detailed reference documents in `docs/development/`, apply value replacements for outdated infrastructure values, and remove the legacy folder. All tasks involve creating or modifying markdown files — no runtime code.

## Tasks

- [x] 1. Update existing steering files in official location
  - [x] 1.1 Update `.kiro/steering/guardrails.md` with `inclusion: auto` frontmatter and refreshed content
    - Change frontmatter from `inclusion: manual` to `inclusion: auto`
    - Ensure content includes: deployment safety rules, S3 bucket separation, environment variable fail-fast policies, safe deployment script references, "ask before adding unrequested features" rule
    - Use current infrastructure values: code bucket `h-dcn-frontend-506221081911`, data bucket `h-dcn-data-506221081911`, API endpoint `https://44sw408alh.execute-api.eu-west-1.amazonaws.com/prod`
    - Include safe deployment scripts: `scripts/deployment/frontend-build-and-deploy-fast.ps1` and `scripts/deployment/backend-build-and-deploy-fast.ps1`
    - Include rule that critical env vars MUST throw errors when missing, no fallback values
    - Ensure no outdated values remain (`testportal-h-dcn-frontend`, `my-hdcn-bucket`, `i3if973sp5`, `eu-west-1_VtKQHhXGN`)
    - Add relative markdown link to `../../docs/development/guardrails.md`
    - Keep file ≤80 lines total
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 6.1_

  - [x] 1.2 Update `.kiro/steering/look-and-feel.md` with reference link and content verification
    - Ensure frontmatter has `inclusion: manual`
    - Ensure content includes: brand colors (primary `#f56500`, hover `#e55a00`), typography scale, component patterns, icon standards, responsive rules
    - Ensure Chakra UI theme tokens rule is present, no custom CSS
    - Ensure icon standards: only `@chakra-ui/icons`, with CRUD action→icon→color mapping (ViewIcon=blue, EditIcon=orange, DeleteIcon=red, AddIcon=green)
    - Add relative markdown link to `../../docs/development/look-and-feel.md`
    - No code blocks exceeding 3 lines; use concise key-value pairs or single-line prop examples
    - Keep file ≤80 lines total
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 6.2_

  - [x] 1.3 Create `.kiro/steering/testing.md` with `inclusion: manual` frontmatter
    - Create new file with YAML frontmatter (`inclusion: manual`)
    - Include: test framework choices (pytest+moto for backend, Jest+RTL for frontend)
    - Include: directory structure conventions
    - Include: coverage targets (80% frontend, 85% backend, 95% critical paths)
    - Include: property-based testing tools (Hypothesis for Python, fast-check for TypeScript)
    - Include testing commands: `pytest tests/`, `pytest --cov=handler --cov-report=term-missing`, `npm test -- --watchAll=false`, `npm test -- --coverage --watchAll=false`
    - Add relative markdown link to `../../docs/development/testing.md`
    - Keep file ≤80 lines total
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 6.3_

- [x] 2. Create reference documents in `docs/development/`
  - [x] 2.1 Create `docs/development/guardrails.md` with full guardrails content
    - Include: S3 bucket architecture (code bucket vs data bucket separation)
    - Include: environment variable validation patterns (fail-fast, no fallbacks)
    - Include: safe/dangerous command lists
    - Include: emergency recovery procedures
    - Include: security checklists and compliance requirements
    - Apply value replacement map for all outdated infrastructure values
    - Cross-reference existing steering files (authentication.md, aws-dynamodb.md) where relevant — do not duplicate their content
    - _Requirements: 4.1, 4.4, 4.5_

  - [x] 2.2 Create `docs/development/look-and-feel.md` with full design system documentation
    - Include: complete color palette, typography scale, spacing system
    - Include: field state patterns (empty, loading, error, success)
    - Include: card/table/modal/form patterns with Chakra UI examples
    - Include: icon standards with full mapping table
    - Include: status badge mappings
    - Include: accessibility requirements
    - Cross-reference existing steering files where relevant — do not duplicate their content
    - _Requirements: 4.2, 4.5_

  - [x] 2.3 Create `docs/development/testing.md` with full testing guidelines
    - Include: test organization structure (unit/, integration/, fixtures/)
    - Include: example tests for both frontend (Jest+RTL) and backend (pytest+moto)
    - Include: coverage commands and interpretation
    - Include: debugging tips for test failures
    - Include: CI pipeline requirements for tests
    - Include: property-based testing examples (Hypothesis, fast-check)
    - Cross-reference existing steering files where relevant — do not duplicate their content
    - _Requirements: 4.3, 4.5_

- [x] 3. Checkpoint - Verify all created files
  - Ensure all 6 target files exist: `.kiro/steering/guardrails.md`, `.kiro/steering/look-and-feel.md`, `.kiro/steering/testing.md`, `docs/development/guardrails.md`, `docs/development/look-and-feel.md`, `docs/development/testing.md`
  - Verify steering files are ≤80 lines each
  - Verify no outdated values remain (grep for old bucket names, API IDs, Cognito values)
  - Verify frontmatter is correct (`auto` for guardrails, `manual` for look-and-feel and testing)
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Remove legacy steering folder
  - [x] 4.1 Delete all 7 legacy files and remove the folder
    - Delete `.kiro/specs/steering/deployment.md`
    - Delete `.kiro/specs/steering/guardrail.md`
    - Delete `.kiro/specs/steering/look-and-feel.md`
    - Delete `.kiro/specs/steering/product.md`
    - Delete `.kiro/specs/steering/structure.md`
    - Delete `.kiro/specs/steering/tech.md`
    - Delete `.kiro/specs/steering/testing.md`
    - Remove the `.kiro/specs/steering/` directory itself
    - Do NOT modify or delete any files in `.kiro/steering/`
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 5. Final checkpoint - Verify migration complete
  - Confirm `.kiro/specs/steering/` directory no longer exists
  - Confirm all 6 target files still exist and are intact
  - Confirm no files in `.kiro/steering/` were accidentally modified or deleted (authentication.md, aws-dynamodb.md, product.md, structure.md, tech.md should be unchanged)
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- No property-based testing applies — this is a static file migration with no runtime code
- Each task references specific requirements for traceability
- Checkpoints ensure verification before destructive operations (legacy deletion)
- The value replacement map must be applied consistently across all new content
- Existing files in `.kiro/steering/` (authentication.md, aws-dynamodb.md, product.md, structure.md, tech.md) must never be modified

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.3"] },
    { "id": 2, "tasks": ["4.1"] }
  ]
}
```
