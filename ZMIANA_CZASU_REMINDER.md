# 📅 PRZYPOMNIENIE: Zmiana czasu letni/zimowy

## Kiedy zmienić cron w scan.yml

SZPERACZ jest skonfigurowany aby uruchamiać się **dokładnie o 9:00 czasu polskiego przez cały rok**.

Ponieważ GitHub Actions używa czasu UTC, musisz ręcznie zmienić cron podczas przejścia na czas letni i zimowy:

### 🌸 WIOSNA: Przejście na czas letni (CEST)
**Kiedy:** Ostatnia niedziela marca (zazwyczaj ~31 marca)

**Co zrobić:**
1. Otwórz plik `.github/workflows/scan.yml`
2. Zmień linię 6:
   ```yaml
   - cron: '0 8 * * *'  # STARE (zimą)
   ```
   na:
   ```yaml
   - cron: '0 7 * * *'  # NOWE (latem)
   ```
3. Commituj i pushuj zmiany

**Wyjaśnienie:** 
- Latem Polska ma CEST (UTC+2)
- 7:00 UTC + 2h = 9:00 CEST ✓

---

### 🍂 JESIEŃ: Przejście na czas zimowy (CET)
**Kiedy:** Ostatnia niedziela października (zazwyczaj ~26 października)

**Co zrobić:**
1. Otwórz plik `.github/workflows/scan.yml`
2. Zmień linię 6:
   ```yaml
   - cron: '0 7 * * *'  # STARE (latem)
   ```
   na:
   ```yaml
   - cron: '0 8 * * *'  # NOWE (zimą)
   ```
3. Commituj i pushuj zmiany

**Wyjaśnienie:**
- Zimą Polska ma CET (UTC+1)
- 8:00 UTC + 1h = 9:00 CET ✓

---

## 📆 Dokładne daty zmian w 2026

| Zmiana | Data | Zmień cron na | Czas w Polsce |
|--------|------|---------------|---------------|
| **→ Czas letni (CEST)** | 29.03.2026 (niedziela, 2:00→3:00) | `'0 7 * * *'` | UTC+2 |
| **→ Czas zimowy (CET)** | 25.10.2026 (niedziela, 3:00→2:00) | `'0 8 * * *'` | UTC+1 |

---

## 🔔 Jak nie zapomnieć?

**Opcja 1: Kalendarz**
- Ustaw przypomnienie w telefonie/kalendarzu na ostatnią niedzielę marca i października

**Opcja 2: Sprawdź dashboard**
- Jeśli scan uruchamia się o 10:00 zamiast 9:00 (lub 8:00) → czas zmienić cron!

**Opcja 3: GitHub Issue**
- Możesz utworzyć recurring issue jako reminder

---

## ✅ Weryfikacja po zmianie

Po zmianie crona, następnego dnia sprawdź:
1. Dashboard SZPERACZ → "Ostatni scan" powinien pokazywać godzinę około 9:00 czasu polskiego
2. GitHub Actions → Workflow runs powinny być około 7:00 UTC (latem) lub 8:00 UTC (zimą)

---

## 🤖 Bonus: Automatyzacja (advanced)

Jeśli chcesz całkowicie zautomatyzować, możesz:
1. Użyć dwóch cronów jednocześnie (ale jeden będzie uruchamiać się o złej porze przez pół roku)
2. Stworzyć skrypt, który automatycznie modyfikuje workflow (zaawansowane)

Ale dla prostoty, **ręczna zmiana 2x rocznie jest OK** - to tylko 5 minut pracy.

---

**Ostatnia aktualizacja:** 2026-02-27  
**Obecny cron:** `'0 8 * * *'` (czas zimowy CET, do 29.03.2026)
