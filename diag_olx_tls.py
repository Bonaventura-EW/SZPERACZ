#!/usr/bin/env python3
"""
Diagnostyka blokady OLX: czy da się dobić do OLX zwykłym HTTP i którym klientem.

Powód powstania (2026-08-24): od skanu 2026-08-12 OLX (CloudFront) zwraca HTTP 403
na KAŻDY request z biblioteki `requests` — niezależnie od nagłówków i wersji HTTP.
Blokada jest po odcisku TLS (JA3), a nie po IP czy nagłówkach. Skutki: profile
użytkowników (API) zwracały 0 ogłoszeń, a verify_listing_active() wpadała w gałąź
fail-safe „zakładam aktywne" i archiwizacja stanęła całkowicie. Patrz §7 CLAUDE.md.

Ten skrypt sprawdza empirycznie, KTÓRY klient przechodzi — uruchamiany na runnerze
GitHub Actions, bo tylko tam widać prawdziwy IP egress (Azure) i prawdziwy TLS.

Użycie:
    python diag_olx_tls.py

Nic nie zapisuje i nie modyfikuje danych — sam odczyt.
"""

import sys
import time

# ─── Cele testowe ────────────────────────────────────────────────────────────

# Profil użytkownika `pokojewlublinie` (uuid z PROFILES w scraper.py)
API_URL = (
    "https://www.olx.pl/api/v1/offers"
    "?offset=0&limit=10&category_id=0"
    "&sort_by=created_at%3Adesc&user_id=23314f02-9f24-4232-afe0-102bda498af4"
)
CATEGORY_URL = "https://www.olx.pl/nieruchomosci/stancje-pokoje/lublin/"

# Ogłoszenie obecne w ostatnim skanie (missed_scans == 0) → oczekujemy 200
LISTING_ALIVE = "https://www.olx.pl/d/oferta/pokoj-2-osobowy-lub-1-osobowy-os-weglin-CID3-ID10Ozam.html"
# Ogłoszenie nieobecne od >= 12 skanów → oczekujemy 404 albo 410
LISTING_DEAD = "https://www.olx.pl/d/oferta/wynajme-pokoj-w-mieszkaniu-3-pokojowym-CID3-ID15LBwM.html"

# Kandydaci do impersonacji. Kolejność = preferencja (najpierw najbardziej
# „przeglądarkowe" i najlepiej utrzymywane w curl_cffi).
IMPERSONATE_CANDIDATES = [
    "chrome131", "chrome124", "chrome120", "chrome116", "chrome110", "chrome99",
    "safari18_0", "safari17_0", "safari15_5",
    "edge101", "edge99",
    "firefox133",
]


def hr(title):
    print()
    print("=" * 68)
    print(title)
    print("=" * 68)


def show_egress_ip():
    hr("0. IP egress runnera")
    try:
        import requests
        r = requests.get("https://api.ipify.org?format=json", timeout=20)
        print(f"   IP: {r.text.strip()}")
    except Exception as e:
        print(f"   nie udało się ustalić: {e}")


def test_plain_requests():
    """Kontrola: potwierdzenie, że `requests` faktycznie dostaje 403."""
    hr("1. KONTROLA — zwykłe `requests` (oczekiwane: 403)")
    import requests
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pl-PL,pl;q=0.9",
    }
    results = {}
    for name, url in [("API", API_URL), ("KATEGORIA", CATEGORY_URL), ("OGŁOSZENIE", LISTING_ALIVE)]:
        try:
            r = requests.get(url, headers=headers, timeout=25)
            results[name] = r.status_code
            print(f"   {name:12} -> HTTP {r.status_code}")
        except Exception as e:
            results[name] = None
            print(f"   {name:12} -> WYJĄTEK {type(e).__name__}: {str(e)[:70]}")
        time.sleep(1)
    return results


def test_impersonations():
    """Sprawdza, które profile impersonacji przechodzą na endpoint API."""
    hr("2. curl_cffi — które profile impersonacji przechodzą (endpoint API)")
    from curl_cffi import requests as cr

    working = []
    for imp in IMPERSONATE_CANDIDATES:
        try:
            r = cr.get(API_URL, impersonate=imp, timeout=25)
            status = r.status_code
            ok = status == 200
            n_ads = None
            if ok:
                try:
                    n_ads = len(r.json().get("data", []))
                except Exception:
                    ok = False
            mark = "OK " if ok else "   "
            extra = f"  ({n_ads} ogłoszeń w odpowiedzi)" if n_ads is not None else ""
            print(f"   {mark}{imp:14} -> HTTP {status}{extra}")
            if ok:
                working.append(imp)
        except Exception as e:
            print(f"      {imp:14} -> WYJĄTEK {str(e)[:60]}")
        time.sleep(1.2)
    return working


def test_full_surface(imp):
    """Dla wybranego profilu sprawdza wszystkie 3 ścieżki, których używa scraper."""
    hr(f"3. Pełna powierzchnia scrapera dla impersonate='{imp}'")
    from curl_cffi import requests as cr

    verdict = {}

    # 3a. API profilu + paginacja
    try:
        r = cr.get(API_URL, impersonate=imp, timeout=25)
        data = r.json()
        total = data.get("metadata", {}).get("total_elements")
        ads = data.get("data", [])
        print(f"   API profilu       -> HTTP {r.status_code}, total_elements={total}, na stronie={len(ads)}")
        if ads:
            print(f"      przykład: {ads[0].get('id')} | {ads[0].get('title','')[:46]}")
        verdict["api"] = r.status_code == 200 and bool(ads)
    except Exception as e:
        print(f"   API profilu       -> BŁĄD {str(e)[:70]}")
        verdict["api"] = False
    time.sleep(1)

    # 3b. Weryfikacja ogłoszeń — sedno przywrócenia archiwizacji
    for label, url, expected in [
        ("żywe (200)", LISTING_ALIVE, {200}),
        ("martwe (404/410)", LISTING_DEAD, {404, 410}),
    ]:
        try:
            r = cr.get(url, impersonate=imp, timeout=25, allow_redirects=True)
            good = r.status_code in expected
            print(f"   Ogłoszenie {label:17} -> HTTP {r.status_code}  {'ZGODNE' if good else 'NIEZGODNE!'}")
            verdict[label] = good
        except Exception as e:
            print(f"   Ogłoszenie {label:17} -> BŁĄD {str(e)[:60]}")
            verdict[label] = False
        time.sleep(1)

    # 3c. Kategoria (dziś robi to Playwright — sprawdzamy tylko czy byłaby dostępna)
    try:
        r = cr.get(CATEGORY_URL, impersonate=imp, timeout=30)
        n_cards = 0
        if r.status_code == 200:
            from bs4 import BeautifulSoup
            n_cards = len(BeautifulSoup(r.text, "lxml").select('[data-cy="l-card"]'))
        print(f"   Kategoria         -> HTTP {r.status_code}, kart [data-cy=l-card]: {n_cards}")
        verdict["kategoria"] = r.status_code == 200 and n_cards > 0
    except Exception as e:
        print(f"   Kategoria         -> BŁĄD {str(e)[:70]}")
        verdict["kategoria"] = False

    return verdict


def main():
    print("SZPERACZ — diagnostyka blokady TLS/JA3 na OLX")
    print(f"Python {sys.version.split()[0]}")
    try:
        import curl_cffi
        print(f"curl_cffi {curl_cffi.__version__}")
    except ImportError:
        print("BŁĄD: brak curl_cffi — zainstaluj: pip install curl_cffi")
        return 1

    show_egress_ip()
    control = test_plain_requests()
    working = test_impersonations()

    hr("PODSUMOWANIE")
    if not working:
        print("   ❌ ŻADEN profil impersonacji nie przeszedł.")
        print("   Wniosek: na IP GitHub Actions sama impersonacja TLS NIE wystarcza")
        print("   (prawdopodobnie dochodzi reputacja IP zakresów Azure).")
        print("   Kierunek: zostać przy Playwrighcie także dla profili i weryfikacji.")
        return 2

    print(f"   Działające profile impersonacji ({len(working)}): {', '.join(working)}")
    best = working[0]
    verdict = test_full_surface(best)

    hr("WERDYKT")
    all_ok = all(verdict.values())
    for k, v in verdict.items():
        print(f"   {'✅' if v else '❌'} {k}")
    print()
    print(f"   Kontrola `requests`: {control}")
    print(f"   Rekomendowany impersonate: {best}")
    if all_ok:
        print("   ✅ curl_cffi odblokowuje WSZYSTKIE ścieżki — można wdrażać podmianę sesji.")
    else:
        print("   ⚠️  Część ścieżek nie działa — patrz wyżej, wdrażać wybiórczo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
