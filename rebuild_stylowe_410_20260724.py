#!/usr/bin/env python3
"""
Jednorazowa, idempotentna naprawa danych po błędzie obsługi HTTP 410 w
verify_listing_active() (naprawiony w scraper.py 2026-07-24).

Kontekst: profil `stylowe_pokoje_ania` pokazał count 10 → 5 (2026-07-24), ale
5 „zniknionych" ogłoszeń nie trafiło do archiwum — utknęły w current_listings
z missed_scans=1. Powód: OLX zwraca dla nich HTTP 410 (Gone), a stara wersja
verify_listing_active() traktowała każdy status != 200/404 jako „aktywne"
(fail-safe), więc ogłoszenia nigdy nie były archiwizowane.

Ten skrypt przenosi do archiwum wyłącznie te ogłoszenia z current_listings,
które BRAKUJE w ostatnim skanie (missed_scans>=1) i które NA ŻYWO zwracają
HTTP 404/410 (ponowna weryfikacja — nie archiwizujemy niczego „na słowo").
Idempotentny: po naprawie ogłoszenia nie są już w current_listings, więc
kolejne uruchomienie to no-op.

Uruchom świadomie (robi commit ręcznie po weryfikacji):
    python rebuild_stylowe_410_20260724.py
"""
import json
import time

import requests
from bs4 import BeautifulSoup

JSON_PATH = "data/dashboard_data.json"
PROFILE = "stylowe_pokoje_ania"

INACTIVE_STATUSES = (404, 410)  # 410 = Gone (OLX: oferta zdjęta/wygasła)
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")


def http_status(url: str, timeout: int = 15):
    """Zwraca kod HTTP strony ogłoszenia (bez query). None przy błędzie sieci."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pl-PL,pl;q=0.9",
    })
    try:
        r = s.get(url.split("?")[0], timeout=timeout, allow_redirects=True)
        return r.status_code
    except Exception as e:
        print(f"  [WARN] błąd sieci {url[:60]}: {e}")
        return None


def main():
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    prof = data["profiles"][PROFILE]
    now_str = data.get("last_scan")  # znacznik skanu, który wykrył nieobecność
    today = now_str.split(" ")[0] if now_str else None

    current = prof.get("current_listings", [])
    archived = prof.setdefault("archived_listings", [])

    # Kandydaci: obecni w current_listings, ale nieobecni w ostatnim skanie.
    candidates = [l for l in current if (l.get("missed_scans") or 0) >= 1]
    print(f"Kandydatów (missed_scans>=1) w {PROFILE}: {len(candidates)}")

    to_archive_ids = set()
    for l in candidates:
        status = http_status(l.get("url", ""))
        gone = status in INACTIVE_STATUSES
        print(f"  {l['id']}  HTTP {status}  -> {'ARCHIWIZUJĘ' if gone else 'zostawiam (aktywne)'}")
        if gone:
            to_archive_ids.add(l["id"])
        time.sleep(0.7)

    if not to_archive_ids:
        print("Brak ogłoszeń do archiwizacji — dane bez zmian.")
        return

    new_current = []
    archived_count = 0
    for l in current:
        if l["id"] in to_archive_ids:
            # Odtworzenie kroków pętli archiwizacji ze scraper.generate_dashboard_json():
            l["archived_date"] = now_str
            r_hist = l.get("reactivation_history", [])
            if r_hist and "active_to_current" not in r_hist[-1]:
                r_hist[-1]["active_to_current"] = now_str
            l["reactivation_count"] = len(r_hist)
            l.setdefault("refresh_history", [])
            l.setdefault("refresh_count", len(l["refresh_history"]))
            l.pop("missed_scans", None)  # pole bez sensu w archiwum
            archived.append(l)
            archived_count += 1
        else:
            new_current.append(l)
    prof["current_listings"] = new_current

    # daily_counts: dzisiejszy wpis powinien pokazać removed = liczba zarchiwizowanych.
    for dc in prof.get("daily_counts", []):
        if dc.get("date") == today:
            old_removed = dc.get("removed")
            dc["removed"] = (old_removed or 0) + archived_count
            print(f"daily_counts[{today}].removed: {old_removed} -> {dc['removed']}")
            break

    # Stabilna serializacja — identyczna jak w scraper.generate_dashboard_json().
    for pk, pd_ in data.get("profiles", {}).items():
        if isinstance(pd_.get("current_listings"), list):
            pd_["current_listings"].sort(key=lambda x: str(x.get("id", "")))
        if isinstance(pd_.get("archived_listings"), list):
            pd_["archived_listings"].sort(key=lambda x: str(x.get("id", "")))

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)

    print(f"\nGotowe. Zarchiwizowano {archived_count} ogłoszeń w {PROFILE}.")
    print(f"current_listings: {len(current)} -> {len(new_current)}, "
          f"archived_listings: {len(archived)}")


if __name__ == "__main__":
    main()
