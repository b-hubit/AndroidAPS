# Fork AndroidAPS b-hubit – AAPSClient na iOS

[🇬🇧 English version](B-HUBIT.md)

Ten fork buduje **AAPSClient** na iOS (aplikację AAPS do podglądu i zdalnego sterowania na iPhonie, nową w AAPS 4.0) w GitHub Actions, bez Maca, i wysyła ją do TestFlight. Zawiera też poprawki, które są tu najpierw testowane, a potem zgłaszane twórcom. Oficjalny projekt to [nightscout/AndroidAPS](https://github.com/nightscout/AndroidAPS); jego własny opis jest w [README.md](README.md).

## Ta gałąź: `ios-live-activity` (aktualny codzienny build)

**Co zawiera:** wszystko z `ios-trend-arrow` oraz:

| Zmiana | Po co | U twórców |
|---|---|---|
| Alarm „brak odczytów BG” czeka na Nightscout po starcie / powrocie z tła i sam znika po świeżym odczycie; nowe połączenie z Nightscout po ponad minucie w tle | fałszywy alarm i stara glukoza przez 1–2 min po otwarciu | [#5495](https://github.com/nightscout/AndroidAPS/issues/5495), poprawione w `dev` |
| **Live Activity**: glukoza, strzałka, delta, minuty od odczytu, IOB, COB na ekranie blokady, w Dynamic Island, na Apple Watch (Smart Stack) i w CarPlay | iOS zamraża aplikację, więc glukoza jest na ekranie tylko wtedy, gdy ktoś ją wypycha; tu robi to Twój Home Assistant przez Apple | tylko fork |
| **Komplikacja Kalendarz**: Home Assistant trzyma jedno wydarzenie w kalendarzu iCloud z najnowszym odczytem | komplikacje innych aplikacji odświeżają się ok. 4×/h, Kalendarz nie ma tego limitu | tylko fork |
| Strona w Ustawieniach iOS (adres webhooka) wyłączona z migracji ustawień AAPS | adres znikał przy każdym starcie | tylko fork |

**Jak działa:** Nightscout → Home Assistant (`ios/live-activity/aaps_live_activity.py`, co 30 s)
→ push Apple → iPhone / zegarek / CarPlay. Aplikacja tylko podaje Home Assistant, dokąd wysyłać
(webhook); każdy iPhone ma własny pasek, a Home Assistant odnawia go przed 8-godzinnym limitem iOS.
Nic nie trafia na cudze serwery.

**Budowanie:** Actions → **iOS TestFlight** → Run workflow → gałąź `ios-live-activity`. W TestFlight
jako **AAPS Live**. Workflow sam rejestruje dodatkowy identyfikator (`…aapsclient.LiveActivity`)
i włącza powiadomienia push dla aplikacji.

**Konfiguracja (raz):**
1. Klucz APNs i Home Assistant: [`ios/live-activity/README.pl.md`](ios/live-activity/README.pl.md)
2. Komplikacja na tarczy: [`ios/live-activity/CALENDAR.pl.md`](ios/live-activity/CALENDAR.pl.md)
3. Na każdym iPhonie: Ustawienia iOS → AAPS Live → adres webhooka, Live Activities włączone,
   raz otworzyć aplikację.

**Problemy:** `shell_command.aaps_live_status` w Home Assistant pokazuje stan każdego iPhone'a.
Brak paska na zegarku, choć jest na iPhonie: uruchom ponownie iPhone'a i zegarek (błąd iOS 26).

**Przy nowym wydaniu AAPS:** wmerguj `master`; weź poprawki twórców dla #5484, #5485, #5495 i usuń
nasze; zostaw pliki Live Activity (`ios/app/LiveActivity`, `ios/app/Shared/*Activity*`,
`ios/live-activity`), wpisy w projekcie Xcode i podpisywanie rozszerzenia w Fastlane.

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
