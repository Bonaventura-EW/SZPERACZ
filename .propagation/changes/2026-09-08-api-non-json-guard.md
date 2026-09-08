---
id: 2026-09-08-api-non-json-guard
repo: Bonaventura-EW/SZPERACZ
family: szperacze
date: 2026-09-08
category: bugfix
what: Odpowiedź 2xx bez JSON-a z API OLX jest teraz jawną awarią pobierania (retry na świeżym połączeniu, potem wyjątek), a nie cicho zaksięgowanym „profilem z zerem ogłoszeń".
why: Przejściowa (~24 min) czkawka OLX 2026-09-08 wyzerowała naraz wszystkie 9 profili scrapowanych przez API — `except: break` w pętli stronicowania zamieniał `JSONDecodeError` w count=0, bez ponowienia i bez śladu w logu, co właściwie przyszło z serwera. Kosztowało to dobę danych dla 9 profili mimo że sam OLX odpowiadał poprawnie 24 minuty później.
how: Nowe `_api_get_json()` skupia pobranie strony API w jednym miejscu: loguje status/content-type/content-encoding/rozmiar/początek ciała, ponawia 3 razy z backoffem i podnosi `OlxApiError`, gdy się nie uda. Każde ponowienie poprzedza `OlxSession.reset_connections()` (zrzut puli keep-alive), bo wszystkie profile dzielą jedną sesję, a odpowiedzi przychodziły w ~7 ms — szybciej niż round-trip, czyli sygnatura zatrutego połączenia z puli. Wyjątek leci też przy błędzie na dalszych stronach: wynik częściowy dawałby zaniżony `count` przy crosschecku wyglądającym na poprawny. Wyżej nic nie trzeba było zmieniać — profil dostaje `crosscheck="error"`, co już uruchamia ochronę danych i alert.
surface: scraper.py, diag_olx_tls.py, CLAUDE.md, CHANGELOG.md
generality: family
propagate: yes
commit: 8722ab444042c8c24bc2a049d4c9c6bdfb9b483a
---

# Kontekst dla brata-ewaluatora

## Kiedy Cię to dotyczy
Jeśli scrapujesz JSON-owe API (OLX czy inne) i gdziekolwiek masz kształt:

```python
try:
    data = r.json()
except Exception as e:
    log.error(...)
    break          # ← tu ginie różnica między „pusto" a „awaria"
```

to masz tę samą lukę. Pusty wynik i nieudane pobranie wyglądają wtedy identycznie dla
całej reszty pipeline'u.

## Dlaczego to nie jest to samo, co blokada 403 z sierpnia
Warto rozróżnić dwie awarie, bo mają różne sygnatury i różne miejsca obrony:

| | 2026-08-12 (JA3) | 2026-09-08 (nie-JSON) |
|---|---|---|
| status HTTP | 403 | **< 400** |
| rotacja odcisku TLS | odpala się | **nie odpala** (reaguje tylko na 403) |
| czas trwania | 13 skanów | ~24 minuty |
| co widział pipeline | 0 ogłoszeń | 0 ogłoszeń |

Obrona zbudowana pod pierwszą awarię (rotacja przy 403 + wyjątek, gdy padną wszystkie
profile) **nie łapie** drugiej. Jeśli u siebie masz tylko obronę „przy 403", sprawdź, co
robi Twój kod, gdy serwer odda 200 z HTML-em zamiast JSON-a.

## Rzecz, którą łatwo przeoczyć: czas odpowiedzi jako dowód
Pierwsze zapytanie trwało 258 ms, wszystkie kolejne — po ~7 ms. Round-trip z runnera do
OLX tyle nie trwa, więc te odpowiedzi nie mogły przyjść z sieci. Wszystkie 9 profili szło
po **jednej** cache'owanej sesji, więc samo ponowienie na tym samym połączeniu powtórzyłoby
błąd. Stąd `reset_connections()` przed retry, a nie tylko `sleep + retry`. Jeśli cache'ujesz
sesje HTTP (a przy `curl_cffi` warto, bo handshake jest drogi), potrzebujesz sposobu na ich
zrzucenie.

## Świadomie NIE zrobione
- **Auto-fallback na Playwrighta dla profili przy awarii API.** Kusi (kategoria działała
  przez cały incydent), ale to drugi silnik na ścieżce krytycznej i ryzyko, że awaria
  przestanie być widoczna. Przy retry + jawnym błędzie ochrona danych wystarcza.
- **Podbicie liczby prób powyżej 3.** Skan i tak jest codzienny, a przy trwałej blokadzie
  długie ponawianie tylko wydłuża run i zwiększa szansę na rate-limit.
- **Backdating / doszacowanie brakującej doby.** W tym repo obowiązuje zasada „nie zgaduj
  danych, których nie pobrałeś" — dziura w `daily_counts` jest uczciwsza niż interpolacja.

## Osobna, drobna lekcja: diagnostyka też gnije
Skrypt diagnostyczny miał zaszyte na stałe dwa linki („żywe" i „martwe" ogłoszenie).
Link „żywy" trafił do archiwum 2 tygodnie po napisaniu skryptu i od tamtej pory każda
diagnostyka kończyła się fałszywym ❌ oraz werdyktem „wdrażać wybiórczo" — czyli narzędzie,
po które sięgasz w kryzysie, kłamało. Teraz dobiera oba ogłoszenia z danych ostatniego skanu.
Jeśli masz podobny skrypt z zaszytym URL-em produkcyjnym, sprawdź, czy jeszcze żyje.
