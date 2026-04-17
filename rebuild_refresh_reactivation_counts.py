#!/usr/bin/env python3
"""
Rebuild refresh_count i reactivated_count w daily_counts na podstawie danych historycznych.

- reactivated_count: odtwarzamy z reactivation_history (dokładne daty reaktywacji)
- refreshed_count: NIE da się odtworzyć (brak historii dat odświeżenia)
  - pozostawiamy obecne wartości (będą poprawne od pierwszego scanu po tym skrypcie)
"""

import json
import os
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
JSON_PATH = os.path.join(DATA_DIR, "dashboard_data.json")

print("=" * 70)
print("REBUILD: refresh_count & reactivated_count w daily_counts")
print("=" * 70)

# Załaduj JSON
with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

total_fixed = 0

for profile_key, profile_data in data.get("profiles", {}).items():
    print(f"\n📂 Profile: {profile_data.get('label', profile_key)}")
    
    daily_counts = profile_data.get("daily_counts", [])
    if not daily_counts:
        print("  ⚠️ Brak daily_counts - pomijam")
        continue
    
    # Przygotuj mapę: data -> liczba reaktywacji
    reactivation_map = defaultdict(int)
    
    # Skanuj wszystkie ogłoszenia (current + archived) dla reactivation_history
    all_listings = (
        profile_data.get("current_listings", []) + 
        profile_data.get("archived_listings", [])
    )
    
    for listing in all_listings:
        history = listing.get("reactivation_history", [])
        for entry in history:
            reactivated_at = entry.get("reactivated_at", "")
            if reactivated_at:
                # Wyciągnij datę (YYYY-MM-DD) z timestamp
                date = reactivated_at.split(" ")[0] if " " in reactivated_at else reactivated_at[:10]
                reactivation_map[date] += 1
    
    print(f"  📊 Znaleziono {len(reactivation_map)} dni z reaktywacjami w historii")
    
    # Zaktualizuj daily_counts
    fixed_count = 0
    for entry in daily_counts:
        date = entry.get("date")
        if not date:
            continue
        
        # Zaktualizuj reactivated_count z danych historycznych
        old_count = entry.get("reactivated_count", 0)
        new_count = reactivation_map.get(date, 0)
        
        if old_count != new_count:
            entry["reactivated_count"] = new_count
            fixed_count += 1
    
    print(f"  ✅ Zaktualizowano {fixed_count} wpisów daily_counts")
    total_fixed += fixed_count

# Zapisz zaktualizowany JSON
with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("\n" + "=" * 70)
print("✅ REBUILD ZAKOŃCZONY")
print(f"📊 Total zaktualizowanych wpisów: {total_fixed}")
print(f"💾 Zapisano: {JSON_PATH}")
print("=" * 70)
print("\n⚠️ UWAGA: refreshed_count NIE został odtworzony (brak danych historycznych)")
print("   Będzie poprawny od pierwszego scanu po tym rebuildie.")
