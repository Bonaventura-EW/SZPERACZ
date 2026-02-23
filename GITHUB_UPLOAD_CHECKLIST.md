# 📤 GitHub Upload Checklist

## Pliki do dodania do repozytorium

### ✅ **OBOWIĄZKOWE** - bez tych plików projekt nie będzie działać:

1. **`main.py`** ⭐ NOWY PLIK
   - Entry point aplikacji
   - Lokalizacja: root repozytorium
   - Zastępuje: brak (nowy plik)

2. **`.gitignore`** ⭐ NOWY PLIK
   - Wykluczenie wrażliwych danych i logów
   - Lokalizacja: root repozytorium
   - Zastępuje: brak (nowy plik)

3. **`README.md`** ⭐ AKTUALIZACJA
   - Pełna dokumentacja projektu
   - Lokalizacja: root repozytorium
   - Zastępuje: istniejący README.md (jeśli był)

4. **`scraper.py`** ⭐ AKTUALIZACJA
   - Poprawiona inicjalizacja katalogu data/
   - Lokalizacja: root repozytorium
   - Zastępuje: istniejący scraper.py

5. **`data/dashboard_data.json`** ⭐ NOWY PLIK
   - Pusty JSON jako starter
   - Lokalizacja: data/dashboard_data.json
   - Uwaga: Musisz utworzyć katalog `data/` jeśli nie istnieje

### 📚 **OPCJONALNE** - pomocne ale nie konieczne:

6. **`SETUP_GUIDE.md`** 📘
   - Szczegółowy przewodnik krok po kroku
   - Lokalizacja: root repozytorium
   - Dla użytkowników, którzy nie znają GitHub

7. **`.env.example`** 📝
   - Template dla lokalnego development
   - Lokalizacja: root repozytorium
   - Pomaga w lokalnym testowaniu

8. **`LICENSE`** ⚖️
   - Licencja MIT
   - Lokalizacja: root repozytorium
   - Dobra praktyka open source

---

## 🚀 Instrukcja krok po kroku

### Metoda 1: Upload przez Web Interface (najłatwiejsza)

#### Krok 1: Dodaj main.py
1. Wejdź na https://github.com/Bonaventura-EW/SZPERACZ
2. Kliknij **Add file** → **Upload files**
3. Przeciągnij plik `main.py` lub kliknij "choose your files"
4. W pole commit message wpisz: `Add main.py - entry point with error handling`
5. Kliknij **Commit changes**

#### Krok 2: Dodaj .gitignore
1. **Add file** → **Create new file**
2. Nazwa: `.gitignore`
3. Skopiuj zawartość z dostarczonego pliku `.gitignore`
4. Commit message: `Add .gitignore - exclude logs and secrets`
5. **Commit changes**

#### Krok 3: Aktualizuj README.md
1. Kliknij na istniejący `README.md`
2. Kliknij ikonę ołówka ✏️ **Edit this file**
3. Zastąp całą zawartość nowym README
4. Commit message: `Update README.md - comprehensive documentation`
5. **Commit changes**

#### Krok 4: Zaktualizuj scraper.py
1. Kliknij na `scraper.py`
2. Kliknij ✏️ **Edit this file**
3. Zastąp zawartość (poprawka to linia ~574: dodano `os.makedirs(DATA_DIR, exist_ok=True)`)
4. Commit message: `Fix scraper.py - ensure data directory exists`
5. **Commit changes**

#### Krok 5: Utwórz data/dashboard_data.json
1. **Add file** → **Create new file**
2. Nazwa: `data/dashboard_data.json` (katalog utworzy się automatycznie!)
3. Skopiuj zawartość z pliku `dashboard_data.json`:
   ```json
   {
     "profiles": {},
     "scan_history": [],
     "last_scan": null,
     "metadata": {
       "created": "2026-02-23 12:00:00",
       "version": "1.0.0"
     }
   }
   ```
4. Commit message: `Initialize data/dashboard_data.json`
5. **Commit changes**

#### (Opcjonalnie) Krok 6-8: Dodaj pozostałe pliki
Powtórz proces dla:
- `SETUP_GUIDE.md`
- `.env.example`
- `LICENSE`

---

### Metoda 2: Git Command Line (dla zaawansowanych)

```bash
# 1. Sklonuj repo
git clone https://github.com/Bonaventura-EW/SZPERACZ.git
cd SZPERACZ

# 2. Skopiuj wszystkie nowe pliki do katalogu
cp /path/to/downloads/main.py .
cp /path/to/downloads/.gitignore .
cp /path/to/downloads/README.md .
cp /path/to/downloads/scraper.py .
cp /path/to/downloads/SETUP_GUIDE.md .
cp /path/to/downloads/.env.example .
cp /path/to/downloads/LICENSE .

# 3. Utwórz katalog data/ i skopiuj JSON
mkdir -p data
cp /path/to/downloads/dashboard_data.json data/

# 4. Dodaj pliki do git
git add main.py .gitignore README.md scraper.py SETUP_GUIDE.md .env.example LICENSE data/dashboard_data.json

# 5. Commit
git commit -m "🚀 Major update: Add main.py, fix scraper, improve docs"

# 6. Push do GitHub
git push origin main
```

---

## 🔍 Weryfikacja

Po uploadzie sprawdź czy:

### 1. Wszystkie pliki są widoczne
Wejdź na https://github.com/Bonaventura-EW/SZPERACZ i sprawdź strukturę:
```
SZPERACZ/
├── .github/workflows/
│   ├── scan.yml
│   └── weekly_report.yml
├── data/
│   └── dashboard_data.json ⭐ NOWY
├── docs/
│   └── index.html
├── .env.example ⭐ NOWY
├── .gitignore ⭐ NOWY
├── email_report.py
├── LICENSE ⭐ NOWY
├── main.py ⭐ NOWY
├── README.md ✏️ ZAKTUALIZOWANY
├── requirements.txt
├── scraper.py ✏️ ZAKTUALIZOWANY
└── SETUP_GUIDE.md ⭐ NOWY
```

### 2. GitHub Actions nie są zepsute
1. Wejdź w zakładkę **Actions**
2. Jeśli widzisz błędy YAML, sprawdź pliki workflow
3. Jeśli wszystko OK, uruchom test: **Run workflow**

### 3. Uprawnienia są poprawne
1. **Settings** → **Actions** → **General**
2. **Workflow permissions** powinno być: **Read and write permissions**
3. Jeśli nie, zmień i **Save**

---

## ⚠️ Częste błędy

### Błąd: "File already exists"
**Rozwiązanie:** 
- Najpierw usuń stary plik (kliknij plik → 🗑️ → Commit)
- Potem dodaj nowy

### Błąd: "Invalid workflow file"
**Przyczyna:** Przypadkowo edytowałeś pliki .yml
**Rozwiązanie:** 
- Nie ruszaj plików w `.github/workflows/` jeśli nie wiesz co robisz
- Jeśli zepsułeś, przywróć poprzednią wersję: kliknij plik → **History** → znajdź ostatnią działającą → **View** → **Raw** → skopiuj

### Błąd: "data/" nie commituje się
**Przyczyna:** Git nie commituje pustych katalogów
**Rozwiązanie:** 
- ZAWSZE dodaj plik `dashboard_data.json` WEWNĄTRZ katalogu `data/`
- Git wtedy commituje katalog razem z plikiem

---

## 🎯 Następne kroki po uploadzeniu

1. **Przeczytaj `SETUP_GUIDE.md`** i wykonaj konfigurację:
   - Dodaj `EMAIL_PASSWORD` do Secrets
   - Zmień adresy email w `email_report.py`
   - Włącz GitHub Pages

2. **Uruchom pierwszy scan:**
   - Actions → Daily Scan → Run workflow

3. **Sprawdź rezultaty:**
   - Dashboard powinien pokazać dane
   - Plik `data/dashboard_data.json` powinien być wypełniony

---

## ✅ Finalna lista kontrolna

Przed zakończeniem upewnij się:

- [ ] `main.py` dodany do root
- [ ] `.gitignore` dodany do root
- [ ] `README.md` zaktualizowany
- [ ] `scraper.py` zaktualizowany (z `os.makedirs`)
- [ ] `data/dashboard_data.json` utworzony
- [ ] (Opcjonalnie) `SETUP_GUIDE.md`, `.env.example`, `LICENSE` dodane
- [ ] Wszystkie pliki widoczne na GitHub
- [ ] Brak błędów w Actions
- [ ] Workflow permissions = Read and write

**Gotowe! Teraz możesz przejść do `SETUP_GUIDE.md` i skonfigurować automatyzację! 🎉**

---

## 💡 Wskazówki

- **Commituj często:** Lepiej 5 małych commitów niż 1 wielki
- **Opisuj zmiany:** Dobre commit messages pomagają w przyszłości
- **Testuj po każdej zmianie:** Actions → Run workflow
- **Backup:** Zapisz lokalnie kopię plików przed uploadem

---

**Powodzenia! 🚀**
