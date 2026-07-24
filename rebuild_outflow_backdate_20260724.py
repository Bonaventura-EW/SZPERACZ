#!/usr/bin/env python3
"""
Jednorazowe, idempotentne „rozsmarowanie" jednorazowego skoku odpływu z 2026-07-24.

Kontekst: skan z poprawką HTTP 410 (2026-07-24) skasował naraz zaległość ~147
martwych ofert, które bug trzymał w current_listings. Wszystkie dostały
archived_date = 2026-07-24, co daje jednorazowy skok na wykresach „Odpływ ofert"
i „Przybyło/Zniknęło". Realnie te oferty gasły stopniowo — a `missed_scans`
mówi, ile skanów (≈ dni) oferta była już nieobecna zanim ją zarchiwizowano.

Ten skrypt przesuwa archived_date ofert zarchiwizowanych 2026-07-24 z polem
missed_scans>=1 wstecz o `missed_scans` dni (szacunkowa data zniknięcia z OLX)
i analogicznie redystrybuuje daily_counts[...].removed z 2026-07-24 na te dni.
Oferty bez missed_scans (zniknęły dopiero dziś) zostają na 2026-07-24.

Idempotentny: po przesunięciu archived_date != 2026-07-24, więc ponowne
uruchomienie nie znajduje nic do zrobienia (żadnego podwójnego liczenia).

    python rebuild_outflow_backdate_20260724.py
"""
import json
from collections import defaultdict
from datetime import date, timedelta

JSON_PATH = "data/dashboard_data.json"
TF_PATH = "docs/api/trend_full.json"
ARCH_DAY = "2026-07-24"
ARCH_DATE_OBJ = date(2026, 7, 24)


def shifted_date(missed):
    return (ARCH_DATE_OBJ - timedelta(days=int(missed))).isoformat()


def main():
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    total_shifted = 0
    # deltas[profile][date] = ile removed dodać danego dnia (a z ARCH_DAY odjąć)
    for pk, p in data["profiles"].items():
        moved_per_day = defaultdict(int)
        for l in p.get("archived_listings", []):
            ad = l.get("archived_date") or ""
            ms = l.get("missed_scans")
            if not ad.startswith(ARCH_DAY) or not ms or int(ms) < 1:
                continue
            new_day = shifted_date(ms)
            time_part = ad[10:]  # zachowaj godzinę (albo pusto)
            l["archived_date"] = f"{new_day}{time_part}"
            moved_per_day[new_day] += 1
            total_shifted += 1

        if not moved_per_day:
            continue

        # Redystrybucja daily_counts.removed
        dc_by_date = {x["date"]: x for x in p.get("daily_counts", [])}
        moved_total = sum(moved_per_day.values())

        # Odejmij z dnia 2026-07-24
        today_dc = dc_by_date.get(ARCH_DAY)
        if today_dc is not None:
            before = today_dc.get("removed") or 0
            today_dc["removed"] = max(0, before - moved_total)
            print(f"[{pk}] removed[{ARCH_DAY}]: {before} -> {today_dc['removed']} (-{moved_total})")

        # Dodaj do dni docelowych (wpisy muszą istnieć — zweryfikowane wcześniej)
        for day, n in sorted(moved_per_day.items()):
            dc = dc_by_date.get(day)
            if dc is None:
                raise SystemExit(f"BŁĄD: brak wpisu daily_counts {pk}/{day} — przerwano "
                                 f"(nie tworzę wpisów, żeby nie zepsuć innych metryk).")
            before = dc.get("removed") or 0
            dc["removed"] = before + n
            print(f"[{pk}] removed[{day}]: {before} -> {dc['removed']} (+{n})")

    if total_shifted == 0:
        print("Nic do rozsmarowania (już zrobione lub brak danych).")
        return

    # Stabilna serializacja — jak scraper.generate_dashboard_json()
    for pk, pd_ in data.get("profiles", {}).items():
        for key in ("current_listings", "archived_listings"):
            if isinstance(pd_.get(key), list):
                pd_[key].sort(key=lambda x: str(x.get("id", "")))
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)

    # Przelicz outflow w trend_full.json z nowych archived_date (jak generate_trend_full)
    tf = json.load(open(TF_PATH, encoding="utf-8"))
    outflow = {}
    for pk, pdata in (data.get("profiles") or {}).items():
        day_counts = defaultdict(int)
        for l in pdata.get("archived_listings", []):
            ad = l.get("archived_date")
            if ad and len(ad[:10]) == 10:
                day_counts[ad[:10]] += 1
        if day_counts:
            outflow[pk] = [{"date": d, "count": day_counts[d]} for d in sorted(day_counts)]
    tf["outflow"] = outflow
    with open(TF_PATH, "w", encoding="utf-8") as f:
        json.dump(tf, f, ensure_ascii=False, indent=2, sort_keys=True)

    print(f"\nGotowe. Przesunięto {total_shifted} archiwizacji wstecz wg missed_scans.")


if __name__ == "__main__":
    main()
