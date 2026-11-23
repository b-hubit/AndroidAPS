# iOS AAPSClient – TestFlight build history (b-hubit)

[🇵🇱 Wersja polska](README.pl.md) · Fork and branch description: `B-HUBIT.md` in every code branch

Every build from the **iOS TestFlight** workflow of this repository. The build number is the minutes
since 1 Jan 2024 at build time, so it only grows and never repeats. The app version is always 4.0.0.

Each build contains everything from the earlier builds of the same line of changes
(`ios-trend-arrow` → `ios-perf-test` → `ios-bg-alarm-test` → `ios-live-activity`).

| Build | Date | TestFlight name | Branch | Commit | What changed | Status |
|---|---|---|---|---|---|---|
| 1491088 | 01.11.2026 | AAPSClient | `b-hubit-ios-match` | [`d8eb54a`](https://github.com/b-hubit/AndroidAPS/commit/d8eb54a) | First AAPSClient on iOS from GitHub Actions: plain official 4.0.0, no changes | active |
| 1492395 | 02.11.2026 | AAPSClient | `ios-trend-arrow` | [`bba8e17`](https://github.com/b-hubit/AndroidAPS/commit/bba8e17) | Trend arrow from Dexcom instead of the one AAPS calculates | active |
| 1495347 | 04.11.2026 | AAPS Perf | `ios-perf-test` | [`4efdc95`](https://github.com/b-hubit/AndroidAPS/commit/4efdc95) | Perf 1: faster logging, Nightscout load cursors, statistics only on screen. Result: “even slower” | expired |
| 1495406 | 04.11.2026 | AAPS Perf | `ios-perf-test` | [`64f93fa`](https://github.com/b-hubit/AndroidAPS/commit/64f93fa) | Perf 2: start-up timing in the log, to find the cause | expired |
| 1495471 | 04.11.2026 | AAPS Perf | `ios-perf-test` | [`9f7f2b5`](https://github.com/b-hubit/AndroidAPS/commit/9f7f2b5) | Perf 3: cached time zone and earlier IOB calculation – start from ~1 min to ~10 s (issues #5484, #5485) | expired |
| 1495539 | 04.11.2026 | AAPSClient | `ios-trend-arrow` | [`cff61f9`](https://github.com/b-hubit/AndroidAPS/commit/cff61f9) | Everyday build: Dexcom arrow + speed fixes from Perf 3 | active |
| 1498040 | 06.11.2026 | AAPS Test | `ios-bg-alarm-test` | [`3ea4bd2`](https://github.com/b-hubit/AndroidAPS/commit/3ea4bd2) | Test 1: “BG readings missed” alarm waits for Nightscout and clears itself on a fresh reading | expired |
| 1498261 | 06.11.2026 | AAPS Test | `ios-bg-alarm-test` | [`ad9e314`](https://github.com/b-hubit/AndroidAPS/commit/ad9e314) | Test 2: fresh Nightscout connection after the background, fixed wait after a freeze (issue #5495) | active |
| 1521870 | 22.11.2026 | AAPS Live | `ios-live-activity` | [`32daab5`](https://github.com/b-hubit/AndroidAPS/commit/32daab5) | Glucose on the Lock Screen, Dynamic Island and Apple Watch (Live Activity), pushed by Home Assistant | expired |
| 1522067 | 23.11.2026 | AAPS Live | `ios-live-activity` | [`19bf4c4`](https://github.com/b-hubit/AndroidAPS/commit/19bf4c4) | Webhook address no longer vanishes from iOS Settings on start | expired |
| 1522097 | 23.11.2026 | AAPS Live | `ios-live-activity` | [`640d4df`](https://github.com/b-hubit/AndroidAPS/commit/640d4df) | Glucose on one line + counting timer (bug: blank bar) | expired |
| 1522118 | 23.11.2026 | AAPS Live | `ios-live-activity` | [`9a6b1b6`](https://github.com/b-hubit/AndroidAPS/commit/9a6b1b6) | Reading time instead of the timer – bar visible again | expired |
| 1522547 | 23.11.2026 | AAPS Live | `ios-live-activity` | [`bcf2d50`](https://github.com/b-hubit/AndroidAPS/commit/bcf2d50) | “3' temu” (minutes ago) instead of the time, refreshed by Home Assistant | active |
| 1522607 | 23.11.2026 | AAPS Live | `ios-live-activity` | [`be85022`](https://github.com/b-hubit/AndroidAPS/commit/be85022) | One bar per iPhone – several people can follow at once (the app sends a device id) | **current** |

## Branches

| Branch | Purpose |
|---|---|
| `master` | Official AAPS + TestFlight workflow. No app changes. |
| `dev` | Copy of the official `dev` branch (4.0.1-dev), not built. |
| `ios-trend-arrow` | Dexcom arrow + faster start (fallback build, “AAPSClient”). |
| `ios-live-activity` | Everything + alarm fix + Live Activity + Calendar complication (everyday build, “AAPS Live”). |
| `ios-builds` | This table. |

Branches `b-hubit-ios-testflight`, `b-hubit-ios-match`, `ios-perf-test`, `ios-bg-alarm-test` and `komplikacja` are deleted: their changes are in `master` or `ios-live-activity`, and the commits in the table still resolve.

## Upstream issues

| Issue | Topic | State |
|---|---|---|
| [#5484](https://github.com/nightscout/AndroidAPS/issues/5484) | Slow start on iOS (time zone) | Fixed in `dev` (`d891e61`, `11f05d3`) |
| [#5485](https://github.com/nightscout/AndroidAPS/issues/5485) | First IOB calculation waits for an event | Fixed in `dev` (`4399aea`, `9668ca4`) |
| [#5495](https://github.com/nightscout/AndroidAPS/issues/5495) | False “BG readings missed” after start / resume | Fixed in `dev` (`3c05320`) |
| [#5512](https://github.com/nightscout/AndroidAPS/issues/5512) | Trend arrow differs from Dexcom | Open |
