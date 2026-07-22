# 📋 CHANGELOG

Wszystkie istotne zmiany w projekcie SZPERACZ OLX są dokumentowane w tym pliku.

Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.0.0/).

---

## [Unreleased]

### Planowane
- Integracja z Telegram Bot

---

## [2026-07-22] - 🔧 Doprecyzowanie alertu `stale_listings`

### Changed 🔧
- **Podniesiono próg alertu `stale_listings` z 5 na 12 skanów** (`STALE_MISSED_SCANS_MIN`
  w `scraper.py`). Powód: przy progu 5 sama **rotacja wyników OLX** (żywe ogłoszenie
  chwilowo poza wynikami skanu, ale potwierdzone jako aktywne przez `verify_listing_active()`)
  generowała fałszywe alarmy prawie codziennie — alert nie odróżnia „ogłoszenie martwe, verify
  daje false positive" od „ogłoszenie żywe, tylko rotuje poza wynikami". Skan z 2026-07-22
  odpalił alert dla 16 ogłoszeń `wszystkie_pokoje` przy `max_missed=5`, mimo że skan był poprawny
  (crosscheck passed, scraped=753/header=760). Próg 12 (~2 tyg.) reaguje dopiero, gdy nieobecność
  jest zbyt długa, by tłumaczyć ją rotacją.

### Added ✨
- Alert `stale_listings` w `status.json` niesie nowe pole **`stale_items`** — lista do 10
  podejrzanych ogłoszeń (od najdłużej nieobecnych) z `id`, `url`, `title`, `missed_scans`.
  Dzięki temu alert jest działający: można otworzyć URL i w kilka sekund sprawdzić na oko,
  czy ogłoszenie faktycznie żyje, czy `verify_listing_active()` daje false positive.

### Uwagi
- Linki `stale_items` trafiają na razie tylko do API (`status.json`); baner na dashboardzie
  (`index.html`/`scans.html`) pokazuje wciąż sam tekst `message`. Ewentualne renderowanie
  klikalnych linków na banerze to osobna, opcjonalna zmiana.

---

## [2026-07-20] - ➕ Nowy monitorowany profil: MyRent

### Added ✨
- Dodano profil **MyRent** do `PROFILES` w `scraper.py`
  (klucz `myrent`, `is_category: False`).
  - URL: https://www.olx.pl/oferty/uzytkownik/56DT9/
  - `uuid` do API OLX: `a17ed560-8913-4f97-9c67-0ebb5c2041c0`
    (odczytany z HTML profilu, potwierdzony zapytaniem `api/v1/offers?user_id=...` —
    zwraca ogłoszenia tego profilu).
- Zaktualizowano listę profili w §5 `CLAUDE.md`.

### Uwagi
- Profil będzie scrapowany od najbliższego skanu przez OLX REST API (jak pozostałe
  profile użytkowników). Pierwszy skan zapisze go do `dashboard_data.json`, ledgera
  i API dashboardu — historia zacznie się od dnia pierwszego skanu.

---

## [2026-07-19] - 🔍 Wzmocnienie weryfikacji aktywności ogłoszeń (verify_listing_active)

### Problem
1. **Fraza `"404"` w `INACTIVE_PHRASES` groziła fałszywą archiwizacją.** Była dopasowywana
   jako substring do CAŁEGO surowego HTML-a strony ogłoszenia — wystarczyło, że ciąg „404"
   wystąpił w ID ogłoszenia, hashu obrazka czy cenie, a aktywne ogłoszenie było uznawane za
   nieaktywne i archiwizowane. Status HTTP 404 i tak jest sprawdzany osobno po `resp.status_code`.
2. **Frazy nieaktywności szukane w surowym HTML** — w blobie JSON-a (`__PRERENDERED_STATE__`)
   komunikaty szablonu (np. „oferta wygasła") mogą siedzieć także na aktywnych stronach.
3. **Brak sygnału, gdy OLX zmieni komunikat o nieaktualności** — martwe ogłoszenia wisiałyby
   wtedy w `current_listings` w nieskończoność z rosnącym `missed_scans`, bez ostrzeżenia.
4. **Seria weryfikacyjnych GET-ów bez pauzy** mogła prowokować blokadę OLX i zafałszować
   kolejne sprawdzenia w tej samej pętli.

### Fixed 🐛
- **`scraper.py` — `verify_listing_active()`**: usunięto `"404"` z listy fraz (status 404
  obsługuje `resp.status_code`); frazy dopasowywane do widocznego tekstu strony
  (`BeautifulSoup(...).get_text()`), nie do surowego HTML-a.

### Added ✨
- **`scraper.py` — `generate_api_json()`**: nowy alert **`stale_listings`** (severity
  `warning`) w `docs/api/status.json`, gdy w profilu jest ogłoszenie z
  `missed_scans >= 5` (`STALE_MISSED_SCANS_MIN`) — sygnał, że `verify_listing_active()`
  mogła przestać wykrywać martwe ogłoszenia (np. OLX zmienił komunikat). Dashboard
  pokazuje go istniejącym banerem alertów (bez zmian we frontendzie). Świadomie BEZ
  automatycznej archiwizacji po N skanach — zasada „nie kasuj przy wątpliwości" zostaje.
- **`scraper.py` — pętla `carried_ids`**: pauza 0,7 s między weryfikacyjnymi GET-ami.
- Dokumentacja API (`docs/api/README.md`, `JAK_DZIALA_API.txt`, `openapi.yaml`): opis
  nowego typu alertu i pól `stale_count`/`max_missed_scans`.

### Weryfikacja ✅
- Testy z zamockowanym HTTP: 7/7 PASS — m.in. „404" w HTML aktywnej strony ≠ nieaktywne,
  fraza w `<script>` ≠ nieaktywne, fraza w widocznym tekście = nieaktywne, HTTP 404 =
  nieaktywne, HTTP 403/wyjątek sieciowy = fail-safe „aktywne".
- Smoke test `generate_api_json()`: profil z `missed_scans=6` → status `warning`
  + alert `stale_listings` (`stale_count=1`, `max_missed_scans=6`).

---

## [2026-07-18] - 🕳️ Naprawa cichego gubienia ogłoszeń przy rotacji wyników OLX

### Problem
Gdy ogłoszenia nie było w skanie, ale `verify_listing_active()` potwierdziło, że wciąż
istnieje na OLX, kod pomijał archiwizację — jednak `current_listings` i tak było nadpisywane
wyłącznie zeskanowanymi ogłoszeniami. Ogłoszenie znikało z danych bez śladu, a przy powrocie
do wyników liczyło się jako NOWE: traciło całą historię (refresh/reaktywacje/ceny, `first_seen`)
i sztucznie zawyżało `added`; samo zniknięcie zawyżało `removed`. Tak incydent 11.07 zgubił
11 ogłoszeń.

### Fixed 🐛
- **`scraper.py` — `generate_dashboard_json()`**: weryfikacja znikniętych ogłoszeń przeniesiona
  PRZED policzenie flow (`added`/`removed`). Ogłoszenia potwierdzone jako aktywne (`carried_ids`):
  - zostają w `current_listings` (przeniesione do nowej listy z zachowaniem wszystkich pól),
  - dostają licznik **`missed_scans`** (+1 co pominięty skan; pole znika, gdy ogłoszenie
    wróci do wyników skanu — świeży rekord go nie kopiuje),
  - NIE liczą się jako `removed` (mniej fałszywych `mass_removal`), a ich późniejszy powrót
    NIE liczy się jako `added`/nowe ogłoszenie.
  Weryfikacja HTTP wykonywana jest raz na ogłoszenie na skan (pętla archiwizacji korzysta
  z wyniku `carried_ids` zamiast pytać OLX ponownie).

### Weryfikacja ✅
- Test symulacyjny (kopia danych, bez sieci): 23/23 PASS — m.in. ogłoszenie nieobecne+aktywne
  zachowane z `missed_scans=1→2`, nieobecne+nieaktywne zarchiwizowane, `removed` liczy tylko
  faktycznie zniknięte, powrót po rotacji bez utraty historii / bez `added` / bez reaktywacji.

---

## [2026-07-18] - 🔄 Naprawa liczenia odświeżeń: backfill dzienny + detekcja None→data

### Problem
1. **Dzienny licznik `refreshed_count` gubił ~54% odświeżeń.** Skan leci raz dziennie rano
   (~9:20), więc odświeżenie po godzinie skanu jest wykrywane dopiero następnego dnia —
   z wczorajszą datą `refreshed_at`. Stare liczenie brało tylko wpisy z `refreshed_at == dzisiaj`,
   więc taki event nie trafiał do żadnego dnia (wczorajszy wpis `daily_counts` był już zamknięty).
   W danych: 659 z 1220 eventów odświeżenia wykryto później niż ich data — żaden nie został
   zliczony w dziennym liczniku.
2. **Pierwsze odświeżenie ogłoszenia bez daty nigdy nie było liczone.** Warunek detekcji wymagał
   istnienia starej daty (`old_refreshed and new > old`), a w kategorii `wszystkie_pokoje`
   493/728 aktywnych ogłoszeń ma `refreshed=None` — przejście `None → data` przepadało.
   Dodatkowo `refreshed` nie było chronione przed regresją do `None` przy nieudanym parsowaniu
   (w przeciwieństwie do `published`), co kasowało punkt odniesienia dla kolejnych eventów.

### Changed 🔧
- **`scraper.py` — `recompute_daily_refresh_reactivation()`** (nowa funkcja) — po każdym skanie
  `refreshed_count`/`reactivated_count` we WSZYSTKICH wpisach `daily_counts` przeliczane są jako
  projekcja historii ogłoszeń (`refresh_history`/`reactivation_history`, current + archived).
  Event wykryty z opóźnieniem trafia do właściwego dnia wstecz (backfill). Event z datą bez wpisu
  w `daily_counts` (dzień bez skanu) doliczany jest do najbliższego późniejszego wpisu. Liczniki
  są **tylko podnoszone** (max ze starej i przeliczonej wartości) — historie bywają tracone przez
  bug cichego gubienia ogłoszeń (CLAUDE.md §7), więc czysta projekcja zerowałaby prawdziwe stare dni.
  Zastępuje stare liczenie „tylko eventy z dzisiaj" w `generate_dashboard_json()`.
- **`scraper.py` — detekcja odświeżenia** (obie ścieżki: aktywne + reaktywacja z archiwum):
  event liczony także przy przejściu `None → data` (deduplikacja po `refreshed_at` bez zmian);
  stara data `refreshed` (+ `last_refresh_timestamp`) zachowywana, gdy nowy skan jej nie ma.

### Added ✨
- **`rebuild_refresh_daily_backfill.py`** — jednorazowe (idempotentne) przeliczenie
  `daily_counts` z historii przez nową projekcję. Uruchomiony 2026-07-18: podniósł 66 wpisów
  (np. `wszystkie_pokoje` 14.07: 11→45, 13.07: 14→43), żadnego nie obniżył.

### Weryfikacja ✅
- Test symulacyjny (kopia danych, bez sieci): 11/11 scenariuszy PASS — None→data, regresja daty,
  backfill do wczoraj, deduplikacja przy drugim skanie dnia.
- Po rebuildzie: 0 wpisów `daily_counts` poniżej projekcji z historii; drugi run skryptu = 0 zmian.

---

## [2026-07-11] - 🚨 Alerty anomalii w API + ochrona przed skanem częściowym

### Incydent
Poranny skan 11.07 (08:54 UTC) pobrał dla `wszystkie_pokoje` tylko **50 z 650** ogłoszeń
(crosscheck `best_of_two`: `1st=50, 2nd=50, header=650`), mimo to został potraktowany jako
poprawny (`ok: true`) i **zarchiwizował 595 istniejących ogłoszeń** (`verify_listing_active()`
przy blokadzie OLX również dała false positives). Wieczorny skan (18:02 UTC) je „reaktywował"
(`added=607`). Ochrona danych działała dotąd tylko przy `crosscheck=error` lub `count==0`.

### Added ✨
- **`scraper.py` — `is_header_shortfall()`** (+ `HEADER_SHORTFALL_RATIO = 0.5`) — skan, który
  pobrał <50% ogłoszeń deklarowanych w nagłówku strony OLX, jest teraz traktowany jak błąd
  scrapera we WSZYSTKICH miejscach ochrony danych: `generate_dashboard_json()` (bez archiwizacji
  i nadpisania `current_listings`, bez wpisu `daily_counts`), `append_history()` (bez wpisu do
  ledgera) oraz `generate_api_json()` (profil `ok:false`, status `partial_failure`).
- **`scraper.py` — `generate_api_json()`: pole `alerts` + status `warning`** w
  `docs/api/status.json` i `history.json`. Typy alertów (severity `critical`):
  - `mass_removal` — z profilu zniknęło ≥30% (`MASS_REMOVAL_RATIO`) i ≥10 szt.
    (`MASS_REMOVAL_MIN`) ogłoszeń względem poprzedniego dnia (`daily_counts`),
  - `header_shortfall` — częściowy scrape jak wyżej (dane profilu nie zostały zaktualizowane).
  Gdy są alerty a nie ma błędów, globalny `status` = `"warning"`. Alerty logowane jako WARNING.
- **Dashboard (`docs/index.html`) i `docs/scans.html`** — czerwony baner z treścią alertów
  z `status.json` (na dashboardzie best-effort fetch, nie blokuje renderu); w tabeli historii
  skanów nowy badge „⚠ anomalia" (status `warning`) + tooltip z treścią alertu.
- Dokumentacja API: `docs/api/README.md`, `JAK_DZIALA_API.txt`, `openapi.yaml` (pole `alerts`,
  status `warning`).

### Changed 🔧
- **`docs/api/status.json` / `history.json`** — retroaktywnie oznaczono skany z 11.07:
  poranny (08:54) → `partial_failure` + alert `header_shortfall`; wieczorny (18:02) →
  `warning` + alert `mass_removal` (595 z 640 ogłoszeń, 93%).

### Fixed 🐛 — czyszczenie danych po incydencie (`rebuild_incident_20260711.py`)
Jednorazowy, idempotentny skrypt (baseline = stan po skanie 10.07, commit `e1dfdc7`)
naprawił skutki uboczne incydentu w `data/dashboard_data.json` i `docs/api/*.json`:
- usunięto **572 fałszywe wpisy** `reactivation_history` (sygnatura `active_to ==
  2026-07-11 08:54:05`) + przywrócono `reactivated`/`reactivation_count`; zachowano
  1 prawdziwą reaktywację z 11.07 (`17jKAL`, zarchiwizowane 06.07),
- cofnięto **12 artefaktów sesji promocji** (ogłoszenia promowane 10.07 i 11.07, którym
  fałszywa archiwizacja zamknęła sesję i otworzyła nową: sessions+1, days reset → przywrócono
  sesje/historię, days = stare+1),
- przywrócono historię `1b1ruw` (wieczorny skan potraktował je jako NOWE: first_seen/
  first_price/refresh_history wyzerowane → przywrócone + doliczony refresh z 11.07),
- **10 zgubionych ogłoszeń** wróciło do archiwum z `archived_date = 2026-07-11 18:02:51`
  (mechanizm zguby: rano `verify_listing_active()` uznała je za aktywne → pominięto
  archiwizację, ale `current_listings` i tak nadpisano 50 zeskanowanymi → wypadły bez śladu),
- `daily_counts` 2026-07-11: `added 607→34`, `removed 595→22` (realny ruch doby),
  `reactivated_count 573→1`, `refreshed_count 20→21`; poprawiono też `scan_history`
  i `docs/api/status.json`/`history.json` (globalnie added 611→38, removed 596→23).
  **Alerty o incydencie w API zostają** — dokumentują zdarzenie.
- Ledger NDJSON nietknięty (append-only; linia porannego skanu count=50 zostaje).

### Known issues ⚠️
- **Ciche gubienie ogłoszeń przy rotacji wyników OLX** (bug istniejący wcześniej, ujawniony
  przez incydent): gdy ogłoszenie nie wypadnie w skanie, a `verify_listing_active()` potwierdzi,
  że nadal istnieje, kod pomija archiwizację, ale i tak nadpisuje `current_listings` samymi
  zeskanowanymi → ogłoszenie znika z danych bez śladu, a przy powrocie jest liczone jako NOWE
  (traci historię). Tak zgubiono ww. 10+1 ogłoszeń. Do naprawy osobno (weryfikowane-aktywne
  powinny zostawać w `current_listings`).

---

## [2026-07-09] - ➕ Nowy profil: „stylowe pokoje-ania"

### Added ✨
- **`scraper.py` — `PROFILES`** — dodano nowy monitorowany profil użytkownika OLX
  `stylowe_pokoje_ania` (label „stylowe pokoje-ania", url
  `https://www.olx.pl/oferty/uzytkownik/1WLoW/`, `is_category: False`,
  `uuid: 6ce22f3f-2dc7-4299-99e6-3c0d7ab9df19`). UUID (user_id do REST API OLX)
  wyciągnięty ze strony profilu i zweryfikowany przez `api/v1/offers` (user „Ania",
  ogłoszenia pokoi w Lublinie / Czechów Dolny).
- Zaktualizowano listę profili w `CLAUDE.md` §5.
- Kafelek pojawi się na dashboardzie automatycznie (renderowanie jest dynamiczne po
  kluczach z `dashboard_data.json`) po pierwszym skanie obejmującym nowy profil.

---

## [2026-07-01] - 🚫 Filtr cenowych outlierów (10x średnia)

### Added ✨
- **`scraper.py` — `filter_price_outliers()`** — nowy krok w `run_scan()` (tuż po scrapowaniu,
  przed `generate_dashboard_json()`), który odrzuca ze skanu ogłoszenia z ceną
  `>= PRICE_OUTLIER_MULTIPLIER` (10) x średnia cena pozostałych ogłoszeń w danym profilu.
  Takie ogłoszenia **nigdy nie trafiają** do `dashboard_data.json`, ledgera ani API — to
  ochrona przed literówkami w cenie / ogłoszeniami-śmieciami, nie retencja danych.
  - Średnia liczona metodą **leave-one-out** (bez ceny sprawdzanego ogłoszenia) — w przeciwnym
    razie sam outlier zawyżałby własną średnią odniesienia i nigdy nie przekroczyłby progu
    (przy małej liczbie ogłoszeń jeden ekstremalny outlier potrafi podbić średnią "ze wszystkich"
    ponad własną wartość / 10).
  - Wymaga min. 3 wycenionych ogłoszeń w profilu (inaczej średnia nie ma sensu — filtr pomija).
  - Filtrowanie iteracyjne (kilka rund), na wypadek więcej niż jednego outliera na profil.
  - Odrzucone ogłoszenia logowane jako `WARNING` (tytuł, cena, url, próg).

### Fixed 🐛
- **`scraper.py` — `parse_price()`** — prawdziwa przyczyna jedynego znalezionego outliera
  (patrz niżej) NIE była literówką na OLX, tylko błędem parsera: funkcja usuwała wszystkie
  znaki niebędące cyfrą (w tym przecinek dziesiętny), więc cena z groszami typu
  `"1 260,65 zł"` zamieniała się w `126065` (10x realna wartość) zamiast `1260`. Poprawka:
  ucinamy część po `.`/`,` PRZED usunięciem separatorów, więc grosze są odrzucane, a nie
  doklejane do części całkowitej. Filtr `filter_price_outliers()` (wyżej) zostaje jako
  dodatkowa siatka bezpieczeństwa na inne, nieprzewidziane przyczyny zawyżonych cen.

### Data — usunięcie błędnego rekordu
- Ręcznie usunięto z `data/dashboard_data.json` jedyny rekord dotknięty ww. bugiem: profil
  `wszystkie_pokoje`, id `1bfXbx`, cena `126065` (przy realnej cenie ~1260 zł), "Pokój
  jednoosobowy na wynajem" — wraz z pustym wpisem w `promotion_history`. Ogłoszenie może
  wrócić przy kolejnym skanie z poprawną ceną (`first_seen` zresetuje się, bo `parse_price()`
  jest już naprawiony). `daily_counts` (median/rozkład cen) nie wymagały korekty — mediana
  z 528 nowych ogłoszeń tego dnia była odporna na ten jeden outlier.

### Fixed 🐛 (dogonienie: `price_distribution`/`count` dalej pokazywały outlier)
- Samo usunięcie rekordu z `current_listings` **nie wystarczyło** — `daily_counts[].price_distribution`
  i `count` to zamrożone snapshoty per-dzień, liczone w momencie skanu, więc dashboard
  (`ROZKŁAD CEN`) nadal pokazywał widmowy słupek ~126–130 tys. zł oraz zawyżone `count`/`ŚREDNIA`
  dla dni **2026-06-29 / 06-30 / 07-01** (te dni miały tego ogłoszenia w danych). Poprawka:
  - **2026-07-01** (dzisiejszy skan) — `price_distribution` i `count` przeliczone od zera
    z aktualnych `current_listings` (560 ogłoszeń, max realnie 2400 zł → drobne kubełki
    zamiast jednego kubełka 0–10000 zł).
  - **2026-06-29 / 06-30** (dni historyczne, bez pełnych archiwalnych cen do przeliczenia
    od zera) — przeniesiono 1 sztukę z widmowego kubełka 120 000–130 000 zł do kubełka
    0–10 000 zł (tam realnie wpadała poprawiona cena ~1260 zł) i przycięto puste kubełki na
    końcu. `count` per dzień **nie zmieniony** (ogłoszenie realnie istniało, zmieniła się
    tylko jego błędna cena).
  - `docs/api/status.json` i `docs/api/history.json` (wpis `2026-07-01`, oba w `scans` i
    `recent`) — `count`/`total_listings` dla `wszystkie_pokoje` skorygowane 561→560 / 624→623.
  - **Ledger `data/history/daily_summary.ndjson` NIE został poprawiony** (append-only, zgodnie
    z regułą projektu — nigdy nie przepisujemy istniejących linii). Jedna linia (2026-07-01,
    `count: 561`) zostaje z historycznym zawyżeniem o 1 — kosmetyczny, jednorazowy efekt
    uboczny ręcznego czyszczenia danych, bez wpływu na przyszłe skany.

### Fixed 🐛 (drugie dogonienie: 06-29/06-30 zamieniły się w jeden pełnoszerokościowy słupek)
- Powyższa "minimalna łatka" dla dni historycznych (przeniesienie 1 sztuki z widmowego kubełka
  do kubełka `0–10000`) po przycięciu pustych kubełków na końcu zostawiała **tylko jeden
  kubełek** obejmujący cały zakres — na wykresie wyglądało to jak jeden pełnoszerokościowy
  słupek zamiast histogramu (widoczne po przełączeniu suwaka „Rozkład cen" na 29.06/30.06).
  Właściwa poprawka: dla dni **2026-06-29** i **2026-06-30** zrekonstruowano pełny zestaw cen
  aktywnych tego dnia ogłoszeń (analogicznie do `backfill_price_distribution.py`: ogłoszenie
  liczy się jako aktywne gdy `first_seen <= dzień <= archived_date`, cena brana z
  `price_history` jeśli się zmieniała, inaczej z bieżącej ceny) i przeliczono
  `price_distribution` od zera tym samym algorytmem co `build_price_distribution()` w
  `scraper.py`. Usunięte ogłoszenie `1bfXbx` samo wypadło z rekonstrukcji (nie ma go już
  w `current_listings`/`archived_listings`), więc oba dni mają teraz normalny, drobnoziarnisty
  histogram (13 kubełków, 0–2600 zł), tak jak dzień 2026-07-01.

---

## [2026-06-22] - 📈 Nowa podstrona „Trend w czasie" (styl betonometr.pl)

### Added ✨
- **`docs/trend.html`** — nowa podstrona dashboardu z wykresem trendu liczby ogłoszeń w stylu
  [betonometr.pl](https://nieruchy.pro/lublin/mieszkania). Konwencja jak `scans.html`: ta sama belka
  (← Dashboard / logo / motyw), te same zmienne kolorów i fonty, **wykres rysowany na czystym canvasie
  (zero zewnętrznych bibliotek)**. Cechy:
  - wykres area z gradientem; linia bieżąca + przerywane linie i etykiety **MAX / MIN w oknie**
    oraz **wartość bieżąca** (boks przy osi Y),
  - pasek statystyk **1D / 1M / 6M / 1R** (zielony +, czerwony −, `—` gdy za mało historii),
  - **drag-to-zoom** (przeciągnij po wykresie → przybliżenie zakresu, przycisk „Reset zoom"),
  - hover z krzyżykiem i dymkiem (data + liczba ogłoszeń),
  - przełącznik profilu/kategorii (wszystkie z `PROFILES`; domyślnie „Wszystkie pokoje w Lublinie")
    + zakresy 1M / 3M / 6M / 1R / Całość, tryb jasny/ciemny.
  - Dane na żywo: `docs/api/trend_full.json` (pełna historia `count`) + etykiety z `docs/api/status.json`
    (`is_category` wyprowadzone z klucza `wszystkie_pokoje`, zgodnie z konwencją `scans.html`).
- **`docs/index.html`** — w belce głównej dodany link **„Trend"** (obok „Scan teraz").

> Uwaga (gotcha): `trend_full.json` zawiera tylko `count`/`date` (bez `label`/`is_category`) —
> etykiety profili bierzemy ze `status.json`, a kategorię rozpoznajemy po kluczu `wszystkie_pokoje`.

---

## [2026-05-31] - 🗄️ Refaktor bazy: ledger NDJSON, Excel on-demand, trend pełnej historii

### Po audycie (sprzątanie)
- **Dashboard**: kafelek kategorii `wszystkie_pokoje` zawsze pierwszy w siatce profili
  (`renderProfileCards` jawnie sortuje — niezależnie od kolejności kluczy JSON, która po `sort_keys` jest alfabetyczna).
- **#1** `rebuild_daily_flows.py` / `rebuild_archive_counters.py` / `rebuild_refresh_history.py` —
  czytają zamrożone `data/archive/szperacz_olx_archiwum_*.xlsx`, gdy live xlsx nie istnieje (nie padają).
- **#2** usunięto martwy kod: `update_excel()` i `load_or_create_workbook()` w `scraper.py` (niewywoływane)
  oraz nieużywaną stałą `EXCEL_PATH` w `email_report.py`.
- **#3** dodano `test_scraper.py` — minimalne testy czystych funkcji (`parse_price`, `extract_listing_id`,
  `parse_date_text`, `_load_daily_ledger`); 17/17. Uruchom: `python test_scraper.py` lub `pytest`.
- **deps**: `requirements.txt` — dodano górne granice `<major` (np. `playwright<2`, `lxml<7`),
  by major bump nie zepsuł scrapingu po cichu. Caps powyżej aktualnych wersji (zero zmian dziś).
- **#4** (odchudzenie `.git` przez `git filter-repo`) — **świadomie pominięte**. Refaktor zatrzymał przyrost;
  ~230 MB starej historii (54 bloby xlsx) zostaje. Backup sprzed refaktoru: gałąź `backup/pre-refactor-2026-05-31` + bundle.

Cel: zatrzymać rozrost repo (`.git` ~209 MB), bo binarny `szperacz_olx.xlsx` (~11,8 MB)
był commitowany przy KAŻDYM scanie (niedeltowalny zip). Założenie użytkownika: pełna
historia zachowana na zawsze i bezpieczna, Excel może być generowany.

### Added ✨
- **`data/history/daily_summary.ndjson`** — append-only ledger trendu (1 linia = 1 skan/profil:
  `date, time, profile, count, crosscheck, change`). Wieczny, niemutowalny zapis liczby ogłoszeń,
  niezależny od `dashboard_data.json`. Git deltuje tekst → przyrost ~KB/scan zamiast ~11 MB.
- **`data/archive/szperacz_olx_archiwum_2026-02-23_do_2026-05-30.xlsx`** — jednorazowy, zamrożony
  backup całego dotychczasowego xlsx (sha256 identyczny z oryginałem) = literalny snapshot per-skan.
- **`migrate_xlsx_to_ndjson.py`** — jednorazowa, weryfikowalna migracja (count==liczba wierszy; multiset
  xlsx == multiset ledger; 1012 linii). Idempotentny (odmawia nadpisania istniejącego ledgera).
- **`scraper.py`**:
  - `build_excel_from_data()` — generuje pełny Excel z `dashboard_data.json` + ledger (current+archiwum,
    `historia_cen` ze zdarzeń cen, `trend_dzienny` z ledgera, `podsumowanie`). Wynik ~0,18 MB vs 11,8 MB.
  - `append_history()` — append-only zapis do ledgera; ta sama ochrona „count==0/błąd scrapera nie psuje danych".
  - `generate_trend_full()` — buduje `docs/api/trend_full.json` (pełna historia `count`, 1 punkt/dzień/profil).
- **Dashboard** — przy tytule „Trend w czasie" przycisk **📅 90 dni / 🗓️ Cała historia**. Domyślnie 90 dni;
  po włączeniu metryka „Ogłoszenia" pokazuje całą historię z ledgera. Pozostałe metryki (mediana, promowane,
  przybyło/zniknęło) nie mają danych historycznych >90 dni → komunikat. Fetch `trend_full.json` best-effort.

### Changed 🔄
- **`run_scan()`** — `update_excel()` zastąpione przez `append_history()` + `generate_trend_full()`.
  Excel NIE jest już zapisywany do repo (generowany na żądanie przy raporcie tygodniowym).
- **`email_report.py`** — załącznik Excela generowany do `/tmp` przez `build_excel_from_data()`
  (fallback: jeśli zawiedzie, mail wychodzi bez załącznika).
- **`generate_dashboard_json()`** — stabilna serializacja `dashboard_data.json` (sort list ogłoszeń po `id`
  + `sort_keys`) → diff przestał być „churnem" z przestawiania kolejności (dashboard sortuje po stronie klienta).
- **`.gitignore`** — `data/szperacz_olx.xlsx` ignorowany (generowany on-demand); `data/email_preview.html` ignorowany.

### Removed 🗑️
- `data/szperacz_olx.xlsx` i `data/dashboard_data_backup_refreshed_count.json` — odpięte od trackingu
  (xlsx zachowany w `data/archive/` + w historii gita; backup-śmieć usunięty na stałe).

### Technical notes
- Stara `update_excel()` pozostawiona w kodzie (legacy, niewywoływana w pipeline).
- Istniejący `.git` (~209 MB) NIE jest czyszczony — refaktor zatrzymuje PRZYSZŁY przyrost; odzyskanie wstecz
  wymagałoby `git filter-repo` + force-push (operacja osobna, destrukcyjna).
- Rozbieżności count xlsx vs `daily_counts` (11/630) okazały się efektem wielu skanów w jednym dniu
  (first-of-day w JSON vs last-of-day) — nie utratą danych. Ledger per-skan zachowuje wszystkie pomiary.

---

## [2026-05-16] - 🔧 Refresh detection oparta o datę (max 1/dzień)

### Fixed 🐛
- **`scraper.py`** — detekcja eventu odświeżenia ogłoszenia: wcześniej trigger oparty był o `last_refresh_timestamp` (pełny ISO timestamp do sekund), co w danych profilu category (`wszystkie_pokoje`) generowało fałszywe duplikaty — ten sam dzień miał różne timestampy i każda zmiana traktowana była jako nowy event. Nowa logika: **event refresh = zmiana wartości `refreshed` (data YYYY-MM-DD) na nowszą**, z deduplikacją per dzień. To zgodne z UI OLX, który pokazuje na stronie ogłoszenia tylko datę ("Odświeżono dnia 12 maja 2026"), nie godzinę. **Max 1 odświeżenie na ogłoszenie na dzień.**
- **`scraper.py`** — usunięto filtr `is_promoted`, który blokował liczenie refresh dla ogłoszeń promowanych. Każda zmiana daty `refreshed` jest teraz liczona, niezależnie od statusu promocji — zapewnia to porównywalność metryki między profilami.
- **`scraper.py`** — gałąź reaktywacji (powrót ogłoszenia z archiwum) teraz wykrywa nowy event refresh: jeśli ogłoszenie wraca z nowszą datą `refreshed` niż miało w archiwum, event jest dopisywany do historii z flagą `during_reactivation: true`. Wcześniej takie "ciche odświeżenia" w trakcie nieaktywności były ignorowane.
- **`scraper.py`** — agregacja `daily_counts[*].refreshed_count`: wcześniej liczyła tylko ogłoszenia, których ostatni wpis `refresh_history[-1].detected_at` zaczynał się od dziś. Teraz zlicza ogłoszenia, których historia zawiera dowolny wpis z `refreshed_at == today` — bardziej odporne, łapie również eventy z reaktywacji oraz przypadki, w których event z dnia X został wykryty w scanie z dnia X+1.

### Changed 🔄
- **`data/dashboard_data.json`** — rebuild historii: usunięto **157 nadmiarowych eventów** w **44 ogłoszeniach** profilu `wszystkie_pokoje`. Wszystkie usunięte wpisy były duplikatami tej samej daty `refreshed` z różnymi timestampami. Wpisy z najwcześniejszym `detected_at` zostały zachowane. Dotknięte ogłoszenia mają teraz pole `_dedup_note` z auditem (`removed_total`, `last_rebuild_at`, `original_count_at_last_rebuild`, `final_count_at_last_rebuild`).
- **`data/dashboard_data.json`** — przeliczone `daily_counts[*].refreshed_count` dla wszystkich profili na podstawie wyczyszczonej historii.

### Added ✨
- **`rebuild_refresh_dedupe.py`** — idempotentny skrypt rebuild deduplikujący `refresh_history` per dzień i synchronizujący `refresh_count` oraz `daily_counts[*].refreshed_count`. Może być uruchamiany wielokrotnie — drugi run nie zmienia nic.

### Technical notes
- Walidacja end-to-end po rebuildzie: 933 ogłoszeń, **0 z >1 refresh/dzień**, **0 mismatchów** `refresh_count == len(refresh_history)`, brak `refreshed_count > count` w żadnym dniu/profilu.
- `last_refresh_timestamp` nadal zapisywany w JSON dla kompletności danych, ale nie jest już używany jako trigger detekcji eventu.
- Rekordzista po rebuild: ogłoszenie `1a6An5` (Czechów) — 22 realne odświeżenia.

---

## [2026-05-10] - 📊 Per-profile added/removed w scan_history

### Added ✨
- **`scraper.py` — `generate_dashboard_json`**: każdy wpis `scan_history[].profiles[pk]` zawiera teraz dodatkowo pola `added` i `removed` (oprócz dotychczasowych `count` i `crosscheck`). Wartości pochodzą z tej samej kalkulacji `flow_added`/`flow_removed` co `daily_counts`, więc są spójne z istniejącą logiką flow. Dla pierwszego scanu profilu (brak historii) — `None`.

### Technical notes
- Zmiana czysto API/JSON, bez modyfikacji `docs/index.html` ani `email_report.py`.
- Konsumenci `scan_history` mogą teraz odczytać granularne flow per scan per profil, zamiast wyłącznie `count` snapshot.

---

## [2026-04-22] - 📈 Nowe metryki: Przybyło/Zniknęło (flow dziennie)

### Added ✨
- **Dashboard**: nowy przycisk `📈 Przybyło/Zniknęło` w toolbarze "Trend w czasie" (obok `Ogłoszenia`, `Mediana ceny`, `% Promowanych`, `Odśw./Reakt.`). Wyświetla dwie linie na wspólnym wykresie:
  - **Przybyło** (zielona) — liczba nowych ogłoszeń pojawiających się danego dnia (ID nieobecne w ostatnim scanie dnia poprzedniego)
  - **Zniknęło** (czerwona) — liczba ogłoszeń znikających danego dnia (ID obecne wczoraj, nieobecne dziś)
- **`scraper.py` — `generate_dashboard_json`**: każdy nowy wpis `daily_counts[]` zawiera pola `added` i `removed`. Dla pierwszego scanu profilu (brak historii) wartości są `None`. Przy wielokrotnych scanach tego samego dnia wartości są akumulowane (każdy scan dodaje swoje delty względem poprzedniego scanu dnia).
- **`rebuild_daily_flows.py`** — skrypt jednorazowy odtwarzający historyczne `added`/`removed` dla 59 dni historii (od 23.02.2026) z arkuszy Excela. Obsługuje dwa formaty kolumn (stary col 12, nowy col 17). Dni z niekompletnymi danymi w Excelu (3-5.04 — bug scrapera) są oznaczane jako `None` (carry-forward do pierwszego kompletnego dnia), nie fałszują flow.

### Technical notes
- Walidacja spójności: dla 4 z 7 profili `added - removed == delta count`. Dla `wszystkie_pokoje` (kategoria, 400+ listingów) są drobne rozbieżności ±kilka wartości/dzień — to efekt tolerancji crosscheck (tol=10), nie bug algorytmu.
- Dni `None` w `daily_counts[]` są poprawnie pomijane przez Chart.js (linia się przerywa, nie łączy przez nulle).
- `beginAtZero: true` dla tej metryki (ustawione dla wszystkich poza `count`).

---

## [2026-04-21] - 🧹 Czyszczenie danych: anomalia refreshed_count dla 17.04.2026

### Fixed 🐛
- **`data/dashboard_data.json` — wpisy z `2026-04-17` w 4 profilach**:
  - `wszystkie_pokoje.refreshed_count`: 115 → 0 (było 30% z count=386)
  - `pokojewlublinie.refreshed_count`: 1 → 0 (było 100% z count=1)
  - `dawny_patron.refreshed_count`: 3 → 0 (było 75% z count=4)
  - `mzuri.refreshed_count`: 38 → 0 (było 83% z count=46)
  - Pominięte: `poqui` (3, tylko 38% z count — w granicach normy), `artymiuk`/`villahome` (0).
  
  **Dlaczego to była anomalia**: jednoczesna szpilka refreshed_count na wielu niezależnych profilach (różni sprzedawcy, różne kategorie) tego samego dnia to wzorzec typowy dla globalnej zmiany kodu, nie dla rzeczywistego eventu rynkowego. Dla profili z małą liczbą ogłoszeń stosunek refreshed/count przekraczał 75-100% co jest nierealistyczne w jeden dzień.
  
  **Root cause**: CHANGELOG `[2026-04-17] - ⏱️ Live detekcja odświeżeń w ciągu dnia (timestamp zamiast daty)` dokumentuje wdrożenie tego dnia (o 21:08:51 — wieczorny manual scan) zmiany, w której pole `last_refresh_timestamp` (ISO timestamp) zastąpiło porównanie stringów dat `YYYY-MM-DD`. Pierwszy scan po deployu wykrył `last_refresh_timestamp` dla wielu ogłoszeń jako "nowe" (transition from `None` to value) i błędnie naliczył to jako eventy odświeżenia — ten sam mechanizm co anomalia z 06.04 (vide wpis powyżej), tylko inny trigger.
  
  **Dowód w danych:** Scan 17.04 jest o 21:08 (reszta scanów: 08:00-09:00 poranek). Scan 18.04 miał `refreshed_count=2` (nienaturalnie nisko vs norma 14-25), co potwierdza że 17.04 "zjadł" eventy, które naturalnie powinny rozłożyć się na kilka kolejnych dni.
  
  **Ślad audytowy**: każdy zmieniony wpis ma pole `_note` z opisem korekty i odniesieniem do CHANGELOG.

### Zweryfikowane ✅
- Profile `poqui` (38%) celowo pominięte jako granicznie mieszczące się w zmienności dziennej.
- Profil `artymiuk` miał `count=0` tego dnia (brak aktywnych ogłoszeń) — wartość `0` niewinna.
- Poprzednia korekta z `2026-04-06` (anomalia 363→0) nienaruszona.

---

## [2026-04-21] - 🧹 Czyszczenie danych: anomalia refreshed_count dla 06.04.2026

### Fixed 🐛
- **`data/dashboard_data.json` — `wszystkie_pokoje.daily_counts` z `2026-04-06`**: wartość `refreshed_count: 363 → 0`.
  
  **Dlaczego to była anomalia**: `refreshed_count=363` przy `count=353` jest fizycznie niemożliwe — nie można odświeżyć więcej ogłoszeń niż jest aktywnych w kategorii. Kontekst otaczających dni potwierdza artefakt: 01.04–05.04 wszystkie miały `refreshed_count=0`, a od 07.04 wartości wróciły do normalnych 14–18 dziennie.
  
  **Root cause**: dzień 06.04.2026 był dniem wdrożenia systemu trackowania odświeżeń (patrz CHANGELOG `[2026-04-06] - 🔄 Refresh Count Tracking & Workflow Fixes`). Tego dnia uruchomiono `rebuild_refresh_history.py`, który odtworzył 576 eventów odświeżenia z historycznych danych Excel sięgających 23.02.2026. Skrypt najprawdopodobniej naliczył pierwszą obserwowaną wartość pola `refreshed` dla każdego ogłoszenia jako "świeże odświeżenie" (transition from `None` to date) — dając ~353 false-positive dla aktywnych ogłoszeń + ~10 prawdziwych = 363.
  
  **Ślad audytowy**: wpis zachowuje pole `_note` z opisem korekty i datą, żeby była pełna przejrzystość rekonstrukcji historycznej.

### Zweryfikowane ✅
- Anomalia dotyczy wyłącznie profilu `wszystkie_pokoje`. Pozostałe profile (`pokojewlublinie`, `poqui`, `artymiuk`, `dawny_patron`, `mzuri`, `villahome`) miały dla 06.04 wartość `refreshed_count=0` (również nietypowe, ale osobny wątek — nie dotknięte w tej edycji).
- Walidacja JSON: plik poprawny, 7 profili, struktura niezmieniona poza dwoma polami wpisu.

---

## [2026-04-21] - 📐 Wykres 30 dni — czytelne etykiety dat (bez nachodzenia)

### Changed 🔧
- **Etykiety dat na wykresie słupkowym**: `font-size` zmniejszony z 10px → 9px + `white-space: nowrap`, żeby daty w formacie `DD.MM` nigdy się nie łamały ani nie nachodziły na siebie.
- **Adaptacyjne rozmiary słupków** (`renderChart` w JS) — zwiększone dla wszystkich zakresów:
  - 7 dni: `barWidth 40→56px`, `gap 8→14px`
  - 14 dni: `barWidth 28→40px`, `gap 6→10px`
  - 30 dni: `barWidth 18→28px`, `gap 4→8px` ← rozwiązanie problemu nachodzących etykiet
- **`chart-container` padding boczny**: `4px → 24px` — słupki nie dotykają już krawędzi panelu.

### Fixed 🐛
- **Nachodzące etykiety dat na wykresie 30 dni** (zgłoszone w zrzucie ekranu): przy 30 słupkach w ciasnym containerze daty `23.10`, `24.10`, `25.10`... tworzyły nieczytelną zlepkę. Po zmniejszeniu czcionki + większych odstępach + szerszych słupkach (w ramach `max-width: 1400px`) etykiety są czytelnie rozdzielone.

### Added ✨
- **`body { overflow-x: hidden }`** — profilaktyczne zabezpieczenie przed ewentualnym poziomym scrollem.

### Iteracja 🔄
Pierwsza wersja tej zmiany rozszerzała `detail-panel` do pełnej szerokości ekranu (full-bleed 100vw). Odrzucone po wizualnej weryfikacji: panel wystawał poza szerokość siatki kafelków u góry, co wyglądało niespójnie. Ostateczne rozwiązanie zachowuje `max-width: 1400px` containera dla całego dashboardu — panel jest tej samej szerokości co kafelki, a problem z nachodzącymi datami rozwiązano samymi zmianami typografii i rozmiarów słupków.

---

## [2026-04-17] - ⏱️ Live detekcja odświeżeń w ciągu dnia (timestamp zamiast daty)

### Fixed 🐛
- **`scraper.py` — detekcja odświeżenia używa pełnego ISO timestampu zamiast samej daty**:
  Dotychczas scraper porównywał `new_refreshed > old_refreshed` na stringach `YYYY-MM-DD`. Problem: gdy OLX zwrócił `last_refresh_time: 2026-04-17T12:03:33+02:00` po wcześniejszym `2026-04-17T08:15:22+02:00` tego samego dnia, porównanie dat dawało `"2026-04-17" > "2026-04-17"` = false. **Wszystkie odświeżenia tego samego dnia były niewidoczne.**
  
  Nowa logika: każde ogłoszenie ma teraz pole `last_refresh_timestamp` z pełnym ISO timestampem z `last_refresh_time` w JSONie OLX (dokładność do sekund + strefa czasowa). Porównanie `new_ts > old_ts` łapie wielokrotne odświeżenia w ciągu tego samego dnia. Fallback na porównanie dat zachowany dla starych wpisów bez timestampa.

### Added ✨
- **Pole `last_refresh_timestamp`** w `current_listings[*]` — pełny ISO timestamp (np. `2026-04-17T12:03:33+02:00`) zachowywany dla wszystkich typów scrapingu (kategoria + profile user).
- Logowanie `[REFRESHED]` zawiera teraz precyzyjny moment odświeżenia.

### Kontekst odkrycia 🔍
Podczas analizy danych zauważyłem, że **17.04.2026 ~12:00** użytkownik `poqui` odświeżył 4 ogłoszenia naraz, ale scraper tego nie wychwycił — w Excelu kolumna "Liczba odświeżeń" skoczyła z 0 do 1, ale JSON dashboardu nadal pokazywał `refresh_count=0`, bo porównanie stringów dat nic nie wykryło. Ta zmiana eliminuje problem.

### Uwaga
- Pierwszy scan po wdrożeniu tylko **zapisze baseline** timestampów — nie liczy żadnych eventów. Od drugiego scanu scraper będzie wykrywał zmiany w czasie rzeczywistym.

---

## [2026-04-17] - 📊 Rebuild v2: pełna rekonstrukcja refresh_history z kolumny „Liczba odświeżeń"

### Changed 🔧
- **`rebuild_archive_counters.py` v2** — przepisana logika rekonstrukcji refresh_history:
  - Poprzednia wersja odtwarzała historię tylko ze zmian kolumny `Data odświeżenia`, która jest pusta dla profili user (`poqui`, `mzuri`, `artymiuk`, `dawny_patron`, `pokojewlublinie`).
  - Nowa wersja używa DWÓCH sygnałów, łączonych z deduplikacją per scan_date:
    - (a) **Wzrosty kolumny „Liczba odświeżeń"** — każdy wzrost wartości X → Y (Y>X) w czasie per ID = (Y-X) eventów. Działa dla wszystkich profili. Resety/spadki (np. gdy OLX zwróci 0 po wcześniejszym 3) są IGNOROWANE — high-water mark aktualizowany tylko w górę.
    - (b) **Zmiany „Data odświeżenia"** — dodatkowa precyzja dla `wszystkie_pokoje`.
  - W obrębie tego samego dnia scanu event liczony jest RAZ (preferując dokładniejsze info z `date_change`).

### Data fix 🔧
Rebuild v2 uruchomiony:
- **753 eventów odświeżeń** zrekonstruowanych (vs 205 w v1, +267%).
- **273 ogłoszeń** z odtworzoną historią odświeżeń (vs 104 w v1, +163%).
- Per-profile breakdown:
  - `wszystkie_pokoje`: 676 eventów, 210 ogłoszeń
  - `mzuri`: **48 eventów, 47 ogłoszeń** (poprzednio: 0 — bo tylko `Data odświeżenia`)
  - `poqui`: **16 eventów, 10 ogłoszeń** (poprzednio: 0)
  - `dawny_patron`: **7 eventów, 4 ogłoszenia** (poprzednio: 0)
  - `pokojewlublinie`: **5 eventów, 1 ogłoszenie** (poprzednio: 0)
  - `artymiuk`: **1 event, 1 ogłoszenie** (poprzednio: 0)
- Wykres „Odśw./Reakt." w dashboardzie pokazuje teraz dane dla wszystkich profili użytkowników, nie tylko kategorii.

### Uwaga 📝
Dla ogłoszeń z bardzo starych scanów używających "slug" ID (np. `183ger`, `17NeTz` w poqui), których nie ma w Excelu, rebuild ustawia `refresh_count=0`. To oczekiwane — dla tych ID nie ma danych historycznych do rekonstrukcji.

---

## [2026-04-17] - 📊 Archiwum: liczniki odświeżeń i reaktywacji + nowa kolumna w dashboardzie

### Fixed 🐛
- **`scraper.py` — archiwizacja zachowuje pełną strukturę liczników**:
  Gdy ogłoszenie trafia do archiwum, teraz zawsze przenoszone są: `refresh_count`, `refresh_history`, `reactivation_count`, `reactivation_history` (z domyślnymi wartościami dla pól które nie istniały). Dodatkowo bieżący otwarty okres aktywności w `reactivation_history[-1]` dostaje pole `active_to_current` (= `archived_date`), żeby zamknąć pełny timeline ogłoszenia.
- **`scraper.py` — zliczanie dziennych eventów odśw./reakt. obejmuje świeżo zarchiwizowane**:
  Dotychczas `daily_counts[*].refreshed_count` / `reactivated_count` były liczone tylko dla ogłoszeń obecnych w `new_listings` po scanie. Problem: jeśli ogłoszenie zostało w tym samym scanie odświeżone a potem zniknęło (user zamknął/archiwizował ogłoszenie po odświeżeniu), event nie liczył się w wykresie. Teraz zliczanie obejmuje `new_listings + newly_archived`.
- **`scraper.py` — kopiowanie refresh_count/history po reaktywacji**:
  Gdy ogłoszenie wraca z archiwum, teraz poprawnie kopiuje `refresh_count` i `refresh_history` z archiwalnego wpisu. Dotychczas traciło historię.

### Added ✨
- **`rebuild_archive_counters.py`** — nowy skrypt rekonstruujący historię z Excela:
  - Dla każdego archiwalnego i aktywnego ogłoszenia odbudowuje `refresh_history`, `refresh_count`, `reactivation_history`, `reactivation_count` na podstawie wpisów z Excela per-ID.
  - Reaktywacja wykrywana jako luka ≥ 2 scanów, w których ID nie występowało, po czym wróciło.
  - Następnie rebuilduje `daily_counts[*].refreshed_count` / `reactivated_count` z rzeczywistych zdarzeń ze wszystkich ogłoszeń (aktywnych + archiwum).
  - Idempotentny — można uruchamiać wielokrotnie.

### Data fix 🔧
Rebuild uruchomiony na żywych danych, efekt:
- Przetworzono **819 ogłoszeń** (aktywne + archiwum, 7 profili).
- Dodano **205 zdarzeń odświeżeń** i **20 zdarzeń reaktywacji** do historii.
- **33 archiwalnych ogłoszeń** zyskało populowany `refresh_count`, **2 archiwalnych** zyskało `reactivation_count`.
- Daily_counts zaktualizowane: `wszystkie_pokoje` (+35 dni z reaktywacjami), `mzuri` (+9), `dawny_patron` (+3), `pokojewlublinie` (+1).

### 📊 Dashboard UI
- **Nowa kolumna „Licz. reakt."** w tabeli ogłoszeń (aktywne i archiwum), obok „Licz. odsw.":
  - Sortowalna.
  - Kolor zielony gdy > 0, szary gdy 0.
  - Tooltip pokazuje datę ostatniej reaktywacji.
- Tabele w obu zakładkach (Aktualne, Archiwum) mają teraz spójne 11 kolumn (12 w archiwum z „Zniknęło").

### Uwaga 📝
Dla profili użytkowników (`poqui`, `mzuri`, `artymiuk`, `dawny_patron`, `pokojewlublinie`) scraper pobiera dane z `__PRERENDERED_STATE__` JSON, który nie zawiera daty odświeżenia — kolumna `Data odświeżenia` w Excelu dla tych profili jest pusta. Z tego powodu rebuild zdarzeń odświeżeń działa tylko dla kategorii `wszystkie_pokoje`. To specyfika źródła danych, nie bug.

---

## [2026-04-17] - 🐛 Fix: Poprawna definicja "odświeżenia" + cleanup fake entries

### Fixed 🐛
- **`scraper.py` — pierwsze wykrycie daty refresh NIE jest eventem odświeżenia**:
  Poprzednia logika `is_new_refresh = old_refreshed is None or new_refreshed > old_refreshed` liczyła każde pierwsze wykrycie pola `refreshed` jako event. Problem: OLX **zawsze** podaje datę refreshu dla każdego ogłoszenia (nawet gdy user nigdy go nie odświeżył — to pokazuje datę publikacji), więc każde nowe ogłoszenie dodawane do tracking'u dostawało `+1` do `refresh_count`. Nowa definicja: event odświeżenia = **ZMIANA** pola refreshed z X na Y (Y>X). Pierwsza wartość pola refreshed to tylko historyczna informacja, nie event.
- **`rebuild_refresh_history.py` — restrictive fallback**:
  Fallback dodawał syntetyczny wpis dla każdego ogłoszenia z `refreshed != None` bez dopasowania w Excelu. Teraz dodaje tylko gdy `json_refreshed` jest **nowsze** niż najnowsza data widziana w Excelu (rzeczywista nowa zmiana). + ten sam fix co w scraper.py: historia liczy tylko zmiany refreshed, nie pierwsze wykrycia.

### Data fix 🔧
- Wyczyszczono **323 fake entries** (`old_date=None`) z `refresh_history` wszystkich ogłoszeń:
  - wszystkie_pokoje: 214
  - mzuri: 86 (agencja, nigdy nie odświeża manualnie)
  - poqui: 10
  - dawny_patron: 7
  - pokojewlublinie: 4
  - artymiuk: 2
- Przeliczono `daily_counts[*].refreshed_count` dla wszystkich dni na podstawie pozostałych **213 prawdziwych eventów** (zmiana refreshed na nowszą datę).
- Najbardziej spektakularne korekty: `wszystkie_pokoje[2026-03-30]: 33 → 0`, `mzuri[2026-04-11]: 8 → 0`, `poqui[2026-03-07]: 6 → 0`.

### Semantic change 📝
- Interpretacja metryki "odświeżenia" w dashboard'zie zmienia się: teraz pokazuje tylko RZECZYWISTE odświeżenia (user kliknął "Odśwież ogłoszenie"), nie pierwsze wykrycie. Liczby będą znacznie niższe niż dotychczas, ale za to prawdziwe.

---

## [2026-04-17] - 🐛 Data fix: Usunięcie fake "synthetic" refresh entries z rebuildu

### Fixed 🐛
- **Data fix refresh_history**: Commit `4343f5f` uruchomił `rebuild_refresh_history.py`, który dla każdego ogłoszenia z `refreshed != None` w JSON ale bez matchu w Excelu dodał **syntetyczny wpis z `detected_at=last_scan_date + last_scan_time`**. Efekt: 70 ogłoszeń (w tym 50 w mzuri) dostało `refresh_count=1` z tym samym timestampem `2026-04-17 08:50:00`. Następnie `rebuild_refreshed_count.py` zliczył je wszystkie jako zdarzenia z tego dnia — stąd `daily_counts[2026-04-17].refreshed_count=45` dla mzuri (mimo że mzuri to agencja i NIGDY nie odświeża ogłoszeń ręcznie, co potwierdza Excel: 71 ogłoszeń, 0 z historią zmian `refreshed`).
- **Cleanup**: usunięto 70 synthetic entries (detected_at=`2026-04-17 08:50:00` + old_date=None) i przeliczono `refreshed_count` w daily_counts:
  - wszystkie_pokoje: 34 → 29
  - pokojewlublinie: 1 → 0
  - poqui: 7 → 4
  - dawny_patron: 4 → 0
  - mzuri: **45 → 0** (główny case)

### Open issue ⚠️
- Logika fallback w `rebuild_refresh_history.py` (linie 173-184) dalej generuje synthetic entries. Powinna być albo usunięta, albo ograniczona do sytuacji gdzie `refreshed_at > last scan date` (czyli rzeczywiście nowa data odświeżenia), inaczej będzie kłamać przy każdym kolejnym uruchomieniu.

---

## [2026-04-17] - 🐛 Fix: Guard rozróżnia legit-empty vs scraper-error

### Fixed 🐛
- **`scraper.py` — rozróżnienie "prawdziwie pusty profil" od "błędu scrapera"**:
  Poprzedni guard `if result["count"] > 0` był za prosty — traktował WSZYSTKIE przypadki count=0 jako błąd scrapera. Efekt: gdy użytkownik (np. artymiuk) realnie usunął swoje ogłoszenia i OLX API zwraca `total_elements=0`, ogłoszenia zostawały martwe w `current_listings` na zawsze. Wprowadzono funkcję `is_scraper_error`:
  - `crosscheck == "error"` → na pewno błąd, chroń dane
  - `count == 0 and header_count is None` → nie można zweryfikować, chroń
  - `crosscheck == "passed" and header_count == 0` → **PRAWDZIWIE pusty profil**, archiwizuj normalnie
  Zarówno archiwizacja, jak i guard na daily_counts używają teraz tego samego sygnału.

### Data fix 🔧
- Ręcznie przeniesiono "Pokój jednoosobowy Wyżynna" (artymiuk) z current_listings do archived_listings — ogłoszenie było nieaktywne na OLX od 2026-04-10, ale poprzedni guard trzymał je w current przez 7 dni.

### Tested ✅
- Dry-run: 3 scenariusze testowe (legit empty, scraper error, normal scan) → wszystkie działają zgodnie z oczekiwaniem.

---

## [2026-04-17] - 🐛 Fix: Audyt kodu + ochrona daily_counts przed błędami scrapera

### Fixed 🐛
- **`scraper.py` — ochrona daily_counts przed błędami scrapera** (`generate_dashboard_json()`):
  Gdy scan zwracał 0 wyników (OLX blocking, network error), archiwizacja i `current_listings` były chronione, ale **`daily_counts` były nadpisywane wartością 0**. Efekt: dashboard dla artymiuka od 5 dni pokazywał `count=0`, mimo że `current_listings` miał 1 ogłoszenie. Dodano guard: jeśli `result["count"]==0` ALE `current_listings` ma >0 elementów → pomijamy całą aktualizację daily_counts.
- **`scraper.py` — promocje dla nowych ogłoszeń**: cały blok `# ═══ PROMOTION TRACKING ═══` był wewnątrz `if lid in old_map:`, więc dla nowo wykrytych ogłoszeń (lub reaktywowanych z archiwum) które od razu były promowane, **pierwszy dzień promocji nie był liczony**. Dodano `else` branch: nowe promowane → `promoted_days_current=1, promoted_sessions_count=1`; reaktywacje promowane → licznik sesji z archiwum + 1; zachowuje `promotion_history` z archived_listings.
- **`email_report.py`** (linia 551): `trend_diff` leak'owało między iteracjami pętli po profilach. Dodano `trend_diff = None` inicjalizację i poprawiono warunek na `trend_diff is not None and trend_diff > 15`.
- **`scraper.py` — shadowing zmiennej**: `new_listings` używane w dwóch różnych znaczeniach w tej samej funkcji. Pierwsza (lista nowych względem `old_map` — do mediany) zmieniona na `newly_detected_listings`.

### Changed 🔧
- **Porządki pyflakes**: usunięte nieużywane importy (`sys`, `json` w diagnose.py; `datetime` w backfill_prices.py, rebuild_refresh_reactivation_counts.py, rebuild_refreshed_count.py; `timedelta` w rebuild_historical_medians.py). Poprawione f-stringi bez placeholderów w 7 plikach.
- **`backfill_prices.py`**: dodane ostrzeżenie DEPRECATED w docstring — skrypt stosuje aktualną medianę do wszystkich historycznych dni, co psuje dane. Zalecany `rebuild_historical_medians.py`.

### Tested ✅
- Dry-run: symulacja scan error dla artymiuka — guard działa, `current_listings` zachowane, brak nowego wpisu `count=0` w daily_counts.
- Normalna operacja: wszystkie profile dostają poprawne daily_counts update.
- Profile prawdziwie puste (villahome, current=0, scan=0) dostają normalny wpis count=0 — guard nie blokuje.
- `py_compile` + `pyflakes` = wszystkie 10 plików czyste.

---

## [2026-04-17] - 🐛 Fix: Licznik odświeżeń dla pierwszego wykrytego refreshu

### Fixed 🐛
- **`scraper.py`** (linia 1591): warunek `if old_refreshed and new_refreshed and new_refreshed > old_refreshed` wymagał by poprzedni `refreshed` był truthy, przez co **pierwsze pojawienie się znacznika odświeżenia nigdy nie było liczone**. Nowa logika jest idempotentna:
  - Pierwsze wykrycie refreshu (`old_refreshed=None` → data) = +1
  - Zmiana daty refreshu (stara → nowa) = +1
  - Ponowne wykrycie tej samej daty = 0 (sprawdzamy czy `refreshed_at` już jest w `refresh_history`)
- **`rebuild_refresh_history.py`**:
  - Ten sam bug w logice rekonstrukcji historii (pierwszy refresh gubiony)
  - **Zła mapa kolumn Excel**: czytał `ID ogłoszenia` z kolumny 12 i `Data odświeżenia` z kolumny 10, a w aktualnym layoucie są w kolumnach 17 i 14 (po dodaniu "Liczba odświeżeń"). Dodano autodetekcję kolumn z nagłówka arkusza.
  - **Rozbieżność Excel vs JSON**: gdy JSON miał `refreshed` którego Excel nie pokazuje dla ostatniego scanu, rebuild to pomijał. Dodano fallback: jeśli aktualny `refreshed` z JSON nie jest obecny w scanach z Excela, dokleja go jako syntetyczny wpis z timestampem `last_scan` (dla current) lub `archived_date` (dla archived).
  - Zawsze nadpisuje `refresh_history` i `refresh_count` (wcześniej zostawiał stare, buggy wartości gdy nie znalazł nowych).

### Changed 🔧
- Rebuild historyczny: refresh_count i refresh_history przeliczone od zera dla wszystkich profili na podstawie pełnych danych Excel + fallback z JSON. Łącznie 389 ogłoszeń z historią odświeżeń, 567 wydarzeń. Invariant `refresh_count == len(refresh_history)` spełniony dla wszystkich ogłoszeń.

### Example 📸
Przed fixem — ogłoszenia które po raz pierwszy dostały datę odświeżenia miały ikonkę 🔄 w UI, ale `refresh_count=0`:
- `Jasny pokoj... ul. Grabskiego` — refreshed=2026-04-15, **count=0** ❌
- `Pokój z balkonem do wynajęcia od zaraz!` — refreshed=2026-04-15, **count=0** ❌

Po fixie: `count=1` dla obu, z wpisem `{refreshed_at: "2026-04-15", old_date: null}` w historii.



### Changed 📊
- **Wykres % Promowanych** — tooltip teraz pokazuje trzy linie informacji:
  - Data (np. `11.04`)
  - `Promowane: 12` — liczba promowanych ogłoszeń
  - `Udział: 6%` — procentowy udział promowanych
- Dodano `promotedCountData` do danych wykresu liniowego

---

## [2026-04-11] - ✨ Feature: Osobna strona Historia skanów (scans.html)

### Added ✨
- **`docs/scans.html`** — dedykowana strona historii skanów, dostępna przez przycisk "Skany" w topbarze:
  - **Hero** — statystyki ostatniego scanu: czas całkowity, ogłoszeń łącznie, nowych ogłoszeń, liczba profili
  - **Karty per profil** — czas scanu, pasek proporcjonalny, metoda (API/Playwright), liczba ogłoszeń, crosscheck
  - **Wykres trendu** — słupkowy chart czasu skanowania dla wszystkich historycznych skanów (do 30), zielony=sukces/czerwony=błąd
  - **Tabela historii** — wszystkie skany od najnowszego: data, status badge, czas, wizualizacja, liczba ogłoszeń
  - Spójna stylizacja z dashboardem (dark/light theme, JetBrains Mono, DM Sans, te same CSS variables)

### Changed 📊
- `docs/index.html`: przycisk "Skany" zmieniony z otwierającego panel na link `href="scans.html"`
- Usunięty stary CSS panelu skanów i JS funkcje `toggleScansPanel`/`renderScansPanel` z `index.html`

---

## [2026-04-11] - ✨ Feature: Zakładka "Skany" z czasami wykonania

### Added ✨
- **Przycisk "Skany"** w topbarze dashboardu — otwiera/zamyka panel z historią skanów
- **Panel skanów** wysuwa się pod topbarem (animacja max-height), zawiera tabelę:
  - Profil, liczba ogłoszeń, crosscheck (✓/✗/~), czas scanu w sekundach, wizualny pasek proporcjonalny
  - Wiersz podsumowania z łącznym czasem całego scanu i datą
- **Pomiar czasu per profil** w `scraper.py` — `duration_seconds` dodany do każdego wyniku profilu
- `status.json` rozszerzony o pole `profiles[pk].duration_seconds`

---

## [2026-04-11] - 🐛 Fix: Playwright dla wszystkich profili

### Fixed 🐛
- **GitHub Actions IP blokowane przez OLX:** scraper `requests` zwracał pustą stronę 200 OK dla każdego profilu — OLX filtruje ruch z IP data center Microsoft/Azure
- Wszystkie profile (kategoria + user profiles) przerzucone na **Playwright** (headless Chromium), który omija blokadę przez zachowanie się jak prawdziwy użytkownik

### Changed 📊
- `scraper.py`: usunięte stare `scrape_profile_playwright` (DEPRECATED) i `scrape_with_crosscheck` z logiką requests
- Nowa `scrape_with_playwright_all(profiles)` — jeden browser context dla wszystkich profili naraz
- Nowa `_scrape_one_profile_playwright(page_obj, profile_key, cfg)` — obsługuje jeden profil:
  - User profiles: `page.evaluate("JSON.stringify(window.__PRERENDERED_STATE__)")` — JSON parsowany przez silnik JS, bez kruchego regex
  - Kategoria: wait for `[data-cy="l-card"]` → BeautifulSoup → paginacja DOM
- Nowa `_parse_ads_json(ads)` — wspólny parser dla `adsOffers.data[]`
- `run_scan()` wywołuje teraz `scrape_with_playwright_all(PROFILES)` zamiast pętli per-profil

---

## [2026-04-10] - 🐛 Fix: refreshed_count Calculation

### Fixed 🐛
- **Naprawa liczenia `refreshed_count` w daily_counts:**
  - **Problem:** `refreshed_count` było błędnie obliczane jako liczba ogłoszeń z `refreshed == today`, co również liczyło nowe ogłoszenia opublikowane dzisiaj (OLX pokazuje "Dzisiaj o..."), a nie tylko rzeczywiste odświeżenia
  - **Rozwiązanie:** Teraz `refreshed_count` jest liczone na podstawie `refresh_history[]` - zlicza tylko ogłoszenia, które mają wpis wykryty danego dnia (`detected_at.startswith(today)`)
  - Analogicznie do sposobu liczenia `reactivated_count`
  
### Changed 📊
- `scraper.py`: Przeniesiono obliczenie `refreshed_count` po przetworzeniu `new_listings`, kiedy `refresh_history` jest już zaktualizowane
- Usunięto błędną logikę: `sum(1 for l in result["listings"] if l.get("refreshed") == today)`

### Added ✨
- **rebuild_refreshed_count.py:** Skrypt do przeliczenia historycznych wartości `refreshed_count` na podstawie `refresh_history[]` w `current_listings` i `archived_listings`
- Naprawiono 107 wpisów w `daily_counts` dla wszystkich profili

---

## [2026-04-06] - 🔄 Refresh Count Tracking & Workflow Fixes

### Added ✨
- **Refresh Count Tracking:**
  - Nowa kolumna "Liczba odświeżeń" w Excel (kolumna 15)
  - Tracking `refresh_count` w JSON - zlicza ile razy ogłoszenie zostało odświeżone
  - Automatyczna inkrementacja gdy `refreshed` date się zmienia
  - Dashboard: nowa kolumna "Licz. odsw." w tabeli ogłoszeń z sortowaniem
  - Kolor accent dla ogłoszeń z refresh_count > 0
  
- **Refresh History Tracking:**
  - Nowe pole `refresh_history[]` - pełna historia odświeżeń (analogiczne do `reactivation_history`)
  - Każdy wpis zawiera: `refreshed_at`, `detected_at`, `old_date`
  - ~~Buduje timeline od momentu wdrożenia (dane historyczne sprzed tego są stracone - OLX nie przechowuje historii)~~ **ODTWORZONE Z EXCEL!**
  - **Rebuild z Excel:** 153 ogłoszenia z historią, 576 wydarzeń odświeżenia od 2026-02-23
  - Pozwala na dokładną analizę: kiedy było każde odświeżenie, jak często sprzedawca odświeża portfolio
  
- **rebuild_refresh_history.py:**
  - Skrypt odtwarzający `refresh_history[]` z danych Excel
  - Analizuje wszystkie historyczne scany i wykrywa zmiany daty `refreshed`
  - Wykorzystany do przeliczenia 576 wpisów historii dla 153 ogłoszeń
  
- **Wykres "Odświeżenia/Reaktywacje" (nowa metryka w line chart):**
  - Nowy przycisk 🔄 w przełączniku metryk (obok Ogłoszenia, Mediana, % Promowanych)
  - Dwie linie na wykresie:
    - 🔵 Odświeżenia (refreshed_count per dzień)
    - 🟢 Reaktywacje (reactivated_count per dzień)
  - Tracking w daily_counts: `refreshed_count`, `reactivated_count`
  - Legenda i tooltips dla obu metryk
  
- **rebuild_refresh_reactivation_counts.py:**
  - Skrypt odtwarzający dane historyczne z reactivation_history
  - Wykorzystany do przeliczenia 36 wpisów w daily_counts

### Fixed 🐛
- **reactivated_count logic:** Zliczał wszystkie ogłoszenia z flagą `reactivated` (86), zamiast tylko tych reaktywowanych danego dnia (3)
- Poprawka: sprawdza `reactivation_history[-1].reactivated_at == date`
- Dane historyczne odtworzone z reactivation_history

- **Excel refresh_count column:**
  - Kolumna "Liczba odświeżeń" nie była zapisywana do Excel mimo że istniała w nagłówkach
  - Root cause #1: `update_excel()` wywoływany przed `generate_dashboard_json()` → ładował stary JSON bez nowych refresh_count
  - Root cause #2: `get_or_create_sheet()` nie aktualizował nagłówków dla istniejących arkuszy
  - Fix #1: Zamieniono kolejność - najpierw JSON, potem Excel
  - Fix #2: `get_or_create_sheet()` teraz aktualizuje nagłówki gdy się zmieniły
  - Zweryfikowano: kolumna dodana, wartości poprawnie zapisane (96 ogłoszeń z refresh_count > 0)

### Fixed 🐛
- **Workflow Comments:**
  - scan.yml: zmiana crona z `0 6 * * *` na `0 7 * * *` (zgodnie z preferencją użytkownika)
  - scan.yml: poprawiony komentarz "7:00 UTC = 8:00 CET (zima) / 9:00 CEST (lato)"
  - weekly_report.yml: poprawiony komentarz "7:30 UTC = 8:30 CET (zima) / 9:30 CEST (lato)"

### Technical Details 🔧
- `scraper.py`: dodano logikę porównywania `old_refreshed` vs `new_refreshed` w `generate_dashboard_json()`
- `scraper.py`: załadowanie istniejącego JSON w `update_excel()` aby pobrać refresh_count dla zapisu
- `docs/index.html`: nowa kolumna w tabeli + case 'refresh_count' w sortowaniu
- Excel: szerokość kolumn zaktualizowana (dodano kolumnę 15 o szerokości 12)

---

## [2026-04-02] - 💰 ROI Calculator & Advanced Analytics

### Added ✨
- **ROI Calculator (Email Report):**
  - Koszt promocji OLX: 69.49 zł / 7 dni (~9.93 zł/dzień)
  - Weekly cost calculation per profile
  - Cost per listing metric
  - Coverage % (promoted / total listings)
  - Average promotion days per listing
  - Total weekly cost summary (with monthly/yearly projections)
  - Tabela: Profil | Promowane | Koszt tygodniowy | Koszt/listing | Pokrycie | Śr. dni

- **Promoted Trend Chart (Dashboard):**
  - Nowa metryka w line chart: 🎯 % Promowanych
  - Toggle: 📊 Ogłoszenia | 💰 Mediana ceny | 🎯 % Promowanych
  - Orange line chart showing promoted percentage over time
  - Historical trend analysis (7/14/30 days)

---

## [2026-04-02] - 🎯 Promoted Listings Detection & Analytics

### Added ✨
- **Multi-strategy promoted detection:**
  - Primary: URL parameter `search_reason=promoted` (100% accurate)
  - Fallback: CSS classes, badges, text markers, icons
  - Confidence scoring (0.0-1.0)
  - Promotion types: `featured` ⭐ / `top_ad` 🔝 / `highlight` ✨

- **Promotion history tracking (JSON):**
  - `promoted_days_current` — dni w bieżącej sesji promocji
  - `promoted_sessions_count` — ile razy ogłoszenie było promowane
  - `promotion_history[]` — pełna historia sesji z start/end dates
  - Profile-level stats: `promoted_count`, `promoted_percentage`, `promotion_breakdown`

- **Excel: 4 nowe kolumny** (po "Cena"):
  - `🎯 Prom.` — ✓/— z emoji badges
  - `Dni prom.` — current session days (green/orange color-coding)
  - `Sesje prom.` — total promotion sessions count
  - `Typ prom.` — ⭐ Featured / 🔝 Top Ad / ✨ Highlight

- **Dashboard UI:**
  - Stat card: **🎯 Promowane X (Y%)** z accent-glow background
  - Stat card: **Typy promocji** z tooltip breakdown
  - 3 nowe kolumny w tabeli listings (między Cena a Zmiana ceny)
  - Sortowanie po promoted metrics
  - Highlighted rows (accent-glow) dla promoted listings
  - Color-coded days: green (<7), orange (>7)

- **Email Report — 🎯 Analiza promocji:**
  - Tabela z % promowanych per profil + 7-day trend (↑↓)
  - Dominant promotion type badges (color-coded)
  - **💡 Insights** (auto-generated):
    - Aggressive strategy detection (>50% promoted)
    - Low investment detection (<10%)
    - Spike alerts (>15pp change)
  - **🏆 Competitor Ranking:**
    - Top 10 by % promoted (medals 🥇🥈🥉)
    - Strategy tiers: 🔥 Aggressive (≥60%) / ⚡ Moderate (30-60%) / 💡 Light (10-30%) / 🌱 Organic (<10%)

### Changed 🔄
- **scraper.py:**
  - `parse_card()` dodaje `is_promoted`, `promotion_type`, `promotion_confidence`
  - `generate_dashboard_json()` trackuje promotion history per listing
  - `daily_counts` zawiera `promoted_count`, `promoted_percentage`, `promotion_breakdown`
  - Promotion session logic: START (0→1), CONTINUE (+1 day), END (save to history)

- **Excel column order:**
  - Było: `Tytuł | Cena | Zmiana ceny | ...`
  - Jest: `Tytuł | Cena | 🎯 Prom. | Dni prom. | Sesje | Typ | Zmiana ceny | ...`

### Technical Details 🔧
**Detection algorithm (`detect_promoted_status`):**
```python
# STRATEGIA 0: URL parameter (strongest signal)
if 'search_reason=search%7Cpromoted' in href:
    signals.append(('url_parameter', 1.0))

# STRATEGIA 1-5: Fallbacks (badges, CSS, text, icons, data attrs)
# Returns: {is_promoted, promotion_type, confidence}
```

**Promotion tracking logic:**
- **START:** `old.is_promoted=False` → `new.is_promoted=True`
  - `promoted_days_current = 1`
  - `promoted_sessions_count += 1`
  - Set `promotion_started_at = now`

- **CONTINUE:** `old.is_promoted=True` → `new.is_promoted=True`
  - `promoted_days_current += 1`

- **END:** `old.is_promoted=True` → `new.is_promoted=False`
  - Save to `promotion_history[]`: `{start_date, end_date, days, type, session_number}`
  - Reset `promoted_days_current = 0`

**Data structure:**
```json
{
  "listing": {
    "is_promoted": true,
    "promotion_type": "featured",
    "promoted_days_current": 5,
    "promoted_sessions_count": 2,
    "promotion_history": [
      {
        "start_date": "2026-03-28 10:00:00",
        "end_date": "2026-04-01 09:00:00",
        "days": 4,
        "promotion_type": "featured",
        "session_number": 1
      }
    ]
  },
  "daily_counts": {
    "promoted_count": 8,
    "promoted_percentage": 66.7,
    "promotion_breakdown": {"featured": 5, "top_ad": 2}
  }
}
```

### Use Cases 💡
- **Competitive intelligence:** Track which competitors invest in paid ads
- **ROI analysis:** Correlate promotion periods with price changes
- **Market trends:** Detect seasonal promotion patterns
- **Strategy insights:** Benchmark promotion aggressiveness across profiles

### Performance Impact ⚡
- Detection adds <1ms per listing (regex on existing HTML)
- No additional HTTP requests required
- JSON size increase: ~5-10% (promotion metadata)
- Dashboard rendering: no noticeable impact

---

## [2026-03-30] - GitHub Actions Node.js 24 Upgrade

### Changed 🔄
- **GitHub Actions:** Upgrade do Node.js 24 compatible versions
  - `actions/checkout@v4` → `actions/checkout@v6`
  - `actions/setup-python@v5` → `actions/setup-python@v6`
- **Zaktualizowane workflow'e:**
  - `.github/workflows/scan.yml`
  - `.github/workflows/weekly_report.yml`
  - `.github/workflows/keep-alive.yml`

### Fixed 🐛
- Rozwiązano deprecation warning Node.js 20 w GitHub Actions
- Przygotowanie na wymuszenie Node.js 24 (2 czerwca 2026)

### Technical Details 🔧
- Node.js 20 osiągnie EOL 30 kwietnia 2026
- GitHub Actions wymusza Node.js 24 od 2 czerwca 2026
- Wszystkie akcje teraz kompatybilne z Node.js 24
- Wymagany runner version: v2.327.1 lub nowszy (automatycznie zapewniony przez GitHub)

### References 📚
- [GitHub Blog: Deprecation of Node 20](https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/)
- [actions/checkout v6.0.0](https://github.com/actions/checkout/releases/tag/v6.0.0)
- [actions/setup-python v6.0.0](https://github.com/actions/setup-python/releases/tag/v6.0.0)

---

## [2026-04-01] - Mediana z Nowych Ogłoszeń

### Changed 🔄
- **Mediana tylko z NOWYCH ogłoszeń:**
  - Liczy się tylko ogłoszenia gdzie `first_seen == dany dzień`
  - Pokazuje jak zmieniają się ceny **nowych ofert wchodzących na rynek**
  - `None` gdy danego dnia nie dodano żadnych ogłoszeń
- **Zmienne mediany w czasie:**
  - Duże profile (wszystkie_pokoje): zmienne 775-1100 zł
  - Małe profile: dużo `None` (dodają rzadko)

### Technical Details 🔧
**Backend (scraper.py):**
```python
old_ids = set(l["id"] for l in pd_.get("current_listings", []))
new_listings = [l for l in result["listings"] if l["listing_id"] not in old_ids]
new_prices = [l["price"] for l in new_listings if ...]
median_price = calculate_median(new_prices)  # None jeśli brak nowych
```

**Rebuild (rebuild_historical_medians.py):**
```python
if first_seen == entry_date:  # DOKŁADNIE tego dnia, nie <=
    prices_on_that_day.append(price)
```

### Example 📊
**Profile "wszystkie_pokoje" (codziennie nowe):**
- 2026-03-17: 800 zł
- 2026-03-18: 950 zł ↑
- 2026-03-21: 1000 zł ↑
- 2026-03-28: 775 zł ↓
- 2026-03-31: 1100 zł ↑

**Profile "poqui" (dodają rzadko):**
- 2026-03-19: 1400 zł
- 2026-03-20-25: None (nic nie dodali)
- 2026-03-26: 1499 zł
- 2026-03-27-29: None
- 2026-03-30: 2499 zł ↑

**Profile "mzuri" (aktywny, duże wahania):**
- 850 zł → 2200 zł → 2520 zł → 1920 zł → 850 zł

---

## [2026-03-31] - Mediana Zamiast Średniej

### Changed 🔄
- **Mediana ceny** zamiast średniej/min/max:
  - Mediana = wartość środkowa (odporna na outliers)
  - Lepiej reprezentuje "typową" cenę
  - 2 przyciski zamiast 4: 📊 Ogłoszenia | 💰 Mediana ceny
- **Prawdziwe historyczne mediany:**
  - Mediana liczona dla ogłoszeń które **istniały danego dnia**
  - Używa `first_seen` ≤ data ≤ `archived_date` (lub wciąż aktywne)
  - Pokazuje **rzeczywiste zmiany cen w czasie**, nie snapshoty

### Removed ➖
- ⬇️ Min cena (przycisk i metryka)
- ⬆️ Max cena (przycisk i metryka)
- avg_price, min_price, max_price z daily_counts

### Technical Details 🔧
- **Backend:** Mediana = sorted_prices[n//2] dla nieparzystej liczby, średnia dwóch środkowych dla parzystej
- **Rebuild:** Przebudowa wszystkich historycznych median (37 dni × 6 profili)
  - Dla każdego dnia: znajdź aktywne ogłoszenia + oblicz medianę ich cen
  - Skrypt: `rebuild_historical_medians.py`
- **Frontend:** Uproszczona konfiguracja metricConfig (2 metryki zamiast 4)

### Example 📊
**Profile "poqui" - historia zmian:**
- 2026-03-22-25: 7 ogłoszeń, mediana **1400 zł**
- 2026-03-26-29: 10 ogłoszeń (pojawiły się 3 nowe), mediana **1450 zł** ↑
- 2026-03-30: 10 ogłoszeń, mediana **1499 zł** ↑
- 2026-03-31: 10 ogłoszeń, mediana **1450 zł** ↓

**Profile "dawny_patron":**
- 2026-03-22-28: 7 ogłoszeń, mediana **730 zł**
- 2026-03-29-31: 8 ogłoszeń (pojawiło się nowe), mediana **750 zł** ↑

---

## [2026-03-30] - Wykres Liniowy z Zoom i Metrykami Cenowymi

### Added ✨
- **Wykres liniowy** z pełną historią danych (wszystkie dostępne dni)
- **4 metryki do wyboru:**
  - 📊 Ogłoszenia (liczba)
  - 💰 Średnia cena
  - ⬇️ Minimalna cena
  - ⬆️ Maksymalna cena
- **Zoom interaktywny:**
  - 🖱️ Kółko myszy — przybliżanie/oddalanie
  - **Przeciąganie** — przesuwanie wykresu (pan) **bez konieczności trzymania Shift**
  - Przycisk "Reset zoom" (pojawia się po przybliżeniu)
- **Tooltips** z dokładnymi wartościami przy hover
- **Statystyki cenowe w backend:**
  - Kalkulacja `avg_price`, `min_price`, `max_price` przy każdym skanie
  - Zapis do `daily_counts` w JSON

### Changed 🔄
- Dashboard: wykres liniowy POD wykresem słupkowym
- Struktura `daily_counts` rozszerzona o pola cenowe
- Przyciski metryk z ikonkami (emoji)

### Technical Details 🔧
- **Backend:** `scraper.py` — funkcja `generate_dashboard_json()`
  - Kalkulacja: `prices = [l["price"] for l in result["listings"] if ...]`
  - Round average price: `round(sum(prices) / len(prices))`
  - Zapisywane w `daily_counts`: `avg_price`, `min_price`, `max_price`
- **Backfill:** `backfill_prices.py` — wypełnienie historycznych danych
  - Dla wpisów z `None` w cenach użyto aktualnych cen jako przybliżenia
  - Zaktualizowano ~35 wpisów na profil (36 dni historii)
- **Frontend:** `docs/index.html`
  - Nowa sekcja: `.line-chart-section` + CSS
  - Chart.js plugin: `chartjs-plugin-zoom` v2.0.1
  - **Hammer.js v2.0.8** — wymagane dla gestów przeciągania (pan)
  - Funkcja: `renderLineChart(key)` — dynamiczna zmiana danych
  - Funkcja: `switchMetric(metric, btn)` — toggle między metrykami
  - Funkcja: `resetLineChartZoom()` — reset zoom
  - Responsywne: `height: 220px`, adaptive ticks
- **CDN:**
  - `https://cdnjs.cloudflare.com/ajax/libs/hammer.js/2.0.8/hammer.min.js`
  - `https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js`
  - `https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-zoom/2.0.1/chartjs-plugin-zoom.min.js`

### Files Modified 📝
- `scraper.py` — rozszerzenie `generate_dashboard_json()` o statystyki cenowe
- `docs/index.html` — nowa sekcja HTML + CSS + JavaScript dla wykresu liniowego
- `backfill_prices.py` — skrypt jednorazowy do wypełnienia historycznych danych
- `data/dashboard_data.json` — wypełnione statystyki cenowe dla 36 dni historii

---

## [2026-03-29] - Dashboard Profile Links

### Added
- [x] Link "Zobacz na OLX" w nagłówku detail panelu
- [x] Klikany przycisk z ikoną external link
- [x] Przekierowanie do profilu OLX w nowej karcie
- [x] Hover effect i animacja

### Changed
- [x] **Dynamiczna skala Y w wykresach** — zamiast zawsze od 0
- [x] Wykres teraz pokazuje zakres od `min - 10%` do `max + 10%`
- [x] Małe różnice (405→409) są teraz widoczne na wykresie
- [x] Skala uwzględnia wybrany zakres (7/14/30 dni)

### Technical Details
- Link wyświetlany obok nazwy profilu w detail-header
- SVG icon: external link (stroke width 2)
- Stylizacja: border, padding, hover transform
- Target: `_blank` (nowa karta)
- **Chart scaling:** `heightPct = ((value - yMin) / yRange) * 100`
- **Y-axis range:** `yMin = max(0, min - 10%)`, `yMax = max + 10%`

### Files Modified
- `docs/index.html` - dodano CSS `.profile-link` + JS w `renderDetail()` + dynamic Y-scale w `renderChart()`

---

## [2026-03-29] - Email Report System Enhancement

### Stan początkowy
- Istniejący `email_report.py` z podstawowym szablonem HTML
- Workflow `weekly_report.yml` uruchamiany w poniedziałki o 9:30 CET
- Brak wykresów w emailu
- Podstawowe tabele z danymi

### Added
- [x] Matplotlib do zależności (wykresy inline Base64)
- [x] Funkcja `generate_trend_chart()` — wykresy słupkowe 7-dniowe jako Base64 PNG
- [x] Funkcja `calculate_weekly_stats()` — statystyki tygodniowe (min/max/avg)
- [x] Nowy szablon HTML z sekcją analityczną
- [x] Grid ze statystykami (aktualna liczba, zakres, średnia cena, nowe 24h)
- [x] Embedded wykresy w emailu (inline Base64)
- [x] Tabela z top 10 najnowszych ogłoszeń dla każdego profilu
- [x] Profesjonalny styling (gradienty, zaokrąglone rogi, responsive grid)

### Changed
- [x] Całkowicie przepisany `email_report.py` — nowa architektura
- [x] Zmieniony subject: "Raport analityczny" zamiast "Raport tygodniowy"
- [x] Dodano emoji do sekcji (📊, 📌, 🏠, 🤖)
- [x] Improved logging (emoji statusy ✅ ❌)

### Fixed
- [x] Stats grid layout — zmieniono z CSS Grid na `<table>` dla lepszej kompatybilności email
- [x] Karty stats wyświetlają się teraz **poziomo w jednym rzędzie** zamiast pionowo
- [x] Dodano `table-layout: fixed` i `width: 25%` dla równych kart
- [x] Używamy `<td class="stat-card">` zamiast `<div>` dla cross-client compatibility

### Technical Details
- **Matplotlib Backend:** `Agg` (non-interactive, server-safe)
- **Chart Format:** PNG → Base64 → `data:image/png;base64,...`
- **Chart Resolution:** 800x300px @ 100 DPI
- **Color Scheme:** Tailwind-inspired (#3b82f6 primary, #10b981 success, #ef4444 danger)
- **Email Size:** ~200-500KB (zależnie od liczby wykresów)
- **Email Compatibility:** Table-based layout (works in Gmail, Outlook, Apple Mail)

### Testing
- [x] Workflow triggered via GitHub API
- [x] Run ID: 23706065185
- [x] Status: ✅ SUCCESS (completed in ~20s)
- [x] Email wysłany do malczarski@gmail.com
- [x] Załącznik Excel poprawnie dołączony
- [x] Layout fix: stats cards teraz poziomo

### Files Modified
- `requirements.txt` - dodano matplotlib>=3.8.0
- `email_report.py` - kompletny rewrite (170 → 430 linii)
- `README.md` - zaktualizowana sekcja email reportów
- `CHANGELOG.md` - utworzony (nowy system dokumentacji)

---

## [2026-02-27] - Scan Timing Fix

### Changed
- Zmieniono harmonogram skanów z 6:00 UTC na 7:00 UTC (9:00 CET zimą)
- Dodano dokumentację `ZMIANA_CZASU_REMINDER.md`

### Fixed
- Problem z automatyczną dezaktywacją workflow po 60 dniach
- Dodano `keep-alive.yml` workflow

### Files Modified
- `.github/workflows/scan.yml`
- `.github/workflows/keep-alive.yml`
- `ZMIANA_CZASU_REMINDER.md` (nowy)

---

## [2026-02-20] - Initial Project Setup

### Added
- Podstawowy scraper OLX (`scraper.py`)
- GitHub Actions workflow dla daily scan
- Dashboard na GitHub Pages (`docs/index.html`)
- Excel export z historią cen
- JSON API dla dashboardu
- Email reporting system (podstawowy)

### Technical Details
- Python 3.11+
- BeautifulSoup4 dla parsowania HTML
- OpenPyXL dla Excela
- GitHub Actions dla automatyzacji
- GitHub Pages dla dashboardu

### Files Created
- `scraper.py`
- `main.py`
- `email_report.py`
- `.github/workflows/scan.yml`
- `.github/workflows/weekly_report.yml`
- `docs/index.html`
- `requirements.txt`
- `README.md`
- `PROJECT_STRUCTURE.md`
- `SETUP_GUIDE.md`

---

## Legenda typów zmian

- **Added**: Nowe funkcje
- **Changed**: Zmiany w istniejących funkcjach
- **Deprecated**: Funkcje które zostaną usunięte
- **Removed**: Usunięte funkcje
- **Fixed**: Poprawki błędów
- **Security**: Poprawki bezpieczeństwa

---

## Konwencje commitów

```
🔍 Scan: zmiany w scraper.py lub logice skanowania
📊 Data: zmiany w strukturze danych (JSON/Excel)
📧 Email: zmiany w systemie raportów email
🎨 UI: zmiany w dashboardzie (docs/index.html)
🔧 Config: zmiany w konfiguracji
📝 Docs: aktualizacje dokumentacji
🐛 Fix: poprawki błędów
✨ Feature: nowe funkcje
♻️ Refactor: refaktoryzacja bez zmian funkcjonalności
🚀 Deploy: zmiany w GitHub Actions workflow
```

---

**Ostatnia aktualizacja:** 2026-03-29
