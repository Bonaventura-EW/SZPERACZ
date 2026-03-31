# 📋 CHANGELOG

Wszystkie istotne zmiany w projekcie SZPERACZ OLX są dokumentowane w tym pliku.

Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.0.0/).

---

## [Unreleased]

### Planowane
- Integracja z Telegram Bot

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

## [2026-03-31] - Mediana Zamiast Średniej

### Changed 🔄
- **Mediana ceny** zamiast średniej/min/max:
  - Mediana = wartość środkowa (odporna na outliers)
  - Lepiej reprezentuje "typową" cenę
  - 2 przyciski zamiast 4: 📊 Ogłoszenia | 💰 Mediana ceny

### Removed ➖
- ⬇️ Min cena (przycisk i metryka)
- ⬆️ Max cena (przycisk i metryka)
- avg_price, min_price, max_price z daily_counts

### Technical Details 🔧
- **Backend:** Mediana = sorted_prices[n//2] dla nieparzystej liczby, średnia dwóch środkowych dla parzystej
- **Backfill:** Przerobione wszystkie historyczne wpisy (37 dni × 6 profili)
- **Frontend:** Uproszczona konfiguracja metricConfig (2 metryki zamiast 4)

### Example 📊
- Profile "poqui": mediana **1450 zł** vs poprzednia średnia 1659 zł
- Profile "wszystkie_pokoje": mediana **850 zł** vs poprzednia średnia 912 zł

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
