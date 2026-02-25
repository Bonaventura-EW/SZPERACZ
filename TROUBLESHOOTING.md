# 🔍 SZPERACZ OLX - Troubleshooting Guide

## ❌ Problem: Daily scan się nie wykonał

### Szybka diagnostyka

```bash
# Sprawdź status workflow
python diagnose.py

# Automatyczna naprawa
python autofix.py
```

---

## 🔧 Manualne rozwiązania

### Problem 1: Workflow jest wyłączony (disabled)

**Symptom:** Brak żadnych wykonań w Actions tab

**Przyczyna:** GitHub wyłącza scheduled workflows po 60 dniach nieaktywności

**Fix:**
```bash
# Reaktywuj przez commit
git commit --allow-empty -m "Re-enable scheduled workflows"
git push
```

Lub:
1. Idź do: `https://github.com/Bonaventura-EW/SZPERACZ/actions/workflows/scan.yml`
2. Jeśli widzisz przycisk "Enable workflow" - kliknij go

---

### Problem 2: Zły timezone w cronie

**Symptom:** Scan wykonuje się o złej godzinie

**Obecny cron:** `0 8 * * *` (8:00 UTC)
- **Zima (CET):** 8:00 UTC = **9:00 czasu polskiego** ✅
- **Lato (CEST):** 8:00 UTC = **10:00 czasu polskiego** ⚠️

**Fix:** Jeśli chcesz zawsze o 9:00 polskiego czasu:
- Zimą: użyj `0 8 * * *`
- Latem: użyj `0 7 * * *`

Lub zaakceptuj, że latem będzie o 10:00.

---

### Problem 3: Brak danych w folderze `data/`

**Symptom:** Workflow się wykonuje, ale nie ma commitów z danymi

**Możliwe przyczyny:**
1. Scraper failnął (sprawdź logi w Actions)
2. Git push failnął (brak uprawnień)

**Fix:**
```bash
# Sprawdź logi ostatniego workflow
# GitHub → Actions → kliknij na ostatnie wykonanie → Zobacz logi

# Uruchom scraper lokalnie
python scraper.py

# Manualnie commit i push
git add data/
git commit -m "Manual scan: $(date)"
git push
```

---

### Problem 4: Dashboard nie aktualizuje danych

**Symptom:** Dane są w repo, ale dashboard pokazuje stare

**Przyczyny:**
1. **Cache CDN:** GitHub raw.githubusercontent.com cachuje pliki
2. **Cache przeglądarki:** Stare dane w localStorage/cache

**Fix:**

**A. Cache CDN (poczekaj 5-10 minut)**
- GitHub CDN aktualizuje się automatycznie, ale może zająć do 10 minut

**B. Cache przeglądarki (natychmiastowy fix)**
```javascript
// W konsoli przeglądarki (F12):
localStorage.clear();
location.reload(true);
```

Lub:
- Hard refresh: `Ctrl+Shift+R` (Windows/Linux) lub `Cmd+Shift+R` (Mac)
- Tryb incognito: `Ctrl+Shift+N`

---

## 🚀 Natychmiastowe uruchomienie scanu

### Opcja A: Dashboard (wymaga GitHub token)

1. Otwórz: https://bonaventura-ew.github.io/SZPERACZ/
2. Kliknij "Scan teraz"
3. Podaj GitHub Personal Access Token:
   - Utwórz: https://github.com/settings/tokens/new?scopes=repo,workflow
   - Wybierz scope: `repo` lub `workflow`
   - Wklej token w modal

### Opcja B: GitHub Actions UI

1. Idź do: https://github.com/Bonaventura-EW/SZPERACZ/actions/workflows/scan.yml
2. Kliknij **"Run workflow"** (prawy górny róg)
3. Wybierz branch: `main`
4. Kliknij zielony **"Run workflow"**
5. Odśwież stronę po 10 sekundach - powinien się pojawić żółty status

### Opcja C: Terminal (lokalnie)

```bash
# Sklonuj repo (jeśli jeszcze nie masz)
git clone https://github.com/Bonaventura-EW/SZPERACZ.git
cd SZPERACZ

# Zainstaluj dependencies
pip install -r requirements.txt

# Uruchom scan
python scraper.py

# Commit i push
git add data/
git commit -m "Manual scan: $(date)"
git push
```

---

## 📊 Weryfikacja naprawy

### 1. Sprawdź czy workflow działa

```bash
# Idź do Actions
https://github.com/Bonaventura-EW/SZPERACZ/actions

# Szukaj zielonych checkmarków ✅
```

### 2. Sprawdź czy dane są aktualne

```bash
# Sprawdź timestamp plików w repo
https://github.com/Bonaventura-EW/SZPERACZ/tree/main/data

# Pliki powinny mieć dzisiejszą datę
```

### 3. Sprawdź dashboard

```bash
# Otwórz dashboard
https://bonaventura-ew.github.io/SZPERACZ/

# Sprawdź "Ostatni scan" w górnym barze
# Powinno pokazywać dzisiejszą datę
```

---

## ⏰ Harmonogram workflow

- **Daily Scan:** Codziennie o 9:00 CET (zimą) / 10:00 CEST (latem)
- **Weekly Report:** Każdy poniedziałek o 9:30 CET

**Cron expressions:**
- Daily: `0 8 * * *` (8:00 UTC)
- Weekly: `30 7 * * 1` (7:30 UTC w poniedziałki)

---

## 🆘 Nadal nie działa?

### Debug checklist

- [ ] Workflow jest enabled w Actions tab
- [ ] Repo ma commits z ostatnich 60 dni
- [ ] Branch `main` istnieje i ma najnowszy kod
- [ ] Secrets są ustawione (dla email reports: `EMAIL_PASSWORD`)
- [ ] `requirements.txt` zawiera wszystkie dependencies
- [ ] `data/` folder istnieje w repo
- [ ] Permissions w workflow: `contents: write`

### Logi debug

```bash
# Zobacz szczegółowe logi workflow
# GitHub → Actions → kliknij na workflow run → kliknij na job "scan"

# Sprawdź git status
git status
git log --oneline -n 5
```

---

## 📞 Kontakt

Jeśli problem nadal występuje, stwórz Issue na GitHubie z:
1. Screenshot z Actions tab
2. Logi z ostatniego workflow run
3. Output z `python diagnose.py`
4. Twoja timezone i oczekiwana godzina scanu

---

## 🎯 Najczęstsze błędy i rozwiązania

### Błąd: "Resource not accessible by integration"

**Przyczyna:** Brak uprawnień `contents: write` w workflow

**Fix:** Sprawdź czy w `.github/workflows/scan.yml` jest:
```yaml
permissions:
  contents: write
```

### Błąd: "fatal: could not read Username"

**Przyczyna:** Brak konfiguracji Git w workflow

**Fix:** Sprawdź czy w workflow jest krok z `git config`

### Błąd: "No module named 'requests'"

**Przyczyna:** Dependencies nie są zainstalowane

**Fix:**
```bash
pip install -r requirements.txt
```

### Dashboard pokazuje "Failed to load data"

**Przyczyna:** Plik `dashboard_data.json` nie istnieje lub jest pusty

**Fix:**
```bash
# Uruchom scan lokalnie
python scraper.py

# Sprawdź czy plik został utworzony
ls -la data/dashboard_data.json

# Commit i push
git add data/
git commit -m "Initialize dashboard data"
git push
```
