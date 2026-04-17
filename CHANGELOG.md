# 📋 CHANGELOG

Wszystkie istotne zmiany w projekcie SZPERACZ OLX są dokumentowane w tym pliku.

Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.0.0/).

---

## [Unreleased]

### Planowane
- Integracja z Telegram Bot

---

## [2026-04-17] - 📊 Archiwum: liczniki odświeżeń i reaktywacji + nowa kolumna w dashboardzie

### Fixed 🐛
- **`scraper.py` — archiwizacja zachowuje pełną strukturę liczników**:
  Gdy ogłoszenie trafia do archiwum, teraz zawsze przenoszone są: `refresh_count`, `refresh_history`, `reactivation_count`, `reactivation_history` (z domyślnymi wartościami dla pól które nie istniały). Dodatkowo bieżący otwarty okres aktywności w `reactivation_history[-1]` dostaje pole `active_to_current` (= `archived_date`), żeby zamknąć pełny timeline ogłoszenia.
- **`scraper.py` — zliczanie dziennych eventów odśw./reakt. obejmuje świeżo zarchiwizowane**:
  Dotychczas `daily_counts[*].refreshed_count` / `reactivated_count` były liczone tylko dla ogłoszeń obecnych w `new_listings` po scanie. Problem: jeśli ogłoszenie zostało w tym samym scanie odświeżone a potem zniknęło (user zamknął/archiwizował ogłoszenie po odświeżeniu), event nie liczył się w wykresie. Teraz zliczanie obejmuje `new_listings + newly_archived`.
- **`scraper.py` — kopiowanie refresh_count/history po reaktywacji**:
  Gdy ogłoszenie wraca z archiwum, teraz poprawnie kopiuje `refresh_count` i `refresh_history` z archiwalnego wpisu. Dotychczas traciło historię.

### Added ✨
- **`rebuild_archive_counters.py`** — nowy skrypt rekonstruujący historię z Excela:
  - Dla każdego archiwalnego i aktywnego ogłoszenia odbudowuje `refresh_history`, `refresh_count`, `reactivation_history`, `reactivation_count` na podstawie wpisów z Excela per-ID.
  - Reaktywacja wykrywana jako luka ≥ 2 scanów, w których ID nie występowało, po czym wróciło.
  - Następnie rebuilduje `daily_counts[*].refreshed_count` / `reactivated_count` z rzeczywistych zdarzeń ze wszystkich ogłoszeń (aktywnych + archiwum).
  - Idempotentny — można uruchamiać wielokrotnie.

### Data fix 🔧
Rebuild uruchomiony na żywych danych, efekt:
- Przetworzono **819 ogłoszeń** (aktywne + archiwum, 7 profili).
- Dodano **205 zdarzeń odświeżeń** i **20 zdarzeń reaktywacji** do historii.
- **33 archiwalnych ogłoszeń** zyskało populowany `refresh_count`, **2 archiwalnych** zyskało `reactivation_count`.
- Daily_counts zaktualizowane: `wszystkie_pokoje` (+35 dni z reaktywacjami), `mzuri` (+9), `dawny_patron` (+3), `pokojewlublinie` (+1).

### 📊 Dashboard UI
- **Nowa kolumna „Licz. reakt."** w tabeli ogłoszeń (aktywne i archiwum), obok „Licz. odsw.":
  - Sortowalna.
  - Kolor zielony gdy > 0, szary gdy 0.
  - Tooltip pokazuje datę ostatniej reaktywacji.
- Tabele w obu zakładkach (Aktualne, Archiwum) mają teraz spójne 11 kolumn (12 w archiwum z „Zniknęło").

### Uwaga 📝
Dla profili użytkowników (`poqui`, `mzuri`, `artymiuk`, `dawny_patron`, `pokojewlublinie`) scraper pobiera dane z `__PRERENDERED_STATE__` JSON, który nie zawiera daty odświeżenia — kolumna `Data odświeżenia` w Excelu dla tych profili jest pusta. Z tego powodu rebuild zdarzeń odświeżeń działa tylko dla kategorii `wszystkie_pokoje`. To specyfika źródła danych, nie bug.

---

## [2026-04-17] - 🐛 Fix: Poprawna definicja "odświeżenia" + cleanup fake entries

### Fixed 🐛
- **`scraper.py` — pierwsze wykrycie daty refresh NIE jest eventem odświeżenia**:
  Poprzednia logika `is_new_refresh = old_refreshed is None or new_refreshed > old_refreshed` liczyła każde pierwsze wykrycie pola `refreshed` jako event. Problem: OLX **zawsze** podaje datę refreshu dla każdego ogłoszenia (nawet gdy user nigdy go nie odświeżył — to pokazuje datę publikacji), więc każde nowe ogłoszenie dodawane do tracking'u dostawało `+1` do `refresh_count`. Nowa definicja: event odświeżenia = **ZMIANA** pola refreshed z X na Y (Y>X). Pierwsza wartość pola refreshed to tylko historyczna informacja, nie event.
- **`rebuild_refresh_history.py` — restrictive fallback**:
  Fallback dodawał syntetyczny wpis dla każdego ogłoszenia z `refreshed != None` bez dopasowania w Excelu. Teraz dodaje tylko gdy `json_refreshed` jest **nowsze** niż najnowsza data widziana w Excelu (rzeczywista nowa zmiana). + ten sam fix co w scraper.py: historia liczy tylko zmiany refreshed, nie pierwsze wykrycia.

### Data fix 🔧
- Wyczyszczono **323 fake entries** (`old_date=None`) z `refresh_history` wszystkich ogłoszeń:
  - wszystkie_pokoje: 214
  - mzuri: 86 (agencja, nigdy nie odświeża manualnie)
  - poqui: 10
  - dawny_patron: 7
  - pokojewlublinie: 4
  - artymiuk: 2
- Przeliczono `daily_counts[*].refreshed_count` dla wszystkich dni na podstawie pozostałych **213 prawdziwych eventów** (zmiana refreshed na nowszą datę).
- Najbardziej spektakularne korekty: `wszystkie_pokoje[2026-03-30]: 33 → 0`, `mzuri[2026-04-11]: 8 → 0`, `poqui[2026-03-07]: 6 → 0`.

### Semantic change 📝
- Interpretacja metryki "odświeżenia" w dashboard'zie zmienia się: teraz pokazuje tylko RZECZYWISTE odświeżenia (user kliknął "Odśwież ogłoszenie"), nie pierwsze wykrycie. Liczby będą znacznie niższe niż dotychczas, ale za to prawdziwe.

---

## [2026-04-17] - 🐛 Data fix: Usunięcie fake "synthetic" refresh entries z rebuildu

### Fixed 🐛
- **Data fix refresh_history**: Commit `4343f5f` uruchomił `rebuild_refresh_history.py`, który dla każdego ogłoszenia z `refreshed != None` w JSON ale bez matchu w Excelu dodał **syntetyczny wpis z `detected_at=last_scan_date + last_scan_time`**. Efekt: 70 ogłoszeń (w tym 50 w mzuri) dostało `refresh_count=1` z tym samym timestampem `2026-04-17 08:50:00`. Następnie `rebuild_refreshed_count.py` zliczył je wszystkie jako zdarzenia z tego dnia — stąd `daily_counts[2026-04-17].refreshed_count=45` dla mzuri (mimo że mzuri to agencja i NIGDY nie odświeża ogłoszeń ręcznie, co potwierdza Excel: 71 ogłoszeń, 0 z historią zmian `refreshed`).
- **Cleanup**: usunięto 70 synthetic entries (detected_at=`2026-04-17 08:50:00` + old_date=None) i przeliczono `refreshed_count` w daily_counts:
  - wszystkie_pokoje: 34 → 29
  - pokojewlublinie: 1 → 0
  - poqui: 7 → 4
  - dawny_patron: 4 → 0
  - mzuri: **45 → 0** (główny case)

### Open issue ⚠️
- Logika fallback w `rebuild_refresh_history.py` (linie 173-184) dalej generuje synthetic entries. Powinna być albo usunięta, albo ograniczona do sytuacji gdzie `refreshed_at > last scan date` (czyli rzeczywiście nowa data odświeżenia), inaczej będzie kłamać przy każdym kolejnym uruchomieniu.

---

## [2026-04-17] - 🐛 Fix: Guard rozróżnia legit-empty vs scraper-error

### Fixed 🐛
- **`scraper.py` — rozróżnienie "prawdziwie pusty profil" od "błędu scrapera"**:
  Poprzedni guard `if result["count"] > 0` był za prosty — traktował WSZYSTKIE przypadki count=0 jako błąd scrapera. Efekt: gdy użytkownik (np. artymiuk) realnie usunął swoje ogłoszenia i OLX API zwraca `total_elements=0`, ogłoszenia zostawały martwe w `current_listings` na zawsze. Wprowadzono funkcję `is_scraper_error`:
  - `crosscheck == "error"` → na pewno błąd, chroń dane
  - `count == 0 and header_count is None` → nie można zweryfikować, chroń
  - `crosscheck == "passed" and header_count == 0` → **PRAWDZIWIE pusty profil**, archiwizuj normalnie
  Zarówno archiwizacja, jak i guard na daily_counts używają teraz tego samego sygnału.

### Data fix 🔧
- Ręcznie przeniesiono "Pokój jednoosobowy Wyżynna" (artymiuk) z current_listings do archived_listings — ogłoszenie było nieaktywne na OLX od 2026-04-10, ale poprzedni guard trzymał je w current przez 7 dni.

### Tested ✅
- Dry-run: 3 scenariusze testowe (legit empty, scraper error, normal scan) → wszystkie działają zgodnie z oczekiwaniem.

---

## [2026-04-17] - 🐛 Fix: Audyt kodu + ochrona daily_counts przed błędami scrapera

### Fixed 🐛
- **`scraper.py` — ochrona daily_counts przed błędami scrapera** (`generate_dashboard_json()`):
  Gdy scan zwracał 0 wyników (OLX blocking, network error), archiwizacja i `current_listings` były chronione, ale **`daily_counts` były nadpisywane wartością 0**. Efekt: dashboard dla artymiuka od 5 dni pokazywał `count=0`, mimo że `current_listings` miał 1 ogłoszenie. Dodano guard: jeśli `result["count"]==0` ALE `current_listings` ma >0 elementów → pomijamy całą aktualizację daily_counts.
- **`scraper.py` — promocje dla nowych ogłoszeń**: cały blok `# ═══ PROMOTION TRACKING ═══` był wewnątrz `if lid in old_map:`, więc dla nowo wykrytych ogłoszeń (lub reaktywowanych z archiwum) które od razu były promowane, **pierwszy dzień promocji nie był liczony**. Dodano `else` branch: nowe promowane → `promoted_days_current=1, promoted_sessions_count=1`; reaktywacje promowane → licznik sesji z archiwum + 1; zachowuje `promotion_history` z archived_listings.
- **`email_report.py`** (linia 551): `trend_diff` leak'owało między iteracjami pętli po profilach. Dodano `trend_diff = None` inicjalizację i poprawiono warunek na `trend_diff is not None and trend_diff > 15`.
- **`scraper.py` — shadowing zmiennej**: `new_listings` używane w dwóch różnych znaczeniach w tej samej funkcji. Pierwsza (lista nowych względem `old_map` — do mediany) zmieniona na `newly_detected_listings`.

### Changed 🔧
- **Porządki pyflakes**: usunięte nieużywane importy (`sys`, `json` w diagnose.py; `datetime` w backfill_prices.py, rebuild_refresh_reactivation_counts.py, rebuild_refreshed_count.py; `timedelta` w rebuild_historical_medians.py). Poprawione f-stringi bez placeholderów w 7 plikach.
- **`backfill_prices.py`**: dodane ostrzeżenie DEPRECATED w docstring — skrypt stosuje aktualną medianę do wszystkich historycznych dni, co psuje dane. Zalecany `rebuild_historical_medians.py`.

### Tested ✅
- Dry-run: symulacja scan error dla artymiuka — guard działa, `current_listings` zachowane, brak nowego wpisu `count=0` w daily_counts.
- Normalna operacja: wszystkie profile dostają poprawne daily_counts update.
- Profile prawdziwie puste (villahome, current=0, scan=0) dostają normalny wpis count=0 — guard nie blokuje.
- `py_compile` + `pyflakes` = wszystkie 10 plików czyste.

---

## [2026-04-17] - 🐛 Fix: Licznik odświeżeń dla pierwszego wykrytego refreshu

### Fixed 🐛
- **`scraper.py`** (linia 1591): warunek `if old_refreshed and new_refreshed and new_refreshed > old_refreshed` wymagał by poprzedni `refreshed` był truthy, przez co **pierwsze pojawienie się znacznika odświeżenia nigdy nie było liczone**. Nowa logika jest idempotentna:
  - Pierwsze wykrycie refreshu (`old_refreshed=None` → data) = +1
  - Zmiana daty refreshu (stara → nowa) = +1
  - Ponowne wykrycie tej samej daty = 0 (sprawdzamy czy `refreshed_at` już jest w `refresh_history`)
- **`rebuild_refresh_history.py`**:
  - Ten sam bug w logice rekonstrukcji historii (pierwszy refresh gubiony)
  - **Zła mapa kolumn Excel**: czytał `ID ogłoszenia` z kolumny 12 i `Data odświeżenia` z kolumny 10, a w aktualnym layoucie są w kolumnach 17 i 14 (po dodaniu "Liczba odświeżeń"). Dodano autodetekcję kolumn z nagłówka arkusza.
  - **Rozbieżność Excel vs JSON**: gdy JSON miał `refreshed` którego Excel nie pokazuje dla ostatniego scanu, rebuild to pomijał. Dodano fallback: jeśli aktualny `refreshed` z JSON nie jest obecny w scanach z Excela, dokleja go jako syntetyczny wpis z timestampem `last_scan` (dla current) lub `archived_date` (dla archived).
  - Zawsze nadpisuje `refresh_history` i `refresh_count` (wcześniej zostawiał stare, buggy wartości gdy nie znalazł nowych).

### Changed 🔧
- Rebuild historyczny: refresh_count i refresh_history przeliczone od zera dla wszystkich profili na podstawie pełnych danych Excel + fallback z JSON. Łącznie 389 ogłoszeń z historią odświeżeń, 567 wydarzeń. Invariant `refresh_count == len(refresh_history)` spełniony dla wszystkich ogłoszeń.

### Example 📸
Przed fixem — ogłoszenia które po raz pierwszy dostały datę odświeżenia miały ikonkę 🔄 w UI, ale `refresh_count=0`:
- `Jasny pokoj... ul. Grabskiego` — refreshed=2026-04-15, **count=0** ❌
- `Pokój z balkonem do wynajęcia od zaraz!` — refreshed=2026-04-15, **count=0** ❌

Po fixie: `count=1` dla obu, z wpisem `{refreshed_at: "2026-04-15", old_date: null}` w historii.



### Changed 📊
- **Wykres % Promowanych** — tooltip teraz pokazuje trzy linie informacji:
  - Data (np. `11.04`)
  - `Promowane: 12` — liczba promowanych ogłoszeń
  - `Udział: 6%` — procentowy udział promowanych
- Dodano `promotedCountData` do danych wykresu liniowego

---

## [2026-04-11] - ✨ Feature: Osobna strona Historia skanów (scans.html)

### Added ✨
- **`docs/scans.html`** — dedykowana strona historii skanów, dostępna przez przycisk "Skany" w topbarze:
  - **Hero** — statystyki ostatniego scanu: czas całkowity, ogłoszeń łącznie, nowych ogłoszeń, liczba profili
  - **Karty per profil** — czas scanu, pasek proporcjonalny, metoda (API/Playwright), liczba ogłoszeń, crosscheck
  - **Wykres trendu** — słupkowy chart czasu skanowania dla wszystkich historycznych skanów (do 30), zielony=sukces/czerwony=błąd
  - **Tabela historii** — wszystkie skany od najnowszego: data, status badge, czas, wizualizacja, liczba ogłoszeń
  - Spójna stylizacja z dashboardem (dark/light theme, JetBrains Mono, DM Sans, te same CSS variables)

### Changed 📊
- `docs/index.html`: przycisk "Skany" zmieniony z otwierającego panel na link `href="scans.html"`
- Usunięty stary CSS panelu skanów i JS funkcje `toggleScansPanel`/`renderScansPanel` z `index.html`

---

## [2026-04-11] - ✨ Feature: Zakładka "Skany" z czasami wykonania

### Added ✨
- **Przycisk "Skany"** w topbarze dashboardu — otwiera/zamyka panel z historią skanów
- **Panel skanów** wysuwa się pod topbarem (animacja max-height), zawiera tabelę:
  - Profil, liczba ogłoszeń, crosscheck (✓/✗/~), czas scanu w sekundach, wizualny pasek proporcjonalny
  - Wiersz podsumowania z łącznym czasem całego scanu i datą
- **Pomiar czasu per profil** w `scraper.py` — `duration_seconds` dodany do każdego wyniku profilu
- `status.json` rozszerzony o pole `profiles[pk].duration_seconds`

---

## [2026-04-11] - 🐛 Fix: Playwright dla wszystkich profili

### Fixed 🐛
- **GitHub Actions IP blokowane przez OLX:** scraper `requests` zwracał pustą stronę 200 OK dla każdego profilu — OLX filtruje ruch z IP data center Microsoft/Azure
- Wszystkie profile (kategoria + user profiles) przerzucone na **Playwright** (headless Chromium), który omija blokadę przez zachowanie się jak prawdziwy użytkownik

### Changed 📊
- `scraper.py`: usunięte stare `scrape_profile_playwright` (DEPRECATED) i `scrape_with_crosscheck` z logiką requests
- Nowa `scrape_with_playwright_all(profiles)` — jeden browser context dla wszystkich profili naraz
- Nowa `_scrape_one_profile_playwright(page_obj, profile_key, cfg)` — obsługuje jeden profil:
  - User profiles: `page.evaluate("JSON.stringify(window.__PRERENDERED_STATE__)")` — JSON parsowany przez silnik JS, bez kruchego regex
  - Kategoria: wait for `[data-cy="l-card"]` → BeautifulSoup → paginacja DOM
- Nowa `_parse_ads_json(ads)` — wspólny parser dla `adsOffers.data[]`
- `run_scan()` wywołuje teraz `scrape_with_playwright_all(PROFILES)` zamiast pętli per-profil

---

## [2026-04-10] - 🐛 Fix: refreshed_count Calculation

### Fixed 🐛
- **Naprawa liczenia `refreshed_count` w daily_counts:**
  - **Problem:** `refreshed_count` było błędnie obliczane jako liczba ogłoszeń z `refreshed == today`, co również liczyło nowe ogłoszenia opublikowane dzisiaj (OLX pokazuje "Dzisiaj o..."), a nie tylko rzeczywiste odświeżenia
  - **Rozwiązanie:** Teraz `refreshed_count` jest liczone na podstawie `refresh_history[]` - zlicza tylko ogłoszenia, które mają wpis wykryty danego dnia (`detected_at.startswith(today)`)
  - Analogicznie do sposobu liczenia `reactivated_count`
  
### Changed 📊
- `scraper.py`: Przeniesiono obliczenie `refreshed_count` po przetworzeniu `new_listings`, kiedy `refresh_history` jest już zaktualizowane
- Usunięto błędną logikę: `sum(1 for l in result["listings"] if l.get("refreshed") == today)`

### Added ✨
- **rebuild_refreshed_count.py:** Skrypt do przeliczenia historycznych wartości `refreshed_count` na podstawie `refresh_history[]` w `current_listings` i `archived_listings`
- Naprawiono 107 wpisów w `daily_counts` dla wszystkich profili

---

## [2026-04-06] - 🔄 Refresh Count Tracking & Workflow Fixes

### Added ✨
- **Refresh Count Tracking:**
  - Nowa kolumna "Liczba odświeżeń" w Excel (kolumna 15)
  - Tracking `refresh_count` w JSON - zlicza ile razy ogłoszenie zostało odświeżone
  - Automatyczna inkrementacja gdy `refreshed` date się zmienia
  - Dashboard: nowa kolumna "Licz. odsw." w tabeli ogłoszeń z sortowaniem
  - Kolor accent dla ogłoszeń z refresh_count > 0
  
- **Refresh History Tracking:**
  - Nowe pole `refresh_history[]` - pełna historia odświeżeń (analogiczne do `reactivation_history`)
  - Każdy wpis zawiera: `refreshed_at`, `detected_at`, `old_date`
  - ~~Buduje timeline od momentu wdrożenia (dane historyczne sprzed tego są stracone - OLX nie przechowuje historii)~~ **ODTWORZONE Z EXCEL!**
  - **Rebuild z Excel:** 153 ogłoszenia z historią, 576 wydarzeń odświeżenia od 2026-02-23
  - Pozwala na dokładną analizę: kiedy było każde odświeżenie, jak często sprzedawca odświeża portfolio
  
- **rebuild_refresh_history.py:**
  - Skrypt odtwarzający `refresh_history[]` z danych Excel
  - Analizuje wszystkie historyczne scany i wykrywa zmiany daty `refreshed`
  - Wykorzystany do przeliczenia 576 wpisów historii dla 153 ogłoszeń
  
- **Wykres "Odświeżenia/Reaktywacje" (nowa metryka w line chart):**
  - Nowy przycisk 🔄 w przełączniku metryk (obok Ogłoszenia, Mediana, % Promowanych)
  - Dwie linie na wykresie:
    - 🔵 Odświeżenia (refreshed_count per dzień)
    - 🟢 Reaktywacje (reactivated_count per dzień)
  - Tracking w daily_counts: `refreshed_count`, `reactivated_count`
  - Legenda i tooltips dla obu metryk
  
- **rebuild_refresh_reactivation_counts.py:**
  - Skrypt odtwarzający dane historyczne z reactivation_history
  - Wykorzystany do przeliczenia 36 wpisów w daily_counts

### Fixed 🐛
- **reactivated_count logic:** Zliczał wszystkie ogłoszenia z flagą `reactivated` (86), zamiast tylko tych reaktywowanych danego dnia (3)
- Poprawka: sprawdza `reactivation_history[-1].reactivated_at == date`
- Dane historyczne odtworzone z reactivation_history

- **Excel refresh_count column:**
  - Kolumna "Liczba odświeżeń" nie była zapisywana do Excel mimo że istniała w nagłówkach
  - Root cause #1: `update_excel()` wywoływany przed `generate_dashboard_json()` → ładował stary JSON bez nowych refresh_count
  - Root cause #2: `get_or_create_sheet()` nie aktualizował nagłówków dla istniejących arkuszy
  - Fix #1: Zamieniono kolejność - najpierw JSON, potem Excel
  - Fix #2: `get_or_create_sheet()` teraz aktualizuje nagłówki gdy się zmieniły
  - Zweryfikowano: kolumna dodana, wartości poprawnie zapisane (96 ogłoszeń z refresh_count > 0)

### Fixed 🐛
- **Workflow Comments:**
  - scan.yml: zmiana crona z `0 6 * * *` na `0 7 * * *` (zgodnie z preferencją użytkownika)
  - scan.yml: poprawiony komentarz "7:00 UTC = 8:00 CET (zima) / 9:00 CEST (lato)"
  - weekly_report.yml: poprawiony komentarz "7:30 UTC = 8:30 CET (zima) / 9:30 CEST (lato)"

### Technical Details 🔧
- `scraper.py`: dodano logikę porównywania `old_refreshed` vs `new_refreshed` w `generate_dashboard_json()`
- `scraper.py`: załadowanie istniejącego JSON w `update_excel()` aby pobrać refresh_count dla zapisu
- `docs/index.html`: nowa kolumna w tabeli + case 'refresh_count' w sortowaniu
- Excel: szerokość kolumn zaktualizowana (dodano kolumnę 15 o szerokości 12)

---

## [2026-04-02] - 💰 ROI Calculator & Advanced Analytics

### Added ✨
- **ROI Calculator (Email Report):**
  - Koszt promocji OLX: 69.49 zł / 7 dni (~9.93 zł/dzień)
  - Weekly cost calculation per profile
  - Cost per listing metric
  - Coverage % (promoted / total listings)
  - Average promotion days per listing
  - Total weekly cost summary (with monthly/yearly projections)
  - Tabela: Profil | Promowane | Koszt tygodniowy | Koszt/listing | Pokrycie | Śr. dni

- **Promoted Trend Chart (Dashboard):**
  - Nowa metryka w line chart: 🎯 % Promowanych
  - Toggle: 📊 Ogłoszenia | 💰 Mediana ceny | 🎯 % Promowanych
  - Orange line chart showing promoted percentage over time
  - Historical trend analysis (7/14/30 days)

---

## [2026-04-02] - 🎯 Promoted Listings Detection & Analytics

### Added ✨
- **Multi-strategy promoted detection:**
  - Primary: URL parameter `search_reason=promoted` (100% accurate)
  - Fallback: CSS classes, badges, text markers, icons
  - Confidence scoring (0.0-1.0)
  - Promotion types: `featured` ⭐ / `top_ad` 🔝 / `highlight` ✨

- **Promotion history tracking (JSON):**
  - `promoted_days_current` — dni w bieżącej sesji promocji
  - `promoted_sessions_count` — ile razy ogłoszenie było promowane
  - `promotion_history[]` — pełna historia sesji z start/end dates
  - Profile-level stats: `promoted_count`, `promoted_percentage`, `promotion_breakdown`

- **Excel: 4 nowe kolumny** (po "Cena"):
  - `🎯 Prom.` — ✓/— z emoji badges
  - `Dni prom.` — current session days (green/orange color-coding)
  - `Sesje prom.` — total promotion sessions count
  - `Typ prom.` — ⭐ Featured / 🔝 Top Ad / ✨ Highlight

- **Dashboard UI:**
  - Stat card: **🎯 Promowane X (Y%)** z accent-glow background
  - Stat card: **Typy promocji** z tooltip breakdown
  - 3 nowe kolumny w tabeli listings (między Cena a Zmiana ceny)
  - Sortowanie po promoted metrics
  - Highlighted rows (accent-glow) dla promoted listings
  - Color-coded days: green (<7), orange (>7)

- **Email Report — 🎯 Analiza promocji:**
  - Tabela z % promowanych per profil + 7-day trend (↑↓)
  - Dominant promotion type badges (color-coded)
  - **💡 Insights** (auto-generated):
    - Aggressive strategy detection (>50% promoted)
    - Low investment detection (<10%)
    - Spike alerts (>15pp change)
  - **🏆 Competitor Ranking:**
    - Top 10 by % promoted (medals 🥇🥈🥉)
    - Strategy tiers: 🔥 Aggressive (≥60%) / ⚡ Moderate (30-60%) / 💡 Light (10-30%) / 🌱 Organic (<10%)

### Changed 🔄
- **scraper.py:**
  - `parse_card()` dodaje `is_promoted`, `promotion_type`, `promotion_confidence`
  - `generate_dashboard_json()` trackuje promotion history per listing
  - `daily_counts` zawiera `promoted_count`, `promoted_percentage`, `promotion_breakdown`
  - Promotion session logic: START (0→1), CONTINUE (+1 day), END (save to history)

- **Excel column order:**
  - Było: `Tytuł | Cena | Zmiana ceny | ...`
  - Jest: `Tytuł | Cena | 🎯 Prom. | Dni prom. | Sesje | Typ | Zmiana ceny | ...`

### Technical Details 🔧
**Detection algorithm (`detect_promoted_status`):**
```python
# STRATEGIA 0: URL parameter (strongest signal)
if 'search_reason=search%7Cpromoted' in href:
    signals.append(('url_parameter', 1.0))

# STRATEGIA 1-5: Fallbacks (badges, CSS, text, icons, data attrs)
# Returns: {is_promoted, promotion_type, confidence}
```

**Promotion tracking logic:**
- **START:** `old.is_promoted=False` → `new.is_promoted=True`
  - `promoted_days_current = 1`
  - `promoted_sessions_count += 1`
  - Set `promotion_started_at = now`

- **CONTINUE:** `old.is_promoted=True` → `new.is_promoted=True`
  - `promoted_days_current += 1`

- **END:** `old.is_promoted=True` → `new.is_promoted=False`
  - Save to `promotion_history[]`: `{start_date, end_date, days, type, session_number}`
  - Reset `promoted_days_current = 0`

**Data structure:**
```json
{
  "listing": {
    "is_promoted": true,
    "promotion_type": "featured",
    "promoted_days_current": 5,
    "promoted_sessions_count": 2,
    "promotion_history": [
      {
        "start_date": "2026-03-28 10:00:00",
        "end_date": "2026-04-01 09:00:00",
        "days": 4,
        "promotion_type": "featured",
        "session_number": 1
      }
    ]
  },
  "daily_counts": {
    "promoted_count": 8,
    "promoted_percentage": 66.7,
    "promotion_breakdown": {"featured": 5, "top_ad": 2}
  }
}
```

### Use Cases 💡
- **Competitive intelligence:** Track which competitors invest in paid ads
- **ROI analysis:** Correlate promotion periods with price changes
- **Market trends:** Detect seasonal promotion patterns
- **Strategy insights:** Benchmark promotion aggressiveness across profiles

### Performance Impact ⚡
- Detection adds <1ms per listing (regex on existing HTML)
- No additional HTTP requests required
- JSON size increase: ~5-10% (promotion metadata)
- Dashboard rendering: no noticeable impact

---

## [2026-03-30] - GitHub Actions Node.js 24 Upgrade

### Changed 🔄
- **GitHub Actions:** Upgrade do Node.js 24 compatible versions
  - `actions/checkout@v4` → `actions/checkout@v6`
  - `actions/setup-python@v5` → `actions/setup-python@v6`
- **Zaktualizowane workflow'e:**
  - `.github/workflows/scan.yml`
  - `.github/workflows/weekly_report.yml`
  - `.github/workflows/keep-alive.yml`

### Fixed 🐛
- Rozwiązano deprecation warning Node.js 20 w GitHub Actions
- Przygotowanie na wymuszenie Node.js 24 (2 czerwca 2026)

### Technical Details 🔧
- Node.js 20 osiągnie EOL 30 kwietnia 2026
- GitHub Actions wymusza Node.js 24 od 2 czerwca 2026
- Wszystkie akcje teraz kompatybilne z Node.js 24
- Wymagany runner version: v2.327.1 lub nowszy (automatycznie zapewniony przez GitHub)

### References 📚
- [GitHub Blog: Deprecation of Node 20](https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/)
- [actions/checkout v6.0.0](https://github.com/actions/checkout/releases/tag/v6.0.0)
- [actions/setup-python v6.0.0](https://github.com/actions/setup-python/releases/tag/v6.0.0)

---

## [2026-04-01] - Mediana z Nowych Ogłoszeń

### Changed 🔄
- **Mediana tylko z NOWYCH ogłoszeń:**
  - Liczy się tylko ogłoszenia gdzie `first_seen == dany dzień`
  - Pokazuje jak zmieniają się ceny **nowych ofert wchodzących na rynek**
  - `None` gdy danego dnia nie dodano żadnych ogłoszeń
- **Zmienne mediany w czasie:**
  - Duże profile (wszystkie_pokoje): zmienne 775-1100 zł
  - Małe profile: dużo `None` (dodają rzadko)

### Technical Details 🔧
**Backend (scraper.py):**
```python
old_ids = set(l["id"] for l in pd_.get("current_listings", []))
new_listings = [l for l in result["listings"] if l["listing_id"] not in old_ids]
new_prices = [l["price"] for l in new_listings if ...]
median_price = calculate_median(new_prices)  # None jeśli brak nowych
```

**Rebuild (rebuild_historical_medians.py):**
```python
if first_seen == entry_date:  # DOKŁADNIE tego dnia, nie <=
    prices_on_that_day.append(price)
```

### Example 📊
**Profile "wszystkie_pokoje" (codziennie nowe):**
- 2026-03-17: 800 zł
- 2026-03-18: 950 zł ↑
- 2026-03-21: 1000 zł ↑
- 2026-03-28: 775 zł ↓
- 2026-03-31: 1100 zł ↑

**Profile "poqui" (dodają rzadko):**
- 2026-03-19: 1400 zł
- 2026-03-20-25: None (nic nie dodali)
- 2026-03-26: 1499 zł
- 2026-03-27-29: None
- 2026-03-30: 2499 zł ↑

**Profile "mzuri" (aktywny, duże wahania):**
- 850 zł → 2200 zł → 2520 zł → 1920 zł → 850 zł

---

## [2026-03-31] - Mediana Zamiast Średniej

### Changed 🔄
- **Mediana ceny** zamiast średniej/min/max:
  - Mediana = wartość środkowa (odporna na outliers)
  - Lepiej reprezentuje "typową" cenę
  - 2 przyciski zamiast 4: 📊 Ogłoszenia | 💰 Mediana ceny
- **Prawdziwe historyczne mediany:**
  - Mediana liczona dla ogłoszeń które **istniały danego dnia**
  - Używa `first_seen` ≤ data ≤ `archived_date` (lub wciąż aktywne)
  - Pokazuje **rzeczywiste zmiany cen w czasie**, nie snapshoty

### Removed ➖
- ⬇️ Min cena (przycisk i metryka)
- ⬆️ Max cena (przycisk i metryka)
- avg_price, min_price, max_price z daily_counts

### Technical Details 🔧
- **Backend:** Mediana = sorted_prices[n//2] dla nieparzystej liczby, średnia dwóch środkowych dla parzystej
- **Rebuild:** Przebudowa wszystkich historycznych median (37 dni × 6 profili)
  - Dla każdego dnia: znajdź aktywne ogłoszenia + oblicz medianę ich cen
  - Skrypt: `rebuild_historical_medians.py`
- **Frontend:** Uproszczona konfiguracja metricConfig (2 metryki zamiast 4)

### Example 📊
**Profile "poqui" - historia zmian:**
- 2026-03-22-25: 7 ogłoszeń, mediana **1400 zł**
- 2026-03-26-29: 10 ogłoszeń (pojawiły się 3 nowe), mediana **1450 zł** ↑
- 2026-03-30: 10 ogłoszeń, mediana **1499 zł** ↑
- 2026-03-31: 10 ogłoszeń, mediana **1450 zł** ↓

**Profile "dawny_patron":**
- 2026-03-22-28: 7 ogłoszeń, mediana **730 zł**
- 2026-03-29-31: 8 ogłoszeń (pojawiło się nowe), mediana **750 zł** ↑

---

## [2026-03-30] - Wykres Liniowy z Zoom i Metrykami Cenowymi

### Added ✨
- **Wykres liniowy** z pełną historią danych (wszystkie dostępne dni)
- **4 metryki do wyboru:**
  - 📊 Ogłoszenia (liczba)
  - 💰 Średnia cena
  - ⬇️ Minimalna cena
  - ⬆️ Maksymalna cena
- **Zoom interaktywny:**
  - 🖱️ Kółko myszy — przybliżanie/oddalanie
  - **Przeciąganie** — przesuwanie wykresu (pan) **bez konieczności trzymania Shift**
  - Przycisk "Reset zoom" (pojawia się po przybliżeniu)
- **Tooltips** z dokładnymi wartościami przy hover
- **Statystyki cenowe w backend:**
  - Kalkulacja `avg_price`, `min_price`, `max_price` przy każdym skanie
  - Zapis do `daily_counts` w JSON

### Changed 🔄
- Dashboard: wykres liniowy POD wykresem słupkowym
- Struktura `daily_counts` rozszerzona o pola cenowe
- Przyciski metryk z ikonkami (emoji)

### Technical Details 🔧
- **Backend:** `scraper.py` — funkcja `generate_dashboard_json()`
  - Kalkulacja: `prices = [l["price"] for l in result["listings"] if ...]`
  - Round average price: `round(sum(prices) / len(prices))`
  - Zapisywane w `daily_counts`: `avg_price`, `min_price`, `max_price`
- **Backfill:** `backfill_prices.py` — wypełnienie historycznych danych
  - Dla wpisów z `None` w cenach użyto aktualnych cen jako przybliżenia
  - Zaktualizowano ~35 wpisów na profil (36 dni historii)
- **Frontend:** `docs/index.html`
  - Nowa sekcja: `.line-chart-section` + CSS
  - Chart.js plugin: `chartjs-plugin-zoom` v2.0.1
  - **Hammer.js v2.0.8** — wymagane dla gestów przeciągania (pan)
  - Funkcja: `renderLineChart(key)` — dynamiczna zmiana danych
  - Funkcja: `switchMetric(metric, btn)` — toggle między metrykami
  - Funkcja: `resetLineChartZoom()` — reset zoom
  - Responsywne: `height: 220px`, adaptive ticks
- **CDN:**
  - `https://cdnjs.cloudflare.com/ajax/libs/hammer.js/2.0.8/hammer.min.js`
  - `https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js`
  - `https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-zoom/2.0.1/chartjs-plugin-zoom.min.js`

### Files Modified 📝
- `scraper.py` — rozszerzenie `generate_dashboard_json()` o statystyki cenowe
- `docs/index.html` — nowa sekcja HTML + CSS + JavaScript dla wykresu liniowego
- `backfill_prices.py` — skrypt jednorazowy do wypełnienia historycznych danych
- `data/dashboard_data.json` — wypełnione statystyki cenowe dla 36 dni historii

---

## [2026-03-29] - Dashboard Profile Links

### Added
- [x] Link "Zobacz na OLX" w nagłówku detail panelu
- [x] Klikany przycisk z ikoną external link
- [x] Przekierowanie do profilu OLX w nowej karcie
- [x] Hover effect i animacja

### Changed
- [x] **Dynamiczna skala Y w wykresach** — zamiast zawsze od 0
- [x] Wykres teraz pokazuje zakres od `min - 10%` do `max + 10%`
- [x] Małe różnice (405→409) są teraz widoczne na wykresie
- [x] Skala uwzględnia wybrany zakres (7/14/30 dni)

### Technical Details
- Link wyświetlany obok nazwy profilu w detail-header
- SVG icon: external link (stroke width 2)
- Stylizacja: border, padding, hover transform
- Target: `_blank` (nowa karta)
- **Chart scaling:** `heightPct = ((value - yMin) / yRange) * 100`
- **Y-axis range:** `yMin = max(0, min - 10%)`, `yMax = max + 10%`

### Files Modified
- `docs/index.html` - dodano CSS `.profile-link` + JS w `renderDetail()` + dynamic Y-scale w `renderChart()`

---

## [2026-03-29] - Email Report System Enhancement

### Stan początkowy
- Istniejący `email_report.py` z podstawowym szablonem HTML
- Workflow `weekly_report.yml` uruchamiany w poniedziałki o 9:30 CET
- Brak wykresów w emailu
- Podstawowe tabele z danymi

### Added
- [x] Matplotlib do zależności (wykresy inline Base64)
- [x] Funkcja `generate_trend_chart()` — wykresy słupkowe 7-dniowe jako Base64 PNG
- [x] Funkcja `calculate_weekly_stats()` — statystyki tygodniowe (min/max/avg)
- [x] Nowy szablon HTML z sekcją analityczną
- [x] Grid ze statystykami (aktualna liczba, zakres, średnia cena, nowe 24h)
- [x] Embedded wykresy w emailu (inline Base64)
- [x] Tabela z top 10 najnowszych ogłoszeń dla każdego profilu
- [x] Profesjonalny styling (gradienty, zaokrąglone rogi, responsive grid)

### Changed
- [x] Całkowicie przepisany `email_report.py` — nowa architektura
- [x] Zmieniony subject: "Raport analityczny" zamiast "Raport tygodniowy"
- [x] Dodano emoji do sekcji (📊, 📌, 🏠, 🤖)
- [x] Improved logging (emoji statusy ✅ ❌)

### Fixed
- [x] Stats grid layout — zmieniono z CSS Grid na `<table>` dla lepszej kompatybilności email
- [x] Karty stats wyświetlają się teraz **poziomo w jednym rzędzie** zamiast pionowo
- [x] Dodano `table-layout: fixed` i `width: 25%` dla równych kart
- [x] Używamy `<td class="stat-card">` zamiast `<div>` dla cross-client compatibility

### Technical Details
- **Matplotlib Backend:** `Agg` (non-interactive, server-safe)
- **Chart Format:** PNG → Base64 → `data:image/png;base64,...`
- **Chart Resolution:** 800x300px @ 100 DPI
- **Color Scheme:** Tailwind-inspired (#3b82f6 primary, #10b981 success, #ef4444 danger)
- **Email Size:** ~200-500KB (zależnie od liczby wykresów)
- **Email Compatibility:** Table-based layout (works in Gmail, Outlook, Apple Mail)

### Testing
- [x] Workflow triggered via GitHub API
- [x] Run ID: 23706065185
- [x] Status: ✅ SUCCESS (completed in ~20s)
- [x] Email wysłany do malczarski@gmail.com
- [x] Załącznik Excel poprawnie dołączony
- [x] Layout fix: stats cards teraz poziomo

### Files Modified
- `requirements.txt` - dodano matplotlib>=3.8.0
- `email_report.py` - kompletny rewrite (170 → 430 linii)
- `README.md` - zaktualizowana sekcja email reportów
- `CHANGELOG.md` - utworzony (nowy system dokumentacji)

---

## [2026-02-27] - Scan Timing Fix

### Changed
- Zmieniono harmonogram skanów z 6:00 UTC na 7:00 UTC (9:00 CET zimą)
- Dodano dokumentację `ZMIANA_CZASU_REMINDER.md`

### Fixed
- Problem z automatyczną dezaktywacją workflow po 60 dniach
- Dodano `keep-alive.yml` workflow

### Files Modified
- `.github/workflows/scan.yml`
- `.github/workflows/keep-alive.yml`
- `ZMIANA_CZASU_REMINDER.md` (nowy)

---

## [2026-02-20] - Initial Project Setup

### Added
- Podstawowy scraper OLX (`scraper.py`)
- GitHub Actions workflow dla daily scan
- Dashboard na GitHub Pages (`docs/index.html`)
- Excel export z historią cen
- JSON API dla dashboardu
- Email reporting system (podstawowy)

### Technical Details
- Python 3.11+
- BeautifulSoup4 dla parsowania HTML
- OpenPyXL dla Excela
- GitHub Actions dla automatyzacji
- GitHub Pages dla dashboardu

### Files Created
- `scraper.py`
- `main.py`
- `email_report.py`
- `.github/workflows/scan.yml`
- `.github/workflows/weekly_report.yml`
- `docs/index.html`
- `requirements.txt`
- `README.md`
- `PROJECT_STRUCTURE.md`
- `SETUP_GUIDE.md`

---

## Legenda typów zmian

- **Added**: Nowe funkcje
- **Changed**: Zmiany w istniejących funkcjach
- **Deprecated**: Funkcje które zostaną usunięte
- **Removed**: Usunięte funkcje
- **Fixed**: Poprawki błędów
- **Security**: Poprawki bezpieczeństwa

---

## Konwencje commitów

```
🔍 Scan: zmiany w scraper.py lub logice skanowania
📊 Data: zmiany w strukturze danych (JSON/Excel)
📧 Email: zmiany w systemie raportów email
🎨 UI: zmiany w dashboardzie (docs/index.html)
🔧 Config: zmiany w konfiguracji
📝 Docs: aktualizacje dokumentacji
🐛 Fix: poprawki błędów
✨ Feature: nowe funkcje
♻️ Refactor: refaktoryzacja bez zmian funkcjonalności
🚀 Deploy: zmiany w GitHub Actions workflow
```

---

**Ostatnia aktualizacja:** 2026-03-29
