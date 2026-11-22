# Glukoza na ekranie blokady i Apple Watch (b-hubit, gałąź ios-live-activity)

AAPSClient pokazuje glukozę jako Live Activity: na ekranie blokady, w Dynamic Island i w Smart
Stacku na Apple Watch (watchOS 11+, iPhone z iOS 18+). Aplikacja sama niczego nie aktualizuje,
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
   - `aaps_live_activity.py` (z tego folderu),
   - plik `.p8`,
   - `config.json` – skopiuj `config.example.json` i uzupełnij:
     - `team_id`, `key_id`, `key_file` (nazwa pliku .p8),
     - `bundle_id`: `org.nightscout.<TEAMID>.aapsclient`,
     - `nightscout_url` i `nightscout_token` (token z rolą `readable` z Nightscout → Admin tools),
       albo `nightscout_api_secret` zamiast tokenu,
     - `units`: `mg/dl` albo `mmol`, `low_mgdl` / `high_mgdl` – granice kolorów.
2. Sprawdź połączenie z Nightscout: Narzędzia deweloperskie → Akcje →
   `shell_command.aaps_live_tick` po dodaniu konfiguracji, albo w terminalu HA:
   `python3 /config/aaps_live/aaps_live_activity.py test` – powinien wypisać aktualną glukozę.
3. Dodaj `shell_command` i dwie automatyzacje z `home_assistant.yaml`. W `webhook_id` wpisz
   długi losowy ciąg zamiast `aaps_live_ZMIEN_MNIE`. Uruchom ponownie Home Assistant.

## 3. iPhone

1. Zainstaluj z TestFlight build **AAPS Live**.
2. Ustawienia iOS → **AAPS Live**:
   - Webhook: `https://<adres-twojego-HA>/api/webhook/<twoj-webhook_id>`
     (adres zewnętrzny, np. Nabu Casa, żeby działało też poza domem),
   - Włączone: tak.
3. Ustawienia iOS → AAPS Live → **Live Activities**: włączone, także „Częstsze aktualizacje”.
4. Otwórz aplikację. Na ekranie blokady pojawi się pasek z glukozą, a po chwili pierwszy odczyt.
5. Apple Watch: przewiń Smart Stack (obróć koronkę na tarczy) – pasek jest tam automatycznie.

## Jak to działa

- Co 30 s Home Assistant sprawdza Nightscout i przy nowym odczycie wysyła push.
- iOS kończy Live Activity po 8 godzinach. Po 7 h 45 min Home Assistant sam uruchamia nową
  (push-to-start, iOS 17.2+), bez otwierania aplikacji. Jeśli pasek kiedyś zniknie,
  wystarczy otworzyć aplikację.
- Stan (tokeny) jest w `/config/aaps_live/state.json`. Usunięcie tego pliku i otwarcie
  aplikacji zaczyna wszystko od nowa.
- Błędy widać w logach Home Assistant (wpisy `aaps_live:`).
