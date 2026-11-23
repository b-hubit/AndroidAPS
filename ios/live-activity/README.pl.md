# Glukoza na ekranie blokady, Apple Watch i CarPlay (b-hubit, gałąź ios-live-activity)

[🇬🇧 English version](README.md) · Komplikacja na tarczy: [CALENDAR.pl.md](CALENDAR.pl.md)

AAPSClient pokazuje glukozę jako Live Activity: na ekranie blokady, w Dynamic Island i w Smart
Stacku na Apple Watch (watchOS 11+) i w CarPlay (iOS 26). Wymaga iOS 18+. Aplikacja sama niczego nie aktualizuje,
bo iOS ją zamraża. Każdy nowy odczyt wysyła Twój Home Assistant jako push przez Apple.
Dane idą tylko: Nightscout → Home Assistant → Apple → Twój iPhone.

## 1. Klucz APNs (raz, na koncie deweloperskim Apple)

1. developer.apple.com → Certificates, Identifiers & Profiles → **Keys** → „+”.
2. Nazwa np. `AAPS Live`, zaznacz **Apple Push Notifications service (APNs)** → Configure →
   Environment: **Sandbox & Production** → Save → Continue → Register.
3. **Download** – plik `AuthKey_XXXXXXXXXX.p8` da się pobrać tylko raz, zachowaj go.
4. Zapisz **Key ID** (10 znaków) i **Team ID** (ten sam co w sekrecie TEAMID).

## 2. Home Assistant

1. Utwórz folder `/config/aaps_live/` i wgraj do niego:
   - `aaps_live_activity.py` (i `aaps_calendar.py` dla tarczy zegarka, zobacz CALENDAR.pl.md),
   - plik `.p8`,
   - `config.json` – skopiuj `config.example.json` i uzupełnij:
     - `team_id`, `key_id`, `key_file` (nazwa pliku .p8),
     - `bundle_id`: `org.nightscout.<TEAMID>.aapsclient`,
     - `nightscout_url` i `nightscout_token` (token z rolą `readable` z Nightscout → Admin tools),
       albo `nightscout_api_secret` zamiast tokenu,
     - `units`: `mg/dl` albo `mmol`, `low_mgdl` / `high_mgdl` – granice kolorów.

     To JSON: przecinek po każdej linii oprócz ostatniej przed `}`.
2. Dodaj `shell_command` i dwie automatyzacje z `home_assistant.yaml`. W `webhook_id` wpisz
   długi losowy ciąg zamiast `aaps_live_CHANGE_ME`. Uruchom ponownie Home Assistant.
3. Sprawdź połączenie z Nightscout: Narzędzia deweloperskie → Akcje →
   `shell_command.aaps_live_test` → Wykonaj akcję. W odpowiedzi (`stdout`) powinna być aktualna
   glukoza. Dodatek Terminal & SSH nie ma Pythona, więc skryptu nie uruchomisz z terminala –
   `shell_command` działa wewnątrz Home Assistant, który Pythona ma.

## 3. iPhone

1. Zainstaluj z TestFlight build **AAPS Live**.
2. Ustawienia iOS → **AAPS Live**:
   - Webhook: `https://<adres-twojego-HA>/api/webhook/<twoj-webhook_id>`
     (adres zewnętrzny, np. Nabu Casa, żeby działało też poza domem),
   - Włączone: tak. Adres traktuj jak hasło.
3. Ustawienia iOS → AAPS Live → **Live Activities**: włączone, także „Częstsze aktualizacje”.
4. Otwórz aplikację. Na ekranie blokady pojawi się pasek z glukozą, a po chwili pierwszy odczyt.
5. Apple Watch: obróć koronkę na tarczy – pasek jest w Smart Stacku. W aplikacji Watch → Smart Stack
   → Live Activities możesz włączyć automatyczne uruchamianie.
6. CarPlay: pasek jest na pierwszej stronie ekranu głównego (przesunięcie w prawo).

Kilka osób może obserwować jednocześnie: każdy iPhone, który otworzy aplikację z webhookiem, ma
własny pasek.

## Jak to działa

- Co 30 s Home Assistant sprawdza Nightscout. Nowy odczyt idzie od razu, a minuty „3' temu”
  odświeża raz na minutę pushem o niskim priorytecie, który nie zużywa limitu aplikacji.
- iOS kończy Live Activity po 8 godzinach. Po 7 h 45 min Home Assistant sam uruchamia nową
  (push-to-start, iOS 17.2+), bez otwierania aplikacji. Jeśli pasek kiedyś zniknie,
  wystarczy otworzyć aplikację.
- Stan jest w `/config/aaps_live/state.json`. `shell_command.aaps_live_status` pokazuje każdy
  iPhone: czy są tokeny, wiek paska i kiedy poszedł ostatni odczyt.

## Problemy

| Objaw | Przyczyna / rozwiązanie |
|---|---|
| `status` nie pokazuje żadnego iPhone'a | aplikacja nie dotarła do webhooka: sprawdź adres w Ustawieniach iOS, `local_only: false`, ślady automatyzacji |
| Pasek pokazuje tylko „--” | Apple odrzuca pushe: ustaw `logger` `homeassistant.components.shell_command: debug` i szukaj `aaps_live:` w logach (`APNs 403` = zły Key ID / Team ID) |
| Pasek jest na iPhonie, a nie ma go na zegarku | uruchom ponownie iPhone'a i zegarek (błąd iOS 26); sprawdź Watch → Smart Stack → Live Activities |
| Adres webhooka znika z Ustawień iOS | buildy starsze niż 1522067 – zainstaluj nowszy |
| `JSONDecodeError` | brak przecinka w `config.json` |
