# ⚡ SZPERACZ OLX - Quick Reference

Szybka ściągawka dla najczęstszych operacji.

---

## 🚀 Pierwsze uruchomienie (5 minut)

```bash
1. Fork repo: github.com/Bonaventura-EW/SZPERACZ → Fork
2. Settings → Secrets → Actions → New secret:
   Name: EMAIL_PASSWORD
   Value: [16-znakowy Gmail App Password]
3. Edytuj email_report.py (linie 14-15):
   SENDER_EMAIL = "twoj@gmail.com"
   RECEIVER_EMAIL = "twoj@gmail.com"
4. Add file → Create: data/dashboard_data.json
   Content: {"profiles":{},"scan_history":[],"last_scan":null}
5. Settings → Pages → Source: main → /docs → Save
6. Actions → Daily Scan → Run workflow
7. Poczekaj 3 min → sprawdź data/ folder
8. Link do dashboardu: https://TWOJA_NAZWA.github.io/SZPERACZ/
```

---

## 📝 Najczęstsze komendy

### Lokalne uruchomienie
```bash
# Scan
python main.py --scan

# Email
python main.py --email

# Status
python main.py --status
```

### GitHub Actions
```
Actions → [Workflow] → Run workflow → Run workflow
```

---

## 🔧 Konfiguracja

### Dodaj nowy profil OLX

**scraper.py (linia ~23):**
```python
PROFILES = {
    "moj_profil": {
        "url": "https://www.olx.pl/oferty/uzytkownik/ABC123/",
        "label": "Nazwa wyświetlana",
        "is_category": False,  # True dla kategorii
    },
}
```

### Zmień harmonogram skanów

**.github/workflows/scan.yml (linia 6):**
```yaml
cron: '0 7 * * *'  # 9:00 CET = 7:00 UTC
      # │ │ │ │ │
      # │ │ │ │ └─ Dzień tygodnia (0-6, 0=niedziela)
      # │ │ │ └─── Miesiąc (1-12)
      # │ │ └───── Dzień miesiąca (1-31)
      # │ └─────── Godzina UTC (0-23)
      # └───────── Minuta (0-59)
```

**Przykłady:**
- `0 6 * * *` = 8:00 CET (6:00 UTC)
- `30 8 * * *` = 10:30 CET (8:30 UTC)
- `0 12 * * 1,3,5` = 14:00 CET, poniedziałki/środy/piątki

Generator: https://crontab.guru/

---

## 🐛 Troubleshooting - 3 najczęstsze problemy

### 1. Workflow nie commituje danych
```
Settings → Actions → General 
→ Workflow permissions 
→ Read and write permissions 
→ Save
```

### 2. Email nie wysyła się
```
1. Sprawdź Settings → Secrets → EMAIL_PASSWORD
2. Upewnij się że to 16-znakowy App Password (NIE hasło Gmail)
3. Sprawdź czy email w email_report.py to ten sam co App Password
4. Sprawdź folder SPAM
```

### 3. Dashboard pusty
```
1. Czy był pierwszy scan? (Actions → Daily Scan → zielony ✅)
2. Czy data/dashboard_data.json istnieje i ma dane?
3. Czy Pages włączone? (Settings → Pages)
4. Wyczyść cache (Ctrl+Shift+R)
5. Poczekaj 5 min (Pages needs rebuild time)
```

---

## 📊 Struktura danych (uproszczona)

### dashboard_data.json
```json
{
  "profiles": {
    "profil_x": {
      "current_listings": [...],  // Aktywne
      "archived_listings": [...], // Zniknęły
      "daily_counts": [...],      // Historia 90 dni
      "price_history": {...}      // Zmiany cen
    }
  },
  "last_scan": "2026-02-23 09:00:00"
}
```

### Excel arkusze
1. **[nazwa_profilu]** - Historia skanów + wszystkie ogłoszenia
2. **historia_cen** - Globalnie wszystkie zmiany cen
3. **podsumowanie** - Bieżący status wszystkich profili

---

## 🔐 Secrets checklist

```
✅ EMAIL_PASSWORD = Gmail App Password (16 chars, no spaces)
   Gdzie: Settings → Secrets → Actions
   Test: Actions → Weekly Report → Run workflow
```

---

## 📁 Katalogi - gdzie co znajdę?

```
.github/workflows/  → Automatyzacja (cron)
data/               → Dane (Excel + JSON)
docs/               → Dashboard (GitHub Pages)
logs/               → Logi (ignorowane przez git)
```

---

## 🌐 Linki

```
Dashboard:     https://TWOJA_NAZWA.github.io/SZPERACZ/
Repo:          https://github.com/TWOJA_NAZWA/SZPERACZ
Actions:       https://github.com/TWOJA_NAZWA/SZPERACZ/actions
Settings:      https://github.com/TWOJA_NAZWA/SZPERACZ/settings
Gmail App PWD: https://myaccount.google.com/apppasswords
Cron generator: https://crontab.guru/
```

---

## ⚡ Szybkie fixy

### Reset wszystkiego
```bash
# Lokalnie:
rm -rf data/ logs/
python main.py --scan

# Na GitHubie:
Delete data/ folder → Run scan → New data/
```

### Przestało działać po edycji
```
1. Code → History → Find last working commit
2. Click commit → View → Raw → Copy
3. Edit current file → Paste → Commit
```

### Excel za duży (>50MB)
```python
# .gitignore - dodaj:
data/szperacz_olx.xlsx

# Dane będą tylko w JSON (dashboard działa)
```

---

## 📞 Gdy nic nie pomaga

1. **Sprawdź logi:**
   - Actions → [Failed workflow] → Click job → Expand steps
   - Szukaj czerwonych linii z ERROR

2. **Sprawdź format JSON:**
   - data/dashboard_data.json
   - Wklej na jsonlint.com
   - Fix syntax errors

3. **GitHub Issue:**
   - https://github.com/Bonaventura-EW/SZPERACZ/issues
   - Template: "Co robiłem → Co się stało → Co widzę w logach"

---

## 🎯 Najczęstsze edycje

| Chcę... | Edytuj... | Linia |
|---------|-----------|-------|
| Dodać profil | scraper.py | ~23 |
| Zmienić email | email_report.py | ~14 |
| Zmienić czas scanu | .github/workflows/scan.yml | ~6 |
| Zmienić język dashboardu | docs/index.html | ~700+ |
| Wyłączyć email | .github/workflows/weekly_report.yml | Usuń plik |

---

## ✅ Checklist "Działa?"

```
□ Fork created
□ EMAIL_PASSWORD in Secrets
□ Email updated in email_report.py
□ data/dashboard_data.json exists
□ GitHub Pages enabled (Settings → Pages)
□ First scan done (Actions → green ✅)
□ Dashboard loads (GitHub Pages link)
□ Email received (test: Actions → Weekly Report)
□ Workflow permissions = Read and write
```

**9/9 = Gotowe! 🎉**

---

## 💡 Pro tips

- **Backup:** Pobieraj `data/szperacz_olx.xlsx` co miesiąc
- **Monitoring:** Star repo → Watch → Custom → Workflows only
- **Debug:** Zmień LOG_LEVEL na DEBUG (main.py line 15)
- **Speed:** Dodaj więcej profili jednocześnie (PROFILES dict)
- **Privacy:** Fork jako private repo (Settings → Danger Zone)

---

**Ostatnia aktualizacja:** 2026-02-23  
**Wersja:** 1.0.0
