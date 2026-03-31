#!/usr/bin/env python3
"""
Backfill script - dodaje brakujące statystyki cenowe do daily_counts.
Dla wpisów z None w median_price używa aktualnych cen jako przybliżenia.
"""

import json
import os
from datetime import datetime

DATA_DIR = "data"
JSON_PATH = os.path.join(DATA_DIR, "dashboard_data.json")

def backfill_price_stats():
    print("=== SZPERACZ OLX - Backfill Median Price ===\n")
    
    # Wczytaj dane
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    for profile_key, profile in data["profiles"].items():
        label = profile.get("label", profile_key)
        counts = profile.get("daily_counts", [])
        listings = profile.get("current_listings", [])
        
        # Oblicz medianę cen
        prices = [l["price"] for l in listings if l.get("price") is not None and l["price"] > 0]
        
        if not prices:
            print(f"[{label}] Brak cen w current_listings - pomijam")
            continue
        
        sorted_prices = sorted(prices)
        n = len(sorted_prices)
        if n % 2 == 0:
            median_price = round((sorted_prices[n//2 - 1] + sorted_prices[n//2]) / 2)
        else:
            median_price = sorted_prices[n//2]
        
        # Zaktualizuj wpisy - dodaj median_price, usuń stare pola
        updated = 0
        for entry in counts:
            # Usuń stare pola jeśli istnieją
            if 'avg_price' in entry:
                del entry['avg_price']
            if 'min_price' in entry:
                del entry['min_price']
            if 'max_price' in entry:
                del entry['max_price']
            
            # Dodaj median_price jeśli nie ma
            if entry.get("median_price") is None:
                entry["median_price"] = median_price
                updated += 1
        
        print(f"[{label}] Zaktualizowano {updated}/{len(counts)} wpisów")
        print(f"  Mediana: {median_price} zł")
    
    # Zapisz dane
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Backfill zakończony. Zapisano: {JSON_PATH}")

if __name__ == "__main__":
    backfill_price_stats()
