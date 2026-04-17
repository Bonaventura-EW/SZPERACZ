#!/usr/bin/env python3
"""
SZPERACZ OLX — Rebuild refreshed_count in daily_counts.

Problem: refreshed_count was incorrectly calculated as count of listings 
where refreshed==today, instead of counting actual refresh events detected
(from refresh_history).

This script recalculates refreshed_count for all historical dates based on
refresh_history entries in current_listings and archived_listings.
"""

import json
import os
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
JSON_PATH = os.path.join(DATA_DIR, "dashboard_data.json")
BACKUP_PATH = os.path.join(DATA_DIR, "dashboard_data_backup_refreshed_count.json")


def rebuild_refreshed_counts():
    print("=" * 60)
    print("SZPERACZ OLX — Rebuild refreshed_count")
    print("=" * 60)
    
    if not os.path.exists(JSON_PATH):
        print(f"ERROR: {JSON_PATH} not found!")
        return False
    
    # Load data
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Backup
    with open(BACKUP_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Backup saved to: {BACKUP_PATH}")
    
    total_fixes = 0
    
    for profile_key, profile_data in data.get("profiles", {}).items():
        print(f"\n--- Profile: {profile_key} ---")
        
        # Collect all refresh events by date (detected_at date)
        refresh_events_by_date = defaultdict(int)
        
        # Check current_listings
        for listing in profile_data.get("current_listings", []):
            refresh_history = listing.get("refresh_history", [])
            for entry in refresh_history:
                detected_at = entry.get("detected_at", "")
                if detected_at:
                    # Extract date part (YYYY-MM-DD)
                    date_str = detected_at.split(" ")[0] if " " in detected_at else detected_at[:10]
                    refresh_events_by_date[date_str] += 1
        
        # Check archived_listings too
        for listing in profile_data.get("archived_listings", []):
            refresh_history = listing.get("refresh_history", [])
            for entry in refresh_history:
                detected_at = entry.get("detected_at", "")
                if detected_at:
                    date_str = detected_at.split(" ")[0] if " " in detected_at else detected_at[:10]
                    refresh_events_by_date[date_str] += 1
        
        if refresh_events_by_date:
            print(f"  Found refresh events on {len(refresh_events_by_date)} dates")
            # Print some stats
            sorted_dates = sorted(refresh_events_by_date.items(), key=lambda x: x[0])
            for date, count in sorted_dates[-10:]:  # Last 10 dates
                print(f"    {date}: {count} refreshes")
        else:
            print("  No refresh_history entries found")
        
        # Update daily_counts
        daily_counts = profile_data.get("daily_counts", [])
        fixes_in_profile = 0
        
        for entry in daily_counts:
            date = entry.get("date", "")
            old_count = entry.get("refreshed_count", 0)
            new_count = refresh_events_by_date.get(date, 0)
            
            if old_count != new_count:
                print(f"  {date}: {old_count} -> {new_count}")
                entry["refreshed_count"] = new_count
                fixes_in_profile += 1
        
        if fixes_in_profile > 0:
            print(f"  Fixed {fixes_in_profile} entries")
            total_fixes += fixes_in_profile
        else:
            print("  No fixes needed")
    
    # Save updated data
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'=' * 60}")
    print(f"Total fixes: {total_fixes}")
    print(f"Data saved to: {JSON_PATH}")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    rebuild_refreshed_counts()
