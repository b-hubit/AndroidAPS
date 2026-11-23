# Glukoza na tarczy Apple Watch – komplikacja Kalendarz (gałąź komplikacja)

Komplikacje innych aplikacji Apple pozwala odświeżać ok. 4 razy na godzinę. Systemowa komplikacja
**Kalendarz** nie ma tego limitu, więc Home Assistant przy każdym odczycie aktualizuje jedno
wydarzenie w Twoim kalendarzu iCloud, np. „116 ↗ +3” o godzinie odczytu. Zegarek pokazuje je obok
zegara albo w kółku, na każdej tarczy z komplikacją Kalendarz. AAPSClient nie jest do tego potrzebny.

Wydarzenie trwa 20 minut od odczytu. Gdy nowy odczyt nie przyjdzie, znika z tarczy, zamiast udawać
aktualną wartość.

## 1. Osobny kalendarz

Na iPhonie: Kalendarz → Kalendarze → Dodaj kalendarz → nazwa **Glukoza**, konto **iCloud**.
W ustawieniach tego kalendarza wyłącz powiadomienia, jeśli się pojawiają.
Na zegarku powinien być widoczny automatycznie (aplikacja Watch → Kalendarz → kalendarze).

## 2. Hasło do aplikacji

account.apple.com → Logowanie i bezpieczeństwo → **Hasła do aplikacji** → utwórz, np. „Home Assistant”.
To jest osobne hasło tylko do kalendarza – nie podawaj swojego hasła Apple ID.

## 3. Home Assistant

1. Wgraj `aaps_calendar.py` do `/config/aaps_live/` (obok `aaps_live_activity.py`, korzysta z niego).
2. W `/config/aaps_live/config.json` dopisz:
   ```json
   "icloud_user": "twoj@apple.id",
   "icloud_app_password": "xxxx-xxxx-xxxx-xxxx",
   "calendar_name": "Glukoza"
   ```
3. W `configuration.yaml`, w `shell_command`, dopisz `aaps_calendar_tick` i `aaps_calendar_test`,
   a w automatyzacji „AAPS Live: nowy odczyt” drugą akcję `shell_command.aaps_calendar_tick`
   (wszystko w `home_assistant.yaml`). Uruchom ponownie Home Assistant.
4. Narzędzia deweloperskie → Akcje → `shell_command.aaps_calendar_test` – w `stdout` powinien być
   adres kalendarza Glukoza. Błąd 401 = złe hasło do aplikacji, „no calendar named” = inna nazwa.

## 4. Tarcza

Przytrzymaj tarczę → Edytuj → Komplikacje → wybierz miejsce → **Kalendarz** (wersja z tekstem
wydarzenia, np. „Najbliższe wydarzenie”). Najlepsze są tarcze z dużym polem tekstowym, np. Modułowa,
Infograf Modułowy, Kalifornia.

Drugi tester: udostępnij mu kalendarz Glukoza w iCloud (Kalendarz → (i) przy Glukoza → Dodaj osobę).
