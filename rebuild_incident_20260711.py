#!/usr/bin/env python3
"""
Jednorazowa naprawa danych po incydencie 2026-07-11 (patrz CHANGELOG 2026-07-11).

Poranny skan 08:54 pobrał 50 z 650 ogłoszeń `wszystkie_pokoje` i błędnie zarchiwizował
595 istniejących ogłoszeń; wieczorny skan 18:02 masowo je "reaktywował". Ten skrypt
przywraca stan danych taki, jakby ochrona `is_header_shortfall()` istniała już rano:

1. Usuwa fałszywe wpisy reaktywacji (sygnatura: active_to == '2026-07-11 08:54:05')
   i przywraca reactivated/reactivation_count; zachowuje 1 prawdziwą reaktywację (17jKAL).
2. Cofa artefakty promocji: ogłoszenia promowane 10.07 i 11.07, którym fałszywa
   archiwizacja zamknęła sesję i otworzyła nową (sessions+1, days reset) — przywraca
   sesje/historię ze stanu 10.07, days = stare+1.
3. Przywraca historię ogłoszenia 1b1ruw potraktowanego jako nowe (first_seen,
   first_price, price_change, refresh_history + doliczony refresh z 11.07).
4. Przywraca do archiwum 10 ogłoszeń zgubionych całkiem (rano verify_listing_active
   uznała je za aktywne → pominięto archiwizację, ale current_listings i tak zostały
   nadpisane 50 zeskanowanymi → wypadły z danych bez śladu).
5. Poprawia daily_counts 2026-07-11: added 607→34, removed 595→22 (realny ruch doby
   10.07→11.07), reactivated_count/refreshed_count przeliczone po naprawie.
6. Poprawia scan_history (oba wpisy z 11.07) oraz docs/api/status.json i history.json
   (added/removed; alerty o incydencie ZOSTAJĄ — dokumentują zdarzenie).

Źródło prawdy dla przywracanych pól: stan po skanie 10.07 (commit e1dfdc7).
Ledger NDJSON nie jest ruszany (append-only). Skrypt jest idempotentny.
"""

import json
import subprocess
import sys

JSON_PATH = "data/dashboard_data.json"
API_STATUS = "docs/api/status.json"
API_HISTORY = "docs/api/history.json"
BASELINE_COMMIT = "e1dfdc7"  # 🔍 Scan: 2026-07-10 10:31 UTC
PK = "wszystkie_pokoje"
FAKE_ARCHIVE_TS = "2026-07-11 08:54:05"
EVENING_TS = "2026-07-11 18:02:51"
TODAY = "2026-07-11"

# Realny ruch doby 10.07→11.07 (diff ID current: 640 → 652)
REAL_ADDED, REAL_REMOVED = 34, 22


def load_baseline():
    out = subprocess.run(["git", "show", f"{BASELINE_COMMIT}:{JSON_PATH}"],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def main():
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    baseline = load_baseline()

    p = data["profiles"][PK]
    bp = baseline["profiles"][PK]
    old_map = {l["id"]: l for l in bp["current_listings"]}
    new_map = {l["id"]: l for l in p["current_listings"]}

    # ── 1. Fałszywe reaktywacje ──────────────────────────────────────────────
    removed_fake = 0
    for prof in data["profiles"].values():
        for l in prof["current_listings"]:
            rh = l.get("reactivation_history")
            if not rh:
                continue
            kept = [r for r in rh if r.get("active_to") != FAKE_ARCHIVE_TS]
            if len(kept) == len(rh):
                continue
            removed_fake += len(rh) - len(kept)
            if kept:
                l["reactivation_history"] = kept
                l["reactivation_count"] = len(kept)
                l["reactivated"] = True
            else:
                # przed incydentem ogłoszenie nie miało pól reaktywacji
                l.pop("reactivation_history", None)
                l.pop("reactivation_count", None)
                l.pop("reactivated", None)
    print(f"1. Usunięto fałszywych wpisów reaktywacji: {removed_fake}")

    # ── 2. Artefakty promocji (promowane oba dni, sessions+1, days reset) ────
    promo_fixed = 0
    prof_ph = p.get("promotion_history", {})
    b_prof_ph = bp.get("promotion_history", {})
    for lid, nl in new_map.items():
        ol = old_map.get(lid)
        if not ol or not ol.get("is_promoted") or not nl.get("is_promoted"):
            continue
        if nl.get("promoted_sessions_count", 0) != ol.get("promoted_sessions_count", 0) + 1:
            continue
        nl["promoted_sessions_count"] = ol.get("promoted_sessions_count", 0)
        nl["promoted_days_current"] = (ol.get("promoted_days_current") or 0) + 1
        nl["promotion_history"] = ol.get("promotion_history", [])
        if lid in b_prof_ph:
            prof_ph[lid] = b_prof_ph[lid]
        else:
            prof_ph.pop(lid, None)
        promo_fixed += 1
    print(f"2. Cofnięto artefakty sesji promocji: {promo_fixed}")

    # ── 3. 1b1ruw — przywrócenie historii (potraktowane jako nowe) ───────────
    nl = new_map.get("1b1ruw")
    ol = old_map.get("1b1ruw")
    if nl and ol and nl.get("first_seen", "").startswith(TODAY):
        nl["first_seen"] = ol["first_seen"]
        nl["first_price"] = ol.get("first_price")
        nl["price_change"] = ol.get("price_change")
        nl["previous_price"] = ol.get("previous_price")
        rh = list(ol.get("refresh_history", []))
        new_refreshed = nl.get("refreshed")
        old_refreshed = ol.get("refreshed")
        if (new_refreshed and old_refreshed and new_refreshed > old_refreshed
                and not any(h.get("refreshed_at") == new_refreshed for h in rh)):
            rh.append({"refreshed_at": new_refreshed, "detected_at": EVENING_TS,
                       "old_date": old_refreshed})
        nl["refresh_history"] = rh
        nl["refresh_count"] = len(rh)
        print("3. Przywrócono historię 1b1ruw (first_seen "
              f"{ol['first_seen']}, refresh_count {len(rh)})")
    else:
        print("3. 1b1ruw: nic do naprawy (już naprawione?)")

    # ── 4. Zgubione ogłoszenia → do archiwum ─────────────────────────────────
    arch_ids = {l["id"] for l in p["archived_listings"]}
    lost = [lid for lid in old_map
            if lid not in new_map and lid not in arch_ids]
    for lid in lost:
        l = json.loads(json.dumps(old_map[lid]))  # kopia
        l["archived_date"] = EVENING_TS
        rh = l.get("reactivation_history", [])
        if rh and "active_to_current" not in rh[-1]:
            rh[-1]["active_to_current"] = EVENING_TS
        l["reactivation_count"] = len(rh)
        l.setdefault("refresh_history", [])
        l.setdefault("refresh_count", len(l["refresh_history"]))
        p["archived_listings"].append(l)
    print(f"4. Przywrócono do archiwum zgubionych ogłoszeń: {len(lost)} {sorted(lost)}")

    # ── 5. daily_counts 2026-07-11 ───────────────────────────────────────────
    dc = next((d for d in p["daily_counts"] if d["date"] == TODAY), None)
    if dc:
        arch_today = [l for l in p["archived_listings"]
                      if str(l.get("archived_date", "")).startswith(TODAY)]
        pool = p["current_listings"] + arch_today
        react_today = sum(
            1 for l in pool
            if any(str(r.get("reactivated_at", "")).startswith(TODAY)
                   for r in l.get("reactivation_history", [])))
        refresh_today = sum(
            1 for l in pool
            if any(str(h.get("refreshed_at", "")).startswith(TODAY)
                   for h in l.get("refresh_history", [])))
        dc["added"], dc["removed"] = REAL_ADDED, REAL_REMOVED
        dc["reactivated_count"] = react_today
        dc["refreshed_count"] = refresh_today
        print(f"5. daily_counts {TODAY}: added={REAL_ADDED}, removed={REAL_REMOVED}, "
              f"reactivated_count={react_today}, refreshed_count={refresh_today}")

    # ── 6a. scan_history ─────────────────────────────────────────────────────
    for se in data["scan_history"]:
        ts = str(se.get("timestamp", ""))
        wp = se.get("profiles", {}).get(PK)
        if not wp:
            continue
        if ts == FAKE_ARCHIVE_TS:
            wp["added"], wp["removed"] = 0, 0
        elif ts == EVENING_TS:
            wp["added"], wp["removed"] = REAL_ADDED, REAL_REMOVED
    print("6a. scan_history: poprawiono wpisy z 11.07")

    # stabilna serializacja jak w generate_dashboard_json()
    for prof in data["profiles"].values():
        prof["current_listings"].sort(key=lambda l: str(l.get("id", "")))
        prof["archived_listings"].sort(key=lambda l: str(l.get("id", "")))
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)

    # ── 6b. docs/api/status.json + history.json ──────────────────────────────
    with open(API_STATUS, encoding="utf-8") as f:
        st = json.load(f)
    if st["lastScan"]["timestamp"] == "2026-07-11T18:02:51Z":
        wp = st["profiles"][PK]
        wp["added"], wp["removed"], wp["new_listings"] = REAL_ADDED, REAL_REMOVED, REAL_ADDED
        tot_added = sum(v.get("added") or 0 for v in st["profiles"].values())
        tot_removed = sum(v.get("removed") or 0 for v in st["profiles"].values())
        ls = st["lastScan"]
        ls["added"], ls["removed"], ls["new_listings"] = tot_added, tot_removed, tot_added
        with open(API_STATUS, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=2)
        print(f"6b. status.json: added={tot_added}, removed={tot_removed} (alerty zostają)")

    with open(API_HISTORY, encoding="utf-8") as f:
        hi = json.load(f)
    for e in hi.get("scans", []):
        wp = e.get("profiles", {}).get(PK)
        if not wp:
            continue
        if e.get("timestamp") == "2026-07-11T08:54:05Z":
            # profil z błędem — daily_counts nie byłyby policzone (null = nie policzono)
            wp["added"] = wp["removed"] = wp["new_listings"] = None
        elif e.get("timestamp") == "2026-07-11T18:02:51Z":
            wp["added"], wp["removed"], wp["new_listings"] = REAL_ADDED, REAL_REMOVED, REAL_ADDED
        else:
            continue
        e["added"] = sum(v.get("added") or 0 for v in e["profiles"].values())
        e["removed"] = sum(v.get("removed") or 0 for v in e["profiles"].values())
        e["new_listings"] = e["added"]
    hi["recent"] = list(reversed(hi["scans"]))
    with open(API_HISTORY, "w", encoding="utf-8") as f:
        json.dump(hi, f, ensure_ascii=False, indent=2)
    print("6b. history.json: poprawiono added/removed wpisów z 11.07")

    print("\nGotowe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
