# b-hubit fork of AndroidAPS – iOS AAPSClient

[🇵🇱 Wersja polska](B-HUBIT.pl.md)

This fork builds the iOS **AAPSClient** (the AAPS follower and remote-control app for iPhone, new in AAPS 4.0) on GitHub Actions, without a Mac, and ships it to TestFlight. It also carries improvements that are tested here first and reported upstream. The official project is [nightscout/AndroidAPS](https://github.com/nightscout/AndroidAPS); its own README is [README.md](README.md).

## This branch: `ios-live-activity` (current everyday build)

**What it is:** everything from `ios-trend-arrow`, plus:

| Change | Why | Upstream |
|---|---|---|
| "BG readings missed" alarm waits for Nightscout after start / return from the background and clears itself when a fresh reading arrives; a fresh Nightscout connection after the app was in the background for over a minute | false missed-readings alarm and old glucose for 1–2 min after opening | [#5495](https://github.com/nightscout/AndroidAPS/issues/5495), fixed upstream in `dev` |
| **Live Activity**: glucose, arrow, delta, minutes since the reading, IOB, COB on the Lock Screen, in the Dynamic Island, on Apple Watch (Smart Stack) and in CarPlay | iOS freezes the app, so the screen shows glucose only if something pushes it; here your own Home Assistant pushes every reading through Apple | fork only |
| **Calendar complication**: Home Assistant keeps one iCloud calendar event with the newest reading | third-party watch complications refresh only ~4×/hour; the Calendar complication has no such limit | fork only |
| Settings page in iOS Settings (webhook address) kept out of the AAPS preferences migration | the address vanished on every start | fork only |

**How it works:** Nightscout → Home Assistant (`ios/live-activity/aaps_live_activity.py`, every 30 s)
→ Apple Push → iPhone / Watch / CarPlay. The app only tells Home Assistant where to push (a webhook);
every iPhone gets its own Live Activity, and Home Assistant restarts it before iOS's 8-hour limit.
Nothing goes to third-party servers.

**Build:** Actions → **iOS TestFlight** → Run workflow → branch `ios-live-activity`. Shows in
TestFlight as **AAPS Live**. The workflow registers the extra App ID (`…aapsclient.LiveActivity`)
and turns on Push for the app by itself.

**Set-up (once):**
1. APNs key and Home Assistant: [`ios/live-activity/README.md`](ios/live-activity/README.md)
2. Watch face complication: [`ios/live-activity/CALENDAR.md`](ios/live-activity/CALENDAR.md)
3. On each iPhone: iOS Settings → AAPS Live → webhook address, Live Activities on, open the app once.

**Troubleshooting:** `shell_command.aaps_live_status` in Home Assistant shows each iPhone's state.
No bar on the Watch although it is on the iPhone: restart iPhone and Watch (an iOS 26 issue).

**To do on a new AAPS release:** merge `master`; take the upstream fixes for #5484, #5485, #5495 and
drop ours; keep the Live Activity files (`ios/app/LiveActivity`, `ios/app/Shared/*Activity*`,
`ios/live-activity`), the Xcode project entries and the Fastlane extension signing.

## Branches

| Branch | Purpose | TestFlight name |
|---|---|---|
| [`master`](https://github.com/b-hubit/AndroidAPS/tree/master) | official AAPS + build pipeline, no app changes | AAPSClient |
| [`dev`](https://github.com/b-hubit/AndroidAPS/tree/dev) | copy of official `dev` (4.0.1-dev), not built | – |
| [`ios-trend-arrow`](https://github.com/b-hubit/AndroidAPS/tree/ios-trend-arrow) | Dexcom trend arrow + faster start (fallback build) | AAPSClient |
| [`ios-live-activity`](https://github.com/b-hubit/AndroidAPS/tree/ios-live-activity) | everything + alarm fix + Live Activity + Calendar complication (**everyday build**) | AAPS Live |
| [`ios-builds`](https://github.com/b-hubit/AndroidAPS/tree/ios-builds) | history of every TestFlight build | – |

## Building

1. Actions → **iOS TestFlight** → **Run workflow** → choose the branch → Run. About 40–60 min.
2. TestFlight shows the build 5–15 min later (App Store Connect → AAPSClient → TestFlight). The build
   number is the minutes since 1 Jan 2024, so it only grows. Record it in `ios-builds`.
3. Already in place (only needed again for a new organisation): org secrets `TEAMID`,
   `FASTLANE_KEY_ID`, `FASTLANE_ISSUER_ID`, `FASTLANE_KEY` (App Store Connect API key, App Manager),
   `GH_PAT`, `MATCH_PASSWORD`; certificates in `b-hubit/Match-Secrets`; App ID
   `org.nightscout.<TEAMID>.aapsclient` and its App Store Connect record with an internal test group.
4. Notes: the job runs only for the `b-hubit` owner; the Kotlin framework is built as Debug because
   Release runs out of memory on GitHub's macOS runners.

## New AAPS release

1. `master` → **Sync fork → Update branch**. Expect a conflict in `.github/workflows/ios-testflight.yml`:
   upstream 4.0.1 brings its own file with that name. Keep ours (rename it, e.g. to
   `b-hubit-ios-testflight.yml`) so both can exist.
2. Merge `master` into `ios-trend-arrow` and `ios-live-activity` (a pull request `master` → branch).
3. Build, test on the phone, add the builds to `ios-builds`.

## Upstream issues

| Issue | Topic | State |
|---|---|---|
| [#5484](https://github.com/nightscout/AndroidAPS/issues/5484) | slow start on iOS (time zone) | fixed in `dev` |
| [#5485](https://github.com/nightscout/AndroidAPS/issues/5485) | first IOB calculation waits for an event | fixed in `dev` |
| [#5495](https://github.com/nightscout/AndroidAPS/issues/5495) | false "BG readings missed" after start / resume | fixed in `dev` |
| [#5512](https://github.com/nightscout/AndroidAPS/issues/5512) | trend arrow differs from Dexcom | open |

## Rules

- AAPS [CONTRIBUTING.md](CONTRIBUTING.md) does not accept AI-generated pull requests. Report problems
  upstream as issues with a description; do not send this fork's code as pull requests. The work in
  this fork was done with help of an AI assistant (Claude) and tested on our own devices.
- Never commit secrets: `config.json`, `*.p8` and `state.json` of the Home Assistant part are in
  `.gitignore`.
