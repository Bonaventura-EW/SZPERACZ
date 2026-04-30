#!/usr/bin/env python3
"""
Backfill price_distribution dla istniejących wpisów daily_counts.

Dla każdego dnia D rekonstruuje listę aktywnych ogłoszeń (first_seen <= D <= archived_date|dziś)
i buduje rozkład cen. Jeśli ogłoszenie zmieniło cenę, użyje price_history żeby znaleźć
cenę aktualną w dniu D.
"""
import json, os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
JSON_PATH = os.path.join(DATA_DIR, "dashboard_data.json")

def build_price_distribution(prices_raw):
    prices = sorted([p for p in prices_raw if p and p > 0])
    if not prices:
        return []
    mn, mx = prices[0], prices[-1]
    if mn == mx:
        return [{"from": mn, "to": mx + 1, "count": len(prices)}]
    raw = (mx - mn) / 14
    mag = 10 ** max(0, int(len(str(int(max(raw, 1)))) - 1))
    step = next((f * mag for f in [1, 2, 2.5, 5, 10] if f * mag >= raw), 10 * mag)
    start = (mn // step) * step
    buckets = []
    s = start
    while s <= mx:
        cnt = sum(1 for p in prices if s <= p < s + step)
        buckets.append({"from": int(s), "to": int(s + step), "count": cnt})
        s += step
    extra = sum(1 for p in prices if p >= s)
    if extra: buckets[-1]["count"] += extra
    while len(buckets) > 1 and buckets[-1]["count"] == 0: buckets.pop()
    while len(buckets) > 1 and buckets[0]["count"] == 0:  buckets.pop(0)
    return buckets

def price_on_day(listing, day_str, profile_price_history):
    """Return the price a listing had on day_str, using price_history."""
    lid = listing.get("id", "")
    ph  = profile_price_history.get(lid, [])
    price = listing.get("price")

    if ph:
        # price_history: [{date, old_price, new_price}] sorted ascending
        ph_sorted = sorted(ph, key=lambda h: h["date"])
        # Find first change AFTER day_str — the price before it is what was active
        after = [h for h in ph_sorted if h["date"][:10] > day_str]
        before = [h for h in ph_sorted if h["date"][:10] <= day_str]
        if after:
            # Price on day_str = old_price of first change after day_str
            price = after[0]["old_price"]
        elif before:
            # All changes happened on/before day_str → latest new_price
            price = before[-1]["new_price"]
        else:
            # No changes recorded — use first_price if available
            price = listing.get("first_price") or listing.get("price")
    else:
        price = listing.get("first_price") or listing.get("price")

    return price

def backfill():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    today_str = datetime.now().strftime("%Y-%m-%d")
    total_filled = 0

    for pk, pd_ in data["profiles"].items():
        dc       = pd_.get("daily_counts", [])
        current  = pd_.get("current_listings", [])
        archived = pd_.get("archived_listings", [])
        all_listings = current + archived
        ph = pd_.get("price_history", {})

        print(f"\n[{pk}] {len(dc)} days, {len(all_listings)} total listings")

        for entry in dc:
            # Skip if already has price_distribution with data
            if entry.get("price_distribution"):
                continue

            d = entry["date"]

            # Collect listings active on day d
            active_prices = []
            for l in all_listings:
                fs  = (l.get("first_seen") or "")[:10]
                arc = (l.get("archived_date") or today_str)[:10]
                if not fs or fs > d or arc < d:
                    continue
                price = price_on_day(l, d, ph)
                if price and price > 0:
                    active_prices.append(price)

            dist = build_price_distribution(active_prices)
            entry["price_distribution"] = dist
            total_filled += 1

            if dist:
                total = sum(b["count"] for b in dist)
                print(f"  {d}: {total} prices, {len(dist)} buckets  [{dist[0]['from']}–{dist[-1]['to']} zł]")
            else:
                print(f"  {d}: no prices found")

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nDone. Filled {total_filled} entries.")

if __name__ == "__main__":
    backfill()
