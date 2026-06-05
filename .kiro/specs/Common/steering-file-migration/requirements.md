# Requirements Document

## Introduction

Consolidate and migrate steering files from the legacy location (`.kiro/specs/steering/`) to the official location (`.kiro/steering/`). Three old files contain unique guidance not covered by current official steering files and must be migrated as concise, actionable steering files with references to detailed documentation. After migration, the legacy steering folder is removed entirely.

## Glossary

- **Steering_File**: A concise markdown file in `.kiro/steering/` that provides actionable rules and guidelines for AI-assisted development, loaded automatically or manually into context.
- **Legacy_Steering_Folder**: The deprecated location `.kiro/specs/steering/` containing 7 outdated steering files.
- **Official_Steering_Folder**: The current canonical location `.kiro/steering/` for all steering files.
- **Reference_Document**: A detailed markdown file in `docs/` containing full explanations, examples, and rationale that a steering file points to.
- **Migration_System**: The process and tooling that creates new steering files, creates reference documents, and removes the legacy folder.

## Requirements

### Requirement 1: Create Guardrails Steering File

**User Story:** As a developer using AI assistance, I want a concise guardrails steering file in the official location, so that AI tools follow safety rules about S3 buckets, environment variables, and deployment without loading a 300-line document.

#### Acceptance Criteria

1. THE Migration_System SHALL create a file at `.kiro/steering/guardrails.md` containing deployment safety rules, S3 bucket separation rules, environment variable fail-fast policies, safe deployment script references, and the "ask before adding unrequested features" rule.
2. THE Steering_File SHALL contain a maximum of 80 lines including frontmatter and blank lines.
3. THE Steering_File SHALL use current actual infrastructure values: code bucket `h-dcn-frontend-506221081911`, data bucket `h-dcn-data-506221081911`, API endpoint `https://44sw408alh.execute-api.eu-west-1.amazonaws.com/prod`.
4. THE Steering_File SHALL reference a detailed document at `docs/development/guardrails.md` using a relative markdown link for full context including emergency procedures, checklists, and compliance requirements.
5. THE Steering_File SHALL NOT contain outdated values from the old account (bucket names `testportal-h-dcn-frontend`, `my-hdcn-bucket`, API `i3if973sp5`, Cognito pool `eu-west-1_VtKQHhXGN`).
6. THE Steering_File SHALL include the rule that critical environment variables (bucket names, API endpoints, auth config) MUST throw errors when missing and SHALL NOT use fallback values.
7. THE Steering_File SHALL list the safe deployment scripts: `scripts/deployment/frontend-build-and-deploy-fast.ps1` and `scripts/deployment/backend-build-and-deploy-fast.ps1`.

### Requirement 2: Create Look-and-Feel Steering File

**User Story:** As a developer building UI components, I want a concise look-and-feel steering file in the official location, so that AI tools generate consistent UI code following H-DCN design patterns.

#### Acceptance Criteria

1. THE Migration_System SHALL create a file at `.kiro/steering/look-and-feel.md` containing sections for brand colors (primary, status, and dark theme values), typography scale (Chakra UI size tokens with pixel equivalents), component patterns (cards, tables, modals, forms, field states), icon standards (library choice and color-per-action mapping), and responsive rules.
2. THE Steering_File SHALL contain a maximum of 80 lines including frontmatter and blank lines.
3. THE Steering_File SHALL include the H-DCN brand color `#f56500`, the hover variant `#e55a00`, and the rule that all styling uses Chakra UI theme tokens and components with no custom CSS.
4. THE Steering_File SHALL reference a detailed document at `docs/development/look-and-feel.md` using a relative markdown link for full design system documentation.
5. THE Steering_File SHALL contain no code blocks exceeding 3 lines and SHALL express design rules as concise key-value pairs or single-line Chakra UI prop examples.
6. WHEN specifying icon standards, THE Steering_File SHALL state that only icons from the `@chakra-ui/icons` package are permitted and SHALL map each CRUD action to a specific icon name and color scheme (ViewIcon=blue, EditIcon=orange, DeleteIcon=red, AddIcon=green).

### Requirement 3: Create Testing Steering File

**User Story:** As a developer writing tests, I want a concise testing steering file in the official location, so that AI tools follow the correct testing patterns, tools, and coverage targets for both frontend and backend.

#### Acceptance Criteria

1. THE Migration_System SHALL create a file at `.kiro/steering/testing.md` containing test framework choices, directory structure conventions, coverage targets, and the commands listed in criterion 6.
2. THE Steering_File SHALL contain a maximum of 80 lines including frontmatter and blank lines.
3. THE Steering_File SHALL specify pytest with moto for backend and Jest with React Testing Library for frontend.
4. THE Steering_File SHALL reference the detailed document at `docs/development/testing.md` using a relative markdown link for full testing guidelines and examples.
5. THE Steering_File SHALL include the property-based testing tools: Hypothesis for Python and fast-check for TypeScript.
6. THE Steering_File SHALL include at minimum the following testing commands: `pytest tests/` for backend, `pytest --cov=handler --cov-report=term-missing` for backend coverage, `npm test -- --watchAll=false` for frontend, and `npm test -- --coverage --watchAll=false` for frontend coverage.
7. THE Steering_File SHALL specify coverage targets of 80% line coverage for frontend, 85% line coverage for backend, and 95% line coverage for critical paths (authentication, payments, data validation).

### Requirement 4: Create Reference Documents

**User Story:** As a developer needing full context, I want detailed reference documents in `docs/development/` that contain the complete guidelines from the old steering files, so that the concise steering files can point to them.

#### Acceptance Criteria

1. THE Migration_System SHALL create `docs/development/guardrails.md` containing the full guardrails content including S3 bucket architecture, environment variable validation patterns, safe/dangerous command lists, emergency recovery procedures, security checklists, and compliance requirements.
2. THE Migration_System SHALL create `docs/development/look-and-feel.md` containing the full design system documentation including color palette, typography, spacing, field state patterns, card/table/modal patterns, icon standards, status badge mappings, and accessibility requirements.
3. THE Migration_System SHALL create `docs/development/testing.md` containing the full testing guidelines including test organization structure, example tests for both frontend and backend, coverage commands, debugging tips, and CI pipeline requirements.
4. WHEN creating reference documents, THE Migration_System SHALL replace all outdated values with current actuals: `testportal-h-dcn-frontend` → `h-dcn-frontend-506221081911`, `my-hdcn-bucket` → `h-dcn-data-506221081911`, `i3if973sp5` → `44sw408alh`, `eu-west-1_VtKQHhXGN` → `eu-west-1_fcUkvwjH5`, `77blkk6a3rpablme00m2die68g` → `6jhvk853b0lfg9q1m861qs0cug`.
5. THE Reference_Document SHALL NOT duplicate information already present in existing official steering files (authentication.md, aws-dynamodb.md, product.md, structure.md, tech.md) and SHALL cross-reference those files where relevant.

### Requirement 5: Remove Legacy Steering Folder

**User Story:** As a project maintainer, I want the old `.kiro/specs/steering/` folder completely removed after migration, so that there is a single source of truth for steering files.

#### Acceptance Criteria

1. WHEN the 3 new steering files (`.kiro/steering/guardrails.md`, `.kiro/steering/look-and-feel.md`, `.kiro/steering/testing.md`) and the 3 reference documents (`docs/development/guardrails.md`, `docs/development/look-and-feel.md`, `docs/development/testing.md`) each exist on disk, THE Migration_System SHALL delete all 7 files in `.kiro/specs/steering/` (deployment.md, guardrail.md, look-and-feel.md, product.md, structure.md, tech.md, testing.md).
2. WHEN all 7 files are deleted, THE Migration_System SHALL remove the `.kiro/specs/steering/` directory itself.
3. THE Migration_System SHALL NOT modify or delete any files in the official `.kiro/steering/` folder, including pre-existing files (authentication.md, aws-dynamodb.md, product.md, structure.md, tech.md) and newly created migration outputs (guardrails.md, look-and-feel.md, testing.md).

### Requirement 6: Steering File Frontmatter

**User Story:** As a developer, I want each new steering file to have proper frontmatter so that the Kiro IDE knows how to load them.

#### Acceptance Criteria

1. THE Steering_File for guardrails SHALL include YAML frontmatter delimited by `---` lines as the first content in the file, with `inclusion: auto` to ensure safety rules are always loaded.
2. THE Steering_File for look-and-feel SHALL include YAML frontmatter delimited by `---` lines as the first content in the file, with `inclusion: manual` since design rules are only needed during UI work.
3. THE Steering_File for testing SHALL include YAML frontmatter delimited by `---` lines as the first content in the file, with `inclusion: manual` since testing rules are only needed during test writing.
