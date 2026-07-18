#!/usr/bin/env python3
"""
Jednorazowe przeliczenie `refreshed_count` i `reactivated_count` we wszystkich
wpisach `daily_counts` z historii ogłoszeń (refresh_history / reactivation_history).

Powód (patrz CHANGELOG 2026-07-18): stare liczenie zliczało tylko eventy
z `refreshed_at` == dzień skanu, a ~54% odświeżeń jest wykrywanych dzień później
(odświeżenie po porannej godzinie skanu) — takie eventy nigdy nie trafiały do
dziennego licznika. Ten skrypt stosuje nową projekcję
(`recompute_daily_refresh_reactivation` ze scraper.py) do już zapisanych danych.

Liczniki są tylko podnoszone (max ze starej i przeliczonej wartości) — stare
wartości z dni, których historie zaginęły (bug cichego gubienia ogłoszeń,
CLAUDE.md §7), nie są zerowane.

Idempotentny — można uruchamiać wielokrotnie.
"""

import json

from scraper import JSON_PATH, recompute_daily_refresh_reactivation

print("=" * 70)
print("REBUILD: backfill refreshed_count/reactivated_count w daily_counts")
print("=" * 70)

with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

total_changed = 0
for pk, pd_ in data.get("profiles", {}).items():
    before = {
        e.get("date"): (e.get("refreshed_count"), e.get("reactivated_count"))
        for e in pd_.get("daily_counts", [])
    }
    recompute_daily_refresh_reactivation(pd_)
    changed = [
        (e.get("date"), before.get(e.get("date")), (e.get("refreshed_count"), e.get("reactivated_count")))
        for e in pd_.get("daily_counts", [])
        if before.get(e.get("date")) != (e.get("refreshed_count"), e.get("reactivated_count"))
    ]
    print(f"\n📂 {pk}: zmienionych wpisów: {len(changed)}")
    for date, old, new in changed:
        print(f"  {date}: refreshed {old[0]} -> {new[0]}, reactivated {old[1]} -> {new[1]}")
    total_changed += len(changed)

# Stabilna serializacja — identyczna jak w generate_dashboard_json()
for pk, pd_ in data.get("profiles", {}).items():
    if isinstance(pd_.get("current_listings"), list):
        pd_["current_listings"].sort(key=lambda l: str(l.get("id", "")))
    if isinstance(pd_.get("archived_listings"), list):
        pd_["archived_listings"].sort(key=lambda l: str(l.get("id", "")))

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)

print("\n" + "=" * 70)
print(f"✅ REBUILD ZAKOŃCZONY — zmienionych wpisów: {total_changed}")
print(f"💾 Zapisano: {JSON_PATH}")
print("=" * 70)
