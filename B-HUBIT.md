# b-hubit fork of AndroidAPS – iOS AAPSClient

[🇵🇱 Wersja polska](B-HUBIT.pl.md)

This fork builds the iOS **AAPSClient** (the AAPS follower and remote-control app for iPhone, new in AAPS 4.0) on GitHub Actions, without a Mac, and ships it to TestFlight. It also carries improvements that are tested here first and reported upstream. The official project is [nightscout/AndroidAPS](https://github.com/nightscout/AndroidAPS); its own README is [README.md](README.md).

## This branch: `ios-trend-arrow`

**What it is:** `master` plus two improvements for the iOS client:

| Change | Why | Upstream |
|---|---|---|
| Trend arrow from the CGM source (Dexcom) instead of the one AAPS 4.0 calculates from the last 5 minutes | AAPS 4.0 always draws its own arrow, which often differs from the Dexcom app | [#5512](https://github.com/nightscout/AndroidAPS/issues/5512), open |
| Faster start: time zone cached, quicker log writer, Nightscout load cursors kept, statistics computed only on screen, first IOB calculation right after start | the client needed about 1 minute after opening; now about 10 s | [#5484](https://github.com/nightscout/AndroidAPS/issues/5484), [#5485](https://github.com/nightscout/AndroidAPS/issues/5485), fixed upstream in `dev` |

**Why it is kept:** a fallback everyday build without the Live Activity and without Home Assistant.
`ios-live-activity` contains everything from this branch.

**Build:** Actions → **iOS TestFlight** → Run workflow → branch `ios-trend-arrow`. Shows in
TestFlight as **AAPSClient** (last build 1495539).

**To do on a new AAPS release:** merge `master` into this branch; where upstream fixed the same
problem (start time, IOB), take the upstream code and drop ours; keep the trend arrow until #5512
is solved.

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
