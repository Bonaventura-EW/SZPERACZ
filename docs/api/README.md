# SZPERACZ OLX — API dla aplikacji mobilnej

**Base URL:** `https://bonaventura-ew.github.io/SZPERACZ/api`

Statyczne JSON serwowane przez GitHub Pages. Brak autentykacji. Dane aktualizowane codziennie ~09:00 CET.

---

## Endpointy

| Endpoint | Opis |
|---|---|
| `GET /status.json` | Aktualny status ostatniego skanu |
| `GET /history.json` | Historia 30 skanów + pole `recent` (3 najnowsze) |

> ⚠️ Dodaj cache-bust do URL: `?t={timestamp_ms}`

---

## status.json

```json
{
  "status": "success",
  "message": "Skan 7 profili zakończony pomyślnie",
  "lastScan": {
    "timestamp":        "2026-04-30T09:23:08Z",
    "duration_seconds": 94,
    "profiles_scanned": 7,
    "total_listings":   449,
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
| `partial_failure` | Część profili z błędem |
| `failure` | Błąd krytyczny — zero danych |

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
      "new_listings":     12,
      "price_changes":    3,
      "profiles_scanned": 7,
      "errors":           [],
      "profiles": {
        "wszystkie_pokoje": {
          "label":        "Wszystkie pokoje w Lublinie",
          "count":        380,
          "new_listings": 11,
          "price_changes": 0,
          "crosscheck":   "passed",
          "ok":           true,
          "error":        null
        }
      }
    }
  ],

  "scans": [ /* pełna historia do 30 wpisów, od najstarszego */ ]
}
```

`recent` — tablica 3 najnowszych skanów (od najnowszego). Używaj tego w UI.

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
