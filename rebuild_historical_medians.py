#!/usr/bin/env python3
"""
Rebuild historical medians - przebudowuje median_price dla każdego dnia w historii.
Używa informacji o first_seen i archived_date aby określić które ogłoszenia istniały danego dnia.
"""

import json
import os
from datetime import datetime, timedelta

DATA_DIR = "data"
JSON_PATH = os.path.join(DATA_DIR, "dashboard_data.json")


def parse_datetime(dt_str):
    """Parse datetime string to date object."""
    if not dt_str:
        return None
    try:
        # Format: "2026-03-30 12:34:56" -> date
        return datetime.strptime(dt_str.split()[0], "%Y-%m-%d").date()
    except:
        return None


def calculate_median(prices):
    """Calculate median from list of prices."""
    if not prices:
        return None
    sorted_prices = sorted(prices)
    n = len(sorted_prices)
    if n % 2 == 0:
        return round((sorted_prices[n//2 - 1] + sorted_prices[n//2]) / 2)
    else:
        return sorted_prices[n//2]


def rebuild_medians():
    print("=== SZPERACZ OLX - Rebuild Historical Medians ===\n")
    
    # Wczytaj dane
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    for profile_key, profile in data["profiles"].items():
        label = profile.get("label", profile_key)
        counts = profile.get("daily_counts", [])
        current_listings = profile.get("current_listings", [])
        archived_listings = profile.get("archived_listings", [])
        
        print(f"[{label}] Przebudowuję {len(counts)} dni historii...")
        
        # Wszystkie ogłoszenia (aktualne + archiwalne)
        all_listings = current_listings + archived_listings
        
        if not all_listings:
            print(f"  Brak ogłoszeń - pomijam\n")
            continue
        
        # Dla każdego dnia w daily_counts
        updated = 0
        for entry in counts:
            entry_date_str = entry.get("date")
            if not entry_date_str:
                continue
            
            entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d").date()
            
            # Znajdź ogłoszenia które istniały tego dnia
            prices_on_that_day = []
            
            for listing in all_listings:
                first_seen = parse_datetime(listing.get("first_seen"))
                archived_date = parse_datetime(listing.get("archived_date"))
                price = listing.get("price")
                
                if not first_seen or price is None or price <= 0:
                    continue
                
                # Sprawdź czy ogłoszenie istniało entry_date
                was_active = first_seen <= entry_date
                
                if archived_date:
                    # Jeśli jest archived_date, sprawdź czy nie zniknęło wcześniej
                    was_active = was_active and entry_date <= archived_date
                
                if was_active:
                    prices_on_that_day.append(price)
            
            # Oblicz medianę
            if prices_on_that_day:
                median = calculate_median(prices_on_that_day)
                entry["median_price"] = median
                updated += 1
            else:
                entry["median_price"] = None
        
        print(f"  Zaktualizowano: {updated}/{len(counts)} dni")
        
        # Pokaż przykład
        if counts:
            example = counts[-1]
            print(f"  Przykład (ostatni dzień {example['date']}):")
            print(f"    Median: {example.get('median_price')} zł")
        print()
    
    # Zapisz dane
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Rebuild zakończony. Zapisano: {JSON_PATH}")


if __name__ == "__main__":
    rebuild_medians()
