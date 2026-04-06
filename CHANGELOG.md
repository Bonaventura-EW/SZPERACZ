# 📋 CHANGELOG

Wszystkie istotne zmiany w projekcie SZPERACZ OLX są dokumentowane w tym pliku.

Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.0.0/).

---

## [Unreleased]

### Planowane
- Integracja z Telegram Bot

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
  - Buduje timeline od momentu wdrożenia (dane historyczne sprzed tego są stracone - OLX nie przechowuje historii)
  - Pozwala na dokładną analizę: kiedy było każde odświeżenie, jak często sprzedawca odświeża portfolio
  
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
