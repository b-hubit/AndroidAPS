# Glucose on the Lock Screen, Apple Watch and CarPlay (b-hubit, branch ios-live-activity)

[🇵🇱 Wersja polska](README.pl.md) · Watch face complication: [CALENDAR.md](CALENDAR.md)

The iOS AAPSClient shows glucose as a **Live Activity**: on the Lock Screen, in the Dynamic Island,
in the Apple Watch Smart Stack (watchOS 11+) and in CarPlay (iOS 26). The app cannot update it
itself – iOS freezes it in the background – so your own **Home Assistant** pushes every new reading
through Apple. Data only goes Nightscout → Home Assistant → Apple → your iPhone. Needs iOS 18+.

## 1. APNs key (once, in the Apple developer account)

1. developer.apple.com → Certificates, Identifiers & Profiles → **Keys** → "+".
2. Name e.g. `AAPS Live`, tick **Apple Push Notifications service (APNs)** → Configure →
   Environment **Sandbox & Production** → Save → Continue → Register.
3. **Download** `AuthKey_XXXXXXXXXX.p8` – it can be downloaded only once, keep it safe.
4. Note the **Key ID** (10 characters) and the **Team ID** (same as the `TEAMID` secret).

## 2. Home Assistant

1. Create `/config/aaps_live/` and put in it:
   - `aaps_live_activity.py` (and `aaps_calendar.py` for the watch face, see CALENDAR.md),
   - the `.p8` file,
   - `config.json` – copy `config.example.json` and fill in:
     - `team_id`, `key_id`, `key_file` (the .p8 file name),
     - `bundle_id`: `org.nightscout.<TEAMID>.aapsclient`,
     - `nightscout_url` and `nightscout_token` (a token with the `readable` role, Nightscout →
       Admin tools), or `nightscout_api_secret` instead,
     - `units`: `mg/dl` or `mmol`; `low_mgdl` / `high_mgdl` – colour limits.

     It is JSON: a comma after every line except the last one before `}`.
2. Add the `shell_command` block and the two automations from `home_assistant.yaml`. Put a long
   random string in `webhook_id` instead of `aaps_live_CHANGE_ME`. Restart Home Assistant.
3. Check Nightscout: Developer tools → Actions → `shell_command.aaps_live_test` → Perform action.
   `stdout` should show the current glucose. The Terminal & SSH add-on has no Python – the scripts
   only run through `shell_command`, inside Home Assistant.

## 3. Each iPhone

1. Install **AAPS Live** from TestFlight.
2. iOS Settings → **AAPS Live**: Webhook `https://<your HA external address>/api/webhook/<webhook_id>`
   (external, e.g. Nabu Casa, so it also works away from home), Enabled on. Treat the address
   like a password.
3. iOS Settings → AAPS Live → **Live Activities**: on, with "More Frequent Updates".
4. Open the app. The bar appears on the Lock Screen and the first reading follows.
5. Apple Watch: turn the Digital Crown on the face – the bar is in the Smart Stack. Watch app →
   Smart Stack → Live Activities lets you switch on Auto-Launch.
6. CarPlay: the bar is on the first Home Screen page (swipe right).

Several people can follow at once: every iPhone that opens the app with the webhook gets its own bar.

## How it works

- Every 30 s Home Assistant reads Nightscout. A new reading is pushed right away; the "3' ago" minutes
  are refreshed once a minute with low-priority pushes, which do not use the app's push budget.
- iOS ends a Live Activity after 8 hours. After 7 h 45 min Home Assistant ends it and starts a new
  one by push (push-to-start), without opening the app.
- State is in `/config/aaps_live/state.json`. `shell_command.aaps_live_status` shows each iPhone:
  whether its tokens are known, the activity's age and when the last reading went out.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `status` shows no iPhone | the app has not reached the webhook: check the address in iOS Settings, `local_only: false`, the automation's traces |
| Bar shows "--" only | pushes rejected: set `logger` `homeassistant.components.shell_command: debug` and look for `aaps_live:` in the log (`APNs 403` = wrong Key ID / Team ID) |
| Bar on iPhone but not on the Watch | restart iPhone and Watch (an iOS 26 issue); check Watch app → Smart Stack → Live Activities |
| Webhook address disappears from iOS Settings | builds before 1522067 – install a newer one |
| `JSONDecodeError` | a missing comma in `config.json` |
