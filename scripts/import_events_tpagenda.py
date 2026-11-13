"""
Import the edited TP-Agenda CSV (TPAgenda_2027_H-DCN.csv) into the DynamoDB Events table.

CSV format (semicolon-delimited, UTF-8):
    startdatum;einddatum;naam;regio;locatie;plaats;voorlopig;Type

    startdatum/einddatum : d-m-Y (e.g. 18-6-2027)
    naam                 : event name (taken verbatim)
    regio                : Dutch region label (mapped to EVENT_REGIOS enum)
    locatie, plaats      : merged into the single `location` field
    voorlopig            : Draft -> status draft, Publish -> status published
    Type                 : Dutch type label (mapped to EVENT_TYPES registry key)

Duplicate handling:
    Existing events keep their values and are never modified. A row whose
    (date + fuzzy name/location) matches an existing event is SKIPPED.
    Existing start_date values are ISO with a time suffix (2027-06-18T00:00),
    so dedup compares on the date part only.

Usage (run from repo root; needs `pip install python-docx` is NOT required here):
    python scripts/import_events_tpagenda.py --input-file "/mnt/c/Users/peter/Downloads/TPAgenda_2027_H-DCN.csv" --dry-run
    python scripts/import_events_tpagenda.py --input-file <csv>            # live import
    python scripts/import_events_tpagenda.py --input-file <csv> --profile nonprofit-deploy
"""

from __future__ import annotations

import argparse
import csv
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3

from import_events_stan import generate_slug
from shared import event_dedup

PARTICIPATION: str = "open"
IMPORT_SOURCE: str = "manual"  # registry enum has no "csv"/"pdf"; "manual" is closest

# --- Type label -> registry key -------------------------------------------
TYPE_MAP: dict[str, str] = {
    "nationaal treffen": "nationaal_treffen",
    "internationaal treffen": "internationaal_treffen",
    "rlv": "rlv",
    "vbv": "vbv",
    "alv": "alv",
    "regio rit": "regio_rit",
    "regiorit": "regio_rit",
    "openingsrit": "openingsrit",
    "sluitingsrit": "sluitingsrit",
    "presmeet": "presmeet",
    "tourweekend": "tourweekend",
    "anders": "other",
    "other": "other",
}

# event_type -> event_category (from EVENT_TYPES_BY_CATEGORY)
CATEGORY_MAP: dict[str, str] = {
    "presmeet": "vergadering", "alv": "vergadering", "rlv": "vergadering",
    "vbv": "vergadering", "vergader_queue": "vergadering",
    "internationaal_treffen": "rally", "nationaal_treffen": "rally",
    "openingsrit": "rit", "regio_rit": "rit", "tourweekend": "rit", "sluitingsrit": "rit",
    "webshop": "overig", "other": "overig",
}

# --- Region label -> EVENT_REGIOS enum -------------------------------------
REGIO_MAP: dict[str, str] = {
    "overig": "Overig",
    "alle regio's (landelijk)": "regio_all",
    "landelijk": "regio_all",
    "noord-holland": "Noord-Holland",
    "noord-halland": "Noord-Holland",  # typo in source
    "zuid-holland": "Zuid-Holland",
    "z-holland": "Zuid-Holland",
    "friesland": "Friesland",
    "utrecht": "Utrecht",
    "oost": "Oost",
    "limburg": "Limburg",
    "groningen/drenthe": "Groningen/Drenthe",
    "gron/drenth": "Groningen/Drenthe",
    "noord-brabant/zeeland": "Brabant/Zeeland",
    "brabant/zeeland": "Brabant/Zeeland",
    "n-brabant/zeeland": "Brabant/Zeeland",
    "duitsland": "Duitsland",
}

STATUS_MAP: dict[str, str] = {
    "draft": "draft", "publish": "published", "published": "published", "archived": "archived",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import the edited TP-Agenda CSV into the Events table.",
    )
    parser.add_argument("--input-file", required=True, help="Path to TPAgenda_2027_H-DCN.csv")
    parser.add_argument("--profile", default="nonprofit-deploy", help="AWS profile (default: nonprofit-deploy)")
    parser.add_argument("--table", default="Events", help="DynamoDB table (default: Events)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen, write nothing")
    return parser.parse_args()


def parse_date(value: str) -> str | None:
    """Parse d-m-Y (and a few variants) to YYYY-MM-DD."""
    cleaned = value.strip()
    if not cleaned:
        return None
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%y"):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def map_type(label: str) -> str | None:
    return TYPE_MAP.get(label.strip().lower())


def map_regio(label: str) -> str | None:
    return REGIO_MAP.get(label.strip().lower())


def merge_location(locatie: str, plaats: str) -> str:
    parts = [p.strip() for p in (locatie, plaats) if p and p.strip()]
    return ", ".join(parts)


def build_item(row: dict[str, str]) -> tuple[dict[str, Any] | None, list[str]]:
    """Map a CSV row to a DynamoDB item. Returns (item, errors)."""
    errors: list[str] = []

    name = (row.get("naam") or "").strip()
    if not name:
        errors.append("lege naam")

    start_date = parse_date(row.get("startdatum", ""))
    if start_date is None:
        errors.append(f"ongeldige startdatum: {row.get('startdatum','')!r}")

    end_date = parse_date(row.get("einddatum", "")) if (row.get("einddatum") or "").strip() else None

    event_type = map_type(row.get("Type", ""))
    if event_type is None:
        errors.append(f"onbekend Type: {row.get('Type','')!r}")

    linked_regio = map_regio(row.get("regio", ""))
    if linked_regio is None:
        errors.append(f"onbekende regio: {row.get('regio','')!r}")

    status = STATUS_MAP.get((row.get("voorlopig") or "").strip().lower(), "draft")

    if errors:
        return None, errors

    location = merge_location(row.get("locatie", ""), row.get("plaats", ""))
    year = start_date[:4]

    item: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "name": name,
        "slug": f"{generate_slug(name)}-{year}",
        "event_type": event_type,
        "event_category": CATEGORY_MAP.get(event_type, "overig"),
        "participation": PARTICIPATION,
        "linked_regio": linked_regio,
        "start_date": start_date,
        "status": status,
        "import_source": IMPORT_SOURCE,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if end_date:
        item["end_date"] = end_date
    if location:
        item["location"] = location
    return item, []


def main() -> None:
    args = parse_args()

    path = Path(args.input_file)
    if not path.exists():
        print(f"\n  ✗ Bestand niet gevonden: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    content = path.read_text(encoding="utf-8-sig")
    delimiter = ";" if content.splitlines()[0].count(";") >= content.splitlines()[0].count(",") else ","
    reader = csv.DictReader(content.splitlines(), delimiter=delimiter)
    rows = list(reader)

    print(f"\n[import_events_tpagenda] {len(rows)} rij(en) uit '{args.input_file}' (delimiter '{delimiter}')")

    session = boto3.Session(profile_name=args.profile, region_name="eu-west-1")
    table = session.resource("dynamodb").Table(args.table)
    try:
        table.load()
    except Exception as e:
        print(f"\n  ✗ Kan geen verbinding maken met DynamoDB: {e}", file=sys.stderr)
        sys.exit(1)

    # Preload all existing events once (110 items) to dedup on date prefix.
    existing: list[dict[str, Any]] = []
    r = table.scan()
    existing += r["Items"]
    while "LastEvaluatedKey" in r:
        r = table.scan(ExclusiveStartKey=r["LastEvaluatedKey"])
        existing += r["Items"]

    def find_existing(name: str, start_date: str, location: str) -> dict[str, Any] | None:
        for ev in existing:
            ev_date = str(ev.get("start_date", ""))[:10]  # trim time suffix
            if ev_date != start_date:
                continue
            if event_dedup.fuzzy_name_match(name, ev.get("name", "")):
                return ev
        return None

    mode = "DRY-RUN" if args.dry_run else "LIVE"
    print(f"[import_events_tpagenda] Verwerken ({mode})\n")

    created = skipped = errors = 0
    for i, row in enumerate(rows, start=1):
        item, errs = build_item(row)
        prefix = f"  [{i}/{len(rows)}]"
        if item is None:
            print(f"{prefix} ✗ ONGELDIG: {row.get('naam','?')} — {'; '.join(errs)}")
            errors += 1
            continue

        rng = item["start_date"] + (f" → {item['end_date']}" if "end_date" in item else "")
        match = find_existing(item["name"], item["start_date"], item.get("location", ""))
        if match is not None:
            print(f"{prefix} ⚠ OVERGESLAGEN (bestaat al): '{item['name']}' ({rng}) "
                  f"≈ '{match.get('name','?')}' [{match.get('event_id','?')}]")
            skipped += 1
            continue

        label = f"{item['name']} | {rng} | {item['event_type']} | {item['linked_regio']} | {item['status']} | {item.get('location','(geen locatie)')}"
        if args.dry_run:
            print(f"{prefix} ✓ ZOU AANMAKEN: {label}")
            created += 1
            continue

        try:
            table.put_item(Item=item)
            print(f"{prefix} ✓ AANGEMAAKT: {label} [{item['event_id']}]")
            created += 1
        except Exception as e:
            print(f"{prefix} ✗ FOUT bij schrijven '{item['name']}': {e}")
            errors += 1

    print(f"\n{'=' * 60}")
    print(f"  Modus: {mode} | Totaal: {len(rows)} | Aangemaakt: {created} | "
          f"Overgeslagen: {skipped} | Fouten: {errors}")
    print(f"{'=' * 60}\n")

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
