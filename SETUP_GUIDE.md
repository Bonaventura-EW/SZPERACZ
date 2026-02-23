# 🚀 SZPERACZ OLX — Setup Guide

Przewodnik instalacji krok po kroku dla użytkowników, którzy nigdy nie używali GitHub Actions.

---

## 📋 Wymagania wstępne

Przed rozpoczęciem upewnij się, że masz:

- ✅ Konto GitHub (darmowe)
- ✅ Konto Gmail (do wysyłania raportów email)
- ✅ Komputer z dostępem do internetu
- ✅ Przeglądarka (Chrome, Firefox, Edge, Safari)

**Nie musisz:**
- ❌ Instalować Pythona (GitHub Actions to zrobi za Ciebie)
- ❌ Znać programowania
- ❌ Mieć serwera

---

## 🎯 Krok 1: Fork repozytorium

### 1.1 Zaloguj się do GitHub
Wejdź na https://github.com i zaloguj się na swoje konto.

### 1.2 Fork projektu
1. Wejdź na https://github.com/Bonaventura-EW/SZPERACZ
2. Kliknij przycisk **Fork** (prawy górny róg)
3. Zostaw domyślne ustawienia i kliknij **Create fork**

Teraz masz swoją własną kopię projektu!

---

## ⚙️ Krok 2: Konfiguracja Gmail App Password

### 2.1 Włącz weryfikację dwuetapową
1. Wejdź na https://myaccount.google.com/security
2. W sekcji "Logowanie do konta Google" kliknij **Weryfikacja dwuetapowa**
3. Postępuj zgodnie z instrukcjami (będziesz musiał podać numer telefonu)

### 2.2 Wygeneruj App Password
1. Po włączeniu weryfikacji wróć na https://myaccount.google.com/security
2. Kliknij **Weryfikacja dwuetapowa** → **Hasła aplikacji** (na dole strony)
3. W polu "Wybierz aplikację" wpisz: **SZPERACZ OLX**
4. Kliknij **Wygeneruj**
5. **WAŻNE:** Skopiuj 16-znakowy kod (np. `abcd efgh ijkl mnop`)
   - Usuń spacje, będzie: `abcdefghijklmnop`
   - Zapisz go bezpiecznie, pojawi się tylko raz!

### 2.3 Dodaj hasło do GitHub Secrets
1. Wejdź do **swojego** forka: `https://github.com/TWOJA_NAZWA/SZPERACZ`
2. Kliknij **Settings** (ustawienia)
3. W lewym menu wybierz **Secrets and variables** → **Actions**
4. Kliknij **New repository secret**
5. Wypełnij:
   - **Name:** `EMAIL_PASSWORD`
   - **Secret:** wklej kod z kroku 2.2 (bez spacji!)
6. Kliknij **Add secret**

✅ Gotowe! Twoje hasło jest bezpiecznie zapisane.

---

## 📝 Krok 3: Konfiguracja adresów email

### 3.1 Edytuj plik email_report.py
1. W swoim forku kliknij plik **email_report.py**
2. Kliknij ikonę ołówka (✏️) **Edit this file**
3. Znajdź linie 14-15:
   ```python
   SENDER_EMAIL = "slowholidays00@gmail.com"
   RECEIVER_EMAIL = "malczarski@gmail.com"
   ```
4. Zmień na swoje adresy:
   ```python
   SENDER_EMAIL = "twoj_email@gmail.com"        # email z którego wysyłasz
   RECEIVER_EMAIL = "twoj_email@gmail.com"      # email na który dostajesz raport
   ```
5. Kliknij **Commit changes** (zielony przycisk)
6. W oknie dialogowym ponownie **Commit changes**

✅ Gotowe! Raporty będą wysyłane na Twój email.

---

## 🏗️ Krok 4: Inicjalizacja struktury katalogów

### 4.1 Utwórz katalog data/
1. W swoim forku kliknij **Add file** → **Create new file**
2. W polu nazwy wpisz: `data/dashboard_data.json`
   (Git automatycznie utworzy katalog `data/`)
3. Wklej poniższą zawartość:
   ```json
   {
     "profiles": {},
     "scan_history": [],
     "last_scan": null
   }
   ```
4. Kliknij **Commit changes**

### 4.2 Sprawdź strukturę
Twoje repo powinno teraz zawierać:
```
SZPERACZ/
├── .github/workflows/
├── data/
│   └── dashboard_data.json
├── docs/
├── email_report.py
├── main.py
├── scraper.py
├── requirements.txt
└── README.md
```

---

## 🌐 Krok 5: Aktywacja GitHub Pages (Dashboard)

### 5.1 Włącz GitHub Pages
1. W swoim forku kliknij **Settings**
2. W lewym menu wybierz **Pages**
3. W sekcji "Source":
   - Branch: **main**
   - Folder: **/docs**
4. Kliknij **Save**

### 5.2 Poczekaj 1-2 minuty
GitHub buduje stronę. Odśwież po chwili.

### 5.3 Sprawdź link do dashboardu
Pojawi się zielony box z linkiem:
```
✅ Your site is live at https://TWOJA_NAZWA.github.io/SZPERACZ/
```

**Zapisz ten link** - to Twój dashboard OLX!

---

## ▶️ Krok 6: Pierwszy scan (ręcznie)

### 6.1 Uruchom workflow
1. W swoim forku kliknij zakładkę **Actions**
2. Jeśli widzisz komunikat o wyłączonych workflow, kliknij **I understand, enable them**
3. Po lewej wybierz **SZPERACZ OLX - Daily Scan**
4. Kliknij **Run workflow** (prawy górny róg)
5. Zostaw domyślne ustawienia i kliknij zielony **Run workflow**

### 6.2 Obserwuj postęp
- Pojawi się żółta kółko ⚫ (w trakcie)
- Po 2-3 minutach zmieni się na:
  - ✅ Zielony = sukces
  - ❌ Czerwony = błąd (sprawdź logi)

### 6.3 Sprawdź wyniki
1. Wejdź do **Code** → folder **data/**
2. Kliknij **dashboard_data.json**
3. Powinien być wypełniony danymi z OLX!

---

## 📧 Krok 7: Test wysyłki email

### 7.1 Uruchom email workflow
1. **Actions** → **SZPERACZ OLX — Weekly Report**
2. **Run workflow** → **Run workflow**

### 7.2 Sprawdź email
W ciągu minuty powinieneś dostać email:
```
Od: twoj_email@gmail.com
Temat: 🔍 SZPERACZ OLX — Raport tygodniowy (23.02.2026)
Załącznik: szperacz_olx_20260223.xlsx
```

Jeśli nie otrzymałeś:
- Sprawdź folder SPAM
- Sprawdź czy `EMAIL_PASSWORD` jest poprawne (Secrets → Actions)
- Sprawdź czy email w `email_report.py` to ten sam co App Password

---

## 🤖 Krok 8: Automatyzacja

### 8.1 Sprawdź harmonogram
Workflow działają automatycznie:
- **Scan:** Codziennie o 9:00 rano (polski czas)
- **Email:** Każdy poniedziałek o 9:30

### 8.2 Monitoruj w Actions
Każde uruchomienie będzie widoczne w zakładce **Actions**.

### 8.3 Oglądaj dashboard
Wejdź na swój link GitHub Pages, dane aktualizują się automatycznie!

---

## 🎨 Krok 9: Personalizacja (opcjonalnie)

### 9.1 Zmiana monitorowanych profili
1. Edytuj **scraper.py** (kliknij ✏️)
2. Znajdź sekcję `PROFILES` (linia ~25)
3. Dodaj/usuń profile według schematu:
   ```python
   "nazwa_profilu": {
       "url": "https://www.olx.pl/oferty/uzytkownik/ABC123/",
       "label": "Przyjazna nazwa",
       "is_category": False,
   },
   ```
4. Commit changes

### 9.2 Jak znaleźć URL profilu OLX?
1. Wejdź na OLX.pl
2. Znajdź ogłoszenie użytkownika, który Cię interesuje
3. Kliknij na nazwę użytkownika
4. Skopiuj URL (np. `https://www.olx.pl/oferty/uzytkownik/ABC123/`)

### 9.3 Zmiana harmonogramu
Edytuj `.github/workflows/scan.yml`:
```yaml
schedule:
  - cron: '0 7 * * *'    # 9:00 CET = 7:00 UTC
```

Cron generator: https://crontab.guru/

---

## 🛠️ Troubleshooting

### Problem: Workflow się nie uruchamia
**Rozwiązanie:**
- Sprawdź czy workflow są włączone (Actions → Enable workflows)
- Upewnij się, że fork jest aktualny (Sync fork)

### Problem: Scan zwraca 0 ogłoszeń
**Rozwiązanie:**
- Sprawdź czy URL profilu jest poprawny
- Uruchom ponownie (czasami OLX blokuje tymczasowo)
- Sprawdź logi w Actions (kliknij na failed workflow)

### Problem: Email nie działa
**Rozwiązanie:**
1. Sprawdź czy `EMAIL_PASSWORD` to App Password (16 znaków)
2. Sprawdź czy weryfikacja dwuetapowa jest włączona
3. Sprawdź czy adres email w `email_report.py` zgadza się z tym, dla którego wygenerowałeś App Password

### Problem: Dashboard nie ładuje danych
**Rozwiązanie:**
- Poczekaj 5 minut po pierwszym scanie (GitHub Pages potrzebuje czasu)
- Wyczyść cache przeglądarki (Ctrl+Shift+R)
- Sprawdź czy `data/dashboard_data.json` istnieje i zawiera dane

### Problem: "Permission denied" w Actions
**Rozwiązanie:**
1. Settings → Actions → General
2. Workflow permissions → **Read and write permissions**
3. Save

---

## ✅ Checklist końcowy

Przed zakończeniem upewnij się, że:

- [ ] Fork utworzony
- [ ] Gmail App Password wygenerowane i dodane do Secrets
- [ ] Adresy email zaktualizowane w `email_report.py`
- [ ] Katalog `data/` istnieje
- [ ] GitHub Pages włączone
- [ ] Pierwszy scan uruchomiony i zakończony sukcesem ✅
- [ ] Email testowy otrzymany
- [ ] Dashboard działa (link GitHub Pages)
- [ ] Workflow permissions ustawione na "Read and write"

**Gratulacje! 🎉 SZPERACZ OLX jest gotowy do działania!**

---

## 📞 Pomoc

Jeśli masz problemy:
1. Sprawdź sekcję **Troubleshooting** powyżej
2. Przeczytaj **README.md** dla szczegółów technicznych
3. Otwórz **Issue** na GitHub: https://github.com/Bonaventura-EW/SZPERACZ/issues

---

**Powodzenia w szperactwie! 🔍**
