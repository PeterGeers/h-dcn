#!/usr/bin/env python3
"""
Conform the `workflows` i18n namespace to the project convention
(Requirement 10.2/10.3: max nesting depth 2, lowercase snake_case keys).

Transforms each locale's workflows.json by:
  - promoting membership.<subgroup> -> membership_<subgroup> (depth 3 -> 2)
  - promoting welcomePack.columns -> welcome_pack_columns
  - renaming welcomePack -> welcome_pack
  - snake_casing camelCase leaf keys

Preserves each locale's translated VALUES; only restructures/renames KEYS.
Runs for both src/locales and public/locales, all 8 locales.

Usage:
    python scripts/migrate_workflows_i18n_keys.py            # apply
    python scripts/migrate_workflows_i18n_keys.py --dry-run  # preview
"""
import argparse
import json
import os
import sys

LOCALES = ["nl", "en", "de", "fr", "es", "it", "da", "sv"]
ROOTS = [
    "frontend/src/locales",
    "frontend/public/locales",
]

# Leaf-key rename map (camelCase -> snake_case) applied within any group.
LEAF_RENAMES = {
    "paymentReceived": "payment_received",
    "approvePayment": "approve_payment",
    "transitionFailed": "transition_failed",
    "regionRequired": "region_required",
    "reasonRequired": "reason_required",
    "notInWorkflow": "not_in_workflow",
    "selectSameStatus": "select_same_status",
    "reasonPlaceholder": "reason_placeholder",
    "triggeredBy": "triggered_by",
    "tabTitle": "tab_title",
    "selectAll": "select_all",
    "markSent": "mark_sent",
    "bulkMarkSent": "bulk_mark_sent",
    "sentSuccess": "sent_success",
    "sentError": "sent_error",
    "bulkSuccess": "bulk_success",
    "bulkPartialError": "bulk_partial_error",
    "noAddress": "no_address",
    "addressIncomplete": "address_incomplete",
    "memberNumber": "member_number",
    "activationDate": "activation_date",
}

# membership sub-groups that get promoted to top-level membership_<name>
MEMBERSHIP_SUBGROUPS = [
    "confirm", "description", "status", "errors", "bulk", "fields", "timeline",
]


def rename_leaf(k: str) -> str:
    return LEAF_RENAMES.get(k, k)


def conform(data: dict) -> dict:
    out: dict = {}
    membership = data.get("membership", {})
    # direct action keys (non-dict values) stay under 'membership'
    out["membership"] = {
        rename_leaf(k): v for k, v in membership.items() if not isinstance(v, dict)
    }
    # sub-groups -> membership_<group>
    for grp in MEMBERSHIP_SUBGROUPS:
        if grp in membership and isinstance(membership[grp], dict):
            out[f"membership_{grp}"] = {
                rename_leaf(k): v for k, v in membership[grp].items()
            }
    # welcomePack -> welcome_pack (+ columns promoted)
    wp = data.get("welcomePack", {})
    out["welcome_pack"] = {
        rename_leaf(k): v for k, v in wp.items() if not isinstance(v, dict)
    }
    if isinstance(wp.get("columns"), dict):
        out["welcome_pack_columns"] = {
            rename_leaf(k): v for k, v in wp["columns"].items()
        }
    # history stays as-is (already depth 2, snake_case)
    if "history" in data:
        out["history"] = data["history"]
    return out


def max_depth(obj, d=0):
    if not isinstance(obj, dict) or not obj:
        return d if not isinstance(obj, dict) else d + 1
    return max(max_depth(v, d + 1) for v in obj.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    changed = 0
    for root in ROOTS:
        for loc in LOCALES:
            path = os.path.join(root, loc, "workflows.json")
            if not os.path.exists(path):
                print(f"  SKIP (missing): {path}")
                continue
            data = json.load(open(path, encoding="utf-8"))
            # nl src is already conformed by hand; skip transforming an
            # already-conformed file (idempotent: no 'welcomePack'/nested membership)
            already = "welcomePack" not in data and not any(
                isinstance(v, dict) for v in data.get("membership", {}).values()
            )
            new = data if already else conform(data)
            depth = max_depth(new)
            if depth > 2:
                print(f"  ERROR depth {depth} > 2 after transform: {path}")
                sys.exit(1)
            if args.dry_run:
                print(f"  [dry-run] would write {path} (depth {depth}, "
                      f"{'already conformed' if already else 'transformed'})")
                continue
            with open(path, "w", encoding="utf-8") as f:
                json.dump(new, f, ensure_ascii=False, indent=2)
                f.write("\n")
            print(f"  wrote {path} (depth {depth})")
            changed += 1
    print(f"Done. {changed} files written.")


if __name__ == "__main__":
    main()
