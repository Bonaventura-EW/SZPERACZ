#!/usr/bin/env python3
"""
Minimalne testy czystych funkcji scrapera (bez sieci, bez przeglądarki).
Łapią regresje parsowania i odczytu ledgera.

Uruchomienie:
    python test_scraper.py        # standalone (bez zależności)
    pytest test_scraper.py        # jeśli masz pytest
"""
import json
import os
import tempfile
from datetime import datetime, timedelta

import scraper


# ─── parse_price ────────────────────────────────────────────────────────────

def test_parse_price_basic():
    assert scraper.parse_price("550 zł") == 550

def test_parse_price_space_thousands():
    assert scraper.parse_price("1 200 zł") == 1200

def test_parse_price_nbsp_thousands():
    assert scraper.parse_price("1\xa0200 zł") == 1200

def test_parse_price_with_suffix_text():
    assert scraper.parse_price("2400 zł do negocjacji") == 2400

def test_parse_price_empty_and_none():
    assert scraper.parse_price("") is None
    assert scraper.parse_price(None) is None

def test_parse_price_no_digits():
    assert scraper.parse_price("Zamienię") is None


# ─── extract_listing_id ───────────────────────────────────────────────────────

def test_extract_listing_id_from_olx_url():
    assert scraper.extract_listing_id(
        "https://www.olx.pl/d/oferta/pokoj-IDabc123.html") == "abc123"

def test_extract_listing_id_fallback_last_segment():
    assert scraper.extract_listing_id("https://olx.pl/foo/bar") == "bar"

def test_extract_listing_id_trailing_slash():
    assert scraper.extract_listing_id("https://olx.pl/foo/bar/") == "bar"


# ─── parse_date_text / _extract_date ──────────────────────────────────────────

def test_parse_date_text_refreshed():
    pub, ref = scraper.parse_date_text("Odświeżono dnia 12 maja 2026")
    assert pub is None and ref == "2026-05-12"

def test_parse_date_text_published():
    pub, ref = scraper.parse_date_text("5 czerwca 2026")
    assert pub == "2026-06-05" and ref is None

def test_parse_date_text_today():
    today = datetime.now().strftime("%Y-%m-%d")
    pub, ref = scraper.parse_date_text("Dzisiaj o 10:00")
    assert pub == today and ref == today

def test_parse_date_text_empty():
    assert scraper.parse_date_text("") == (None, None)

def test_extract_date_yesterday():
    expected = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    assert scraper._extract_date("wczoraj") == expected

def test_extract_date_month_no_year():
    expected = f"{datetime.now().year}-01-03"
    assert scraper._extract_date("3 stycznia") == expected


# ─── _load_daily_ledger ────────────────────────────────────────────────────────

def test_load_daily_ledger_reads_lines_skips_blank():
    with tempfile.NamedTemporaryFile("w", suffix=".ndjson", delete=False,
                                     encoding="utf-8") as f:
        f.write(json.dumps({"profile": "a", "count": 1}) + "\n")
        f.write("\n")  # pusta linia ignorowana
        f.write(json.dumps({"profile": "b", "count": 2}) + "\n")
        path = f.name
    try:
        rows = scraper._load_daily_ledger(path)
        assert len(rows) == 2
        assert rows[0]["profile"] == "a" and rows[1]["count"] == 2
    finally:
        os.unlink(path)

def test_load_daily_ledger_missing_file_returns_empty():
    assert scraper._load_daily_ledger("/nonexistent/ledger.ndjson") == []


# ─── standalone runner (bez pytest) ───────────────────────────────────────────

if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"  ✅ {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {fn.__name__}: {e or 'assercja nie przeszła'}")
        except Exception as e:
            print(f"  💥 {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(fns)} testów przeszło")
    raise SystemExit(0 if passed == len(fns) else 1)
