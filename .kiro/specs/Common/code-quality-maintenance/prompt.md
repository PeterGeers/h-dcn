# Code Quality Maintenance — Monthly Scan Prompt

> **⚡ Before pasting:** You will need to confirm several terminal commands (~8-10):
> `git rev-parse` (detect branch), 4 `gh` CLI calls (trigger/list/watch/download the
> Full Test Suite), `vulture` (dead code), `grep` (parse frontend failures), and
> `rm -rf .tmp-test-reports` (cleanup). Several can be batched into single blocks to
> reduce confirmations. File operations use built-in tools and run automatically.

Paste this prompt into Kiro to run a code quality scan. It will execute autonomously and produce a spec with findings and fix tasks.

---

## Prompt

Run a full code quality scan of the H-DCN codebase now. Do not ask for confirmation — execute all steps and produce the output spec.

Steps to execute:

1. **File length**: Find all .py files in backend/handler/ and backend/layers/, and all .ts/.tsx files in frontend/src/ that exceed 500 lines. Flag errors for files over 1000 lines.

2. **Missing tests**: Find backend handlers (backend/handler/\_/app.py) without a corresponding test\_\_.py in backend/tests/, and frontend components/services without .test.tsx/.test.ts files.

3. **Dead code**: Run vulture on the backend Python code and identify unused functions, imports, and variables. Check frontend for unused exports.

4. **Stale documentation**: Check if docs/ files are outdated relative to recent code changes in backend/handler/ and frontend/src/.

5. **Broken/stale tests**: Download and analyze the latest Full Test Suite run artifacts. Categorize each failing test as:
   - **Stale test** — tests removed/refactored code that no longer exists → delete or rewrite
   - **Real bug** — test is correct but code is wrong → fix the handler/component
   - **Test bug** — wrong assertion, broken mock, missing import → fix the test

   ### How to get the test reports:

   Always run the Full Test Suite against the **currently checked-out branch**
   (the branch active in the local repo when the scan runs) — not `main` and not
   "whatever ran last".

   ```bash
   # Detect the active branch at run time (do NOT hardcode a branch name).
   BRANCH=$(git rev-parse --abbrev-ref HEAD)
   echo "Active branch: $BRANCH"

   # 1. Trigger the "Full Test Suite" on the active branch and wait for it.
   #    The workflow is workflow_dispatch with no inputs; --ref selects the branch
   #    that actions/checkout checks out, so the whole suite runs against BRANCH.
   #    NOTE: the branch must be pushed to origin first, or gh has nothing to run.
   gh workflow run full-test-suite.yml --ref "$BRANCH"

   # 2. Wait for the just-created run on this branch, then capture its ID.
   #    (Give GitHub a moment to register the run before querying.)
   sleep 10
   RUN_ID=$(gh run list --workflow full-test-suite.yml --branch "$BRANCH" \
     --limit 1 --json databaseId --jq '.[0].databaseId')
   echo "Run ID: $RUN_ID (branch $BRANCH)"
   gh run watch "$RUN_ID" --exit-status || true   # continue-on-error: true, so don't fail here

   # 3. Download both backend and frontend artifacts for THIS run.
   gh run download "$RUN_ID" --dir .tmp-test-reports

   # This creates:
   #   .tmp-test-reports/backend-test-report/test-report.json   ← structured JSON with failures
   #   .tmp-test-reports/backend-test-report/test-results.xml   ← JUnit XML
   #   .tmp-test-reports/backend-test-report/test-output.txt    ← full pytest output
   #   .tmp-test-reports/frontend-test-report/test-output.txt   ← full Jest output
   ```

   ### How to analyze:

   **Backend** — Parse `test-report.json`:

   ```python
   import json
   report = json.load(open('.tmp-test-reports/backend-test-report/test-report.json'))
   print(f"Failed: {len(report['failed_tests'])}")
   for t in report['failed_tests']:
       print(f"  {t['classname']}::{t['name']}")
       print(f"    {t['message'][:120]}")
   ```

   **Frontend** — Extract FAIL lines from `test-output.txt`:

   ```bash
   grep -E "^FAIL " .tmp-test-reports/frontend-test-report/test-output.txt
   grep -E "^\s+●" .tmp-test-reports/frontend-test-report/test-output.txt | sort -u
   ```

   ### Important notes:
   - Always target the currently checked-out branch, detected at run time via
     `git rev-parse --abbrev-ref HEAD` (see step 1 above). Never hardcode a branch.
   - The branch must exist on origin — push it before triggering, otherwise
     `gh workflow run --ref "$BRANCH"` has no ref to dispatch against.
   - The workflow uses `continue-on-error: true`, so CI always shows "success"
     even with failures — inspect the artifacts, do not trust the run's status.
   - Clean up after: `rm -rf .tmp-test-reports`

Exclude: test files, .venv/, node*modules/, build/, *.generated.\_ files.

## Output

Create a new spec at `.kiro/specs/code-quality-fixes-YYYY-MM/` (use current month) with:

- `requirements.md` — summarize all findings with file paths, line counts, error messages
- `tasks.md` — structured actionable task list grouped by category (dead code → broken tests → file length → missing tests → stale docs), with priority order and dependency graph

Use "Quick Plan" workflow. Do not prompt for intermediate decisions.

## Execution hints

- **Minimize terminal commands**: Use built-in file/directory listing tools for file length scanning and directory exploration. Only use shell for: `gh` CLI (artifact download), `vulture` (dead code), and JSON parsing if needed.
- **Batch shell work**: Combine multiple checks into single commands where possible to reduce confirmation clicks.
