#!/usr/bin/env python3
"""
Jednorazowe przeliczenie historycznych `daily_counts[].price_distribution` na stałą
siatkę 25 zł (histogram „💰 Rozkład cen" na dashboardzie, patrz CHANGELOG 2026-11-03).

Kontekst: do 2026-11-03 scraper zapisywał rozkład cen z DYNAMICZNYM krokiem
(~14 kubełków między min a max ceną dnia — dla `wszystkie_pokoje` wychodziło 200 zł).
Teraz `build_price_distribution()` zapisuje kubełki co `PRICE_DIST_STEP` (25) zł.
Z kubełka 200-złotowego nie da się uczciwie wyciągnąć ośmiu 25-złotowych, więc skrypt
NIE zgaduje — bierze ceny z tamtego dnia z dwóch dokładnych źródeł:

  1. **Przeliczenie wprost** — gdy każdy stary kubełek mieści się w całości w jednym
     kubełku 25 zł (kroki 1/2/3/5/10/20/25 zł wyrównane do siatki; częste przy małych
     profilach). Zero utraty informacji, bez sięgania do gita.
  2. **Migawka z historii gita** — `data/dashboard_data.json` jest commitowany po każdym
     skanie, więc commit skanu z dnia D zawiera `current_listings` z cenami z tego skanu.
     Bierzemy z niej ogłoszenia obecne w skanie (bez `missed_scans` — te były tylko
     „przeniesione", patrz §7 CLAUDE.md) i budujemy rozkład nową funkcją.
     **Weryfikacja:** stary algorytm (`_legacy_build`, kopia 1:1 sprzed zmiany) uruchomiony
     na tych samych cenach musi dać DOKŁADNIE zapisany rozkład. Gdy żadna migawka dnia
     tego nie spełnia, wpis zostaje nietknięty (dashboard pokaże go po staremu).

Rekonstrukcja z per-ogłoszeniowej historii (`first_seen`/`archived_date`, jak w
`backfill_price_distribution.py`) była sprawdzona i odrzucona: myli się o 10–30% liczby
ogłoszeń dnia (reaktywacje, rotacja wyników), więc zastąpiłaby zmierzone dane gorszymi.

Idempotencja: wpis już na siatce 25 zł (każdy kubełek o szerokości 25, `from % 25 == 0`,
bez zerowych kubełków) jest pomijany — drugi przebieg nic nie zmienia.

Wymaga historii gita sięgającej najstarszego dnia w `daily_counts` (~90 dni). W płytkim
klonie (np. checkout w Actions) najpierw:
    git fetch --shallow-since=<najstarszy dzień - 2 dni> origin main

Użycie:
    python rebuild_price_distribution_25.py            # raport (dry-run)
    python rebuild_price_distribution_25.py --apply    # zapis do data/dashboard_data.json
"""

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta

from scraper import PRICE_DIST_STEP, build_price_distribution

DATA_REL = "data/dashboard_data.json"
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_REL)
STEP = PRICE_DIST_STEP


def _legacy_build(prices_raw):
    """Stary algorytm (scraper.py sprzed 2026-11-03) — TYLKO do weryfikacji migawek."""
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
    if prices[-1] >= s - step:
        extra = sum(1 for p in prices if p >= s)
        if extra:
            buckets[-1]["count"] += extra
    while len(buckets) > 1 and buckets[-1]["count"] == 0:
        buckets.pop()
    while len(buckets) > 1 and buckets[0]["count"] == 0:
        buckets.pop(0)
    return buckets


def _norm(dist):
    return [(b["from"], b["to"], b["count"]) for b in dist or []]


def on_grid(dist):
    """Czy rozkład jest już w docelowym formacie (rzadka siatka STEP zł)."""
    return all(b["to"] - b["from"] == STEP and b["from"] % STEP == 0 and b["count"] > 0
               for b in dist)


def direct_rebin(dist):
    """Przelicza wprost, jeśli każdy stary kubełek leży w całości w jednym kubełku STEP."""
    if not all(b["from"] // STEP == (b["to"] - 1) // STEP for b in dist):
        return None
    counts = defaultdict(int)
    for b in dist:
        if b["count"]:
            counts[b["from"] // STEP * STEP] += b["count"]
    return [{"from": f, "to": f + STEP, "count": counts[f]} for f in sorted(counts)]


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def load_snapshots(since_day):
    """{(profil, dzień): [ceny ze skanu, ...]} ze wszystkich commitów pliku danych od since_day."""
    since = (datetime.strptime(since_day, "%Y-%m-%d") - timedelta(days=2)).strftime("%Y-%m-%d")
    commits = git("log", "--format=%H", f"--since={since}", "--", DATA_REL).split()
    print(f"Migawki: {len(commits)} commitów z {DATA_REL} od {since} …")
    snaps = defaultdict(list)
    for i, sha in enumerate(reversed(commits), 1):  # od najstarszego
        try:
            snap = json.loads(git("show", f"{sha}:{DATA_REL}"))
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            continue
        day = str(snap.get("last_scan") or "")[:10]
        if not day:
            continue
        for pk, prof in (snap.get("profiles") or {}).items():
            prices = [l.get("price") for l in prof.get("current_listings", [])
                      if not l.get("missed_scans")]
            snaps[(pk, day)].append((sha[:7], prices))
        if i % 25 == 0:
            print(f"  … {i}/{len(commits)}")
    return snaps


def oldest_commit_day():
    out = git("log", "--format=%ad", "--date=short", "--reverse", "--", DATA_REL).split()
    return out[0] if out else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true", help="zapisz zmiany do pliku danych")
    args = ap.parse_args()

    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    todo = []  # (pk, entry) wymagające migawki z gita
    stats = defaultdict(int)
    changes = {}  # id(entry) -> nowy rozkład

    for pk, prof in data["profiles"].items():
        for e in prof.get("daily_counts", []):
            dist = e.get("price_distribution") or []
            if not dist:
                stats["pusty"] += 1
            elif on_grid(dist):
                stats["już na siatce"] += 1
            else:
                new = direct_rebin(dist)
                if new is not None:
                    changes[id(e)] = (pk, e, new, "wprost")
                else:
                    todo.append((pk, e))

    if todo:
        oldest = min(e["date"] for _, e in todo)
        snaps = load_snapshots(oldest)
        first_day = oldest_commit_day()
        if first_day and first_day > oldest:
            print(f"⚠️  Historia gita zaczyna się {first_day}, a najstarszy dzień do przeliczenia "
                  f"to {oldest}. Pogłęb klon:\n    git fetch --shallow-since={oldest} origin main")
        for pk, e in todo:
            want = _norm(e["price_distribution"])
            matches = [(sha, prices) for sha, prices in snaps.get((pk, e["date"]), [])
                       if _norm(_legacy_build(prices)) == want]
            if not matches:
                stats["brak pasującej migawki"] += 1
                print(f"  ✗ {pk} {e['date']}: żadna migawka dnia nie odtwarza zapisanego rozkładu "
                      f"— zostaje po staremu")
                continue
            sha, prices = matches[-1]  # ostatni skan dnia, który nadpisał rozkład
            new = build_price_distribution([{"price": p} for p in prices])
            variants = {tuple(_norm(build_price_distribution([{"price": p} for p in pr])))
                        for _, pr in matches}
            if len(variants) > 1:
                stats["niejednoznaczne (wzięto ostatni skan)"] += 1
            changes[id(e)] = (pk, e, new, f"git {sha}")

    per_profile = defaultdict(lambda: defaultdict(int))
    for pk, e, new, how in changes.values():
        old_total = sum(b["count"] for b in e["price_distribution"])
        new_total = sum(b["count"] for b in new)
        if old_total != new_total:  # nie powinno się zdarzyć — weryfikacja wyżej
            print(f"  ✗ {pk} {e['date']}: suma {old_total} → {new_total}, pomijam")
            stats["niezgodna suma"] += 1
            continue
        per_profile[pk]["git" if how.startswith("git") else how] += 1
        stats[f"przeliczone ({'git' if how.startswith('git') else how})"] += 1
        if args.apply:
            e["price_distribution"] = new

    print("\nPrzeliczone wpisy per profil:")
    for pk in sorted(per_profile):
        print(f"  {pk:22s} " + ", ".join(f"{k}: {v}" for k, v in sorted(per_profile[pk].items())))
    print("\nPodsumowanie:")
    for k, v in sorted(stats.items()):
        print(f"  {k:40s} {v}")

    if args.apply:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        print(f"\n✅ Zapisano {DATA_PATH}")
    else:
        print("\n(dry-run — nic nie zapisano; dodaj --apply)")


if __name__ == "__main__":
    sys.exit(main())
