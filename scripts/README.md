# H-DCN Scripts

This directory contains utility scripts for the H-DCN project.

## Validation Scripts

These scripts help prevent file corruption and catch errors before deployment.

### validate_all.py

**Master validation script** - runs all validation checks in sequence.

```bash
python scripts/validate_all.py
```

**When to use:**

- After running any script that modifies Python files
- Before committing changes
- As part of pre-deployment checks (automatically run by deployment scripts)

**What it checks:**

- Python syntax validation
- Handler file integrity

**Exit codes:**

- 0: All checks passed
- 1: One or more checks failed

---

### validate_python_syntax.py

Validates Python syntax for all handler files using `py_compile`.

```bash
python scripts/validate_python_syntax.py
```

**What it checks:**

- All `.py` files in `backend/handler/` (except `__init__.py` and migration templates)
- Syntax errors, indentation errors, invalid characters

**Output:**

- ✅ for files with valid syntax
- ❌ for files with syntax errors (with error details)

**Exit codes:**

- 0: All files have valid syntax
- 1: One or more files have syntax errors

---

### check_handler_integrity.py

Checks handler files for common issues that indicate corruption or incomplete modifications.

```bash
python scripts/check_handler_integrity.py
```

**What it checks:**

- File length (detects truncated files)
- Presence of `lambda_handler` function
- Auth import patterns (with smart detection for Cognito triggers and maintenance fallback)
- Problematic `sys.exit(0)` usage
- Return statement patterns

**Output:**

- ✅ for handlers that pass all checks
- ❌ for handlers with ERRORS (critical issues)
- ⚠️ for handlers with WARNINGS (informational, may be false positives)

**Exit codes:**

- 0: All handlers passed (warnings are OK)
- 1: One or more handlers have critical errors

**Note:** Warnings about "Missing auth import" are often false positives for:

- Simple public endpoints (like `get_memberships`)
- Cognito trigger handlers
- Handlers using maintenance fallback pattern

---

## Deployment Scripts

See `scripts/deployment/README.md` for deployment script documentation.

---

## Best Practices

### Before Running File Modification Scripts

1. **Commit your current work** - so you can easily revert if something goes wrong
2. **Run validation before** - ensure files are in good state
3. **Run the modification script**
4. **Run validation after** - catch any issues immediately
5. **Review git diff** - check what actually changed
6. **Test locally if possible**
7. **Commit the changes**

### Example Workflow

```bash
# 1. Commit current work
git add .
git commit -m "Before running modification script"

# 2. Run validation (should pass)
python scripts/validate_all.py

# 3. Run your modification script
python your_modification_script.py

# 4. Run validation again (catch any issues)
python scripts/validate_all.py

# 5. Review changes
git diff

# 6. If everything looks good, commit
git add .
git commit -m "Applied modifications"

# 7. If something went wrong, revert
git reset --hard HEAD
```

---

## Integration with Deployment

The validation scripts are automatically run as part of the deployment process:

- `scripts/deployment/backend-build-and-deploy-fast.ps1` runs `validate_all.py` before building
- Deployment will **fail** if validation checks don't pass
- This prevents deploying broken code to production

---

## Troubleshooting

### Syntax Errors

If you see syntax errors:

1. Open the file in your editor
2. Look at the line number mentioned in the error
3. Check for:
   - Missing quotes or brackets
   - Incorrect indentation
   - Escaped characters that shouldn't be escaped (`\'` should be `'`)
   - Leftover code from incomplete edits

### Handler Integrity Errors

If you see "File too short" errors:

1. The file was likely truncated by a script
2. Check git history: `git log --oneline -- path/to/file.py`
3. Restore from a previous commit: `git checkout <commit-hash> -- path/to/file.py`
4. Or restore from backup if available

### False Positive Warnings

Some warnings are expected:

- "Missing auth import" for simple public endpoints
- "Missing auth import" for Cognito trigger handlers
- These won't fail the validation, they're just informational

---

## Adding New Validation Checks

To add a new validation check:

1. Create a new script in `scripts/` (e.g., `check_something.py`)
2. Follow the pattern:
   - Print progress with emojis (🔍, ✅, ❌)
   - Exit with code 0 for success, 1 for failure
   - Provide clear error messages
3. Add it to `validate_all.py` in the `checks` list
4. Update this README

---

## Related Documentation

- [Deployment Scripts](deployment/README.md) - Build and deployment automation
- [Smoke Tests](deployment/smoke-test-production.js) - Post-deployment validation
