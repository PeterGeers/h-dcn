# Root Folder Reorganization - January 18, 2026

## Summary

Cleaned up the root directory by moving 100+ files into organized folders and deleting outdated files.

## Files Remaining in Root (Essential Config Only)

- `.awsCredentials.json` - AWS credentials
- `.cache_ggshield` - GitGuardian cache
- `.gitguardian.yaml` - GitGuardian config
- `.gitignore` - Git ignore rules
- `.gitlensrc` - GitLens config
- `.googleCredentials.json` - Google credentials
- `.secrets` - Secrets file
- `.secrets.example` - Secrets template
- `start.ps1` - Main startup script

## Files Moved

### To `scripts/maintenance/` (26 files)

One-off maintenance and migration scripts:

- `add_auth_layer_to_functions.py`
- `auto_assign_regional_roles.py`
- `centralize_auth_architecture.py`
- `cleanup_duplicate_roles.py`
- `cleanup-s3-bucket.ps1`
- `complete_role_migration.py`
- `create_missing_export_roles.py`
- `create_missing_groups.py`
- `create_regio_all_group.py`
- `create_regional_groups.py`
- `final_role_check.py`
- `fix_group_alignment.py`
- `fix_handler_fallback_pattern.py`
- `fix_handler_fallback_simple.py`
- `fix_indentation_after_else.py`
- `fix_sys_exit_in_handlers.py`
- `fix_verzoek_lid_group.py`
- `implement_simplified_roles.py`
- `migrate_cognito_users.py`
- `restore_and_fix_handlers.py`
- `restore_verzoek_lid_group.py`
- `selective_restore_handlers.py`
- `update_all_handlers_to_new_pattern.py`
- `update_codebase_roles.py`
- `update_regional_user_roles.py`
- `update_source_roles.py`
- `verify_regio_all.py`

### To `scripts/testing/` (47 files)

Test scripts for API endpoints, authentication, and integration:

- All `test_*.py` files (36 files)
- All `test-*.js` files (4 files)
- All `test-*.ps1` files (6 files)
- `trigger_real_request.py`

### To `scripts/debugging/` (34 files)

Debug and check scripts for logs, Cognito, DynamoDB:

- All `check_*.py` files (24 files)
- All `check-*.js` files (2 files)
- All `debug_*.py` files (3 files)
- All `decode_*.py` files (2 files)
- All `find_*.py` files (3 files)
- All `list_*.py` files (2 files)
- All `read_*.py` files (2 files)

### To `docs/archive/` (10 files)

Old documentation and planning files:

- `auth_alignment_plan.py`
- `auth_layer_alignment_check.md`
- `manual_testing_guide_current_roles.md`
- `member_self_service_field_alignment.md`
- `members_me_self_service_enhancement_proposal.md`
- `migration_data_quality_report_20260106_182410.json`
- `role_migration_plan.md`
- `SMART_FALLBACK_PATTERN.md`
- `test-task-buttons.md`
- `update_frontend_config.md`

### To `temp/old-tests/` (7 files)

Temporary test files and debug HTML:

- `debug_frontend_rendering.html`
- `debug-frontend-auth.html`
- `simple-oauth-test.js`
- `temp_frontend_test_runner.js`
- `test_cors_issue.html`
- `test-frontend-auth.html`
- `test-payload.json`

### To `temp/old-scripts/` (3 files)

Old utility scripts:

- `fixed-powershell-profile.ps1`
- `frontend_regional_filtering.ts`
- `simple-profile.ps1`

### To `temp/` (2 files)

Temporary config files:

- `response.json`
- `cloudfront-config.json`

## Files Deleted (Outdated)

- `test-parquet-generation.py` - Parquet system removed from production
- `test-parquet-file.parquet` - Parquet test data no longer needed

## Result

Root directory reduced from 100+ files to 9 essential configuration files. All scripts and documentation are now organized in appropriate subdirectories.

## Directory Structure

```
.
├── .kiro/                    # Kiro configuration
├── backend/                  # Backend Lambda functions
├── docs/                     # Documentation
│   ├── archive/             # Old documentation (10 files)
│   ├── architecture/
│   ├── authentication/
│   └── ...
├── frontend/                 # Frontend React app
├── scripts/                  # All scripts organized by purpose
│   ├── debugging/           # Debug/check scripts (34 files)
│   ├── deployment/          # Deployment scripts
│   ├── maintenance/         # One-off maintenance scripts (26 files)
│   ├── testing/             # Test scripts (47 files)
│   └── utilities/           # Utility scripts
├── temp/                     # Temporary files
│   ├── old-scripts/         # Old utility scripts (3 files)
│   └── old-tests/           # Old test files (7 files)
└── [9 config files]         # Essential configuration only
```

## Notes

- All moved files retain their original functionality
- No deployment scripts were affected
- Test scripts can still be run from their new locations
- Consider deleting files in `temp/` after verifying they're no longer needed
