---
id: 2026-11-03-price-histogram-fixed-step
repo: Bonaventura-EW/SZPERACZ
family: szperacze
date: 2026-11-03
category: feature
what: Histogram rozkładu cen jest zapisywany w stałych kubełkach co 25 zł (rzadko, pełny zakres), a dashboard rysuje go z progiem ceny 1500 zł i wspólną osią dla wszystkich dni profilu.
why: Dynamiczny krok (~14 kubełków między min a max ceną dnia) dawał dla głównej kategorii słupki co 200 zł — pojedyncze drogie oferty rozciągały zakres, cały realny rynek mieścił się w 3 słupkach, a rozkłady z różnych dni miały różną siatkę, więc suwak dnia przestawiał oś.
how: Scraper zapisuje `price_distribution` jako listę niepustych kubełków `[from, from+25)` na siatce od zera — pełny zakres cen, bez progu. Próg prezentacji (oferty > 1500 zł pominięte, ich liczba w osobnym kafelku) i dopełnianie zer robi dashboard; oś liczy z wszystkich dni profilu, statystyki z dolnych granic kubełków (dokładne dla „okrągłych" cen). Historię przeliczono skryptem z migawek `dashboard_data.json` w historii gita, weryfikując każdą migawkę starym algorytmem (musi odtworzyć zapisany rozkład 1:1).
surface: scraper.py (build_price_distribution, PRICE_DIST_STEP, generate_dashboard_json), docs/index.html (histogram Rozkład cen), rebuild_price_distribution_25.py, backfill_price_distribution.py, test_scraper.py
generality: family
propagate: maybe
commit: (uzupełnić po merge'u)
---

# Kontekst

Przenośne są dwie rzeczy, nieprzenośna jedna:

1. **Stała, rzadka siatka kubełków w danych + próg tylko w prezentacji** — wzorzec dla każdego
   brata z histogramem cen w `daily_counts`. Dane trzymają pełny zakres, więc zmiana progu
   czy kroku wyświetlania nie wymaga przeliczania historii.
2. **Przeliczanie per-dniowych agregatów z migawek w historii gita** — skoro dane są commitowane
   po każdym skanie, `git show <commit>:data/dashboard_data.json` jest dokładnym zapisem stanu
   dnia D (ogłoszenia bez `missed_scans` = lista ze skanu). Kluczowa jest weryfikacja: stary
   algorytm na cenach z migawki musi dać dokładnie zapisany agregat, inaczej wpisu nie ruszamy.
   Rekonstrukcja z `first_seen`/`archived_date` była sprawdzona i odrzucona (10–30% błędu
   liczby ogłoszeń dnia). Płytki klon wymaga `git fetch --shallow-since=...`.

**Lokalne (nie kopiować 1:1): próg 1500 zł i krok 25 zł** są dobrane pod rynek pokoi w Lublinie
(85% cen podzielnych przez 25, oferty > 1500 zł to w praktyce całe mieszkania). Brat monitorujący
mieszkania musi dobrać własne wartości (`PRICE_DIST_STEP`, `HIST_MAX_PRICE`) — tamtejszy rynek
leży w zupełnie innym przedziale i przy tym progu histogram byłby prawie pusty.
