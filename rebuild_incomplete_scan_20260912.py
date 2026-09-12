#!/usr/bin/env python3
"""
Naprawa danych po skanie z urwaną paginacją (2026-09-12, profil `wszystkie_pokoje`).

Kontekst
--------
Poranny skan 2026-09-12 08:47 UTC pobrał 612 z 883 ogłoszeń kategorii — paginacja
Playwright urwała się na stronie 16 (OLX oddał stronę bez kart ogłoszeń). 612/883
to 69%, czyli POWYŻEJ progu HEADER_SHORTFALL_RATIO (50%), więc ochrona danych się
nie włączyła i skan zapisał się jako poprawny:
  * `daily_counts[2026-09-12].count = 612` (wykres 90-dniowy na index.html),
  * wpis w ledgerze `daily_summary.ndjson` (wykres „Cała historia" na trend.html).
Efekt: fałszywy dołek -267 ogłoszeń w trendzie w dniu, w którym OLX deklarował 879.

Ogłoszenia per-sztuka NIE ucierpiały: 267 nieobecnych w skanie zostało zweryfikowanych
przez verify_listing_active() i zachowanych w current_listings z missed_scans=1
(mechanizm rotacji wyników OLX z 2026-07-18). Archiwizacja też była weryfikowana
sztuka po sztuce, więc archived_date z tego dnia zostają nietknięte.

Co robi ten skrypt
------------------
1. `data/dashboard_data.json` — w `daily_counts` profilu `wszystkie_pokoje` dla dnia
   2026-09-12 podmienia `count` 612 -> 879 (liczba deklarowana przez nagłówek OLX
   w tym samym dniu) oraz `change` -267 -> 0 (badge „zmiana" na kafelku profilu
   w index.html), zostawiając ślad korekty: `count_original`/`change_original`
   + `count_corrected`.
2. `data/history/daily_summary.ndjson` — ledger jest APPEND-ONLY, więc błędnej linii
   nie ruszamy; DOPISUJEMY rekord korygujący z późniejszą godziną (czytnik bierze
   per dzień wpis o największym `time`, patrz generate_trend_full).
3. Przelicza `docs/api/trend_full.json`, żeby oba wykresy zgadzały się od razu.

Idempotentny. Domyślnie dry-run; zapis dopiero z `--apply`.
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE, "data", "dashboard_data.json")
LEDGER = os.path.join(BASE, "data", "history", "daily_summary.ndjson")

PROFILE = "wszystkie_pokoje"
DATE = "2026-09-12"
BAD_COUNT = 612
GOOD_COUNT = 879          # nagłówek OLX ze skanu 11:21 UTC tego samego dnia
CORRECTION_TIME = "23:59"  # późniejsza niż którykolwiek skan tego dnia


def fix_dashboard(apply_changes):
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    pd_ = data.get("profiles", {}).get(PROFILE)
    if not pd_:
        print(f"[dashboard] brak profilu {PROFILE} — pomijam")
        return False

    entry = next((e for e in pd_.get("daily_counts", []) if e.get("date") == DATE), None)
    if entry is None:
        print(f"[dashboard] brak wpisu daily_counts {DATE} — nic do naprawy")
        return False
    if entry.get("count_corrected"):
        print(f"[dashboard] wpis {DATE} już poprawiony (count={entry.get('count')}) — pomijam")
        return False
    if entry.get("count") != BAD_COUNT:
        print(f"[dashboard] wpis {DATE} ma count={entry.get('count')} (oczekiwano {BAD_COUNT}) — pomijam")
        return False

    # `change` (badge na kafelku profilu) liczony jest względem poprzedniego dnia
    prev = None
    for e in pd_.get("daily_counts", []):
        if e.get("date") < DATE:
            prev = e
    new_change = GOOD_COUNT - prev["count"] if prev else 0

    print(f"[dashboard] {PROFILE} {DATE}: count {BAD_COUNT} -> {GOOD_COUNT}, "
          f"change {entry.get('change')} -> {new_change} (+ ślad korekty)")
    if not apply_changes:
        return True

    entry["count_original"] = BAD_COUNT
    entry["count_corrected"] = True
    entry["count"] = GOOD_COUNT
    if entry.get("change") != new_change:
        entry["change_original"] = entry.get("change")
        entry["change"] = new_change
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
    return True


def fix_ledger(apply_changes):
    with open(LEDGER, encoding="utf-8") as f:
        lines = [l for l in f.read().splitlines() if l.strip()]

    for l in lines:
        try:
            rec = json.loads(l)
        except json.JSONDecodeError:
            continue
        if (rec.get("date") == DATE and rec.get("profile") == PROFILE
                and rec.get("source") == "correction"):
            print(f"[ledger] rekord korygujący dla {DATE}/{PROFILE} już istnieje — pomijam")
            return False

    rec = {
        "date": DATE,
        "time": CORRECTION_TIME,
        "profile": PROFILE,
        "count": GOOD_COUNT,
        "crosscheck": "corrected",
        "change": 0,
        "source": "correction",
        "note": (f"skan {DATE} 08:47 UTC pobrał {BAD_COUNT} z 883 (urwana paginacja Playwright); "
                 f"count z nagłówka OLX — patrz rebuild_incomplete_scan_20260912.py"),
    }
    print(f"[ledger] dopisuję rekord korygujący: count={GOOD_COUNT} (append-only, błędna linia zostaje)")
    if not apply_changes:
        return True
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return True


def main():
    apply_changes = "--apply" in sys.argv
    if not apply_changes:
        print("=== DRY-RUN (dodaj --apply, żeby zapisać) ===")

    changed = fix_dashboard(apply_changes)
    changed = fix_ledger(apply_changes) or changed

    if apply_changes and changed:
        import scraper
        scraper.generate_trend_full()
        print("[trend_full] przeliczony")
    print("Gotowe.")


if __name__ == "__main__":
    main()
