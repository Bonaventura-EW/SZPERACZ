---
id: 2026-09-13-category-exit-archiving
repo: Bonaventura-EW/SZPERACZ
family: scrapery-olx
date: 2026-09-13
category: bugfix
what: Ogłoszenie, które nadal żyje, ale zostało przeniesione poza monitorowaną kategorię, jest archiwizowane zamiast wisieć w stanie profilu w nieskończoność.
why: Weryfikacja „czy strona żyje" nie odpowiada na pytanie „czy to nadal nasze". Autor zmienił miasto ogłoszenia z Lublina na Chełm — strona działa, więc wpis został w current_listings 16 skanów, zawyżał stan profilu, nie liczył się jako removed i codziennie odpalał alert o zupełnie innej klasie problemu. Alert świecący codziennie przestaje cokolwiek znaczyć.
how: Po kilku nieobecnościach w wynikach (próg osobny i niski — zwykła rotacja wyników mija po 1-2 przebiegach) pytamy dodatkowo o przynależność do kategorii: okruszki na stronie ogłoszenia niosą ścieżki kategorii, więc wystarczy sprawdzić, czy jest wśród nich ścieżka monitorowanej kategorii. Funkcja zwraca trójwartościowo (jest / nie ma / nie ustalono), a archiwizuje wyłącznie twarde „nie ma" — brak danych zostawia ogłoszenie w spokoju. Sprawdzenie działa tylko dla profili kategorii (nie dla profili sprzedawcy) i tylko dla ogłoszeń już nieobecnych, więc kosztuje kilka żądań na przebieg. Zarchiwizowany wpis dostaje jawny powód.
surface: scraper.py (listing_left_category, generate_dashboard_json — pętla carried/archiwizacji)
generality: family
propagate: yes
commit: (uzupełnić po merge'u)
---

# Kontekst

Wzorzec przenośny na każdy scraper, który monitoruje WYCINEK serwisu (kategorię, miasto,
tag, zapytanie) i trzyma własny stan „co jest teraz w tym wycinku": **weryfikacja istnienia
rekordu to nie to samo co weryfikacja przynależności**. Rekord może żyć i jednocześnie
przestać należeć do monitorowanego zbioru — przez edycję po stronie autora, przekategoryzowanie
albo zmianę atrybutu, po którym filtrujemy. Jeśli scraper sprawdza tylko istnienie, taki rekord
zostaje na zawsze: zawyża stan, nie liczy się jako odpływ i zatruwa alerty.

Druga lekcja jest o alertach: alert, który świeci codziennie z powodu, którego nie opisuje,
jest gorszy niż brak alertu — uczy ignorowania. Nasz `stale_listings` miał znaczyć „serwis
zmienił komunikat o nieaktualności, weryfikacja przestała działać". Zanim to naprawiliśmy,
znaczył „jedno ogłoszenie się przeprowadziło" i człowiek przestawał na niego patrzeć.

Trzecia, jeśli brat ma podobną ochronę przed fałszywym kasowaniem: trójwartościowy wynik
(tak / nie / nie wiem) i archiwizacja wyłącznie na twarde „nie" jest tu istotą, nie ozdobą.
Zmiana HTML-a po stronie serwisu ma dawać „nie wiem" i zerowy efekt, nigdy masową archiwizację.
