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

Lista skanów pochodzi z LEDGERA `data/history/daily_summary.ndjson` (1 linia = 1 skan
danego profilu), a NIE z `daily_counts`. To istotne: `daily_counts` ma 1 wpis na DOBĘ, więc
dzień z dwoma skanami (jak 2026-08-24: zepsuty 11:22 i naprawczy 17:27) zlewa się w jeden
wpis i całe mapowanie przesuwa się o jeden dzień wstecz. Ledger i licznik `missed_scans`
rosną dokładnie na tych samych skanach (oba pomijane przy błędzie scrapera), więc indeksy
się zgadzają.

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
LEDGER_PATH = os.path.join("data", "history", "daily_summary.ndjson")

# Pierwszy skan dotknięty blokadą TLS. Twarda granica zakresu: ogłoszenia zarchiwizowane
# WCZEŚNIEJ zniknęły przy działającej weryfikacji i ich daty są poprawne — nie ruszamy ich,
# nawet jeśli mają missed_scans > 0 (normalna rotacja wyników OLX, potem realna śmierć).
INCIDENT_START = "2026-08-12"


def load_scan_sequences():
    """
    {profil: [data_skanu, ...]} w kolejności chronologicznej — po JEDNYM wpisie na SKAN
    (dzień z dwoma skanami daje dwie pozycje z tą samą datą).
    """
    seqs = {}
    with open(LEDGER_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("profile") and e.get("date"):
                seqs.setdefault(e["profile"], []).append(e["date"])
    return seqs


def correct_date(seq, missed_scans):
    """
    Data pierwszego skanu, w którym ogłoszenia zabrakło.

    Ogłoszenie z missed_scans == N było nieobecne w N skanach PRZED skanem
    archiwizującym (ostatnia pozycja `seq`) oraz w nim samym, więc pierwszy skan bez
    niego to seq[-1 - N]. Zwraca None, gdy historia skanów jest za krótka — wtedy
    nie zgadujemy i zostawiamy datę bez zmian.
    """
    idx = len(seq) - 1 - missed_scans
    if idx < 0:
        return None
    return seq[idx]


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
                if l.get("archived_date_corrected"):
                    continue          # już poprawione — nie licz do wykrywania lawiny
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
    total_short = 0
    total_already_ok = 0
    per_date = Counter()

    seqs = load_scan_sequences()

    for pk, prof in data.get("profiles", {}).items():
        seq = seqs.get(pk, [])
        # Skan archiwizujący musi być ostatnim skanem profilu w ledgerze, inaczej
        # indeksowanie wstecz nie ma sensu (np. skrypt uruchomiony za późno).
        if not seq or seq[-1] != avalanche:
            if seq:
                print(f"  [{pk}] pomijam — ostatni skan w ledgerze to {seq[-1]}, "
                      f"a lawina jest z {avalanche}")
            continue
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

            new_date = correct_date(seq, n)
            if new_date is None:
                total_short += 1          # historia skanów krótsza niż missed_scans
                continue
            if new_date == avalanche:
                total_already_ok += 1     # zniknęło w dniu lawiny — data już poprawna
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
    print(f"Do poprawy: {total_fixed}")
    print(f"Bez zmian (zniknęły w dniu lawiny — data już poprawna): {total_already_ok}")
    if total_short:
        print(f"Pominięte (historia skanów krótsza niż missed_scans): {total_short}")
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
