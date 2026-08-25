#!/usr/bin/env python3
"""
Jednorazowe uzupełnienie `docs/api/history.json` do 30 dni wstecz.

`generate_api_json()` trzymało w API tylko 3 ostatnie skany, więc podstrona
„Historia skanów" (docs/scans.html) pokazywała 3 wiersze i 3 słupki, mimo że front
był na 30 gotowy od początku (`scans.slice(0, 30)`). Po zmianie retencji na
API_HISTORY_DAYS = 30 plik zapełniłby się dopiero po miesiącu — ten skrypt odtwarza
brakujące wpisy z `scan_history` w `data/dashboard_data.json` (1 wpis na skan,
90 pozycji wstecz), żeby historia była widoczna od razu.

CZEGO NIE DA SIĘ ODTWORZYĆ: `duration_seconds`, `price_changes`, `status`, `message`
i `alerts` nigdy nie trafiały do `scan_history`. Odtworzone wpisy dostają w tych polach
null / pustą listę oraz znacznik `"reconstructed": true`, żeby nie udawały pełnych
pomiarów — `scans.html` renderuje je z czasem „—" i pomija w wykresie czasu skanowania.
Wpisy już obecne w history.json (prawdziwe, z pełnymi danymi) mają pierwszeństwo
i NIE są nadpisywane.

Użycie:
    python rebuild_api_history_30d.py            # raport (dry-run)
    python rebuild_api_history_30d.py --apply
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

DATA_PATH = os.path.join("data", "dashboard_data.json")
HISTORY_PATH = os.path.join("docs", "api", "history.json")

RETENTION_DAYS = 30
MAX_ENTRIES = 60
RECENT = 10


def norm_ts(ts):
    """
    Wspólny klucz porównania timestampów. history.json trzyma ISO ze strefą
    ("2026-08-24T21:24:55Z"), a scan_history format ze spacją ("2026-08-24 21:24:55")
    — bez normalizacji te same skany trafiały do pliku dwa razy (raz jako pełny wpis,
    raz jako odtworzony).
    """
    if not ts:
        return ""
    return str(ts).replace("T", " ").replace("Z", "").strip()


def build_entry(sh_entry, labels):
    """Wpis history.json odtworzony z pozycji `scan_history`."""
    profiles = {}
    total = added = removed = 0
    errors = []

    for pk, pv in sh_entry.get("profiles", {}).items():
        count = pv.get("count", 0) or 0
        a = pv.get("added")
        r = pv.get("removed")
        crosscheck = pv.get("crosscheck", "unknown")
        # `ok` odtwarzamy tą samą regułą co generate_api_json: 0 ogłoszeń przy
        # crosscheck spoza listy „udanych" to błąd. Nie mamy tu stanu
        # current_listings z tamtej chwili, więc reguły `profile_empty` nie
        # stosujemy wstecz — nie zgadujemy.
        ok = not (count == 0 and crosscheck not in
                  ("passed", "passed_retry", "consistent", "best_of_two"))
        if not ok:
            errors.append(pk)
        profiles[pk] = {
            "label": labels.get(pk, pk),
            "count": count,
            "added": a,
            "removed": r,
            "new_listings": a,
            "price_changes": None,
            "crosscheck": crosscheck,
            "ok": ok,
            "error": None,
        }
        total += count
        added += a or 0
        removed += r or 0

    return {
        "timestamp": sh_entry.get("timestamp"),
        "date": sh_entry.get("date"),
        "status": None,
        "message": None,
        "alerts": [],
        "duration_seconds": None,
        "total_listings": total,
        "added": added,
        "removed": removed,
        "new_listings": added,
        "price_changes": None,
        "profiles_scanned": len(profiles),
        "errors": errors,
        "profiles": profiles,
        "reconstructed": True,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="zapisz (domyślnie dry-run)")
    args = ap.parse_args()

    for path in (DATA_PATH, HISTORY_PATH):
        if not os.path.exists(path):
            print(f"BŁĄD: brak {path} — uruchom z katalogu repo.")
            return 1

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    with open(HISTORY_PATH, encoding="utf-8") as f:
        history = json.load(f)

    try:
        import scraper
        labels = {pk: cfg["label"] for pk, cfg in scraper.PROFILES.items()}
    except Exception:
        labels = {}

    existing = {norm_ts(sc.get("timestamp")): sc for sc in history.get("scans", [])}
    print(f"history.json: {len(existing)} istniejących wpisów")

    today = datetime.now()
    cutoff = (today - timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%d")

    merged = dict(existing)
    added_n = 0
    for sh in data.get("scan_history", []):
        ts = norm_ts(sh.get("timestamp"))
        if not ts or (sh.get("date") or "") < cutoff:
            continue
        if ts in merged:
            continue                      # prawdziwy wpis wygrywa
        merged[ts] = build_entry(sh, labels)
        added_n += 1

    scans = sorted(merged.values(), key=lambda x: norm_ts(x.get("timestamp")))
    scans = [sc for sc in scans if (sc.get("date") or "") >= cutoff][-MAX_ENTRIES:]

    real = sum(1 for sc in scans if not sc.get("reconstructed"))
    print(f"Odtworzono ze scan_history: {added_n}")
    print(f"Po scaleniu: {len(scans)} wpisów ({real} pełnych, {len(scans)-real} odtworzonych)")
    if scans:
        print(f"Zakres dat: {scans[0].get('date')} … {scans[-1].get('date')}")

    if not args.apply:
        print("\n(dry-run — nic nie zapisano; dodaj --apply)")
        return 0

    out = {
        "last_updated": history.get("last_updated") or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "retention_days": RETENTION_DAYS,
        "scans": scans,
        "recent": list(reversed(scans))[:RECENT],
    }
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    size = os.path.getsize(HISTORY_PATH) / 1024
    print(f"\nZapisano {HISTORY_PATH} ({size:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
