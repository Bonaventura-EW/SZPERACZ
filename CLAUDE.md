# CLAUDE.md

Przewodnik po projekcie dla Claude Code. Czytaj go na początku każdej sesji,
a po każdej istotnej zmianie **aktualizuj** (patrz sekcja "Utrzymywanie tego pliku").

> **Na początku każdej sesji przeczytaj też `CHANGELOG.md`** (zwłaszcza najnowsze
> wpisy u góry), żeby być na bieżąco z ostatnimi zmianami, naprawami i decyzjami.
> CLAUDE.md zawiera tylko zwięzłe reguły — pełny kontekst zmian jest w `CHANGELOG.md`
> oraz w raportach napraw (`ROOT_CAUSE_RAPORT_*`, `NAPRAWA_*`).

---

## 1. Czym jest SZPERACZ

Autonomiczny monitor ogłoszeń **OLX.pl**. Codziennie scrapuje wybrane profile
i kategorie, śledzi liczbę ogłoszeń, ceny, odświeżenia, promocje i archiwizację,
a wyniki zapisuje do plików w repo. Brak backendu — wszystko działa na
GitHub Actions + GitHub Pages.

Pętla działania:
1. GitHub Action (cron) uruchamia scraper.
2. Scraper pobiera dane z OLX i zapisuje `data/dashboard_data.json` + `data/szperacz_olx.xlsx` + `docs/api/*.json`.
3. Action commituje te pliki z powrotem do repo.
4. Dashboard (`docs/index.html`, GitHub Pages) czyta JSON i renderuje wykresy/tabele.
5. Co poniedziałek osobny Action wysyła raport email.

Język projektu i dokumentacji: **polski**. Pisz komunikaty/commity po polsku.

---

## 2. Stos technologiczny

- Python 3.11+ (Actions używają 3.12)
- `requests` + `beautifulsoup4` + `lxml` — scraping HTML
- `playwright` — główny silnik scrapingu (renderuje stronę OLX)
- `brotli` — **wymagany**, OLX zwraca `Content-Encoding: br` (patrz Gotchas)
- `openpyxl` — generowanie Excela
- `matplotlib` — wykresy w mailu
- Dashboard: czysty HTML/CSS/JS (bez frameworków, bez build-stepu)

Pełna lista: `requirements.txt`.

---

## 3. Mapa plików

### Kod główny
- `main.py` — entry point / dispatcher CLI. Komendy: `--scan`, `--email`, `--status`, `--help`.
  Setup logowania, tworzenie `data/`, generowanie `docs/api/status.json` i `history.json`,
  obsługa błędów (zapis statusu failu do API).
- `scraper.py` — silnik (~2200 linii). Najważniejsze:
  - `PROFILES` — słownik monitorowanych profili/kategorii (patrz §5).
  - `scrape_with_playwright_all()` — główny scrape wszystkich profili w jednej przeglądarce.
  - `scrape_with_crosscheck()` — scrape + weryfikacja liczby wyników z nagłówkiem strony.
  - `parse_card()` / `parse_listings_from_soup()` — parsowanie kart ogłoszeń (selektor `[data-cy="l-card"]` z fallbackami).
  - `detect_promoted_status()` / `promotion_dict_to_fields()` — wykrywanie płatnych promocji.
  - `generate_dashboard_json()` — scala nowy scan ze stanem: archiwizacja, ceny, refresh, reaktywacje, promocje, daily_counts.
  - `update_excel()` — zapis arkuszy Excela.
  - `generate_api_json()` — pisze `docs/api/status.json` + `history.json` (ostatnie 30 scanów).
  - `run_scan()` — orkiestracja: scrape → JSON → Excel → API.
  - `verify_listing_active()` — przed archiwizacją sprawdza, czy ogłoszenie naprawdę zniknęło.
- `email_report.py` — raport tygodniowy. `SENDER_EMAIL = slowholidays00@gmail.com`,
  `RECEIVER_EMAIL = malczarski@gmail.com`. `build_report_html()` (podsumowanie rynku, wykresy,
  top spadki cen, nowe ogłoszenia, wiersze per profil), `send_report()` (SMTP Gmail + załącznik Excel),
  `save_preview()` → `data/email_preview.html`.

### Skrypty pomocnicze (jednorazowe naprawy/migracje danych)
- `diagnose.py` — checklist diagnostyczny (linki do Actions).
- `autofix.py` — pusty commit reaktywujący wyłączone scheduled workflows.
- `rebuild_historical_medians.py` — odtwarza `median_price` per dzień.
- `rebuild_daily_flows.py` — przelicza `added`/`removed` w `daily_counts`.
- `rebuild_refresh_history.py` / `rebuild_refresh_dedupe.py` / `rebuild_refreshed_count.py` — naprawa danych o odświeżeniach.
- `rebuild_archive_counters.py` / `rebuild_refresh_reactivation_counts.py` — liczniki refresh/reaktywacji.
- `backfill_prices.py` (przestarzały) / `backfill_price_distribution.py` — uzupełnianie historii cen.
  > Te skrypty modyfikują `data/*.json`. Uruchamiaj świadomie, rób kopię/commit przed.

### Dane (commitowane do repo!)
- `data/dashboard_data.json` — główny plik stanu (patrz §4).
- `data/szperacz_olx.xlsx` — pełna historia, arkusze: per-profil, `historia_cen`, `podsumowanie`.
- `docs/api/status.json`, `docs/api/history.json` — lekki API dla dashboardu/aplikacji.
  - `status.json` — stan ostatniego scanu: globalnie `total_listings`/`added`/`removed`/`price_changes`
    oraz per profil `count`/`added`/`removed`/`crosscheck`. `added`/`removed` = przybyło/zniknęło
    (czytane ze świeżego `daily_counts`; `null` = nie policzono, nie 0).
  - `history.json` — **3 ostatnie scany** (`scans` od najstarszego, `recent` od najnowszego), z added/removed per profil.
  - Generuje `generate_api_json()` w scraper.py. Opis: `docs/api/JAK_DZIALA_API.txt`, `README.md`, `openapi.yaml`.

### Dashboard
- `docs/index.html` (~2500 linii) — SPA czytająca `dashboard_data.json` i `docs/api/*`.
  Karty profili, wykresy (słupkowy 7/14/30 dni, liniowy z zoomem, 4 metryki),
  sortowalne tabele aktywnych/archiwalnych, tryb jasny/ciemny, przycisk ręcznego scanu (przez GitHub PAT).

### Automatyzacja (`.github/workflows/`)
- `scan.yml` — `cron: '0 7 * * *'` (LATEM/CEST = 9:00 PL). Uruchamia scraper, commituje `data/` + `docs/api/`. Wymaga `permissions: contents: write`.
- `weekly_report.yml` — `cron: '30 7 * * 1'` (poniedziałki). Uruchamia `email_report.py`. Wymaga sekretu `EMAIL_PASSWORD`.
- `keep-alive.yml` — `cron: '0 3 */50 * *'`. Pusty commit co 50 dni, żeby GitHub nie wyłączył crona po 60 dniach.
- `failsafe.yml` — `cron: '0 11 * * *'`. Sprawdza, czy dzisiejszy scan się udał; jeśli nie — dispatch `scan.yml`.

### Dokumentacja
README.md, SETUP_GUIDE.md, PROJECT_STRUCTURE.md, QUICK_REFERENCE.md, TROUBLESHOOTING.md,
ARCHIWUM_DOCUMENTATION.md, ZMIANA_CZASU_REMINDER.md, GITHUB_UPLOAD_CHECKLIST.md,
CHANGELOG.md (pełna historia zmian) + raporty napraw (NAPRAWA_*, ROOT_CAUSE_RAPORT_*).

---

## 4. Struktura `dashboard_data.json`

```
{
  "profiles": {
    "<klucz>": {
      "label", "url", "is_category",
      "current_listings": [ {
        id, title, price, price_text, url, published, refreshed,
        first_seen, last_seen, first_price, price_change, previous_price,
        is_promoted, promotion_type, promoted_days_current, promoted_sessions_count, promotion_history[],
        image_url, refresh_count, refresh_history[],
        reactivated, reactivation_history[], reactivation_count
      } ],
      "archived_listings": [ { ...jw. + archived_date } ],   // BEZ LIMITU (paginacja po stronie dashboardu, scraper.py:2012)
      "price_history": { "<id>": [ {date, old_price, new_price, change} ] },
      "daily_counts": [ {date, count, added, removed, new_count, median_price,
                         price_distribution, refreshed_count, reactivated_count, promoted_count} ], // limit 90 dni
      "promotion_history": { "<id>": [ {start_date, end_date, days, session_number} ] }
    }
  },
  "scan_history": [ ... ],   // limit ~90
  "last_scan": "YYYY-MM-DD HH:MM:SS",
  "metadata": { created, version }
}
```

`promotion_type`: `top_ad | highlight | urgent | premium | pushup | unknown`.

---

## 5. Monitorowane profile (`PROFILES` w scraper.py)

`wszystkie_pokoje` (kategoria), `pokojewlublinie`, `poqui`, `artymiuk`, `dawny_patron`,
`mzuri`, `villahome`. Profile użytkowników mają `uuid` do API OLX; kategoria ma `is_category: True`.
Dodawanie profilu: dopisz wpis do `PROFILES` (url, label, is_category) i uruchom scan.

---

## 6. Najczęstsze komendy

```bash
pip install -r requirements.txt
playwright install chromium      # wymagane raz dla scrapingu

python main.py --scan            # pełny scan (najczęstsze)
python main.py --email           # wyślij raport (wymaga EMAIL_PASSWORD)
python main.py --status          # status systemu
python scraper.py                # bezpośredni scan (tak robi Action)
```

Brak testów automatycznych i lintera w repo — weryfikacja przez `--scan`/`--status` i podgląd danych.

---

## 7. Gotchas / wiedza krytyczna (uczyć się na błędach z raportów)

- **Brotli jest obowiązkowy.** OLX zwraca `Content-Encoding: br`. Bez pakietu `brotli`
  `resp.text` to binarne śmieci → 0 ogłoszeń dla wszystkich profili. Nie usuwaj z requirements.
- **Nigdy nie nadpisuj danych przy count == 0.** Gdy scan zwróci 0 ogłoszeń (oznaka błędu/blokady),
  kod NIE archiwizuje i NIE nadpisuje `current_listings` — stare dane zostają. Zachowaj tę ochronę
  przy zmianach w `generate_dashboard_json()`.
- **Zmiana czasu = ręczna zmiana crona w `scan.yml`** (cel: 9:00 czasu PL przez cały rok):
  - czas letni (CEST, ~ostatnia niedziela marca): `cron: '0 7 * * *'`  ← **obecnie aktywne**
  - czas zimowy (CET, ~ostatnia niedziela października): `cron: '0 8 * * *'`
  Szczegóły w `ZMIANA_CZASU_REMINDER.md`.
- **GitHub Actions bywa opóźniony** (scany realnie lecą ~11:00 UTC mimo crona 7:00). `failsafe.yml`
  i `keep-alive.yml` to zabezpieczenia — nie usuwaj ich.
- **Dane są w gicie.** `data/*` i `docs/api/*` są commitowane. Przy ręcznych naprawach danych
  najpierw commit/backup — git history to jedyny backup.
- **Retencja ≠ okno scrapingu.** Scraper pobiera WSZYSTKIE ogłoszenia obecne na OLX *teraz* (bez okna
  czasowego). Przycinane są tylko agregaty: `daily_counts[-90:]` (scraper.py:1710) i `scan_history[-90:]`
  (scraper.py:2059) → wykresy trendów obejmują ~90 dni. Natomiast `current_listings`, `archived_listings`
  (nieograniczone!) oraz `price_history`/`refresh_history`/`promotion_history` rosną BEZ limitu → `dashboard_data.json`
  puchnie latami. To (obok binarnego `xlsx`) główne źródło rozrostu repo.
- **Archiwizacja po znikinięciu** weryfikowana przez `verify_listing_active()` (false positives przy blokadach OLX).
- **Email**: `EMAIL_PASSWORD` to 16-znakowy Gmail App Password (nie hasło konta), w GitHub Secrets.

---

## 8. Konwencje pracy w tym repo

- Gałąź robocza tej sesji: `claude/fervent-mendel-2AWyk`. Commituj i pushuj tam.
- Commity i komunikaty po polsku, w stylu istniejącej historii.
- Nie dodawaj PR bez wyraźnej prośby.
- **Po skończonych zmianach pytaj, czy zmergować je do `main`** (sam nie pushuj do `main` ani nie otwieraj PR bez zgody).
- Edytuj istniejące pliki; nie twórz nowej dokumentacji bez potrzeby.

---

## 9. Utrzymywanie tego pliku (WAŻNE)

Ten plik ma odzwierciedlać **aktualny stan projektu**. Po każdej istotnej zmianie zaktualizuj
odpowiednią sekcję CLAUDE.md w tym samym commicie co zmianę kodu. W szczególności:

- Zmiana `cron` w workflow → zaktualizuj §3 i §7.
- Dodanie/usunięcie profilu → §5.
- Nowe pole w `dashboard_data.json` → §4.
- Nowa zależność / zmiana w pipeline → §2, §3.
- Nowy "gotcha" wykryty podczas debugowania → dopisz do §7 (to nasza pamięć instytucjonalna).

Dłuższe historie napraw zapisuj w `CHANGELOG.md` lub osobnym raporcie (jak `ROOT_CAUSE_RAPORT_*`),
a w CLAUDE.md zostaw tylko zwięzły wniosek/regułę. Cel: czytając sam ten plik, można zrozumieć
i bezpiecznie zmieniać projekt.

**Na start sesji:** przeczytaj CLAUDE.md **oraz** najnowsze wpisy w `CHANGELOG.md`,
żeby znać ostatnie zmiany i nie cofnąć cudzych napraw. Każdą istotną zmianę dopisuj
do `CHANGELOG.md` (najnowsze na górze) w tym samym commicie co kod.
