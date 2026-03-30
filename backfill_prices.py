#!/usr/bin/env python3
"""
Backfill script - dodaje brakujące statystyki cenowe do daily_counts.
Dla wpisów z None w avg_price/min_price/max_price używa aktualnych cen jako przybliżenia.
"""

import json
import os
from datetime import datetime

DATA_DIR = "data"
JSON_PATH = os.path.join(DATA_DIR, "dashboard_data.json")

def backfill_price_stats():
    print("=== SZPERACZ OLX - Backfill Price Stats ===\n")
    
    # Wczytaj dane
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    for profile_key, profile in data["profiles"].items():
        label = profile.get("label", profile_key)
        counts = profile.get("daily_counts", [])
        listings = profile.get("current_listings", [])
        
        # Oblicz aktualne statystyki cenowe
        prices = [l["price"] for l in listings if l.get("price") is not None and l["price"] > 0]
        
        if not prices:
            print(f"[{label}] Brak cen w current_listings - pomijam")
            continue
        
        avg_price = round(sum(prices) / len(prices))
        min_price = min(prices)
        max_price = max(prices)
        
        # Zaktualizuj wpisy które mają None
        updated = 0
        for entry in counts:
            if entry.get("avg_price") is None:
                entry["avg_price"] = avg_price
                entry["min_price"] = min_price
                entry["max_price"] = max_price
                updated += 1
        
        print(f"[{label}] Zaktualizowano {updated}/{len(counts)} wpisów")
        print(f"  Użyte statystyki: avg={avg_price}, min={min_price}, max={max_price}")
    
    # Zapisz dane
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Backfill zakończony. Zapisano: {JSON_PATH}")

if __name__ == "__main__":
    backfill_price_stats()
