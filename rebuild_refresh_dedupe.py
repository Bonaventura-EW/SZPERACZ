#!/usr/bin/env python3
"""
SZPERACZ OLX — Rebuild refresh_history z deduplikacją per dzień.

REGUŁA: OLX pokazuje na stronie ogłoszenia tylko datę ostatniego odświeżenia
("Odświeżono dnia 12 maja 2026"). Max 1 odświeżenie na ogłoszenie na dzień.

CO ROBI:
1. Dla każdego ogłoszenia (aktywne + archiwum) w `refresh_history`:
   - Grupuje eventy po `refreshed_at[:10]` (YYYY-MM-DD).
   - Zachowuje 1 wpis na dzień (najwcześniejszy `detected_at`).
   - Jeśli zostały usunięte wpisy → dodaje audit `_dedup_note` z licznikiem.
2. Synchronizuje `refresh_count = len(refresh_history)`.
3. Przelicza `daily_counts[*].refreshed_count` dla każdego profilu:
   - Dla każdego dnia z `daily_counts`: zlicza ogłoszenia, które miały tego dnia
     wpis `refreshed_at == today` w `refresh_history` (aktywne lub archiwum).

IDEMPOTENTNY: można uruchamiać wielokrotnie, drugi run nie zmieni nic.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
JSON_PATH = os.path.join(DATA_DIR, "dashboard_data.json")


def dedupe_listing_history(listing):
    """
    Dla danego ogłoszenia deduplikuje refresh_history per dzień.
    Zwraca (removed_count, new_count) — ile wpisów usunięto, ile zostało.
    """
    hist = listing.get("refresh_history", []) or []
    if not hist:
        # Nawet jeśli historia pusta — wymuś refresh_count = 0
        listing["refresh_count"] = 0
        return 0, 0

    # Grupowanie po dacie (YYYY-MM-DD) — bierzemy wpis z najwcześniejszym detected_at
    by_day = defaultdict(list)
    for h in hist:
        ra = h.get("refreshed_at", "") or ""
        day = ra[:10]  # YYYY-MM-DD
        if not day:
            # Wpis bez daty — pomijamy (corrupt) i raportujemy jako usunięty
            continue
        by_day[day].append(h)

    # Dla każdego dnia: pierwszy detected_at wygrywa
    cleaned = []
    for day in sorted(by_day.keys()):
        entries = by_day[day]
        entries_sorted = sorted(entries, key=lambda h: h.get("detected_at", "") or "")
        cleaned.append(entries_sorted[0])

    original_count = len(hist)
    new_count = len(cleaned)
    removed = original_count - new_count

    listing["refresh_history"] = cleaned
    listing["refresh_count"] = new_count

    if removed > 0:
        # Audit note
        existing_note = listing.get("_dedup_note", {})
        if isinstance(existing_note, dict):
            existing_removed = existing_note.get("removed_total", 0)
        else:
            existing_removed = 0
        listing["_dedup_note"] = {
            "rule": "max 1 refresh/day per listing (OLX shows date only)",
            "removed_total": existing_removed + removed,
            "last_rebuild_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "original_count_at_last_rebuild": original_count,
            "final_count_at_last_rebuild": new_count,
        }
    return removed, new_count


def rebuild_daily_refreshed_counts(profile_data):
    """
    Dla każdego dnia w `daily_counts` przelicza `refreshed_count` na podstawie
    aktualnej (wyczyszczonej) `refresh_history` we wszystkich ogłoszeniach.

    refreshed_count[day] = liczba ogłoszeń, które mają wpis w refresh_history
    z `refreshed_at == day` (aktywne + archiwum).
    """
    all_listings = (
        list(profile_data.get("current_listings", []))
        + list(profile_data.get("archived_listings", []))
    )

    # Set of (listing_id, day) — żeby nie liczyć tego samego ogłoszenia 2x
    # (na wypadek gdyby ten sam ID był i w current i w archived, choć nie powinien być)
    seen = set()
    day_to_listings = defaultdict(int)

    for l in all_listings:
        lid = l.get("id")
        hist = l.get("refresh_history", []) or []
        days_for_listing = set()
        for h in hist:
            ra = h.get("refreshed_at", "") or ""
            day = ra[:10]
            if day:
                days_for_listing.add(day)
        for day in days_for_listing:
            key = (lid, day)
            if key in seen:
                continue
            seen.add(key)
            day_to_listings[day] += 1

    # Przelicz refreshed_count w daily_counts (tylko dla istniejących dni —
    # nie tworzymy nowych wpisów)
    dc = profile_data.get("daily_counts", [])
    changed = 0
    for entry in dc:
        day = entry.get("date")
        if not day:
            continue
        new_val = day_to_listings.get(day, 0)
        old_val = entry.get("refreshed_count", 0)
        if new_val != old_val:
            entry["refreshed_count"] = new_val
            changed += 1
    return changed


def main():
    if not os.path.exists(JSON_PATH):
        print(f"ERROR: {JSON_PATH} nie istnieje")
        sys.exit(1)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("=" * 70)
    print("REBUILD: deduplikacja refresh_history per dzień (max 1/dzień)")
    print("=" * 70)

    total_removed = 0
    total_listings_touched = 0

    for pk, pd in data.get("profiles", {}).items():
        print(f"\n[{pk}]")
        per_profile_removed = 0
        per_profile_touched = 0

        for collection_name in ("current_listings", "archived_listings"):
            collection = pd.get(collection_name, [])
            for listing in collection:
                removed, _ = dedupe_listing_history(listing)
                if removed > 0:
                    per_profile_removed += removed
                    per_profile_touched += 1

        print(f"  Eventów usuniętych: {per_profile_removed}")
        print(f"  Ogłoszeń dotkniętych: {per_profile_touched}")

        # Przelicz daily_counts.refreshed_count z wyczyszczonej historii
        changed = rebuild_daily_refreshed_counts(pd)
        print(f"  daily_counts zaktualizowanych: {changed}")

        total_removed += per_profile_removed
        total_listings_touched += per_profile_touched

    print(f"\n{'=' * 70}")
    print(f"PODSUMOWANIE: usunięto {total_removed} duplikatów w {total_listings_touched} ogłoszeniach")
    print("=" * 70)

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nZapisano: {JSON_PATH}")


if __name__ == "__main__":
    main()
