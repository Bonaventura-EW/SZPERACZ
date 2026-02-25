# 📦 SZPERACZ - System archiwizacji ogłoszeń

## 🎯 Czym jest archiwum?

**Archiwum** przechowuje ogłoszenia, które **zniknęły z OLX** (zostały usunięte, wynajęte, lub wygasły).

---

## 📋 Zasady archiwizacji

### Kiedy ogłoszenie trafia do archiwum?

```
Scan N-1 (wczoraj):
- Ogłoszenie X jest na OLX → znajduje się w "Aktualne"

Scan N (dzisiaj):
- Ogłoszenie X NIE MA na OLX → przeniesione do "Archiwum"
```

### Kod odpowiedzialny (scraper.py, linie 681-684):

```python
for old_l in pd_.get("current_listings", []):
    if old_l["id"] not in current_ids:
        old_l["archived_date"] = now_str
        pd_["archived_listings"].append(old_l)
```

**Logika:**
1. Iteruj przez wszystkie ogłoszenia z poprzedniego scanu (`current_listings`)
2. Sprawdź czy każde z nich jest w obecnym scanie (`current_ids`)
3. Jeśli **NIE MA** → dodaj timestamp `archived_date` i przenieś do `archived_listings`

---

## 📊 Struktura danych

### Ogłoszenie w archiwum:

```json
{
  "id": "abc123",
  "title": "Pokój blisko UMCS",
  "price": 1200,
  "first_price": 1200,
  "price_change": 0,
  "url": "https://www.olx.pl/...",
  "first_seen": "2026-02-15 09:00:00",
  "last_seen": "2026-02-24 09:00:00",
  "archived_date": "2026-02-25 09:00:00"  // ← KLUCZOWE
}
```

### Pola specyficzne dla archiwum:

- **`archived_date`**: Data i czas gdy ogłoszenie zniknęło z OLX
- **`first_seen`**: Kiedy po raz pierwszy zobaczyliśmy ogłoszenie
- **`last_seen`**: Ostatni scan gdy ogłoszenie było jeszcze aktywne

---

## 🔍 Dlaczego ogłoszenie może zniknąć?

### 1. **Wynajęte / Sprzedane** ✅
```
Ogłoszenie: Pokój 1200 zł
Status: Właściciel znalazł najemcę
Archiwum: ✅ TAK (normalna sytuacja)
```

### 2. **Wygasło** ⏰
```
Ogłoszenie: Pokój 800 zł
Status: Minęło 30 dni, automatycznie usunięte przez OLX
Archiwum: ✅ TAK
```

### 3. **Usunięte przez właściciela** 🗑️
```
Ogłoszenie: Kawalerka 2500 zł
Status: Właściciel zrezygnował z wynajmu
Archiwum: ✅ TAK
```

### 4. **Błąd scrapera** ❌
```
Ogłoszenie: Studio 1800 zł
Status: Scraper nie znalazł (OLX blocking, błąd parsowania)
Archiwum: ⚠️ FAŁSZYWIE ZARCHIWIZOWANE
```

### 5. **Zmiana URL** 🔄
```
Ogłoszenie: Pokój 900 zł
Status: Właściciel edytował → nowe ID w URL
Archiwum: ⚠️ Stare ID w archiwum, nowe ID w aktualnych
```

---

## 📈 Limity archiwum

### Maksymalna liczba: **200 ogłoszeń** na profil

```python
if len(pd_["archived_listings"]) > 200:
    pd_["archived_listings"] = pd_["archived_listings"][-200:]
```

**Dlaczego limit?**
- Oszczędność miejsca w JSON
- Szybsze ładowanie dashboardu
- Skoncentrowanie na ostatnich danych

**Co się dzieje po przekroczeniu?**
- Przechowywane są **ostatnie 200** zarchiwizowanych
- Najstarsze są usuwane
- FIFO (First In, First Out)

---

## 🎨 Dashboard - zakładka "Archiwum"

### Jak wygląda:

```
┌────────────────────────────────────────────────────────────┐
│ poqui                                              [✕]     │
├────────────────────────────────────────────────────────────┤
│  Aktualne  |  Archiwum  ← TAB                              │
├────────────────────────────────────────────────────────────┤
│ Ogłoszenie            │ Cena  │ Zmiana  │ Publ.  │ Zniknęło│
├────────────────────────────────────────────────────────────┤
│ Pokój UMCS            │1200zł │   —     │15.02   │ 25.02   │
│ Kawalerka centrum     │2500zł │ +100zł🔴│10.02   │ 24.02   │
│ Studio Lubartowska    │1800zł │   —     │08.02   │ 23.02   │
└────────────────────────────────────────────────────────────┘
```

### Dodatkowa kolumna: **Zniknęło**

Pokazuje datę gdy ogłoszenie zostało zarchiwizowane (= ostatni scan gdy go nie było).

---

## 💡 Zastosowania archiwum

### 1. **Analiza tempa wynajmu**

```
Ogłoszenie: Pokój 1000 zł
First seen: 2026-02-10
Archived:   2026-02-15
Czas na rynku: 5 dni ← Szybko! Dobra cena.
```

```
Ogłoszenie: Pokój 1500 zł
First seen: 2026-01-20
Archived:   2026-02-25
Czas na rynku: 36 dni ← Długo. Za drogo?
```

### 2. **Tracking zmian cen przed wynajęciem**

```
Ogłoszenie: Studio centrum
First price: 2500 zł
Last price:  2200 zł (-300 zł)
Archived:    2026-02-25

→ Właściciel obniżył o 300 zł przed znalezieniem najemcy
→ Wniosek: Może 2200 zł to maksimum dla tej lokalizacji
```

### 3. **Identyfikacja właścicieli z wieloma ogłoszeniami**

```
Profil: pokojewlublinie
Archived (ostatni miesiąc): 15 ogłoszeń
Current: 2 ogłoszenia

→ Aktywny właściciel/pośrednik
→ Regularnie wynajmuje pokoje
→ Warto sprawdzić czy ma jeszcze coś dostępnego
```

### 4. **Monitoring reaktywacji**

```
Ogłoszenie ID: abc123
Archived:  2026-02-20
Current:   2026-02-25 (to samo ID!)

→ Właściciel przywrócił ogłoszenie
→ Poprzedni najemca zrezygnował?
→ Może jest problem z lokalem?
```

---

## ⚠️ Znane problemy

### Problem 1: Fałszywa archiwizacja przez scraper errors

**Scenariusz:**
```
08:50 - Scan failnął (OLX blocking) → 0 ogłoszeń
        Wszystkie aktualne → przeniesione do archiwum ❌

09:00 - Scan zadziałał → 445 ogłoszeń
        Wszystkie jako "nowe" ✅
        
Skutek: 445 ogłoszeń fałszywie w archiwum z datą 08:50
```

**Rozwiązanie:**
- Nie archiwizuj jeśli `count == 0` (oznaka błędu)
- Wymaga poprawki w kodzie

### Problem 2: Duplikaty przy zmianie URL

**Scenariusz:**
```
Ogłoszenie edytowane → nowe ID w URL
Stare ID → archiwum
Nowe ID → aktualne

Skutek: To samo ogłoszenie 2x (różne ID)
```

**Rozwiązanie:**
- Matching po tytule + cenie + lokalizacji
- Obecnie nie zaimplementowane

---

## 📊 Statystyki z obecnych danych

```
Profil                          | Aktualne | Archiwum | Ratio
--------------------------------|----------|----------|-------
Wszystkie pokoje w Lublinie     |    445   |   200*   | 2.2:1
pokojewlublinie                 |      2   |     2    | 1:1
poqui                           |      3   |     4    | 0.75:1
artymiuk                        |      0   |     0    | -
dawny patron                    |      2   |     0    | -

* limit 200 osiągnięty (może było więcej)
```

**Wnioski:**
- Kategoria "Wszystkie" ma najwięcej rotacji
- Profile użytkowników mają stabilniejsze ogłoszenia
- poqui ma więcej zarchiwizowanych niż aktualnych (możliwa sezonowość?)

---

## 🔮 Możliwe ulepszenia

### 1. **Prevent false archiving**

```python
# Przed archiwizacją sprawdź czy to nie błąd scrapera
if result["count"] == 0 and result.get("crosscheck") == "error":
    log.warning("Skip archiving - scan failed")
    return  # Nie archiwizuj!
```

### 2. **Resurrection detection**

```python
# Wykryj ogłoszenia które wróciły
if lid in archived_ids:
    log.info(f"Resurrection detected: {lid}")
    listing["resurrection"] = True
```

### 3. **Time-on-market analytics**

```python
# Oblicz średni czas na rynku
time_on_market = (archived_date - first_seen).days
avg_time = sum(all_times) / len(all_times)
```

### 4. **Price drop before archiving**

```python
# Ile ogłoszeń obniżono przed wynajęciem?
if listing["price_change"] < 0:
    log.info(f"Price dropped before renting: {listing['price_change']}")
```

---

## 🎯 TL;DR

### Co to jest archiwum?
**Ogłoszenia które zniknęły z OLX**

### Kiedy ogłoszenie trafia do archiwum?
**Gdy w obecnym scanie go nie ma, a w poprzednim było**

### Ile ogłoszeń może być w archiwum?
**Max 200 na profil (najstarsze są usuwane)**

### Do czego to jest przydatne?
- Analiza tempa wynajmu
- Tracking zmian cen
- Monitoring aktywności właścicieli
- Wykrywanie problemów z lokalami

### Jakie są problemy?
- Fałszywa archiwizacja przy błędach scrapera
- Duplikaty przy zmianie URL

---

**Status:** ✅ Działające  
**Ostatnia aktualizacja:** 2026-02-25  
**Lokalizacja kodu:** `scraper.py` linie 681-687
