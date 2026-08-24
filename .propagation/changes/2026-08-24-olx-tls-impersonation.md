---
id: 2026-08-24-olx-tls-impersonation
repo: Bonaventura-EW/SZPERACZ
family: szperacze
date: 2026-08-24
category: bugfix
what: Podmiana warstwy HTTP do OLX z `requests` na `curl_cffi` z impersonacją TLS, bo OLX zaczął blokować po odcisku JA3.
why: Od 2026-08-12 OLX (CloudFront) zwraca 403 na KAŻDE zapytanie z `requests` — 9 profili scrapowanych przez API zwracało 0 ogłoszeń, a weryfikacja ogłoszeń wpadała w fail-safe „zakładam aktywne", przez co archiwizacja stanęła całkowicie na 13 skanów.
how: Fabryki sesji (`get_session`/`get_api_session`) budują `OlxSession` opartą na `curl_cffi.requests.Session(impersonate=...)`; wywołania wyżej zostają nietknięte, bo łapią `except Exception`, a nie typy z `requests`. `OlxSession` ponawia 429/5xx i błędy transportu, przy 403 rotuje profil impersonacji, a gdy padną wszystkie — podnosi wyjątek zamiast zwrócić cichą 403. Dołożone alerty (`profile_empty`, `ok:false` przy count==0 mimo znanego stanu) i telemetria odcisku w status.json.
surface: scraper.py, requirements.txt, diag_olx_tls.py, .github/workflows/diag_olx_tls.yml
generality: family
propagate: yes
commit: c5e22d2ace7d65b00f9bb6435a2c16094286695b
---

# Kontekst dla brata-ewaluatora

## To jest pilne, jeśli scrapujesz OLX
Blokada jest po stronie OLX i dotyczy **każdego** klienta z pythonowym odciskiem TLS.
Jeśli Twój scraper używa `requests`/`httpx` do olx.pl, prawie na pewno masz ten sam
problem — sprawdź, czy Twoje profile nie zwracają zer i czy archiwizacja jeszcze działa.

## Co zostało zmierzone (a nie zgadnięte)
Eksperyment kontrolny, **ten sam IP egress**, zmieniana tylko warstwa klienta:

| Klient | Wynik |
|---|---|
| `requests` + pełny zestaw nagłówków przeglądarki | 403 |
| `httpx` z HTTP/2 | 403 |
| `httpx` HTTP/1.1 | 403 |
| `curl_cffi` z `impersonate` | **200** |

Wnioski: nagłówki nie są zmienną decydującą, HTTP/2 też nie. Zostaje odcisk TLS.
Na runnerze GitHub Actions **wszystkie 12** sprawdzonych profili impersonacji dało 200,
więc reputacja IP zakresów Azure też nie jest czynnikiem.

## Odrzucone alternatywy
- **Same nagłówki** (darmowe, bez zależności) — zmierzone, nie działa.
- **Przepisanie profili na Playwrighta** (zero nowych zależności; u nas i tak renderuje
  kategorię) — działa, ale nawigacja przeglądarki na każde z ~380 weryfikowanych ogłoszeń
  jest nieporównywalnie wolniejsza od GET-a. Sensowne jako plan B, gdyby impersonacja padła.
- **Rezygnacja z Playwrighta na rzecz `curl_cffi` także dla kategorii** — sprawdzone, że
  działa (200, komplet kart), ale świadomie NIE zrobione: to przepisywanie działającej
  ścieżki i utrata jedynego kanału, który podczas awarii **nie** był zablokowany.

## Pułapki przy adaptacji
1. **Nie nadpisuj User-Agenta.** `curl_cffi` ustawia komplet nagłówków spójny z podszywaną
   przeglądarką. Doklejenie własnego UA (np. Chrome'owego przy TLS Safari) tworzy dokładnie
   tę niespójność, której szukają WAF-y. U nas oznaczało to porzucenie starej listy
   `USER_AGENTS` w sesjach HTTP (została tylko dla Playwrighta).
2. **404/410 nie są awarią.** Jeśli, tak jak my, używasz statusu HTTP do wykrywania zdjętych
   ogłoszeń — te statusy muszą wracać BEZ ponawiania i bez rotacji profilu.
3. **`curl_cffi` nie ma `HTTPAdapter`/`Retry` z urllib3.** Ponawianie trzeba napisać
   samemu (u nas w `OlxSession.get`).
4. **Cache'uj sesje.** Jeśli Twój odpowiednik `verify_listing_active()` woła fabrykę sesji
   per ogłoszenie, budowanie sesji `curl_cffi` za każdym razem kosztuje pełny handshake TLS.
5. **Nazwy profili impersonacji są wersjonowane** (`chrome131`, `safari18_0`…) i znikają
   między wydaniami `curl_cffi`. Stąd cap `<1` i lista fallbacków zamiast jednej wartości.

## Osobna lekcja: monitoring, nie tylko fix
Awaria przez 11 skanów raportowała status `success`, bo ochrona „count==0 nie nadpisuje
danych" działała poprawnie — dane były bezpieczne, więc nic nie krzyczało. Jeśli masz taką
samą ochronę, prawdopodobnie masz też tę samą ślepą plamkę. Warto dołożyć alert na
„źródło zwróciło 0, choć mamy dla niego niepusty stan" — to sygnał od pierwszego dnia,
podczas gdy liczniki typu `missed_scans` odpalają dopiero po tygodniach.
