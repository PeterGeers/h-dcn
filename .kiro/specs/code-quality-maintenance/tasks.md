# Implementation Plan: Code Quality Maintenance

## Overview

Implement the Quality Scanner as a Python CLI tool in the `quality_scanner/` directory at the project root. The tool provides four independent checkers (File Length Enforcer, Dead Code Detector, Documentation Freshness Checker, Test Alignment Checker), a unified reporting system, baseline-driven suppression, and CI/CD integration via GitHub Actions.

## Tasks

- [ ] 1. Set up project structure and core interfaces
  - [ ] 1.1 Create package structure and data models
    - Create `quality_scanner/` directory with `__init__.py`, `__main__.py`, `models.py`
    - Implement `Finding`, `ScanResult`, `ScanConfig` dataclasses, `Severity` and `Category` enums
    - Create `checkers/__init__.py` and `checkers/base.py` with `BaseChecker` abstract class
    - _Requirements: 5.1, 5.2_

  - [ ] 1.2 Implement configuration loader
    - Create `quality_scanner/config.py` with YAML loading and defaults merging
    - Implement validation: reject thresholds < 50, reject unrecognized keys, handle invalid YAML with line/column errors
    - Support partial config merging with defaults
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

  - [ ]\* 1.3 Write property tests for configuration
    - **Property 16: Configuration threshold validation** — reject values < 50, accept values >= 50
    - **Property 17: Configuration merge with defaults** — partial config produces complete output with overrides applied
    - **Validates: Requirements 8.2, 8.8**

  - [ ] 1.4 Implement shared utilities
    - Create `quality_scanner/file_discovery.py` with glob-based file enumeration and exclusion pattern matching
    - Create `quality_scanner/git_utils.py` with git log/diff timestamp retrieval functions
    - Create `quality_scanner/suppression.py` with inline comment detection for `# quality-ignore:` and `// quality-ignore:`
    - _Requirements: 1.3, 8.3, 3.10, 9.4, 9.5_

  - [ ]\* 1.5 Write property tests for shared utilities
    - **Property 2: File exclusion filtering** — files matching exclusion patterns never appear in findings; non-matching files are included
    - **Property 8: Inline suppression skips findings** — suppression comments on preceding lines cause the checker to skip that symbol
    - **Validates: Requirements 1.3, 8.3, 2.14, 3.10, 9.4, 9.5**

- [ ] 2. Implement File Length Enforcer
  - [ ] 2.1 Implement file length checker
    - Create `quality_scanner/checkers/file_length.py` implementing `FileLengthChecker`
    - Count total lines per file (including blank lines and comments)
    - Produce WARNING for files exceeding target (500), ERROR for exceeding maximum (1000)
    - Attach Python/TypeScript-specific split suggestions for ERROR findings
    - Filter to `.py` in `backend/handler/` and `backend/layers/`, `.ts`/`.tsx` (excluding `.d.ts`) in `frontend/src/`
    - Apply exclusion patterns for test files, generated files, config files
    - Sort findings by line count descending in summary
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10_

  - [ ]\* 2.2 Write property tests for file length checker
    - **Property 1: Severity assignment by line count** — ERROR when > maximum, WARNING when target < count ≤ maximum, no finding when ≤ target
    - **Property 3: Summary sort order** — findings sorted by line count descending
    - **Validates: Requirements 1.1, 1.2, 1.7**

  - [ ]\* 2.3 Write unit tests for file length checker
    - Test exclusion of test files, generated files, and config file extensions
    - Test split suggestions are attached for Python vs TypeScript files
    - Test exit code logic (non-zero for > 1000 lines, zero for warnings only)
    - _Requirements: 1.3, 1.6, 1.8, 1.9, 1.10_

- [ ] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Implement Dead Code Detector
  - [ ] 4.1 Implement Python dead code analysis
    - Create `quality_scanner/checkers/dead_code.py` implementing `DeadCodeChecker`
    - Parse Python files with `ast.parse()` to build symbol definition table (FunctionDef, ClassDef, Import, ImportFrom)
    - Build reference table from all Name and Attribute nodes across files in scope
    - Identify unused symbols: defined but not referenced in any other file
    - Parse SAM `template.yaml` to identify Lambda handler references and exclude them
    - Exclude `__all__` members, mark dynamic import/reflection references as "uncertain"
    - Count test file imports as valid references to production symbols
    - Support inline suppression comments
    - _Requirements: 2.1, 2.4, 2.5, 2.9, 2.10, 2.11, 2.13, 2.14_

  - [ ] 4.2 Implement TypeScript dead code analysis
    - Add TypeScript analysis to `DeadCodeChecker` using regex-based export/import detection
    - Extract exported symbols (`export function`, `export const`, `export class`, `export default`)
    - Scan all `.ts`/`.tsx` files for import statements and cross-reference
    - Exclude React component default exports from dead code reporting
    - Identify unused imports and unused variables
    - _Requirements: 2.2, 2.3, 2.4, 2.6_

  - [ ]\* 4.3 Write property tests for dead code detector
    - **Property 5: Unused symbol detection** — symbol reported as unused iff not referenced by any other symbol in scope
    - **Property 6: Symbol exclusion from dead code analysis** — lambda_handler, **all** members, React default exports never reported
    - **Property 7: Test imports count as references** — production symbols imported by test files are not flagged
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.9, 2.10, 2.11, 2.13**

  - [ ]\* 4.4 Write unit tests for dead code detector
    - Test SAM template parsing (extract handler references from YAML)
    - Test categorized report output (grouped by type with file path, line number, symbol name)
    - Test "uncertain" classification for dynamic imports
    - Test empty result reporting (zero findings confirmation)
    - _Requirements: 2.7, 2.8, 2.12, 2.13_

- [ ] 5. Implement Documentation Freshness Checker
  - [ ] 5.1 Implement documentation freshness checker
    - Create `quality_scanner/checkers/docs_freshness.py` implementing `DocsFreshnessChecker`
    - Load source-to-docs mapping from config
    - Use git log to get last commit dates for source and doc files
    - Flag documentation as stale when source modified more than staleness_threshold days before doc
    - Only flag when source changes affect public interfaces (compare function signatures via AST)
    - Check README files, architecture documents in `docs/`, and module-level docstrings
    - Handle missing/invalid mapping file gracefully (log warning, continue)
    - Support inline suppression at top of file
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

  - [ ]\* 5.2 Write property tests for documentation freshness
    - **Property 9: Documentation staleness threshold** — flag when source_date - doc_date > threshold
    - **Property 10: Public interface change detection** — only flag for public interface changes, not internal
    - **Validates: Requirements 3.3, 3.5, 3.9**

  - [ ]\* 5.3 Write unit tests for documentation freshness
    - Test public interface diff detection (AST comparison of function signatures)
    - Test missing mapping file handling (warning logged, continues)
    - Test staleness report format (stale doc path, related source path, date)
    - _Requirements: 3.6, 3.7, 3.8_

- [ ] 6. Implement Test Alignment Checker
  - [ ] 6.1 Implement test alignment checker
    - Create `quality_scanner/checkers/test_alignment.py` implementing `TestAlignmentChecker`
    - Implement naming convention mapping: `backend/handler/<name>/app.py` → `test_<name>.py`, `Component.tsx` → `Component.test.tsx`
    - Verify test file existence; report as "untested" (ERROR) if missing
    - Compare git timestamps; report as "test potentially outdated" (WARNING) if source is newer
    - Handle multiple matching test files (use most recently modified)
    - Produce summary categorizing each file as "aligned", "test potentially outdated", or "untested"
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

  - [ ]\* 6.2 Write property tests for test alignment
    - **Property 11: Test file path derivation** — correct expected path from source name + template pattern
    - **Property 12: Test staleness detection** — report "test potentially outdated" when source commit is newer than test commit
    - **Validates: Requirements 4.3, 4.4, 4.6, 8.5**

  - [ ]\* 6.3 Write unit tests for test alignment
    - Test naming convention mapping for backend handlers and frontend components/services
    - Test multiple test file resolution (uses most recently modified)
    - Test summary output format with all three categories
    - _Requirements: 4.4, 4.7, 4.8_

- [ ] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Implement Report Generator and Baseline Manager
  - [ ] 8.1 Implement report generator
    - Create `quality_scanner/reporter.py` with `Reporter` class
    - Implement console output (human-readable, color-coded, grouped by category)
    - Implement JSON output with findings array and summary section (total, by_category, by_severity, suppressed, stale_baseline)
    - Implement GitHub Actions annotations (`::error file={path},line={line}::{message}` and `::warning`)
    - Support filtering by category, severity, and file path with AND logic
    - Produce zero-findings confirmation message when no issues detected
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 7.5_

  - [ ]\* 8.2 Write property tests for report generator
    - **Property 13: Report summary count accuracy** — total == sum of per-category counts == sum of per-severity counts
    - **Property 14: Report filtering with AND logic** — filtered results match ALL specified criteria
    - **Property 15: GitHub Actions annotation format** — correct `::error`/`::warning` format for each finding
    - **Validates: Requirements 5.4, 5.5, 7.5**

  - [ ] 8.3 Implement baseline manager
    - Create `quality_scanner/baseline.py` with `BaselineManager` class
    - Load `.quality-scanner-baseline.json`, match findings by (file_path, category, symbol_name)
    - Suppress matched findings from report output and exit code calculation
    - Generate/update baseline from current scan results
    - Detect stale baseline entries (entries no longer matching any current finding)
    - Report suppressed count and stale baseline entries in summary
    - Support `--no-baseline` flag to ignore baseline
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

  - [ ]\* 8.4 Write property tests for baseline manager
    - **Property 18: Baseline matching and suppression** — matched findings excluded from report; suppressed count accurate
    - **Property 19: Stale baseline detection** — unmatched baseline entries reported as stale
    - **Validates: Requirements 9.2, 9.6, 9.8**

  - [ ]\* 8.5 Write unit tests for reporter and baseline
    - Test JSON report structure matches expected schema
    - Test GitHub Actions annotation format correctness
    - Test baseline file generation and serialization
    - Test empty baseline / missing baseline file handling
    - _Requirements: 5.2, 5.6, 9.1, 9.3_

- [ ] 9. Implement CLI and Scan Orchestrator
  - [ ] 9.1 Implement scan orchestrator
    - Create `quality_scanner/scanner.py` with orchestration logic
    - Run selected checkers, collect findings, apply baseline filtering
    - Pass results to reporter for output generation
    - Determine exit code: 0 for no errors, 1 for error-severity findings, 2 for config/system failures
    - _Requirements: 5.7, 6.6_

  - [ ] 9.2 Implement CLI entry point
    - Create `quality_scanner/__main__.py` with argparse-based CLI
    - Support `--check` (repeatable, select specific checks), `--changed-only`, `--format`, `--output`, `--no-baseline`, `--update-baseline`, `--filter-category`, `--filter-severity`, `--filter-path`, `--ci`, `--config`
    - Enable "changed files only" mode limiting scan to files modified since last commit
    - _Requirements: 6.1, 6.2, 6.4, 6.7_

  - [ ]\* 9.3 Write property tests for exit code logic
    - **Property 4: Exit code determined by error severity** — exit 0 iff zero error-severity findings, exit 1 otherwise
    - **Validates: Requirements 1.8, 1.9, 5.7, 6.6, 7.3, 7.4**

  - [ ]\* 9.4 Write unit tests for CLI and orchestrator
    - Test CLI argument parsing
    - Test changed-files-only mode (git diff integration)
    - Test error handling paths (invalid config, permission errors, git failures)
    - _Requirements: 6.1, 6.2, 6.4_

- [ ] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. CI/CD Integration and Configuration Files
  - [ ] 11.1 Create default configuration file
    - Create `.quality-scanner.yml` at project root with default configuration
    - Include file_length paths, dead_code SAM template reference, docs_freshness mapping examples, test_alignment patterns, and exclusion list
    - _Requirements: 8.1, 8.6_

  - [ ] 11.2 Add quality check job to GitHub Actions workflows
    - Add `quality-check` job to `.github/workflows/deploy-backend.yml` (before deploy, path filter: `backend/**`)
    - Add `quality-check` job to `.github/workflows/deploy-frontend.yml` (before deploy, path filter: `frontend/**`)
    - Include steps: checkout with fetch-depth 0, setup Python 3.11, install quality_scanner, run with `--ci --format both`
    - Upload report artifact, configure cache using file path hash as key
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

  - [ ] 11.3 Create setup.py/pyproject.toml for quality_scanner package
    - Create packaging config so the scanner can be installed with `pip install -e quality_scanner/`
    - Add dependencies: `pyyaml`, `hypothesis` (dev)
    - Create `quality_scanner/tests/__init__.py` and `quality_scanner/tests/conftest.py` with shared fixtures
    - _Requirements: 6.1, 6.3_

- [ ] 12. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document using Hypothesis
- Unit tests validate specific examples and edge cases
- The scanner uses Python 3.11 matching the project's backend runtime
- All git-dependent functionality gracefully degrades when not in a git repository
- Exit code 2 is reserved for configuration/system errors (distinct from finding-based exit code 1)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.4"] },
    { "id": 2, "tasks": ["1.3", "1.5"] },
    { "id": 3, "tasks": ["2.1", "4.1", "5.1", "6.1"] },
    { "id": 4, "tasks": ["2.2", "2.3", "4.2", "5.2", "5.3", "6.2", "6.3"] },
    { "id": 5, "tasks": ["4.3", "4.4", "8.1", "8.3"] },
    { "id": 6, "tasks": ["8.2", "8.4", "8.5"] },
    { "id": 7, "tasks": ["9.1"] },
    { "id": 8, "tasks": ["9.2"] },
    { "id": 9, "tasks": ["9.3", "9.4"] },
    { "id": 10, "tasks": ["11.1", "11.2", "11.3"] }
  ]
}
```
