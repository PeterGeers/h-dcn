# Vulture whitelist for the H-DCN backend (report-mode dead-code analysis).
#
# WHY THIS FILE EXISTS:
#   Vulture flags symbols it cannot see a static reference to. Several backend
#   symbols are referenced *dynamically* or by an *external* runtime (AWS Lambda,
#   pytest, API dispatch) that vulture's static scan cannot follow. Listing them
#   here suppresses those false positives WITHOUT deleting real code.
#
# FORMAT:
#   Vulture treats this file as ordinary Python. Any name that appears here counts
#   as "used". Reference each symbol as a bare attribute/name so vulture records a
#   use. Group entries and give EACH group a reason comment — an unexplained
#   whitelist entry is as dangerous as unexplained dead code.
#
# INVOCATION (report-mode; run from the repo root). Vulture treats the whitelist
# as a positional PATH, so it must come with the other paths BEFORE any option
# flag — placing it after `--min-confidence 80` makes argparse reject it:
#   unset VIRTUAL_ENV
#   backend/.venv/bin/vulture backend/handler backend/layers backend/.vulture_whitelist.py --min-confidence 80
#
# Complementary to ruff (ruff = within-file, vulture = cross-module). See
# docs/development/local-backend-testing.md. Whitelist the genuinely-referenced;
# fix only the genuinely-dead safe items during triage (T3.5).

# ---------------------------------------------------------------------------
# AWS Lambda entry points.
# Every handler exposes `lambda_handler(event, context)`. AWS invokes it by name
# at runtime; there is no static caller in the repo, so vulture flags it.
# ---------------------------------------------------------------------------
lambda_handler  # AWS Lambda runtime entry point (referenced by config, not code)
event           # Lambda handler signature param (AWS-supplied)
context         # Lambda handler signature param (AWS-supplied)

# ---------------------------------------------------------------------------
# Intentionally-retained public API (hdcn_cognito_admin/permission_utils.py).
# Consumed by callers / dispatched dynamically and proven by tests; vulture's
# static view does not see those references.
# ---------------------------------------------------------------------------
validate_field_permissions   # public permission API (permission_utils.py)
get_user_field_permissions   # public permission API (permission_utils.py)
check_role_permission        # public permission API (permission_utils.py)
get_role_summary             # public permission API (permission_utils.py)

# ---------------------------------------------------------------------------
# Shared auth-layer contract (backend/layers/auth-layer/python/shared).
# Re-exported / imported by handlers via the try/except ImportError fallback;
# some are used only in the degraded (maintenance_fallback) path.
# ---------------------------------------------------------------------------
create_smart_fallback_handler  # maintenance fallback, used only when layer import fails
# ---------------------------------------------------------------------------
# Shared auth-layer public API (backend/layers/auth-layer/python/shared/*).
# T3.5 triage: vulture flagged these at 60% confidence. They are public
# library functions/methods the shared layer EXPOSES to handlers and tests
# across the layer boundary — a boundary vulture's per-invocation static scan
# does not cross. Conservative call per dead-code steering: shared-layer public
# API at low confidence is whitelisted, NOT deleted. Re-audit if a future
# blocking-mode pass raises confidence with cross-layer analysis.
# ---------------------------------------------------------------------------
to_error_response                    # mollie_client.py — public error mapper
verify_webhook_signature             # mollie_client.py — public webhook verifier (security-relevant; keep)
validate_fulfilment_transition       # order_state_machine.py — public state-machine API
get_valid_transitions_for_actor      # order_state_machine.py — public state-machine API
get_next_valid_states                # order_state_machine.py — public state-machine API
validate_variant_attributes          # product_validation.py — public validation API
validate_variant_schema              # product_validation.py — public validation API
get_regional_permissions             # role_permissions.py — public permissions API
get_organizational_role_combination  # role_permissions.py — public permissions API
assign_organizational_role           # role_permissions.py — public permissions API
validate_organizational_role_structure  # role_permissions.py — public permissions API
get_all_organizational_roles         # role_permissions.py — public permissions API
