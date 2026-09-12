---
id: 2026-09-12-pagination-abort-guard
repo: Bonaventura-EW/SZPERACZ
family: scrapery-olx
date: 2026-09-12
category: bugfix
what: Strona paginacji, której nie udało się pobrać, nie jest już brana za koniec wyników — scrape zgłasza wynik niepełny zamiast cicho zwracać połowę danych.
why: OLX pod obciążeniem oddawał kolejne strony kategorii bez kart ogłoszeń; scraper robił `break` i zapisywał 612 z 883 ogłoszeń jako poprawny stan profilu, co wbiło fałszywy dołek -267 w historię trendu. Progowa ochrona (< 50% nagłówka) tego nie złapała, bo 612/883 to 69%.
how: Nawigacja i oczekiwanie na treść trafiły do wspólnej pętli ponowień (3 próby, backoff rosnący) — przejściowy throttling nie kosztuje już doby danych. Każde awaryjne wyjście z pętli paginacji ustawia w wyniku `incomplete` + `incomplete_reason` (zamiast cicho zwracać wynik częściowy), a `is_incomplete_scrape()` wpina to w te same miejsca ochrony danych co próg procentowy: brak wpisu do historii, brak nadpisania stanu, brak archiwizacji, `ok: false` w API + alert `scrape_incomplete` z powodem urwania. Jeśli mimo urwania pobrano tyle, ile deklaruje nagłówek, wynik jest nadal pełny.
surface: scraper.py (_scrape_one_profile_playwright, scrape_with_playwright_all, is_incomplete_scrape, append_history, generate_dashboard_json, generate_api_json), rebuild_incomplete_scan_20260912.py
generality: universal
propagate: yes
commit: (uzupełnić po merge'u)
---

# Kontekst

Wzorzec jest szerszy niż OLX i niż Playwright: **każda pętla paginacji musi rozróżniać
„skończyły się wyniki" od „nie udało się pobrać strony"**. Koniec wyników ma pozytywny
sygnał (brak linku „następna", pusta lista `next` w API); brak treści to awaria. Jeśli
oba prowadzą do tego samego `break`, scraper cicho oddaje wynik częściowy, a wszystkie
ochrony niżej widzą go jako poprawny, tylko mniejszy.

Druga lekcja, przenośna niezależnie od stosu: **ochrona progowa (procent oczekiwanej
liczby) nie zastępuje flagi błędu**. Urwana paginacja daje dowolny procent — u nas
69% przy progu 50%. Flaga „wynik niepełny" jest zerojedynkowa i musi wchodzić do tych
samych bramek co próg, inaczej zostaje loteria. Odwrotnie też: progu nie warto obniżać,
bo nagłówki bywają zawyżone i fałszywe alarmy wracają.

Trzecia rzecz, jeśli brat trzyma historię w dwóch miejscach (agregat + wieczny ledger):
korekta po takim incydencie musi objąć OBA, a ledger append-only poprawia się przez
DOPISANIE rekordu korygującego z późniejszym znacznikiem czasu, nie przez edycję linii.
