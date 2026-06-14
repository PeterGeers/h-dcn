# Code Quality Maintenance — Monthly Scan Prompt

Paste this prompt into Kiro to run a code quality scan and generate a task list for fixing findings.

---

## Prompt

Scan the H-DCN codebase for code quality issues and create a new spec with a tasks.md to fix the findings. Specifically:

1. **File length**: Find all .py files in backend/handler/ and backend/layers/, and all .ts/.tsx files in frontend/src/ that exceed 500 lines. Flag errors for files over 1000 lines.

2. **Missing tests**: Find backend handlers (backend/handler/\_/app.py) without a corresponding test\_\_.py in backend/tests/, and frontend components/services without .test.tsx/.test.ts files.

3. **Dead code**: Run vulture on the backend Python code and identify unused functions, imports, and variables. Check frontend for unused exports.

4. **Stale documentation**: Check if docs/ files are outdated relative to recent code changes in backend/handler/ and frontend/src/.

5. **Broken/stale tests**: Run `gh workflow run "Full Test Suite"` (or check the latest run artifact) and analyze failures. Categorize each failing test as:
   - **Stale test** — tests removed/refactored code that no longer exists → delete or rewrite
   - **Real bug** — test is correct but code is wrong → fix the handler/component
   - **Test bug** — wrong assertion, broken mock, missing import → fix the test

   Download the test-report.json artifact with `gh run download <run-id> -n backend-test-report` and use it as input.

Exclude: test files, .venv/, node*modules/, build/, *.generated.\_ files.

Then create a new spec at .kiro/specs/code-quality-fixes-YYYY-MM/ with:

- requirements.md summarizing the findings
- tasks.md with a structured, actionable task list to fix each finding, grouped by category (file length → dead code → missing tests → broken tests → stale docs), with file paths and specific actions

Use "Quick Plan" workflow. Name the spec with the current month (e.g., code-quality-fixes-2026-06).
