# SZPERACZ OLX API

REST API dla aplikacji mobilnej monitorującej status skanów OLX.

## Base URL

```
https://bonaventura-ew.github.io/SZPERACZ/api
```

## Endpoints

### GET /status.json

Aktualny status ostatniego skanu.

**Response:**
```json
{
  "status": "success",
  "message": "Skan 7 profili zakończony pomyślnie",
  "lastScan": {
    "timestamp": "2025-03-07T08:00:00Z",
    "duration_seconds": 145,
    "profiles_scanned": 7,
    "total_listings": 847,
    "new_listings": 12,
    "price_changes": 3
  },
  "nextScan": {
    "scheduled": "2025-03-08T07:00:00Z",
    "in_seconds": 82800
  },
  "profiles": {
    "wszystkie_pokoje": {
      "label": "Wszystkie pokoje w Lublinie",
      "count": 523,
      "crosscheck": "passed"
    }
  }
}
```

### GET /history.json

Historia skanów z ostatnich 30 dni.

**Response:**
```json
{
  "last_updated": "2025-03-07T08:00:00Z",
  "scans": [
    {
      "timestamp": "2025-03-07T08:00:00Z",
      "date": "2025-03-07",
      "status": "success",
      "total_listings": 847,
      "profiles_scanned": 7,
      "duration_seconds": 145
    }
  ]
}
```

## Status Values

| Status | Opis |
|--------|------|
| `success` | Wszystkie profile zeskanowane poprawnie |
| `partial_failure` | Niektóre profile miały błędy |
| `failure` | Skan całkowicie nie powiódł się |

## Crosscheck Values

| Crosscheck | Opis |
|------------|------|
| `passed` | Dane zweryfikowane poprawnie |
| `passed_retry` | Poprawne po ponownej próbie |
| `consistent` | Spójne wyniki między próbami |
| `best_of_two` | Wybrano lepszy z dwóch wyników |
| `error` | Błąd podczas skanowania |

## OpenAPI Specification

Pełna specyfikacja OpenAPI 3.0 dostępna pod:
```
https://bonaventura-ew.github.io/SZPERACZ/api/openapi.yaml
```

## Flutter/Dart Example

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class SzperaczApi {
  static const baseUrl = 'https://bonaventura-ew.github.io/SZPERACZ/api';

  Future<Map<String, dynamic>> getStatus() async {
    final response = await http.get(Uri.parse('$baseUrl/status.json'));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    }
    throw Exception('Failed to load status');
  }

  Future<Map<String, dynamic>> getHistory() async {
    final response = await http.get(Uri.parse('$baseUrl/history.json'));
    if (response.statusCode == 200) {
      return json.decode(response.body);
    }
    throw Exception('Failed to load history');
  }
}
```

## Update Schedule

Dane aktualizowane są codziennie około **9:00 CET** (7:00 UTC + opóźnienia GitHub Actions).

## CORS

API jest serwowane przez GitHub Pages, które wspiera CORS dla wszystkich domen.
