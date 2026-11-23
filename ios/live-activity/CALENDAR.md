# Glucose on the Apple Watch face – Calendar complication (b-hubit, branch ios-live-activity)

[🇵🇱 Wersja polska](CALENDAR.pl.md)

Apple lets third-party watch complications refresh about 4 times an hour. The system **Calendar**
complication has no such limit, so Home Assistant keeps one event in an iCloud calendar up to date
with every reading, e.g. "116 ↗ +3" at the time of the reading. The watch shows it on any face with
a Calendar complication. No AAPSClient build is needed for this.

The event lasts 20 minutes from the reading. If no new reading comes, it disappears from the face
instead of showing an old value as current.

## 1. A separate calendar

iPhone: Calendar → Calendars → Add Calendar → name **Glukoza** (or any, matching `calendar_name`),
account **iCloud**. Turn off its alerts if any appear.

## 2. App-specific password

account.apple.com → Sign-In and Security → **App-Specific Passwords** → create one, e.g.
"Home Assistant". Never use the Apple ID password itself.

## 3. Home Assistant

1. Put `aaps_calendar.py` in `/config/aaps_live/` (next to `aaps_live_activity.py`, which it uses).
2. Add to `/config/aaps_live/config.json` (mind the commas):
   ```json
   "icloud_user": "you@apple.id",
   "icloud_app_password": "xxxx-xxxx-xxxx-xxxx",
   "calendar_name": "Glukoza"
   ```
3. `configuration.yaml` → `shell_command`: add `aaps_calendar_tick` and `aaps_calendar_test`; in the
   automation "AAPS Live: new reading" add a second action `shell_command.aaps_calendar_tick`
   (all in `home_assistant.yaml`). Restart Home Assistant.
4. Developer tools → Actions → `shell_command.aaps_calendar_test`: `stdout` shows the calendar
   address. HTTP 401 = wrong app-specific password; "no calendar named" = different name.

## 4. Watch face

Easiest on the iPhone: Watch app → **Face Gallery** → a face with a large text field, e.g.
**Modular** or **Modular Duo** → Complications → the large middle field → **Calendar → Your Schedule**
→ Add. ("Today's Date" shows only the date.)

To show only the glucose calendar on the Watch: Watch app → My Watch → Calendar → **Custom** → leave
only Glukoza ticked. The Calendar app on the Watch then hides your other events too.

Another person: share the Glukoza calendar with them in iCloud (Calendar → (i) next to Glukoza →
Add Person).
