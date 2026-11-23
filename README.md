# AAPSClient na iOS – historia buildów TestFlight (b-hubit)

Każdy build z workflow **„iOS TestFlight”** w tym repo. Numer buildu to liczba minut od 1.01.2024
w chwili budowania, więc rośnie z czasem i nigdy się nie powtarza. Wersja aplikacji to zawsze 4.0.0.

Każdy build zawiera wszystko z wcześniejszych buildów tej samej linii zmian
(`ios-trend-arrow` → `ios-perf-test` → `ios-bg-alarm-test` → `ios-live-activity`).

| Build | Data | Nazwa w TestFlight | Gałąź | Commit | Co weszło | Status |
|---|---|---|---|---|---|---|
| 1491088 | 01.11.2026 | AAPSClient | `b-hubit-ios-match` | [`d8eb54a`](https://github.com/b-hubit/AndroidAPS/commit/d8eb54a) | Pierwszy AAPSClient na iOS z GitHub Actions: czysty, oficjalny 4.0.0 bez zmian | aktywny |
| 1492395 | 02.11.2026 | AAPSClient | `ios-trend-arrow` | [`bba8e17`](https://github.com/b-hubit/AndroidAPS/commit/bba8e17) | Strzałka trendu z Dexcoma zamiast liczonej przez AAPS | aktywny |
| 1495347 | 04.11.2026 | AAPS Perf test | `ios-perf-test` | [`4efdc95`](https://github.com/b-hubit/AndroidAPS/commit/4efdc95) | Perf 1: szybsze logowanie, kursory Nightscout, statystyki liczone tylko na ekranie. Efekt: „nawet wolniej” | wygaszony |
| 1495406 | 04.11.2026 | AAPS Perf test | `ios-perf-test` | [`64f93fa`](https://github.com/b-hubit/AndroidAPS/commit/64f93fa) | Perf 2: pomiary czasu startu w logu, żeby znaleźć przyczynę | wygaszony |
| 1495471 | 04.11.2026 | AAPS Perf test | `ios-perf-test` | [`9f7f2b5`](https://github.com/b-hubit/AndroidAPS/commit/9f7f2b5) | Perf 3: zapamiętana strefa czasowa i wcześniejsze przeliczenie IOB – start z ok. 1 min do ok. 10 s (zgłoszenia #5484, #5485) | wygaszony |
| 1495539 | 04.11.2026 | AAPSClient | `ios-trend-arrow` | [`cff61f9`](https://github.com/b-hubit/AndroidAPS/commit/cff61f9) | Codzienny build: strzałka Dexcom + poprawki szybkości z Perf 3 | aktywny |
| 1498040 | 06.11.2026 | AAPS Test | `ios-bg-alarm-test` | [`3ea4bd2`](https://github.com/b-hubit/AndroidAPS/commit/3ea4bd2) | Test 1: alarm „brak odczytów BG” czeka, aż Nightscout doczyta dane, i sam znika po świeżym odczycie | wygaszony |
| 1498261 | 06.11.2026 | AAPS Test | `ios-bg-alarm-test` | [`ad9e314`](https://github.com/b-hubit/AndroidAPS/commit/ad9e314) | Test 2: nowe połączenie z Nightscout po powrocie z tła, poprawione czekanie po zamrożeniu (zgłoszenie #5495) | aktywny |
| 1521870 | 22.11.2026 | AAPS Live | `ios-live-activity` | [`32daab5`](https://github.com/b-hubit/AndroidAPS/commit/32daab5) | Glukoza na ekranie blokady, w Dynamic Island i na Apple Watch (Live Activity), pushe z Home Assistant | wygaszony |
| 1522067 | 23.11.2026 | AAPS Live | `ios-live-activity` | [`19bf4c4`](https://github.com/b-hubit/AndroidAPS/commit/19bf4c4) | Adres webhooka nie znika już z Ustawień iOS przy starcie | wygaszony |
| 1522097 | 23.11.2026 | AAPS Live | `ios-live-activity` | [`640d4df`](https://github.com/b-hubit/AndroidAPS/commit/640d4df) | Glukoza w jednej linii + licznik czasu (błąd: pusty pasek) | wygaszony |
| 1522118 | 23.11.2026 | AAPS Live | `ios-live-activity` | [`9a6b1b6`](https://github.com/b-hubit/AndroidAPS/commit/9a6b1b6) | Godzina odczytu zamiast licznika – pasek znowu widoczny | wygaszony |
| 1522547 | 23.11.2026 | AAPS Live | `ios-live-activity` | [`bcf2d50`](https://github.com/b-hubit/AndroidAPS/commit/bcf2d50) | „3' temu” zamiast godziny, minuty odświeżane przez Home Assistant | **aktualny** |

## Gałęzie

| Gałąź | Do czego |
|---|---|
| `master` | Czysta kopia oficjalnego `nightscout/AndroidAPS` + workflow do TestFlight. Bez własnych zmian w aplikacji. |
| `dev` | Czysta kopia oficjalnej gałęzi `dev` (wersja rozwojowa 4.0.1-dev). |
| `ios-trend-arrow` | Codzienny build: strzałka Dexcom + szybszy start. |
| `ios-perf-test` | Testy szybkości startu (zakończone, wmergowane do `ios-trend-arrow`). |
| `ios-bg-alarm-test` | Testy alarmu „brak odczytów BG” (czeka na wydanie 4.0.1 z poprawką twórców). |
| `ios-live-activity` | AAPS Live: wszystko powyżej + glukoza na ekranie blokady i Apple Watch. Konfiguracja Home Assistant w `ios/live-activity`. |
| `ios-builds` | Ta tabela. |

## Zgłoszenia w oficjalnym repo

| Zgłoszenie | Temat | Stan |
|---|---|---|
| [#5484](https://github.com/nightscout/AndroidAPS/issues/5484) | Wolny start na iOS (strefa czasowa) | Poprawione w `dev` (`d891e61`, `11f05d3`) |
| [#5485](https://github.com/nightscout/AndroidAPS/issues/5485) | Pierwsze przeliczenie IOB czeka na zdarzenie | Poprawione w `dev` (`4399aea`, `9668ca4`) |
| [#5495](https://github.com/nightscout/AndroidAPS/issues/5495) | Fałszywy alarm „brak odczytów BG” po starcie / powrocie | Poprawione w `dev` (`3c05320`) |
| [#5512](https://github.com/nightscout/AndroidAPS/issues/5512) | Inna strzałka trendu niż w Dexcomie | Otwarte |
