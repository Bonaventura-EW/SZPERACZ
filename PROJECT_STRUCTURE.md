# 📁 SZPERACZ OLX - Struktura Projektu

## 🌲 Drzewo katalogów

```
SZPERACZ/
│
├── 📂 .github/
│   └── 📂 workflows/
│       ├── scan.yml                    # GitHub Action: Dzienny scan (9:00 CET)
│       └── weekly_report.yml           # GitHub Action: Email w poniedziałki (9:30 CET)
│
├── 📂 data/                             # Dane (tracked in git, updated by Actions)
│   ├── dashboard_data.json             # JSON dla dashboardu (90 dni historii)
│   └── szperacz_olx.xlsx               # Excel z pełną historią skanów
│
├── 📂 docs/                             # GitHub Pages
│   └── index.html                      # Dashboard (HTML + CSS + JS)
│
├── 📂 logs/                             # Logi (git ignored)
│   └── szperacz_YYYYMMDD.log           # Daily logs
│
├── 📄 main.py                          # ⭐ ENTRY POINT - orchestracja
├── 📄 scraper.py                       # Logika scrapingu OLX
├── 📄 email_report.py                  # Wysyłanie email raportów
│
├── 📄 requirements.txt                 # Python dependencies
├── 📄 .gitignore                       # Co wykluczyć z git
├── 📄 .env.example                     # Template dla lokalnych zmiennych
│
├── 📄 README.md                        # Główna dokumentacja
├── 📄 SETUP_GUIDE.md                   # Przewodnik instalacji krok po kroku
├── 📄 PROJECT_STRUCTURE.md             # Ten plik
└── 📄 LICENSE                          # MIT License
```

---

## 📝 Opis plików

### 🎯 Core Files (Główne pliki)

#### **main.py**
```
Rola: Entry point aplikacji
Funkcje:
  - Dispatcher dla różnych komend (--scan, --email, --status)
  - Error handling i logging
  - Inicjalizacja katalogów
  - Statystyki wykonania

Wywoływany przez:
  - GitHub Actions workflows
  - Ręcznie: python main.py --scan

Wywołuje:
  - scraper.run_scan()
  - email_report.send_report()
```

#### **scraper.py**
```
Rola: Autonomiczny web scraper dla OLX
Funkcje:
  - HTTP requests z rotacją User-Agent
  - Parsing HTML (BeautifulSoup)
  - Crosscheck (weryfikacja kompletności danych)
  - Generowanie Excel (openpyxl)
  - Generowanie JSON dla dashboardu
  
Konfiguracja:
  - PROFILES: dict z monitorowanymi profilami/kategoriami
  - DATA_DIR: katalog na dane (./data/)
  
Wynik:
  - data/szperacz_olx.xlsx (arkusze: profil, historia_cen, podsumowanie)
  - data/dashboard_data.json (struktura dla dashboardu)
```

#### **email_report.py**
```
Rola: Generowanie i wysyłanie email raportów
Funkcje:
  - HTML email z tabelami i wykresami
  - Załącznik Excel
  - SMTP via Gmail (wymaga App Password)
  
Konfiguracja:
  - SENDER_EMAIL: Gmail z którego wysyłasz
  - RECEIVER_EMAIL: Email na który dostajesz raport
  - EMAIL_PASSWORD: z GitHub Secrets
  
Wywoływany: Co poniedziałek o 9:30 (weekly_report.yml)
```

---

### 🤖 GitHub Actions

#### **.github/workflows/scan.yml**
```yaml
Trigger: Codziennie o 9:00 CET (7:00 UTC)
Kroki:
  1. Checkout repository
  2. Setup Python 3.12
  3. Install dependencies (requirements.txt)
  4. Run: python main.py --scan
  5. Commit & push data/ (updated JSON + Excel)
  
Permissions: contents: write (do commitowania)
Timeout: 30 minut
```

#### **.github/workflows/weekly_report.yml**
```yaml
Trigger: Poniedziałki o 9:30 CET (7:30 UTC)
Kroki:
  1. Checkout repository
  2. Setup Python 3.11
  3. Install dependencies
  4. Run: python email_report.py
  
Secrets: EMAIL_PASSWORD (Gmail App Password)
Timeout: 5 minut
```

---

### 📊 Data Files

#### **data/dashboard_data.json**
```json
Struktura:
{
  "profiles": {
    "profile_key": {
      "label": "Nazwa",
      "url": "https://...",
      "daily_counts": [              // Ostatnie 90 dni
        {"date": "2026-02-23", "count": 15, "change": 2}
      ],
      "current_listings": [          // Aktywne ogłoszenia
        {
          "id": "ABC123",
          "title": "...",
          "price": 1200,
          "first_seen": "...",
          "last_seen": "...",
          "price_change": -100
        }
      ],
      "archived_listings": [...],    // Ostatnie 200 archiwalnych
      "price_history": {             // Historia zmian cen
        "ABC123": [
          {"date": "...", "old_price": 1300, "new_price": 1200}
        ]
      }
    }
  },
  "scan_history": [...],             // Ostatnie 90 skanów
  "last_scan": "2026-02-23 09:00:00"
}

Rozmiar: ~100KB - 2MB (w zależności od liczby profili)
Update: Co scan (codziennie o 9:00)
Używany przez: docs/index.html (dashboard)
```

#### **data/szperacz_olx.xlsx**
```
Arkusze:
  1. [Nazwa profilu] (jeden arkusz na profil)
     Kolumny:
       - Data scanu, Godzina
       - Liczba ogłoszeń, Zmiana vs poprzedni
       - Crosscheck
       - Tytuł, Cena, Zmiana ceny
       - Data publikacji, Data odświeżenia
       - URL, ID ogłoszenia
  
  2. historia_cen (globalnie dla wszystkich profili)
     Kolumny:
       - Data, Profil, ID ogłoszenia
       - Tytuł, Cena, Poprzednia cena
       - Zmiana ceny, URL
  
  3. podsumowanie
     Kolumny:
       - Profil, Label
       - Dzisiejsza liczba, Poprzednia liczba
       - Zmiana, Crosscheck
       - Data scanu

Formatowanie:
  - Zielone ↑ dla wzrostów
  - Czerwone ↓ dla spadków
  - Nagłówki: niebieski background, białe fonty
  
Rozmiar: Rośnie z czasem (po roku ~5-20MB)
Backup: Commitowany do git (można wyłączyć w .gitignore)
```

---

### 🌐 Dashboard (GitHub Pages)

#### **docs/index.html**
```
Technologie:
  - Pure HTML/CSS/JavaScript (no frameworks)
  - Fonts: JetBrains Mono, DM Sans
  - Theme: Dark/Light mode (localStorage)
  
Funkcje:
  - Fetch danych z data/dashboard_data.json
  - Profile cards (grid layout)
  - Detail panel z wykresami (ostatnie 7 dni)
  - Tabele: aktualne vs archiwalne ogłoszenia
  - Scan button (GitHub API - wymaga PAT)
  - Auto-refresh co 5 minut
  
GitHub API:
  - POST /repos/{owner}/{repo}/actions/workflows/{workflow}/dispatches
  - Scope: repo lub workflow
  - Rate limit: 5000 requests/hour
```

---

### 🔧 Configuration Files

#### **requirements.txt**
```
requests>=2.31.0           # HTTP client
beautifulsoup4>=4.12.0     # HTML parser
openpyxl>=3.1.0            # Excel generation
lxml>=5.0.0                # BS4 parser (faster)
```

#### **.gitignore**
```
Wyklucza:
  - __pycache__/, *.pyc      # Python cache
  - logs/, *.log             # Logi
  - .env, .venv/             # Environment variables
  - *.tmp, *.bak             # Temporary files
  - .vscode/, .idea/         # IDE configs
  
Śledzi:
  - data/*.json, data/*.xlsx  # WAŻNE: dane są commitowane!
```

#### **.env.example**
```
Template dla lokalnego developmentu:

EMAIL_PASSWORD=            # Gmail App Password
LOG_LEVEL=INFO            # DEBUG/INFO/WARNING/ERROR
REQUEST_TIMEOUT=30        # Sekundy
```

---

## 🔄 Data Flow (Przepływ danych)

### Dzienny scan (9:00 CET)

```
┌─────────────────┐
│ GitHub Actions  │
│   (scan.yml)    │
└────────┬────────┘
         │
         ├─> python main.py --scan
         │
┌────────▼────────┐
│    main.py      │
│  - setup logs   │
│  - ensure data/ │
└────────┬────────┘
         │
         ├─> scraper.run_scan()
         │
┌────────▼──────────┐
│   scraper.py      │
│  For each profile:│
│   1. HTTP GET     │
│   2. Parse HTML   │
│   3. Crosscheck   │
│   4. Deduplicate  │
└────────┬──────────┘
         │
         ├─> update_excel(results)
         ├─> generate_dashboard_json(results)
         │
┌────────▼──────────┐
│  data/            │
│  - .xlsx updated  │
│  - .json updated  │
└────────┬──────────┘
         │
         ├─> git commit & push
         │
┌────────▼──────────┐
│  GitHub repo      │
│  main branch      │
└───────────────────┘
         │
         ├─> GitHub Pages rebuild
         │
┌────────▼──────────┐
│  Dashboard        │
│  (index.html)     │
│  - fetch .json    │
│  - render charts  │
└───────────────────┘
```

### Cotygodniowy email (poniedziałek 9:30)

```
┌─────────────────┐
│ GitHub Actions  │
│ (weekly_.yml)   │
└────────┬────────┘
         │
         ├─> python email_report.py
         │
┌────────▼────────────┐
│  email_report.py    │
│  1. Load JSON       │
│  2. Build HTML      │
│  3. Attach Excel    │
│  4. SMTP send       │
└────────┬────────────┘
         │
         ├─> Gmail SMTP (587)
         │   (App Password)
         │
┌────────▼────────────┐
│  Recipient inbox    │
│  - HTML email       │
│  - Excel attachment │
└─────────────────────┘
```

---

## 🧩 Komponenty i zależności

### Moduł dependencies

```
scraper.py imports:
  - requests          → HTTP
  - BeautifulSoup     → HTML parsing
  - openpyxl          → Excel generation
  - json, os, re      → Standard lib
  - datetime, time    → Timestamps
  - logging           → Logs

email_report.py imports:
  - smtplib           → SMTP client
  - email.mime.*      → Email construction
  - json, os          → Data loading
  - datetime          → Dates

main.py imports:
  - sys, os           → CLI, filesystem
  - logging           → Logs
  - json              → JSON I/O
  - scraper           → run_scan()
  - email_report      → send_report()
```

### External services

```
OLX.pl:
  - Target: Profile pages & category pages
  - Method: HTTP GET with User-Agent rotation
  - Rate limit: ~1 request/2-3 seconds
  
Gmail SMTP:
  - Server: smtp.gmail.com:587
  - Auth: App Password (16 chars)
  - TLS: Required
  
GitHub API:
  - Workflow dispatch: /actions/workflows/{id}/dispatches
  - Auth: Personal Access Token (PAT)
  - Rate: 5000/hour
```

---

## 🔐 Secrets & Environment

### GitHub Secrets (Settings → Secrets → Actions)

```
EMAIL_PASSWORD
  - Typ: Gmail App Password
  - Format: 16 znaków bez spacji (abcdefghijklmnop)
  - Używany przez: weekly_report.yml
  - Generuj: https://myaccount.google.com/apppasswords
```

### Local environment (.env)

```
EMAIL_PASSWORD=abcdefghijklmnop
LOG_LEVEL=DEBUG
```

---

## 📏 Code metrics

```
main.py:               ~250 lines
scraper.py:            ~650 lines
email_report.py:       ~150 lines
docs/index.html:       ~850 lines (HTML+CSS+JS)
.github/workflows:     ~80 lines (YAML)

Total LOC:             ~2000 lines
Languages:             Python (65%), HTML/CSS/JS (30%), YAML (5%)
```

---

## 🎯 Kluczowe lokalizacje do edycji

| Co chcesz zmienić | Edytuj plik | Linia |
|-------------------|-------------|-------|
| Monitorowane profile | `scraper.py` | ~23-45 (PROFILES dict) |
| Email sender/receiver | `email_report.py` | ~14-15 |
| Harmonogram scanu | `.github/workflows/scan.yml` | ~6 (cron) |
| Harmonogram emaila | `.github/workflows/weekly_report.yml` | ~6 (cron) |
| Dashboard GitHub owner/repo | `docs/index.html` | ~752-753 |
| Log level | `main.py` lub `.env` | ~15 lub ENV |

---

**Ostatnia aktualizacja:** 2026-02-23  
**Wersja dokumentacji:** 1.0.0
