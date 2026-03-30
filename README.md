# 🔍 SZPERACZ OLX

**Autonomiczny agent monitorujący ogłoszenia OLX** — śledzi ceny, analizuje trendy i generuje raporty.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Active-success.svg)

---

## 📋 Spis treści

- [Funkcje](#-funkcje)
- [Architektura](#-architektura)
- [Instalacja](#-instalacja)
- [Konfiguracja](#-konfiguracja)
- [Użycie](#-użycie)
- [GitHub Actions](#-github-actions)
- [Dashboard](#-dashboard)
- [Troubleshooting](#-troubleshooting)
- [Rozwój projektu](#-rozwój-projektu)

---

## ✨ Funkcje

### 🤖 Automatyczny scraping
- Monitorowanie wielu profili OLX i kategorii
- Crosscheck z nagłówkiem strony (weryfikacja kompletności danych)
- Retry logic przy rozbieżnościach
- Rotacja User-Agent i randomowe opóźnienia

### 📊 Analityka
- Śledzenie zmian liczby ogłoszeń w czasie
- Monitorowanie zmian cen (historia cen dla każdego ogłoszenia)
- **Statystyki cenowe w daily_counts:** avg_price, min_price, max_price
- Wykrywanie nowych i archiwalnych ogłoszeń
- Statystyki: min/max/avg cena, nowe ogłoszenia (24h)
- **Wykresy trendów** — wizualizacja historii z możliwością zoom

### 📁 Eksport danych
- **Excel** (`data/szperacz_olx.xlsx`):
  - Arkusz dla każdego profilu z historią skanów
  - Arkusz "historia_cen" ze wszystkimi zmianami cen
  - Arkusz "podsumowanie" z bieżącym statusem
  - Kolorowe formatowanie (zielony ↑ czerwony ↓)
  
- **JSON** (`data/dashboard_data.json`):
  - Struktura zoptymalizowana pod dashboard
  - 90-dniowa historia daily_counts
  - Price history dla każdego ogłoszenia

### 📧 Raporty email (NOWE: Analityka)
- **Cotygodniowy raport analityczny** (każdy poniedziałek o 9:30 CET)
- **Embedded wykresy trendów** (matplotlib Base64 inline)
- **Statystyki tygodniowe:** min/max liczba ogłoszeń, średnia/min/max cena
- **Nowe ogłoszenia (24h)** — licznik dla każdego profilu
- **Top 10 najnowszych** ogłoszeń w każdym profilu
- **Załącznik Excel** z pełnymi danymi
- Profesjonalny HTML z responsive grid i gradientami

### 🌐 Interaktywny dashboard
- Widok wszystkich profili na jednym ekranie
- **Wykres słupkowy** — ostatnie 7/14/30 dni (przełączalne)
- **Wykres liniowy z zoom** — pełna historia danych:
  - 🖱️ Zoom kółkiem myszy
  - 4 metryki: Ogłoszenia / Średnia cena / Min cena / Max cena
  - Tooltips z wartościami przy hover
  - Reset zoom button
- Tabele z aktualnymi i archiwalnymi ogłoszeniami
- Sortowanie kolumn (kliknij nagłówek)
- Tryb jasny/ciemny
- Ręczne uruchamianie skanów przez GUI

---

## 🏗️ Architektura

```
SZPERACZ/
├── .github/
│   └── workflows/
│       ├── scan.yml              # Dzienny scan (9:00 CET)
│       └── weekly_report.yml     # Email w poniedziałki (9:30 CET)
├── data/                         # Dane (tracked in git)
│   ├── dashboard_data.json       # JSON dla dashboardu
│   └── szperacz_olx.xlsx         # Excel z historią
├── docs/
│   └── index.html                # Dashboard (GitHub Pages)
├── logs/                         # Logi (git ignored)
│   └── szperacz_YYYYMMDD.log
├── main.py                       # Entry point
├── scraper.py                    # Logika scrapingu
├── email_report.py               # Wysyłanie emaili
├── requirements.txt              # Dependencies
├── .gitignore
└── README.md
```

---

## 🚀 Instalacja

### Wymagania

- Python 3.11+
- Git
- Konto GitHub (dla automatyzacji)
- Gmail z App Password (dla emaili)

### Krok 1: Klonowanie repo

```bash
git clone https://github.com/Bonaventura-EW/SZPERACZ.git
cd SZPERACZ
```

### Krok 2: Instalacja zależności

```bash
pip install -r requirements.txt
```

### Krok 3: Pierwszy scan (lokalnie)

```bash
python main.py --scan
```

To utworzy katalog `data/` z początkowymi plikami.

---

## ⚙️ Konfiguracja

### Profle OLX

Edytuj `scraper.py` — sekcja `PROFILES`:

```python
PROFILES = {
    "nazwa_profilu": {
        "url": "https://www.olx.pl/oferty/uzytkownik/XXXXX/",
        "label": "Przyjazna nazwa",
        "is_category": False,  # True dla kategorii, False dla profili
    },
}
```

### Email credentials

#### Lokalnie (development)

Utwórz plik `.env`:

```bash
EMAIL_PASSWORD=your_gmail_app_password_here
```

Lub export:

```bash
export EMAIL_PASSWORD="your_gmail_app_password_here"
```

#### GitHub Actions (production)

1. Wygeneruj Gmail App Password:
   - https://myaccount.google.com/apppasswords
   - Wybierz "Mail" i "Other (Custom name)"
   - Skopiuj 16-znakowy kod

2. Dodaj do GitHub Secrets:
   - Repo → Settings → Secrets and variables → Actions
   - New repository secret
   - Name: `EMAIL_PASSWORD`
   - Value: `wklej_kod_z_kroku_1`

3. Ustaw email w `email_report.py`:

```python
SENDER_EMAIL = "your_email@gmail.com"
RECEIVER_EMAIL = "recipient@gmail.com"
```

---

## 🎮 Użycie

### Lokalne uruchamianie

```bash
# Scan OLX
python main.py --scan

# Wyślij email report
python main.py --email

# Sprawdź status systemu
python main.py --status

# Pomoc
python main.py --help
```

### Status systemu

```bash
python main.py --status
```

Wyświetla:
- Ostatni scan
- Liczba śledzonych profili
- Aktualna liczba ogłoszeń
- Status plików (JSON, Excel)
- Konfiguracja środowiska

---

## 🤖 GitHub Actions

### Automatyczne skany (codziennie o 9:00)

Workflow: `.github/workflows/scan.yml`

- Uruchamia się codziennie o 9:00 czasu polskiego
  - **Zimą (CET):** `cron: '0 8 * * *'` → 8:00 UTC = 9:00 CET
  - **Latem (CEST):** Zmień na `cron: '0 7 * * *'` → 7:00 UTC = 9:00 CEST
  - 📅 Zobacz [ZMIANA_CZASU_REMINDER.md](ZMIANA_CZASU_REMINDER.md) dla dat i instrukcji
- Wykonuje `python scraper.py`
- Commituje zaktualizowane pliki `data/*` do repo
- Można uruchomić ręcznie: Actions → SZPERACZ OLX - Daily Scan → Run workflow

### Keep-alive (co 50 dni)

Workflow: `.github/workflows/keep-alive.yml`

- Uruchamia się automatycznie co 50 dni
- **Cel:** Zapobiega dezaktywacji scheduled workflows przez GitHub
  - GitHub automatycznie wyłącza crony po 60 dniach bezczynności w repo
  - Keep-alive robi małego commita aby "pokazać aktywność"
- Tworzy/aktualizuje plik `.github/KEEP_ALIVE.txt` z timestampem
- **Nie wymaga żadnej akcji z Twojej strony** — działa automatycznie

### Email raport (poniedziałki o 9:30)

Workflow: `.github/workflows/weekly_report.yml`

- Uruchamia się w poniedziałki o 9:30 CET
- Wykonuje `python email_report.py`
- Wymaga ustawionego `EMAIL_PASSWORD` w Secrets

### Ręczne uruchomienie

1. Wejdź w GitHub repo → **Actions**
2. Wybierz workflow (Scan lub Weekly Report)
3. Kliknij **Run workflow** → **Run workflow**

---

## 🌐 Dashboard

### Aktywacja GitHub Pages

1. Repo → **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: **main** → Folder: **/docs**
4. Save

Dashboard będzie dostępny pod:
```
https://bonaventura-ew.github.io/SZPERACZ/
```

### Funkcje dashboardu

- **Profile cards**: Aktywne/zarchiwizowane ogłoszenia, zmiana vs poprzedni scan
- **Wykresy**: Ostatnie 7 dni dla każdego profilu
- **Tabele**: Aktualne i archiwalne ogłoszenia z cenami i zmianami
- **Scan button**: Uruchom scan przez API GitHub (wymaga Personal Access Token)

### Uruchomienie scanu z dashboardu

1. Dashboard → **Scan teraz**
2. Wklej GitHub Personal Access Token (PAT):
   - https://github.com/settings/tokens/new
   - Scope: `repo` lub `workflow`
   - Wygeneruj token i skopiuj
3. Opcjonalnie zaznacz "Zapamiętaj token"
4. Kliknij **▶ Uruchom**

Dane zaktualizują się automatycznie po ~3 minutach.

---

## 🛠️ Troubleshooting

### Problem: Workflow nie commituje danych

**Objawy:** GitHub Actions przechodzi zielono, ale `data/` się nie aktualizuje

**Rozwiązanie:**
```yaml
# W .github/workflows/scan.yml sprawdź permissions:
permissions:
  contents: write  # MUSI być ustawione
```

### Problem: Email nie wysyła się

**Objawy:** Error `SMTP auth failed`

**Rozwiązanie:**
1. Sprawdź czy `EMAIL_PASSWORD` jest App Password (16 znaków), NIE hasło do konta
2. Upewnij się, że secret jest ustawiony: Settings → Secrets → Actions
3. Gmail wymaga włączonej weryfikacji dwuetapowej do App Passwords

### Problem: Scraper zwraca 0 ogłoszeń

**Objawy:** Crosscheck: `MISMATCH`, scraped=0

**Przyczyny:**
- OLX zmieniło strukturę HTML
- Rate limiting / blokada IP
- Profil nie istnieje / zmienił URL

**Diagnostyka:**
```bash
# Sprawdź logi
python main.py --scan 2>&1 | grep "ERROR\|WARNING"

# Ręcznie sprawdź URL w przeglądarce
curl -A "Mozilla/5.0" https://www.olx.pl/oferty/uzytkownik/XXXXX/
```

**Fix:**
- Zaktualizuj selektory CSS w `scraper.py` → funkcja `parse_card()`
- Dodaj więcej opóźnień w `scrape_profile()` (zwiększ `time.sleep()`)

### Problem: Dashboard nie ładuje danych

**Objawy:** "Nie udało się pobrać danych" na dashboardzie

**Rozwiązanie:**
1. Sprawdź czy `data/dashboard_data.json` istnieje w repo
2. Sprawdź czy GitHub Pages jest włączone (Settings → Pages)
3. Wyczyść cache przeglądarki (Ctrl+Shift+R)
4. Sprawdź URL w `docs/index.html`:
   ```javascript
   const DATA_URL = `https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/main/data/dashboard_data.json`;
   ```

### Problem: Excel jest zbyt duży (>100MB)

**Rozwiązanie:**
- Usuń starsze wiersze ręcznie lub przez skrypt
- Dodaj `data/szperacz_olx.xlsx` do `.gitignore` (dane będą tylko w JSON)

---

## 🔧 Rozwój projektu

### Dodawanie nowego profilu

1. Znajdź URL profilu na OLX (np. `https://www.olx.pl/oferty/uzytkownik/ABC123/`)
2. Edytuj `scraper.py`:
   ```python
   PROFILES = {
       # ... existing profiles ...
       "nowy_profil": {
           "url": "https://www.olx.pl/oferty/uzytkownik/ABC123/",
           "label": "Nazwa wyświetlana",
           "is_category": False,
       },
   }
   ```
3. Uruchom scan: `python main.py --scan`

### Testy lokalne

```bash
# Test scrapingu
python scraper.py

# Test emaila
python email_report.py

# Test pełnego workflow
python main.py --scan && python main.py --email
```

### Struktura danych JSON

```json
{
  "profiles": {
    "profile_key": {
      "label": "Display name",
      "url": "https://...",
      "is_category": false,
      "daily_counts": [
        {"date": "2026-02-23", "count": 15, "change": 2, "timestamp": "..."}
      ],
      "current_listings": [
        {
          "id": "ABC123",
          "title": "Pokój do wynajęcia",
          "price": 1200,
          "url": "https://...",
          "first_seen": "2026-02-20 10:00:00",
          "last_seen": "2026-02-23 09:00:00",
          "price_change": -100,
          "previous_price": 1300
        }
      ],
      "archived_listings": [...],
      "price_history": {
        "ABC123": [
          {"date": "...", "old_price": 1300, "new_price": 1200, "change": -100}
        ]
      }
    }
  },
  "scan_history": [...],
  "last_scan": "2026-02-23 09:00:00"
}
```

---

## 📜 License

MIT License - see LICENSE file for details

---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📧 Contact

Project maintainer: [@Bonaventura-EW](https://github.com/Bonaventura-EW)

**Issues:** https://github.com/Bonaventura-EW/SZPERACZ/issues

---

## 🎯 Roadmap

- [ ] Telegram bot notifications
- [ ] Price alerts (email gdy cena spadnie poniżej X zł)
- [ ] Web scraping dla konkurencyjnych serwisów (Otodom, Gratka)
- [ ] Machine learning: predykcja trendów cenowych
- [ ] Mobile app (React Native)
- [ ] Multi-user support (każdy użytkownik swoje profile)

---

**Zrobione z ❤️ dla szperaczy OLX** 🔍
