#!/usr/bin/env python3
"""
Jednorazowa korekta dat archiwizacji po blokadzie TLS z 2026-08-12
(patrz CHANGELOG 2026-08-24 i §7 CLAUDE.md).

Od skanu 2026-08-12 OLX blokował każde zapytanie `requests` (403), przez co
verify_listing_active() wpadała w gałąź fail-safe „zakładam aktywne" i archiwizacja
stanęła całkowicie. Martwe ogłoszenia zostawały w current_listings z rosnącym
licznikiem `missed_scans` (do 13). Pierwszy skan po naprawie archiwizuje je wszystkie
naraz — z datą DNIA NAPRAWY, a nie datą realnego zniknięcia. Bez korekty wykres
„Odpływ ofert" (docs/trend.html, źródło: trend_full.json.outflow) dostaje sztuczny
pik kilkuset ogłoszeń w jednym dniu, a poprzednie ~13 dni pokazuje zero.

Prawdziwą datę da się odtworzyć, bo `missed_scans` przeżywa archiwizację: ogłoszenie
z missed_scans == N było nieobecne w skanie archiwizującym ORAZ w N skanach przed nim,
więc po raz pierwszy zniknęło w skanie oddalonym o N pozycji wstecz.

    archived_date = data skanu o indeksie (k - N),  gdzie k = indeks skanu archiwizującego

Lista dat skanów pochodzi z `daily_counts` profilu (1 wpis na dobę ze skanem).

Uruchamiać PO pierwszym udanym skanie z curl_cffi. Domyślnie tylko raportuje —
zapis wymaga jawnego `--apply`. Skrypt jest idempotentny (poprawione wpisy dostają
znacznik `archived_date_corrected`, więc drugi przebieg ich nie rusza).

Użycie:
    python rebuild_archived_dates_20260824.py            # raport (dry-run)
    python rebuild_archived_dates_20260824.py --apply    # zapis do data/dashboard_data.json
    python rebuild_archived_dates_20260824.py --date 2026-08-25 --apply
"""

import argparse
import json
import os
import sys
from collections import Counter

DATA_PATH = os.path.join("data", "dashboard_data.json")

# Pierwszy skan dotknięty blokadą TLS. Twarda granica zakresu: ogłoszenia zarchiwizowane
# WCZEŚNIEJ zniknęły przy działającej weryfikacji i ich daty są poprawne — nie ruszamy ich,
# nawet jeśli mają missed_scans > 0 (normalna rotacja wyników OLX, potem realna śmierć).
INCIDENT_START = "2026-08-12"


def scan_dates(profile):
    """Uporządkowana lista dat skanów profilu (z daily_counts, 1 wpis na dobę)."""
    return [e["date"] for e in profile.get("daily_counts", []) if e.get("date")]


def correct_date(dates, avalanche_date, missed_scans):
    """
    Zwraca datę pierwszego skanu, w którym ogłoszenia zabrakło, albo None gdy
    historia dat jest za krótka, żeby to policzyć (nie zgadujemy — zostawiamy jak jest).
    """
    if avalanche_date not in dates:
        return None
    k = dates.index(avalanche_date)
    idx = k - missed_scans
    if idx < 0:
        return None
    return dates[idx]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="zapisz zmiany (domyślnie tylko raport)")
    ap.add_argument("--date", default=None,
                    help="dzień lawiny archiwizacji YYYY-MM-DD (domyślnie: wykryty automatycznie)")
    args = ap.parse_args()

    if not os.path.exists(DATA_PATH):
        print(f"BŁĄD: brak {DATA_PATH} — uruchom z katalogu repo.")
        return 1

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # Dzień lawiny = dzień, w którym zarchiwizowano najwięcej ogłoszeń MAJĄCYCH missed_scans.
    # (Zwykła archiwizacja daje missed_scans == 0 — ogłoszenie znika i od razu jest sprawdzone.)
    if args.date:
        avalanche = args.date
    else:
        c = Counter()
        for prof in data.get("profiles", {}).values():
            for l in prof.get("archived_listings", []):
                d = (l.get("archived_date") or "")[:10]
                if (l.get("missed_scans") or 0) > 0 and d >= INCIDENT_START:
                    c[d] += 1
        if not c:
            print(f"Nic do poprawienia: brak archiwizacji z missed_scans > 0 od {INCIDENT_START}.")
            print("Czy pierwszy skan po naprawie curl_cffi już się wykonał?")
            return 0
        avalanche = c.most_common(1)[0][0]
        print(f"Wykryty dzień lawiny archiwizacji: {avalanche} ({c[avalanche]} ogłoszeń)")

    total_fixed = 0
    total_skipped = 0
    per_date = Counter()

    for pk, prof in data.get("profiles", {}).items():
        dates = scan_dates(prof)
        fixed_here = 0
        for l in prof.get("archived_listings", []):
            if l.get("archived_date_corrected"):
                continue                                    # idempotencja
            n = l.get("missed_scans") or 0
            if n <= 0 or not l.get("archived_date"):
                continue
            if l["archived_date"][:10] != avalanche:
                continue
            if avalanche < INCIDENT_START:
                continue  # poza oknem incydentu — nie przepisujemy starych danych

            new_date = correct_date(dates, avalanche, n)
            if new_date is None or new_date == avalanche:
                total_skipped += 1
                continue

            old = l["archived_date"]
            # Zachowujemy porę dnia z oryginalnego wpisu — liczy się część dzienna,
            # bo wykres odpływu grupuje po archived_date[:10].
            l["archived_date"] = new_date + old[10:]
            l["archived_date_corrected"] = True
            l["archived_date_original"] = old
            per_date[new_date] += 1
            fixed_here += 1
            total_fixed += 1

        if fixed_here:
            print(f"  [{pk}] poprawiono {fixed_here} dat archiwizacji")

    print()
    print(f"Do poprawy: {total_fixed}   pominięte (za krótka historia dat): {total_skipped}")
    if per_date:
        print("Rozkład po korekcie:")
        for d in sorted(per_date):
            print(f"   {d}: {per_date[d]}")

    if not args.apply:
        print("\n(dry-run — nic nie zapisano; dodaj --apply)")
        return 0

    if total_fixed == 0:
        print("\nNic do zapisania.")
        return 0

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"\nZapisano {DATA_PATH}.")
    print("Pamiętaj: przelicz trend_full.json (uruchom skan albo generate_trend_full()).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
