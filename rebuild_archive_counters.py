#!/usr/bin/env python3
"""
SZPERACZ OLX — Rebuild liczników odświeżeń i reaktywacji dla ARCHIWUM oraz wykresu.

Co robi ten skrypt:
1. Dla KAŻDEGO archiwalnego ogłoszenia rekonstruuje z danych Excel:
   - refresh_history[] + refresh_count (zmiany daty 'refreshed')
   - reactivation_history[] + reactivation_count (luki w obecności ID między scanami)
2. Dodaje brakujące pola reactivation_count do aktywnych ogłoszeń (spójność).
3. Rebuilds daily_counts[*].refreshed_count oraz reactivated_count
   na podstawie WSZYSTKICH zrekonstruowanych zdarzeń (aktywne + archiwum).

Idempotentny: uruchomienie wielokrotne daje ten sam rezultat (rekonstruuje od zera z Excela).
"""

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from openpyxl import load_workbook

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
EXCEL_PATH = os.path.join(DATA_DIR, "szperacz_olx.xlsx")
JSON_PATH = os.path.join(DATA_DIR, "dashboard_data.json")

PROFILES = [
    "wszystkie_pokoje",
    "pokojewlublinie",
    "poqui",
    "artymiuk",
    "dawny_patron",
    "mzuri",
    "villahome",
]

# Jeśli luka między kolejnymi pojawieniami ID w Excel (na podstawie Data scanu) jest >= tej liczby dni,
# traktujemy to jako archiwizację + reaktywację.
REACTIVATION_GAP_DAYS = 2


# ─── I/O ────────────────────────────────────────────────────────────────────

def load_dashboard_json():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_dashboard_json(data):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── Excel parsing ──────────────────────────────────────────────────────────

def _normalize_date(val):
    if val is None:
        return None
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    return str(val)


def _normalize_time(val):
    if val is None:
        return "00:00"
    if hasattr(val, "strftime"):
        return val.strftime("%H:%M")
    return str(val)


def parse_excel_per_listing():
    """
    Zwraca:
      {
        "profile_key": {
          "listing_id": [
             {"scan_date": "YYYY-MM-DD", "scan_time": "HH:MM", "refreshed": "YYYY-MM-DD"|None},
             ...  (posortowane po scan_date+scan_time)
          ]
        }
      }
    Wiersze są już per-ogłoszenie (pomijamy summary rows bez ID).
    """
    print("=" * 70)
    print("🔍 PARSOWANIE EXCEL — per listing history")
    print("=" * 70)

    if not os.path.exists(EXCEL_PATH):
        print(f"❌ Brak pliku Excel: {EXCEL_PATH}")
        return {}

    wb = load_workbook(EXCEL_PATH, read_only=True, data_only=True)
    result = {}

    for profile_key in PROFILES:
        sheet_name = profile_key[:31]
        if sheet_name not in wb.sheetnames:
            print(f"   ⚠️  [{profile_key}] brak arkusza '{sheet_name}' — pomijam")
            continue

        ws = wb[sheet_name]
        data = defaultdict(list)

        # Autodetekcja kolumn z nagłówka
        header_row = next(ws.iter_rows(min_row=1, max_row=1))
        header = {cell.value: idx for idx, cell in enumerate(header_row)}

        required = ["Data scanu", "Godzina", "Tytuł", "Data odświeżenia", "ID ogłoszenia"]
        missing = [c for c in required if c not in header]
        if missing:
            print(f"   ⚠️  [{profile_key}] brak kolumn {missing} — pomijam")
            continue

        col_scan_date = header["Data scanu"]
        col_scan_time = header["Godzina"]
        col_title = header["Tytuł"]
        col_refreshed = header["Data odświeżenia"]
        col_listing_id = header["ID ogłoszenia"]

        max_col_needed = max(col_scan_date, col_scan_time, col_title, col_refreshed, col_listing_id)

        for row in ws.iter_rows(min_row=2):
            row_values = [cell.value for cell in row]
            if len(row_values) <= max_col_needed:
                continue

            scan_date = _normalize_date(row_values[col_scan_date])
            scan_time = _normalize_time(row_values[col_scan_time])
            title = row_values[col_title]
            refreshed = _normalize_date(row_values[col_refreshed])
            listing_id = row_values[col_listing_id]

            # Pomiń summary rows (bez ID lub bez tytułu)
            if not listing_id or not title:
                continue

            data[listing_id].append({
                "scan_date": scan_date,
                "scan_time": scan_time,
                "refreshed": refreshed,
                "title": str(title)[:80],
            })

        # Sortuj rosnąco po scan_date + scan_time
        for lid in data:
            data[lid].sort(key=lambda e: (e.get("scan_date") or "", e.get("scan_time") or ""))

        result[profile_key] = dict(data)
        print(f"   ✓ [{profile_key}] {len(data)} unikalnych ID")

    wb.close()
    return result


# ─── History reconstruction ─────────────────────────────────────────────────

def build_refresh_history(entries):
    """
    Zbuduj refresh_history[] ze zmian pola 'refreshed' w kolejnych wpisach scanu.
    Event = zmiana z old_refreshed na new_refreshed gdzie new > old.

    Returns: (history, count)
    """
    history = []
    prev_refreshed = None

    for e in entries:
        cur = e.get("refreshed")
        if cur and prev_refreshed and cur > prev_refreshed:
            already_logged = any(h.get("refreshed_at") == cur for h in history)
            if not already_logged:
                history.append({
                    "refreshed_at": cur,
                    "detected_at": f"{e['scan_date']} {e['scan_time']}",
                    "old_date": prev_refreshed,
                })
        if cur:
            prev_refreshed = cur

    return history, len(history)


def build_reactivation_history(entries, all_scan_dates, gap_days=REACTIVATION_GAP_DAYS):
    """
    Reaktywacja = ID znika z Excela na >= gap_days dni (w kontekście dni w których scan w ogóle się odbył),
    a potem wraca. Zlicza tylko POTWIERDZONE reaktywacje (ID faktycznie wróciło do scanu).

    all_scan_dates: posortowany set dat, kiedy dany profil był skanowany (do wykrywania prawdziwej luki).

    Returns: (history, count, periods_of_activity)
    """
    # Zbierz dni obecności ID (unikalne, posortowane)
    presence_days = sorted(set(e["scan_date"] for e in entries if e.get("scan_date")))
    if not presence_days:
        return [], 0, []

    # Podziel na "okresy aktywności" (ciągłe bloki obecności)
    # Okres zamyka się, gdy w scan_dates między present_day a next_present_day
    # jest >= gap_days dni scanów bez obecności.
    periods = []  # list of (start_day, end_day)
    current_start = presence_days[0]
    current_end = presence_days[0]

    scan_dates_list = sorted(all_scan_dates)
    scan_date_to_idx = {d: i for i, d in enumerate(scan_dates_list)}

    for i in range(1, len(presence_days)):
        prev = presence_days[i - 1]
        cur = presence_days[i]

        # Policz ile dni scanów było między prev a cur (exclusive)
        idx_prev = scan_date_to_idx.get(prev)
        idx_cur = scan_date_to_idx.get(cur)

        if idx_prev is not None and idx_cur is not None:
            gap_scans = idx_cur - idx_prev - 1  # liczba scanów bez obecności
        else:
            # Fallback: licz dni kalendarzowe
            d_prev = datetime.strptime(prev, "%Y-%m-%d")
            d_cur = datetime.strptime(cur, "%Y-%m-%d")
            gap_scans = (d_cur - d_prev).days - 1

        if gap_scans >= gap_days:
            # Zamknij poprzedni okres, otwórz nowy
            periods.append((current_start, current_end))
            current_start = cur
        current_end = cur

    # Zamknij ostatni okres
    periods.append((current_start, current_end))

    # Historia reaktywacji = wszystko poza pierwszym okresem (każdy kolejny okres to reaktywacja)
    history = []
    for i in range(1, len(periods)):
        prev_start, prev_end = periods[i - 1]
        cur_start, cur_end = periods[i]
        history.append({
            "active_from": f"{prev_start} 00:00:00",
            "active_to": f"{prev_end} 23:59:59",
            "reactivated_at": f"{cur_start} 00:00:00",
        })

    return history, len(history), periods


# ─── Main rebuild logic ────────────────────────────────────────────────────

def rebuild_all():
    data = load_dashboard_json()
    excel_data = parse_excel_per_listing()

    # Zbierz set wszystkich dat scanów per profil (do wykrywania prawdziwych luk)
    scan_dates_by_profile = defaultdict(set)
    for pk, pd_ in data.get("profiles", {}).items():
        for dc in pd_.get("daily_counts", []):
            if dc.get("date"):
                scan_dates_by_profile[pk].add(dc["date"])

    print()
    print("=" * 70)
    print("🔨 REKONSTRUKCJA HISTORII dla CURRENT + ARCHIVED")
    print("=" * 70)

    stats = {
        "listings_processed": 0,
        "refresh_events_added": 0,
        "reactivation_events_added": 0,
        "archived_with_refresh": 0,
        "archived_with_reactivation": 0,
    }

    # Zbieranie globalnych zdarzeń per dzień (do rebuild daily_counts)
    refresh_events_per_day = defaultdict(lambda: defaultdict(int))  # profile -> date -> count
    reactivation_events_per_day = defaultdict(lambda: defaultdict(int))  # profile -> date -> count

    for pk in PROFILES:
        if pk not in data.get("profiles", {}):
            continue
        pd_ = data["profiles"][pk]
        per_listing = excel_data.get(pk, {})
        scan_dates = scan_dates_by_profile.get(pk, set())

        # Przetwarzaj zarówno current_listings jak i archived_listings
        current_listings = pd_.get("current_listings", [])
        archived_listings = pd_.get("archived_listings", [])

        print(f"\n📊 [{pk}] current={len(current_listings)} archived={len(archived_listings)} excel_ids={len(per_listing)}")

        for listings, is_archived in [(current_listings, False), (archived_listings, True)]:
            for listing in listings:
                lid = listing.get("id")
                if not lid:
                    continue

                stats["listings_processed"] += 1
                entries = per_listing.get(lid, [])

                if not entries:
                    # Brak danych w Excel — ustaw puste struktury (jeśli nie istnieją)
                    if "refresh_history" not in listing:
                        listing["refresh_history"] = []
                    if "refresh_count" not in listing:
                        listing["refresh_count"] = 0
                    if "reactivation_history" not in listing:
                        listing["reactivation_history"] = []
                    listing["reactivation_count"] = len(listing.get("reactivation_history", []))
                    continue

                # Zbuduj refresh_history
                refresh_hist, refresh_cnt = build_refresh_history(entries)
                listing["refresh_history"] = refresh_hist
                listing["refresh_count"] = refresh_cnt

                # Zarejestruj zdarzenia refresh do per-day stats (liczymy w dniu detekcji = scan_date)
                for ev in refresh_hist:
                    det_date = ev["detected_at"].split(" ")[0]
                    refresh_events_per_day[pk][det_date] += 1

                # Zbuduj reactivation_history
                reactivation_hist, reactivation_cnt, _ = build_reactivation_history(
                    entries, scan_dates, gap_days=REACTIVATION_GAP_DAYS
                )
                listing["reactivation_history"] = reactivation_hist
                listing["reactivation_count"] = reactivation_cnt

                if reactivation_cnt > 0:
                    listing["reactivated"] = True

                # Zarejestruj zdarzenia reactivation per day (liczymy w dniu reaktywacji)
                for ev in reactivation_hist:
                    ra_date = ev["reactivated_at"].split(" ")[0]
                    reactivation_events_per_day[pk][ra_date] += 1

                # Zamknij otwarty bieżący okres reaktywacji w archived_listings
                if is_archived and reactivation_hist:
                    last = reactivation_hist[-1]
                    if "active_to_current" not in last:
                        archived_date = listing.get("archived_date")
                        if archived_date:
                            last["active_to_current"] = archived_date

                # Statystyki archiwum
                if is_archived:
                    if refresh_cnt > 0:
                        stats["archived_with_refresh"] += 1
                    if reactivation_cnt > 0:
                        stats["archived_with_reactivation"] += 1

                stats["refresh_events_added"] += refresh_cnt
                stats["reactivation_events_added"] += reactivation_cnt

    # ─── Rebuild daily_counts[*].refreshed_count / reactivated_count ───
    print()
    print("=" * 70)
    print("🔨 REBUILD daily_counts.refreshed_count / reactivated_count")
    print("=" * 70)

    for pk in PROFILES:
        if pk not in data.get("profiles", {}):
            continue
        pd_ = data["profiles"][pk]
        dc = pd_.get("daily_counts", [])

        updated_refresh = 0
        updated_reactivation = 0
        for entry in dc:
            date = entry.get("date")
            if not date:
                continue
            r = refresh_events_per_day[pk].get(date, 0)
            a = reactivation_events_per_day[pk].get(date, 0)
            old_r = entry.get("refreshed_count", 0)
            old_a = entry.get("reactivated_count", 0)
            entry["refreshed_count"] = r
            entry["reactivated_count"] = a
            if r != old_r:
                updated_refresh += 1
            if a != old_a:
                updated_reactivation += 1

        print(f"   [{pk}] daily_counts updated: refreshed={updated_refresh} reactivated={updated_reactivation}")

    # ─── Save ───
    save_dashboard_json(data)

    print()
    print("=" * 70)
    print("✅ PODSUMOWANIE")
    print("=" * 70)
    print(f"   Przetworzono ogłoszeń:            {stats['listings_processed']}")
    print(f"   Dodano zdarzeń odświeżeń:         {stats['refresh_events_added']}")
    print(f"   Dodano zdarzeń reaktywacji:       {stats['reactivation_events_added']}")
    print(f"   Archiwum z odświeżeniami:         {stats['archived_with_refresh']}")
    print(f"   Archiwum z reaktywacjami:         {stats['archived_with_reactivation']}")
    print()
    print(f"   Zapisano: {JSON_PATH}")


if __name__ == "__main__":
    rebuild_all()
