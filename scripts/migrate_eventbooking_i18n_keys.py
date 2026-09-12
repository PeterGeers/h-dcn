#!/usr/bin/env python3
"""Conform the eventBooking i18n namespace to convention (depth<=2, snake_case).

Generic transform (handles locale drift uniformly):
  - snake_case every key (camelCase / UPPERCASE / mixed -> lower_snake)
  - flatten depth-3: a nested group `parent.child.leaf` becomes top-level
    `parent_child.leaf` (parent's own scalar leaves stay under `parent`).

Preserves translated values. Runs for src+public across all 8 locales. Idempotent
(snake_case of an already-snake key is unchanged; no depth-3 remains after a run).

Usage: python scripts/migrate_eventbooking_i18n_keys.py [--dry-run]
"""
import argparse, json, re, sys

LOCS = ["nl", "en", "de", "fr", "es", "it", "da", "sv"]
ROOTS = ["frontend/src/locales", "frontend/public/locales"]


def snake(k: str) -> str:
    # camelCase -> camel_case ; UPPER_SNAKE -> upper_snake ; leave dots alone
    s = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', '_', k)
    return s.lower()


def conform(d: dict) -> dict:
    """Return a depth<=2, snake_case version of the namespace dict."""
    out: dict = {}
    for k, v in d.items():
        sk = snake(k)
        if isinstance(v, dict):
            base = {}
            promoted = {}
            for kk, vv in v.items():
                skk = snake(kk)
                if isinstance(vv, dict):
                    # depth-3 subgroup -> promote to top-level `sk_skk`
                    promoted[f"{sk}_{skk}"] = {snake(x): y for x, y in vv.items()}
                else:
                    base[skk] = vv
            if base:
                out[sk] = base
            out.update(promoted)
        else:
            out[sk] = v
    return out


def depth(o, dd=0):
    if not isinstance(o, dict) or not o:
        return dd if not isinstance(o, dict) else dd + 1
    return max(depth(v, dd + 1) for v in o.values())


KEY = re.compile(r'^[a-z][a-z0-9_.]*[a-z0-9]$')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    for loc in LOCS:
        for root in ROOTS:
            p = f"{root}/{loc}/eventBooking.json"
            d = json.load(open(p, encoding="utf-8"))
            n = conform(d)
            dp = depth(n)
            bad = [f"{g}.{k}" for g, v in n.items() if isinstance(v, dict) for k in v if not KEY.match(k)]
            bad += [g for g in n if not KEY.match(g)]
            if dp > 2 or bad:
                print(f"PROBLEM {p}: depth={dp} bad={bad[:8]}"); sys.exit(1)
            if args.dry_run:
                print(f"[dry-run] {p} depth={dp} ok ({len(n)} groups)"); continue
            json.dump(n, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            open(p, "a").write("\n")
    print("eventBooking conformed OK (all depth<=2 snake_case)")


if __name__ == "__main__":
    main()
