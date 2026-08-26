#!/usr/bin/env python3
"""
Jednorazowa korekta dziennych liczników `removed` (metryka „Zniknęło") po lawinie
archiwizacji z 2026-08-24 — druga połowa naprawy danych po blokadzie TLS
(patrz CHANGELOG 2026-08-24/2026-08-26 i §7 CLAUDE.md).

Kontekst: przez blokadę 403 archiwizacja stała 13 dni, a pierwszy skan po naprawie
zarchiwizował 362 ogłoszenia naraz. `rebuild_archived_dates_20260824.py` poprawił
`archived_date` tych ogłoszeń (odtworzył realną datę zniknięcia z `missed_scans`),
przez co wykres „Odpływ ofert" na trend.html jest już poprawny. Ale ta sama informacja
żyje w danych DRUGI raz — jako `daily_counts[].removed` — i tam korekta nie dotarła:

    2026-08-12..23: removed = 0    (blokada: verify_listing_active zwracała „aktywne")
    2026-08-24:     removed = 362  (lawina — 13 dni odpływu w jednej dobie)

To źródło wykresu „📈 Przybyło/Zniknęło" na dashboardzie (docs/index.html, oba widoki:
90 dni z `daily_counts` i „Cała historia" z `trend_full.json`, który dla dni obecnych
w `daily_counts` bierze wartości AUTORYTATYWNE stamtąd). Efekt: pionowy pik 362 przy
tle ~25/dobę i płaskie zero przez poprzednie 13 dni.

Skrypt PRZENOSI dokładnie te zniknięcia, które poprawił skrypt dat archiwizacji —
nic nie zgaduje i niczego nie przelicza od zera:

  * dla każdego ogłoszenia z `archived_date_corrected` bierze parę
    (`archived_date_original` → `archived_date`),
  * dzień docelowy dostaje +1 do `removed`, dzień lawiny -1,
  * suma zniknięć w oknie incydentu zostaje bez zmian.

Świadomie NIE przelicza `removed` z całego archiwum (`archived_date == D`): ogłoszenie
zarchiwizowane i później reaktywowane wraca do `current_listings` i znika z archiwum,
więc czysta projekcja zaniżyłaby stare dni (np. poqui 2026-08-24: removed=3, w archiwum
został 1 wpis). Przenoszenie różnicowe tego problemu nie ma.

Profile użytkowników (mzuri, poqui, ...) NIE są ruszane: przez blokadę ich skany
kończyły się błędem, więc ochrona „count == 0 nie nadpisuje" w ogóle nie utworzyła
wpisów `daily_counts` za 12–23.08 (jest tam luka, nie zera), a ich ogłoszenia nie mają
`archived_date_corrected` — nie da się ustalić, którego dnia zniknęły. Wartość z 24.08
jest dla nich uczciwym „odpływem od ostatniego pomiaru".

Idempotencja: poprawiony wpis `daily_counts` dostaje `removed_corrected: true`
(+ `removed_original` z wartością sprzed korekty), więc drugi przebieg go pomija.

Użycie:
    python rebuild_daily_removed_20260824.py            # raport (dry-run)
    python rebuild_daily_removed_20260824.py --apply    # zapis do data/dashboard_data.json

Po zapisie przelicz `docs/api/trend_full.json`:
    python -c "import scraper; scraper.generate_trend_full()"
"""

import argparse
import json
import os
import sys
from collections import Counter

DATA_PATH = os.path.join("data", "dashboard_data.json")


def collect_moves(prof):
    """
    Zwraca (moved_to, moved_from) — liczniki przeniesionych zniknięć per dzień.
    Źródłem jest wyłącznie znacznik `archived_date_corrected` zostawiony przez
    rebuild_archived_dates_20260824.py.
    """
    moved_to = Counter()
    moved_from = Counter()
    for l in prof.get("archived_listings", []):
        if not l.get("archived_date_corrected"):
            continue
        old = str(l.get("archived_date_original") or "")[:10]
        new = str(l.get("archived_date") or "")[:10]
        if len(old) != 10 or len(new) != 10 or old == new:
            continue
        moved_to[new] += 1
        moved_from[old] += 1
    return moved_to, moved_from


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="zapisz zmiany (domyślnie tylko raport)")
    args = ap.parse_args()

    if not os.path.exists(DATA_PATH):
        print(f"BŁĄD: brak {DATA_PATH} — uruchom z katalogu repo.")
        return 1

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    total_changed = 0
    total_orphan = 0

    for pk, prof in data.get("profiles", {}).items():
        moved_to, moved_from = collect_moves(prof)
        if not moved_to:
            continue

        dc_by_date = {e["date"]: e for e in prof.get("daily_counts", []) if e.get("date")}
        print(f"[{pk}] przeniesionych zniknięć: {sum(moved_to.values())}")

        # Delta per dzień: dzień lawiny na minus, dni realnego zniknięcia na plus.
        delta = Counter()
        for d, n in moved_to.items():
            delta[d] += n
        for d, n in moved_from.items():
            delta[d] -= n

        for d in sorted(delta):
            n = delta[d]
            if n == 0:
                continue
            entry = dc_by_date.get(d)
            if entry is None:
                # Dzień poza oknem daily_counts (starszy niż 90 dni) — nie ma czego poprawiać.
                if n > 0:
                    total_orphan += n
                    print(f"   {d}: {n:+d} — brak wpisu w daily_counts (poza oknem 90 dni), pomijam")
                continue
            if entry.get("removed_corrected"):
                print(f"   {d}: już poprawione (removed={entry.get('removed')}) — pomijam")
                continue
            before = entry.get("removed")
            after = max(0, (before or 0) + n)
            entry["removed_original"] = before
            entry["removed"] = after
            entry["removed_corrected"] = True
            total_changed += 1
            print(f"   {d}: removed {before} → {after}  ({n:+d})")

    print()
    print(f"Wpisów daily_counts do poprawy: {total_changed}")
    if total_orphan:
        print(f"Zniknięć bez wpisu w daily_counts (poza oknem): {total_orphan}")

    if not args.apply:
        print("\n(dry-run — nic nie zapisano; dodaj --apply)")
        return 0

    if total_changed == 0:
        print("\nNic do zapisania.")
        return 0

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"\nZapisano {DATA_PATH}.")
    print('Pamiętaj: przelicz trend_full.json — python -c "import scraper; scraper.generate_trend_full()"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
