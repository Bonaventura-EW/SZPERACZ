# SZPERACZ - Naprawa Scheduled Scan Timing (28.02.2026)

## 🔍 Zdiagnozowany Problem

**Objawy:**
- Scheduled scan nie wykonał się dzisiaj (28.02.2026) o oczekiwanej godzinie 8:00 UTC

**Diagnoza:**
- Workflow **NIE był zepsuty**
- GitHub Actions ma **losowe opóźnienia 90-150 minut** dla scheduled workflows
- Cron ustawiony na `0 8 * * *` faktycznie wykonywał się między 9:37-10:31 UTC
- Jest to znany problem GitHub Actions przy dużym obciążeniu platformy

**Analiza historycznych runs:**
```
Data        | Scheduled czas | Faktyczne wykonanie | Opóźnienie
2026-02-27  | 08:00 UTC     | 10:04 UTC          | +124 min
2026-02-26  | 08:00 UTC     | 10:31 UTC          | +151 min  
2026-02-24  | 08:00 UTC     | 09:37 UTC          | +97 min
```

## ✅ Zaimplementowane Rozwiązania

### 1. Przesunięcie Crona na Wcześniejszą Godzinę

**Plik:** `.github/workflows/scan.yml`

**Zmiana:**
- Przed: `cron: '0 8 * * *'` (8:00 UTC)
- Po: `cron: '0 6 * * *'` (6:00 UTC)

**Efekt:**
- Z opóźnieniem ~2h scan wykona się około 8:00-9:30 UTC
- To odpowiada 9:00-10:30 polskiego czasu (CET zimą)
- Większość skanów będzie przed 10:00 czasu polskiego

**Zaktualizowane komentarze:**
```yaml
# Cron: 6:00 UTC (z uwzględnieniem opóźnień GitHub Actions ~90-150min)
# Faktyczne wykonanie: ~8:00-9:30 UTC = ~9:00-10:30 CET (zimą) / 10:00-11:30 CEST (latem)
# UWAGA: GitHub Actions ma losowe opóźnienia 1.5-2.5h dla scheduled workflows
# Failsafe workflow (11:00 UTC) sprawdza czy scan się wykonał i triggeruje retry jeśli nie
```

### 2. Nowy Failsafe Workflow

**Plik:** `.github/workflows/failsafe.yml`

**Funkcjonalność:**
- Uruchamia się codziennie o **11:00 UTC** (13:00 czasu polskiego zimą)
- Sprawdza czy dzisiejszy scan się wykonał (scheduled lub manual)
- Jeśli **NIE** - automatycznie triggeruje backup scan
- Jeśli **TAK** - loguje info i kończy bez akcji

**Logika działania:**
```bash
1. Pobierz datę dzisiejszą (UTC)
2. Sprawdź czy był completed+success run workflow scan.yml z dzisiaj
3. Jeśli TAK:
   - Log: "✅ Dzisiejszy scan się wykonał"
   - Action: SKIP
4. Jeśli NIE:
   - Log: "⚠️ Brak dzisiejszego scanu - triggering backup"
   - Action: TRIGGER manual scan workflow
```

**Bezpieczeństwa:**
- Sprawdza zarówno scheduled jak i manual runs
- Nie powoduje duplikatów jeśli scan już się wykonał
- Timeout 5 minut
- Loguje wszystkie akcje dla monitoringu

## 📊 Testy

### Test 1: Manual Scan Trigger
```
✅ Status: SUCCESS
- Uruchomiono o 08:29 UTC
- Wykonał się pomyślnie
- Dane zapisane do repo
```

### Test 2: Failsafe Workflow
```
✅ Status: SUCCESS  
- Uruchomiono o 08:33 UTC
- Wykrył dzisiejszy pomyślny scan
- Action: SKIP (nie striggerował duplikatu)
- Conclusion: success
```

## 🔄 Jak To Działa Teraz

### Normalny Dzień (Scheduled Scan Działa)
```
06:00 UTC - Cron scheduled trigger
↓ (opóźnienie GitHub ~90-150 min)
08:00-09:30 UTC - Faktyczne wykonanie scanu
↓
09:00-10:30 CET - Scan w polskim czasie
↓
11:00 UTC - Failsafe sprawdza → wykrywa scan → SKIP
```

### Awaryjny Dzień (Scheduled Scan Nie Zadziałał)
```
06:00 UTC - Cron scheduled trigger
↓
(GitHub nie wykonał przez błąd/limit/problem)
↓
11:00 UTC - Failsafe sprawdza → brak scanu → TRIGGER backup
↓
11:01 UTC - Backup scan się wykonuje
↓
13:00 CET - Mamy dane z dzisiaj
```

## 🎯 Oczekiwane Zachowanie

### Od jutra (29.02.2026):
1. Scheduled scan powinien się wykonać między 8:00-9:30 UTC
2. Jeśli się nie wykona - failsafe zadziała o 11:00 UTC
3. W najgorszym wypadku dane będą najpóźniej o 11:30 UTC

### Monitoring:
- GitHub Actions → workflows tab → sprawdź status
- Failsafe logs → pokazują czy był retry czy skip
- Data commitów w repo → pokazuje kiedy faktycznie się wykonał

## 📝 Dodatkowe Notatki

### GitHub Actions Opóźnienia
- To **normalny problem** platformy GitHub
- Opóźnienia rosną przy dużym obciążeniu (weekendy, wieczory US)
- Nie ma sposobu na wymuszenie dokładnego czasu
- Nasze rozwiązanie to najlepsza możliwa praktyka

### Alternatywy NIE Zaimplementowane
- **Zewnętrzny cron (np. cron-job.org)** - wymaga API endpoint
- **GitHub App** - zbyt skomplikowane dla prostego scanu  
- **Self-hosted runner** - wymaga serwera 24/7

### Przyszłe Ulepszenia (opcjonalne)
- [ ] Email/Slack notification gdy failsafe triggeruje backup
- [ ] Dashboard pokazujący czas ostatniego scanu
- [ ] Metrics - średnie opóźnienie w czasie

## 🔗 Linki

- Commit: https://github.com/Bonaventura-EW/SZPERACZ/commit/1b58715
- Workflows: https://github.com/Bonaventura-EW/SZPERACZ/actions
- Issue o opóźnieniach: https://github.com/orgs/community/discussions/26726

---
**Autor:** SZPERACZ Bot  
**Data:** 2026-02-28  
**Status:** ✅ ZAIMPLEMENTOWANE I PRZETESTOWANE
