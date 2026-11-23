# Fork AndroidAPS b-hubit – AAPSClient na iOS

[🇬🇧 English version](B-HUBIT.md)

Ten fork buduje **AAPSClient** na iOS (aplikację AAPS do podglądu i zdalnego sterowania na iPhonie, nową w AAPS 4.0) w GitHub Actions, bez Maca, i wysyła ją do TestFlight. Zawiera też poprawki, które są tu najpierw testowane, a potem zgłaszane twórcom. Oficjalny projekt to [nightscout/AndroidAPS](https://github.com/nightscout/AndroidAPS); jego własny opis jest w [README.md](README.md).

## Ta gałąź: `ios-trend-arrow`

**Co zawiera:** `master` i dwie poprawki klienta na iOS:

| Zmiana | Po co | U twórców |
|---|---|---|
| Strzałka trendu ze źródła CGM (Dexcom) zamiast liczonej przez AAPS 4.0 z ostatnich 5 minut | AAPS 4.0 zawsze rysuje własną strzałkę, często inną niż w aplikacji Dexcom | [#5512](https://github.com/nightscout/AndroidAPS/issues/5512), otwarte |
| Szybszy start: zapamiętana strefa czasowa, szybsze logowanie, zapamiętane kursory Nightscout, statystyki liczone tylko na ekranie, pierwsze przeliczenie IOB od razu po starcie | klient potrzebował ok. 1 minuty po otwarciu, teraz ok. 10 s | [#5484](https://github.com/nightscout/AndroidAPS/issues/5484), [#5485](https://github.com/nightscout/AndroidAPS/issues/5485), poprawione w `dev` |

**Dlaczego zostaje:** zapasowy codzienny build bez Live Activity i bez Home Assistant.
`ios-live-activity` zawiera wszystko z tej gałęzi.

**Budowanie:** Actions → **iOS TestFlight** → Run workflow → gałąź `ios-trend-arrow`. W TestFlight
jako **AAPSClient** (ostatni build 1495539).

**Przy nowym wydaniu AAPS:** wmerguj `master` do tej gałęzi; tam, gdzie twórcy poprawili ten sam
problem (start, IOB), weź ich kod i usuń nasz; strzałkę zostaw, dopóki #5512 nie jest rozwiązane.

## Gałęzie

| Gałąź | Do czego | Nazwa w TestFlight |
|---|---|---|
| [`master`](https://github.com/b-hubit/AndroidAPS/tree/master) | oficjalny AAPS + budowanie, bez zmian w aplikacji | AAPSClient |
| [`dev`](https://github.com/b-hubit/AndroidAPS/tree/dev) | kopia oficjalnego `dev` (4.0.1-dev), nie jest budowana | – |
| [`ios-trend-arrow`](https://github.com/b-hubit/AndroidAPS/tree/ios-trend-arrow) | strzałka Dexcom + szybszy start (build zapasowy) | AAPSClient |
| [`ios-live-activity`](https://github.com/b-hubit/AndroidAPS/tree/ios-live-activity) | wszystko + poprawka alarmu + Live Activity + komplikacja Kalendarz (**codzienny build**) | AAPS Live |
| [`ios-builds`](https://github.com/b-hubit/AndroidAPS/tree/ios-builds) | historia wszystkich buildów TestFlight | – |

## Budowanie

1. Actions → **iOS TestFlight** → **Run workflow** → wybierz gałąź → Run. Ok. 40–60 min.
2. Build pojawia się w TestFlight 5–15 min później (App Store Connect → AAPSClient → TestFlight).
   Numer buildu to liczba minut od 1.01.2024, więc zawsze rośnie. Zapisz go w `ios-builds`.
3. Już skonfigurowane (potrzebne ponownie tylko w nowej organizacji): sekrety organizacji `TEAMID`,
   `FASTLANE_KEY_ID`, `FASTLANE_ISSUER_ID`, `FASTLANE_KEY` (klucz API App Store Connect, rola App
   Manager), `GH_PAT`, `MATCH_PASSWORD`; certyfikaty w `b-hubit/Match-Secrets`; identyfikator
   `org.nightscout.<TEAMID>.aapsclient` i aplikacja w App Store Connect z wewnętrzną grupą testerów.
4. Uwagi: zadanie działa tylko dla właściciela `b-hubit`; framework Kotlin jest budowany jako Debug,
   bo Release zużywa za dużo pamięci na macOS w GitHub Actions.

## Nowe wydanie AAPS

1. `master` → **Sync fork → Update branch**. Spodziewaj się konfliktu w
   `.github/workflows/ios-testflight.yml`: 4.0.1 przynosi własny plik o tej nazwie. Zostaw nasz pod
   inną nazwą, np. `b-hubit-ios-testflight.yml`, żeby oba mogły istnieć.
2. Wmerguj `master` do `ios-trend-arrow` i `ios-live-activity` (pull request `master` → gałąź).
3. Zbuduj, przetestuj na telefonie, dopisz buildy w `ios-builds`.

## Zgłoszenia u twórców

| Zgłoszenie | Temat | Stan |
|---|---|---|
| [#5484](https://github.com/nightscout/AndroidAPS/issues/5484) | wolny start na iOS (strefa czasowa) | poprawione w `dev` |
| [#5485](https://github.com/nightscout/AndroidAPS/issues/5485) | pierwsze przeliczenie IOB czeka na zdarzenie | poprawione w `dev` |
| [#5495](https://github.com/nightscout/AndroidAPS/issues/5495) | fałszywy alarm „brak odczytów BG” po starcie / powrocie | poprawione w `dev` |
| [#5512](https://github.com/nightscout/AndroidAPS/issues/5512) | strzałka trendu inna niż w Dexcomie | otwarte |

## Zasady

- [CONTRIBUTING.md](CONTRIBUTING.md) AAPS nie przyjmuje pull requestów napisanych przez AI. Problemy
  zgłaszaj twórcom jako issue z opisem, nie wysyłaj kodu z tego forka. Prace w tym forku powstały
  z pomocą asystenta AI (Claude) i były testowane na własnych urządzeniach.
- Nigdy nie commituj sekretów: `config.json`, `*.p8` i `state.json` części Home Assistant są
  w `.gitignore`.
