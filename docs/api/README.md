# SZPERACZ OLX — API dla aplikacji mobilnej

**Base URL:** `https://bonaventura-ew.github.io/SZPERACZ/api`

Statyczne JSON serwowane przez GitHub Pages. Brak autentykacji. Dane aktualizowane codziennie ~09:00 CET.

---

## Endpointy

| Endpoint | Opis |
|---|---|
| `GET /status.json` | Aktualny status ostatniego skanu |
| `GET /history.json` | 3 ostatnie skany (`scans`) + pole `recent` (te same 3, od najnowszego) |

> ⚠️ Dodaj cache-bust do URL: `?t={timestamp_ms}`

---

## status.json

```json
{
  "status": "success",
  "message": "Skan 7 profili zakończony pomyślnie",
  "alerts": [],
  "lastScan": {
    "timestamp":        "2026-04-30T09:23:08Z",
    "duration_seconds": 94,
    "profiles_scanned": 7,
    "total_listings":   449,
    "added":            12,
    "removed":          8,
    "new_listings":     12,
    "price_changes":    3,
    "errors":           []
  },
  "nextScan": {
    "scheduled":  "2026-05-01T07:00:00Z",
    "in_seconds": 77811
  },
  "profiles": {
    "wszystkie_pokoje": {
      "label":             "Wszystkie pokoje w Lublinie",
      "count":             380,
      "added":             11,
      "removed":           7,
      "new_listings":      11,
      "price_changes":     0,
      "crosscheck":        "passed",
      "crosscheck_detail": "scraped=380, header=380",
      "duration_seconds":  74,
      "ok":                true,
      "error":             null
    }
  }
}
```

### Wartości `status`

| Wartość | Znaczenie |
|---|---|
| `success` | Wszystkie profile OK |
| `warning` | Scan przeszedł, ale wykryto poważną anomalię (patrz `alerts`) |
| `partial_failure` | Część profili z błędem |
| `failure` | Błąd krytyczny — zero danych |

### Pole `alerts`

Lista anomalii wykrytych w ostatnim scanie (pusta, gdy wszystko OK). Typy:

| `type` | Znaczenie |
|---|---|
| `mass_removal` | Z profilu zniknęło ≥30% (i ≥10 szt.) ogłoszeń w ciągu doby — możliwy poważny błąd skanu |
| `header_shortfall` | Pobrano <50% ogłoszeń deklarowanych w nagłówku OLX — dane profilu NIE zostały zaktualizowane (ochrona) |
| `stale_listings` | Ogłoszenia nieobecne w wynikach od ≥5 skanów, a wciąż uznawane za aktywne — możliwa zmiana komunikatu OLX o nieaktualności |

Każdy alert ma pola: `profile`, `type`, `severity` (`critical` lub `warning`), `message` (opis po polsku)
oraz liczby zależne od typu (`removed`/`previous_count`/`count`/`header_count`/`stale_count`/`max_missed_scans`).

```json
"alerts": [{
  "profile": "wszystkie_pokoje",
  "type": "mass_removal",
  "severity": "critical",
  "message": "⚠️ POWAŻNA ANOMALIA: z profilu „Wszystkie pokoje w Lublinie” zniknęło 595 z 640 ogłoszeń (93%) w ciągu doby — możliwy błąd skanu/blokada OLX.",
  "removed": 595,
  "previous_count": 640,
  "count": 652
}]
```

### Wartości `crosscheck` (per profil)

| Wartość | Znaczenie |
|---|---|
| `passed` | Wynik zgodny z nagłówkiem OLX ✓ |
| `passed_retry` | OK po drugiej próbie ✓ |
| `consistent` | Dwie próby dały ten sam wynik ✓ |
| `best_of_two` | Wybrano lepszy z dwóch (rozbieżność) |
| `error` | Wyjątek podczas scrapowania ✗ |

---

## history.json

```json
{
  "last_updated": "2026-04-30T09:23:08Z",

  "recent": [
    {
      "timestamp":        "2026-04-30T09:23:08Z",
      "date":             "2026-04-30",
      "status":           "success",
      "message":          "Skan 7 profili zakończony pomyślnie",
      "duration_seconds": 94,
      "total_listings":   449,
      "added":            12,
      "removed":          8,
      "new_listings":     12,
      "price_changes":    3,
      "profiles_scanned": 7,
      "errors":           [],
      "profiles": {
        "wszystkie_pokoje": {
          "label":        "Wszystkie pokoje w Lublinie",
          "count":        380,
          "added":        11,
          "removed":      7,
          "new_listings": 11,
          "price_changes": 0,
          "crosscheck":   "passed",
          "ok":           true,
          "error":        null
        }
      }
    }
  ],

  "scans": [ /* 3 ostatnie skany, od najstarszego */ ]
}
```

`scans` — 3 ostatnie skany (od najstarszego). `recent` — te same 3, od najnowszego (wygodne do UI).

### Pola `added` / `removed`

- **`added`** — ile ogłoszeń **przybyło** względem poprzedniego skanu.
- **`removed`** — ile ogłoszeń **zniknęło** względem poprzedniego skanu.
- `null` = nie dało się policzyć (pierwszy skan profilu lub skan pominięty przez błąd) — to **nie** znaczy 0.
- `new_listings` = alias `added` (zostaje dla zgodności wstecznej).

---

## Monitorowane profile

| Klucz JSON | Label |
|---|---|
| `wszystkie_pokoje` | Wszystkie pokoje w Lublinie |
| `pokojewlublinie` | pokojewlublinie |
| `poqui` | poqui |
| `artymiuk` | artymiuk |
| `dawny_patron` | dawny patron |
| `mzuri` | mzuri |
| `villahome` | villahome |

---

## Polling

- **Co 15 minut** gdy app aktywna
- **onResume** — przy powrocie z tła
- Scan dzienny: **09:00 CET** (07:00 UTC), trwa ~60–180s
- GitHub Pages cache propagacja: ~30–60s po skanie
