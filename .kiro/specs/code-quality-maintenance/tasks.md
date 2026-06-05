# Implementation Plan: Code Quality Maintenance

## Overview

Build a Python CLI tool (`quality_scanner`) that performs automated code quality checks across the H-DCN monorepo. The scanner wraps external tools (vulture for Python dead code, knip for TypeScript dead code) and implements custom checkers for file length, documentation freshness, and test alignment. Output is unified into console, JSON, and GitHub Actions annotation formats.

## Tasks

- [ ] 1. Set up project structure and core interfaces
  - [ ] 1.1 Create package structure and data models
    - Create `quality_scanner/` directory with `__init__.py`, `__main__.py`, `models.py`
    - Implement `Finding`, `ScanResult`, `ScanConfig`, `Severity`, `Category` dataclasses/enums in `models.py`
    - Create `checkers/__init__.py` and `checkers/base.py` with `BaseChecker` abstract class
    - Add `setup.py` or `pyproject.toml` with dependencies (PyYAML>=6.0, vulture>=2.11, hypothesis>=6.0)
    - _Requirements: 5.1, 8.1_

  - [ ] 1.2 Implement configuration loader
    - Create `quality_scanner/config.py` with YAML loading and defaults merging
    - Implement `load_config()` with deep-merge of provided settings over DEFAULTS
    - Validate thresholds (must be positive integers >= 50), reject unrecognized keys
    - Raise `ConfigError` with line/column info for invalid YAML or unrecognized keys
    - Handle missing config file gracefully (use defaults silently)
    - _Requirements: 8.1, 8.2, 8.6, 8.7, 8.8_

  - [ ] 1.3 Implement shared utilities
    - Create `quality_scanner/file_discovery.py` with glob-based file enumeration and exclusion pattern matching
    - Create `quality_scanner/git_utils.py` with `get_last_modified_date()` using `git log -1 --format=%aI`
    - Create `quality_scanner/suppression.py` for inline comment detection (`# quality-ignore:` / `// quality-ignore:`)
    - Handle git errors gracefully (not a git repo, command failures)
    - _Requirements: 8.3, 9.4, 9.5_

  - [ ]\* 1.4 Write property tests for configuration (Properties 16, 17)
    - **Property 16: Configuration threshold validation** — verify values < 50 are rejected, values >= 50 are accepted
    - **Property 17: Configuration merge with defaults** — verify partial configs produce complete configs with overrides applied correctly
    - **Validates: Requirements 8.2, 8.8**

- [ ] 2. Implement File Length Enforcer
  - [ ] 2.1 Implement file length checker
    - Create `quality_scanner/checkers/file_length.py` with `FileLengthChecker` class
    - Filter files to `.py` in `backend/handler/` and `backend/layers/`, `.ts/.tsx` (excluding `.d.ts`) in `frontend/src/`
    - Apply exclusion patterns (test files, generated files, config files)
    - Count lines per file using `len(file.readlines())`
    - Produce WARNING for > target (default 500), ERROR for > maximum (default 1000)
    - Attach split suggestions for ERROR-level findings (Python: helpers/service layer/modules; TS: hooks/components/utils)
    - Sort findings by line count descending
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [ ]\* 2.2 Write property tests for file length (Properties 1, 2, 3)
    - **Property 1: Severity assignment by line count** — generate random line counts and thresholds, verify correct severity assignment
    - **Property 2: File exclusion filtering** — generate random paths and glob patterns, verify matching files are excluded
    - **Property 3: Summary sort order** — generate random findings, verify descending line count sort
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.7, 8.3**

  - [ ]\* 2.3 Write unit tests for file length checker
    - Test known file with exact line count at threshold boundaries (500, 501, 1000, 1001)
    - Test exclusion of test files, generated files, .d.ts files
    - Test split suggestion content for Python and TypeScript files
    - Mock filesystem with `tmp_path` fixtures
    - _Requirements: 1.1, 1.2, 1.3, 1.6_

- [ ] 3. Implement Dead Code Detector (vulture + knip wrapper)
  - [ ] 3.1 Implement vulture wrapper for Python dead code
    - Create `quality_scanner/checkers/dead_code.py` with `DeadCodeChecker` class
    - Implement `_generate_vulture_whitelist()` that parses SAM `template.yaml` to find Lambda handler entry points
    - Add `lambda_handler` references and `__all__` members and inline-suppressed symbols to whitelist
    - Implement `_run_vulture()` that executes `vulture <paths> <whitelist_file> --min-confidence 80` via `subprocess.run`
    - Parse vulture's line-based output format: `{file}:{line}: unused {type} '{name}' (confidence: {pct}%)`
    - Convert each parsed line to a `Finding` object; mark findings with confidence < 100% as "uncertain"
    - Handle vulture not installed (log error with install instructions, skip Python analysis)
    - Handle subprocess failures gracefully (log stderr, skip, continue)
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 2.7, 2.8, 2.9, 2.11, 2.13, 2.14_

  - [ ] 3.2 Implement knip wrapper for TypeScript dead code
    - Implement `_generate_knip_config()` that creates knip.json with entry patterns, project globs, and ignore patterns
    - Configure knip to exclude test files from dead code sources but count test imports as references
    - Implement `_run_knip()` that executes `npx knip --reporter json --no-exit-code` via `subprocess.run` from frontend directory
    - Parse knip's JSON output (unused exports, unused files, unused dependencies)
    - Convert each finding to a `Finding` object, mapping knip categories to scanner finding types
    - Filter out React component default exports via knip configuration
    - Handle knip not installed (log error with install instructions, skip TypeScript analysis)
    - Handle subprocess failures gracefully (log stderr, skip, continue)
    - _Requirements: 2.2, 2.3, 2.4, 2.6, 2.9, 2.10, 2.12_

  - [ ]\* 3.3 Write unit tests for dead code detector (mocked subprocess)
    - Mock `subprocess.run` to return known vulture output lines, verify correct Finding objects are produced
    - Mock `subprocess.run` to return known knip JSON output, verify correct Finding objects are produced
    - Test vulture whitelist generation from a fixture SAM template YAML
    - Test knip config generation produces correct JSON structure
    - Test handling of vulture not installed (FileNotFoundError from subprocess)
    - Test handling of knip not installed (FileNotFoundError from subprocess)
    - Test "uncertain" marking for findings with confidence < 100%
    - Test inline suppression → whitelist entry conversion
    - _Requirements: 2.1, 2.3, 2.5, 2.7, 2.13_

  - [ ]\* 3.4 Write property tests for dead code detection (Properties 5, 6, 7, 8)
    - **Property 5: Unused symbol detection** — generate random vulture/knip output, verify all reported symbols are converted to findings
    - **Property 6: Symbol exclusion** — generate lambda_handler paths and **all** members, verify they appear in whitelist
    - **Property 7: Test imports count as references** — verify knip config excludes test files from sources but includes as reference targets
    - **Property 8: Inline suppression skips findings** — generate suppression comments, verify suppressed symbols are added to whitelist
    - **Validates: Requirements 2.1, 2.5, 2.10, 2.14**

- [ ] 4. Checkpoint - Core checkers complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement Documentation Freshness Checker
  - [ ] 5.1 Implement documentation freshness checker
    - Create `quality_scanner/checkers/docs_freshness.py` with `DocsFreshnessChecker` class
    - Load source-to-docs mapping from config
    - Use `git_utils.get_last_modified_date()` to compare timestamps
    - Flag documentation as stale when source_date - doc_date > staleness_threshold_days
    - Implement public interface change detection: compare function signatures/exported symbols between commits using `ast.parse()` for Python and regex on `export` statements for TypeScript
    - Only flag when public interfaces changed (not internal implementation)
    - Support inline suppression (`# quality-ignore: docs-freshness`)
    - Handle missing mapping file (log warning, continue with available mappings)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.9, 3.10_

  - [ ]\* 5.2 Write property tests for documentation freshness (Properties 9, 10)
    - **Property 9: Documentation staleness threshold** — generate random timestamps and thresholds, verify correct staleness detection
    - **Property 10: Public interface change detection** — generate function signatures with/without changes, verify only public changes trigger staleness
    - **Validates: Requirements 3.3, 3.5, 3.9**

  - [ ]\* 5.3 Write unit tests for documentation freshness checker
    - Test staleness detection with mocked git dates
    - Test public interface detection (Python AST diff, TypeScript export regex)
    - Test inline suppression skips file
    - Test missing mapping file handling
    - _Requirements: 3.3, 3.9, 3.10_

- [ ] 6. Implement Test Alignment Checker
  - [ ] 6.1 Implement test alignment checker
    - Create `quality_scanner/checkers/test_alignment.py` with `TestAlignmentChecker` class
    - Implement naming convention mapping: `backend/handler/<name>/app.py` → `test_<name>.py`; `Component.tsx` → `Component.test.tsx`
    - Check existence of expected test files in configured paths
    - Compare git timestamps: if source newer than test → "test potentially outdated" (WARNING)
    - If no test file → "untested" (ERROR)
    - If multiple test files match, use most recently modified
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

  - [ ]\* 6.2 Write property tests for test alignment (Properties 11, 12)
    - **Property 11: Test file path derivation** — generate source file names and templates, verify correct test path derivation
    - **Property 12: Test staleness detection** — generate timestamp pairs, verify correct staleness classification
    - **Validates: Requirements 4.4, 4.3, 4.6, 8.5**

  - [ ]\* 6.3 Write unit tests for test alignment checker
    - Test naming convention mapping for backend handlers and frontend components
    - Test "untested" detection when no test file exists
    - Test "potentially outdated" detection with mocked git timestamps
    - Test multiple test file resolution (most recent wins)
    - _Requirements: 4.4, 4.5, 4.6, 4.8_

- [ ] 7. Implement Reporting and Baseline
  - [ ] 7.1 Implement report generator
    - Create `quality_scanner/reporter.py` with `Reporter` class
    - Implement `console_report()` with human-readable grouped output, color coding, severity indicators
    - Implement `json_report()` with full findings, summary section (total, by_category, by_severity, suppressed, stale_baseline)
    - Implement `github_annotations()` producing `::error file={path},line={line}::{message}` and `::warning` commands
    - Ensure summary counts: total == sum(by_category) == sum(by_severity)
    - Support filtering by category, severity, file path (AND logic)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 7.5_

  - [ ] 7.2 Implement baseline manager
    - Create `quality_scanner/baseline.py` with `BaselineManager` class
    - Implement `load()` to read `.quality-scanner-baseline.json`
    - Implement `matches()` using composite key: (file_path, category, symbol_name) — line numbers excluded
    - Implement `generate()` to create baseline from current findings
    - Implement `find_stale()` to identify baseline entries with no matching current finding
    - Handle missing/invalid baseline file gracefully (treat as empty)
    - _Requirements: 9.1, 9.2, 9.3, 9.6, 9.7, 9.8_

  - [ ]\* 7.3 Write property tests for reporting and baseline (Properties 13, 14, 15, 18, 19)
    - **Property 13: Report summary count accuracy** — generate random findings, verify total == sum(by_category) == sum(by_severity)
    - **Property 14: Report filtering with AND logic** — generate findings and filters, verify all returned findings match ALL criteria
    - **Property 15: GitHub Actions annotation format** — generate findings, verify output matches `::error`/`::warning` format
    - **Property 18: Baseline matching and suppression** — generate findings and baseline entries, verify matching findings are excluded and suppressed count is accurate
    - **Property 19: Stale baseline detection** — generate baseline entries without matching findings, verify they're reported as stale
    - **Validates: Requirements 5.4, 5.5, 7.5, 9.2, 9.6, 9.8**

  - [ ]\* 7.4 Write unit tests for reporter and baseline
    - Test JSON report structure matches expected schema
    - Test console output contains all findings grouped by category
    - Test GitHub annotation format with edge cases (no line number, special characters)
    - Test baseline matching with exact and non-matching entries
    - Test stale baseline detection
    - Test empty results produce zero-count summary with confirmation message
    - _Requirements: 5.2, 5.4, 5.6, 9.2, 9.8_

- [ ] 8. Checkpoint - All checkers and reporting complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Implement CLI and Orchestrator
  - [ ] 9.1 Implement scan orchestrator
    - Create `quality_scanner/scanner.py` with orchestration logic
    - Run selected checkers based on `--check` arguments (or all if none specified)
    - Collect findings from all checkers into unified `ScanResult`
    - Apply baseline suppression, count suppressed findings
    - Detect stale baseline entries
    - Determine exit code: 0 if no ERROR-severity findings, 1 if any ERROR findings, 2 for config/system errors
    - Support `--changed-only` mode using `git diff --name-only HEAD~1`
    - _Requirements: 5.1, 5.7, 6.1, 6.2, 6.4, 6.6, 9.2_

  - [ ] 9.2 Implement CLI entry point
    - Create `quality_scanner/__main__.py` with argparse
    - Support all CLI flags: `--check`, `--changed-only`, `--format`, `--output`, `--no-baseline`, `--update-baseline`, `--filter-category`, `--filter-severity`, `--filter-path`, `--ci`, `--config`
    - Wire CLI to config loader → orchestrator → reporter pipeline
    - Implement `--update-baseline` to generate baseline from current scan
    - Implement `--no-baseline` to skip baseline suppression
    - _Requirements: 6.1, 6.2, 6.4, 9.3, 9.7_

  - [ ]\* 9.3 Write property test for exit code (Property 4)
    - **Property 4: Exit code determined by error severity** — generate random scan results with mixed severities, verify exit code is 0 iff zero ERROR findings
    - **Validates: Requirements 1.8, 1.9, 5.7, 6.6, 7.3, 7.4**

  - [ ]\* 9.4 Write unit tests for CLI and orchestrator
    - Test CLI argument parsing for all flag combinations
    - Test orchestrator runs only selected checkers
    - Test `--changed-only` filters file list correctly
    - Test `--no-baseline` flag disables suppression
    - Test `--update-baseline` generates correct baseline file
    - Test exit code 0, 1, 2 scenarios
    - _Requirements: 6.1, 6.2, 6.6, 9.3, 9.7_

- [ ] 10. CI/CD Integration
  - [ ] 10.1 Add quality check job to GitHub Actions workflows
    - Add `quality-check` job to `.github/workflows/deploy-backend.yml` before deploy job
    - Add `quality-check` job to `.github/workflows/deploy-frontend.yml` before deploy job
    - Include steps: checkout (fetch-depth 0), setup-python 3.11, setup-node 20, pip install quality_scanner, npm install knip + typescript in frontend, run scanner with `--ci --format both`
    - Add `needs: quality-check` dependency to existing deploy jobs
    - Upload `quality-report.json` as artifact
    - Use same path filters as parent workflow (backend/** for backend, frontend/** for frontend)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

  - [ ] 10.2 Create default configuration file
    - Create `.quality-scanner.yml` at project root with sensible defaults for the H-DCN project
    - Configure file length thresholds (500/1000), exclusion patterns, docs mapping, test naming conventions
    - Configure dead code settings: SAM template path, vulture confidence, Python/TypeScript paths
    - _Requirements: 8.1, 8.4, 8.5, 8.6_

- [ ] 11. Final checkpoint - Full integration complete
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Dead code detector tests use `unittest.mock.patch` on `subprocess.run` to mock vulture/knip output
- `vulture` is a Python pip dependency; `knip` requires Node.js and npm
- CI workflows need both Python 3.11 and Node.js 20 setup steps

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3"] },
    { "id": 2, "tasks": ["1.4", "2.1", "3.1", "3.2"] },
    { "id": 3, "tasks": ["2.2", "2.3", "3.3", "3.4", "5.1", "6.1"] },
    { "id": 4, "tasks": ["5.2", "5.3", "6.2", "6.3", "7.1", "7.2"] },
    { "id": 5, "tasks": ["7.3", "7.4"] },
    { "id": 6, "tasks": ["9.1"] },
    { "id": 7, "tasks": ["9.2"] },
    { "id": 8, "tasks": ["9.3", "9.4", "10.1", "10.2"] }
  ]
}
```
