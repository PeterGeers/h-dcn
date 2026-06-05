# Requirements Document

## Introduction

The H-DCN project requires a standardized, automated approach to maintaining code quality across the backend (Python/SAM) and frontend (React/TypeScript) codebases. This feature introduces tooling and CI/CD integration for four quality dimensions: documentation freshness, test coverage alignment, dead code detection, and file length enforcement. The goal is to catch quality drift early through regular, automated execution — both locally and in CI pipelines.

## Glossary

- **Quality_Scanner**: The automated tooling system that performs code quality checks across the H-DCN codebase
- **Documentation_Checker**: The component that detects outdated or missing documentation relative to code changes
- **Test_Alignment_Checker**: The component that identifies code changes lacking corresponding test updates
- **Dead_Code_Detector**: The component that identifies unused code (functions, imports, variables, components)
- **File_Length_Enforcer**: The component that validates file line counts against configured thresholds
- **Quality_Report**: The structured output produced by the Quality_Scanner summarizing all findings
- **Referral_Document**: A documentation file that references or describes code located elsewhere (e.g., architecture docs, API docs, README files)
- **Staleness_Threshold**: The maximum number of commits or days since a documentation file was last updated relative to the code it describes

## Requirements

### Requirement 1: File Length Enforcement

**User Story:** As a developer, I want automated file length checks, so that files stay within the project's size guidelines and remain maintainable.

#### Acceptance Criteria

1. THE File_Length_Enforcer SHALL report a warning for any source file exceeding 500 total lines (including blank lines and comments)
2. THE File_Length_Enforcer SHALL report an error for any source file exceeding 1000 total lines (including blank lines and comments)
3. THE File_Length_Enforcer SHALL exclude files matching any of the following patterns from enforcement: files within directories named `tests/` or `test/`, files with names containing `.test.` or `.spec.` or `_test.py`, files with names containing `.generated.` or `.auto.`, and files with extensions `.json`, `.yaml`, `.yml`, `.toml`, or `.config.*`
4. THE File_Length_Enforcer SHALL scan Python files (`.py` extension) in `backend/handler/` and `backend/layers/`
5. THE File_Length_Enforcer SHALL scan TypeScript and TSX files (`.ts` and `.tsx` extensions, excluding `.d.ts` declaration files) in `frontend/src/`
6. WHEN a file exceeds 1000 lines, THE File_Length_Enforcer SHALL suggest splitting strategies: for Python files, suggest extracting helpers, using a service layer, or separating into modules; for TypeScript/TSX files, suggest extracting hooks, splitting components, or moving utilities to separate files
7. THE File_Length_Enforcer SHALL produce a summary listing all files exceeding the 500-line target, showing file path and line count for each entry, sorted by line count descending
8. IF any scanned file exceeds 1000 lines, THEN THE File_Length_Enforcer SHALL exit with a non-zero exit code to indicate failure in CI pipelines
9. IF no scanned file exceeds 1000 lines, THEN THE File_Length_Enforcer SHALL exit with exit code 0 regardless of warning-level violations
10. IF the File_Length_Enforcer encounters a system error or invalid configuration during execution, THEN it SHALL exit with a non-zero exit code regardless of file length results

### Requirement 2: Dead Code Detection

**User Story:** As a developer, I want to identify unused code, so that the codebase stays lean and maintainable without accumulating technical debt.

#### Acceptance Criteria

1. THE Dead_Code_Detector SHALL identify unused Python functions and classes in backend code under `backend/handler/` and `backend/layers/`
2. THE Dead_Code_Detector SHALL identify unused imports in both backend Python files and frontend TypeScript files
3. THE Dead_Code_Detector SHALL identify unused TypeScript/React components, functions, and exported symbols in frontend code under `frontend/src/`
4. THE Dead_Code_Detector SHALL identify unused variables in both backend and frontend code
5. THE Dead_Code_Detector SHALL preemptively exclude Lambda handler entry points (`lambda_handler` functions) from dead code analysis before scanning begins
6. THE Dead_Code_Detector SHALL preemptively exclude React component default exports from dead code analysis before scanning begins
7. IF the Dead_Code_Detector flags code that is referenced only via dynamic imports or reflection, THEN THE Dead_Code_Detector SHALL mark the finding as "uncertain" rather than "confirmed"
8. THE Dead_Code_Detector SHALL produce a categorized report grouping findings by type (unused function, unused import, unused variable, unused component), where each finding includes the file path, line number, and symbol name
9. THE Dead_Code_Detector SHALL define a symbol as "unused" when it is not referenced by any other symbol within the analysis scope, excluding references that appear only in the symbol's own definition
10. THE Dead_Code_Detector SHALL exclude files matching test naming patterns (`*_test.py`, `*.test.ts`, `*.test.tsx`, `*.spec.ts`, `*.spec.tsx`) from being analyzed as dead code sources, while still counting test-file imports as valid references to production symbols
11. THE Dead_Code_Detector SHALL actively mark symbols listed in Python `__all__` declarations as referenced and not flag them as unused
12. WHEN the Dead_Code_Detector completes analysis with no unused code found, THE Dead_Code_Detector SHALL still produce a report confirming zero findings
13. THE Dead_Code_Detector SHALL parse the SAM `template.yaml` file to identify all Lambda function handler references (the `Handler` property of each `AWS::Serverless::Function` resource) and preemptively exclude those referenced functions from dead code analysis
14. IF a source file contains an inline suppression comment (`# quality-ignore: dead-code` for Python, `// quality-ignore: dead-code` for TypeScript) on the line preceding a symbol definition, THEN THE Dead_Code_Detector SHALL skip that symbol during analysis

### Requirement 3: Documentation Freshness Detection

**User Story:** As a developer, I want to detect when documentation becomes outdated relative to code changes, so that referral documents stay accurate and trustworthy.

#### Acceptance Criteria

1. WHEN a source file in `backend/handler/` or `frontend/src/` is modified (as determined by git commit history), THE Documentation_Checker SHALL identify related documentation files that are mapped to the modified source file
2. THE Documentation_Checker SHALL map source files to their related documentation using a configurable mapping file that defines source-to-documentation relationships
3. THE Documentation_Checker SHALL detect when a documentation file has not been updated within a configurable Staleness_Threshold (default: 7 days, specified in days) after its related source code was last modified
4. THE Documentation_Checker SHALL check README files, architecture documents in `docs/`, and Python/TypeScript module-level docstrings as documentation targets
5. IF a mapped documentation file has not been modified within the Staleness_Threshold after its related source was changed, THEN THE Documentation_Checker SHALL report the documentation file as stale, including the file path of the stale document and the file path of the triggering source change
6. THE Documentation_Checker SHALL produce a summary report listing all stale documentation files, each entry containing the stale documentation file path, the related source file path, and the date of the last source modification
7. IF the mapping file is missing or contains invalid syntax, THEN THE Documentation_Checker SHALL log a warning and continue staleness detection for files that can be processed without the mapping file
8. WHEN no explicit mapping exists between a source file and documentation, THE Documentation_Checker SHALL still check modification times of all documentation targets to detect potential staleness
9. THE Documentation_Checker SHALL only flag documentation as stale when the triggering source code change affects public interfaces (function signatures, exported symbols, API route definitions, or class/method declarations), not for internal implementation changes (variable renames, formatting, logic refactoring within existing function bodies)
10. IF a source file contains an inline suppression comment (`# quality-ignore: docs-freshness` for Python, `// quality-ignore: docs-freshness` for TypeScript) at the top of the file, THEN THE Documentation_Checker SHALL skip staleness detection for that file

### Requirement 4: Test Coverage Alignment

**User Story:** As a developer, I want to detect when tests are not updated alongside code changes, so that test coverage remains meaningful and aligned with current behavior.

#### Acceptance Criteria

1. WHEN a backend handler file (`backend/handler/*/app.py`) is modified, THE Test_Alignment_Checker SHALL verify that a corresponding test file exists in `backend/tests/unit/` or `backend/tests/integration/`
2. WHEN a frontend component file (`frontend/src/modules/**/*.tsx`, `frontend/src/components/**/*.tsx`) or service file (`frontend/src/services/**/*.ts`) is modified, THE Test_Alignment_Checker SHALL verify that a corresponding test file exists in `frontend/src/__tests__/` or co-located as a `.test.tsx`/`.test.ts` file in the same directory
3. WHEN the checker is invoked, THE Test_Alignment_Checker SHALL compare git last-modified timestamps (most recent commit touching each file) to detect when a source file was modified more recently than its corresponding test file
4. THE Test*Alignment_Checker SHALL use naming conventions to match source files to test files: backend handler `backend/handler/<handler_name>/app.py` maps to `test*<handler_name>.py`; frontend component `Component.tsx`maps to`Component.test.tsx`or`<Component>.test.tsx`in the`**tests**/` directory
5. IF a source file has no corresponding test file matching the naming conventions defined in criterion 4, THEN THE Test_Alignment_Checker SHALL report the source file as "untested"
6. IF a source file's most recent git commit is newer than its corresponding test file's most recent git commit, THEN THE Test_Alignment_Checker SHALL report the pair as "test potentially outdated"
7. WHEN the checker completes analysis, THE Test_Alignment_Checker SHALL produce a summary report to standard output categorizing each analyzed file as "aligned", "test potentially outdated", or "untested"
8. IF the checker encounters a source file that matches multiple test files by naming convention, THEN THE Test_Alignment_Checker SHALL use the most recently modified test file for the staleness comparison

### Requirement 5: Quality Report Generation

**User Story:** As a developer, I want a unified quality report, so that I can see all code quality issues in one place and track improvement over time.

#### Acceptance Criteria

1. THE Quality_Scanner SHALL produce a unified Quality_Report combining results from the File_Length_Enforcer, Dead_Code_Detector, Documentation_Checker, and Test_Alignment_Checker, where each finding includes the source file path, line number (where applicable), category (which checker produced it), severity level, and a description of the issue
2. THE Quality_Scanner SHALL output the Quality_Report in both human-readable (console) and machine-readable (JSON) formats
3. THE Quality_Scanner SHALL assign a severity level to each finding using these rules: "error" for violations that indicate broken or missing functionality (e.g., missing required tests, files exceeding the maximum line limit), "warning" for issues that degrade maintainability but do not block functionality (e.g., files exceeding the target line limit but below the maximum, missing documentation on public interfaces), and "info" for advisory suggestions (e.g., unused imports, minor documentation gaps)
4. THE Quality_Scanner SHALL include a summary section with total finding count, counts per category (File_Length_Enforcer, Dead_Code_Detector, Documentation_Checker, Test_Alignment_Checker), and counts per severity level (error, warning, info)
5. THE Quality_Scanner SHALL support filtering findings by category, severity, or file path, where multiple filters are combined using AND logic (all specified conditions must match)
6. WHEN no findings are detected, THE Quality_Scanner SHALL produce a report containing the summary section with all counts at zero and a confirmation message that all checks passed
7. THE Quality_Scanner SHALL return exit code 0 when no "error"-severity findings are present, and exit code 1 when one or more "error"-severity findings are detected, to enable CI pipeline integration

### Requirement 6: Local Execution

**User Story:** As a developer, I want to run quality checks locally before pushing, so that I can fix issues before they reach the CI pipeline.

#### Acceptance Criteria

1. THE Quality_Scanner SHALL be executable via a single command (with optional arguments for check selection) from the project root directory
2. THE Quality_Scanner SHALL support running individual checks independently (e.g., only file length, only dead code) via command-line arguments
3. THE Quality_Scanner SHALL complete a full scan of the codebase within 60 seconds on a machine with at least 4 CPU cores and 8 GB RAM
4. THE Quality_Scanner SHALL support a "changed files only" mode that limits scanning to files modified since the last commit
5. WHEN run in "changed files only" mode, THE Quality_Scanner SHALL complete within 10 seconds for changesets of up to 20 files
6. WHEN the scan completes, THE Quality_Scanner SHALL exit with code 0 if all checks pass, and a non-zero exit code if any check fails
7. IF any check fails, THEN THE Quality_Scanner SHALL output the file path, line number (where applicable), and a description of the violation for each finding

### Requirement 7: CI/CD Integration

**User Story:** As a team lead, I want quality checks to run automatically in CI, so that quality standards are enforced consistently on every push to main.

#### Acceptance Criteria

1. THE Quality_Scanner SHALL run as a dedicated job in each existing GitHub Actions deploy workflow (deploy-backend.yml, deploy-frontend.yml), executing before the deploy job
2. THE Quality_Scanner job SHALL use the same path filters as its parent workflow (backend/** for deploy-backend, frontend/** for deploy-frontend) and trigger on pushes to the `main` branch
3. WHEN the Quality_Scanner detects errors (file length exceeding 1000 lines), THE CI pipeline SHALL exit with a non-zero exit code, causing the workflow run to fail and blocking the subsequent deploy job
4. WHEN the Quality_Scanner detects only warnings (file length between 500 and 1000 lines), THE CI pipeline SHALL exit with code 0 and produce GitHub Actions warning-level annotations for each finding
5. THE Quality_Scanner SHALL produce GitHub Actions annotations (via workflow commands) for each finding, including the severity level (error or warning), file path, and start line number
6. THE Quality_Scanner SHALL cache analysis results using a hash of scanned file paths as the cache key, and the quality check job SHALL complete within 60 seconds for repositories with up to 500 scanned files
7. IF no pull request is associated with the push to main, THEN THE Quality_Scanner SHALL still produce annotations visible in the Actions run summary

### Requirement 8: Configuration

**User Story:** As a developer, I want the quality checks to be configurable, so that thresholds and exclusions can be adjusted as the project evolves.

#### Acceptance Criteria

1. THE Quality_Scanner SHALL read configuration from a YAML file named `.quality-scanner.yml` at the project root
2. THE Quality_Scanner SHALL support configurable file length thresholds (target and maximum) as positive integer values representing line counts, with a minimum enforced value of 50 lines to prevent unusably small thresholds
3. THE Quality_Scanner SHALL support configurable file and directory exclusion patterns using glob syntax for each check type
4. THE Quality_Scanner SHALL support configurable documentation-to-source mapping definitions as a list of source-path to documentation-path pairs
5. THE Quality_Scanner SHALL support configurable test file naming convention patterns using template placeholders for the source file name
6. WHEN no configuration file is present, THE Quality*Scanner SHALL use default values: 500-line target and 1000-line maximum for file length, exclusion of `.venv/`, `node_modules/`, `build/`, and `*.generated._`directories/files, and`test_<handler_name>.py`/`<Component>.test.tsx` test naming conventions
7. IF the configuration file contains invalid YAML syntax or unrecognized keys, THEN THE Quality_Scanner SHALL report a configuration error indicating the location of the problem and refuse to proceed with the scan
8. WHEN a configuration file specifies only a subset of settings, THE Quality_Scanner SHALL merge the provided settings with defaults for any unspecified settings

### Requirement 9: False Positive Suppression

**User Story:** As a developer, I want to suppress known false positives, so that quality reports remain actionable and don't create noise from irrelevant findings.

#### Acceptance Criteria

1. THE Quality_Scanner SHALL support a baseline file (`.quality-scanner-baseline.json`) at the project root that records known findings to suppress on subsequent runs
2. WHEN a baseline file is present, THE Quality_Scanner SHALL exclude any finding that matches an entry in the baseline (matched by file path, line number, category, and symbol name) from the report output and exit code calculation
3. THE Quality_Scanner SHALL provide a command to generate or update the baseline file from the current scan results, capturing all current findings as suppressed
4. THE Quality_Scanner SHALL support inline suppression comments in source files: `# quality-ignore: <check-type>` for Python and `// quality-ignore: <check-type>` for TypeScript, where `<check-type>` is one of `dead-code`, `file-length`, `docs-freshness`, or `test-alignment`
5. WHEN an inline suppression comment is present on the line immediately preceding a symbol definition or at the top of a file, THE Quality_Scanner SHALL skip that symbol or file for the specified check type
6. THE Quality_Scanner SHALL report the count of suppressed findings separately in the summary section, so developers remain aware of accumulated suppressions
7. THE Quality_Scanner SHALL provide a `--no-baseline` flag that ignores the baseline file and reports all findings including previously suppressed ones
8. IF a baseline entry no longer matches any finding in the current scan (the issue was resolved), THEN THE Quality_Scanner SHALL report the resolved entry as "stale baseline" in the summary so the baseline can be cleaned up
