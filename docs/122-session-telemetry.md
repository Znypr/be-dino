# Session and run telemetry (BD-426)

Status: **Review / test. CURRENT BUILD BEHAVIOR: off by default; on only in the playtest profile.** Not owner-approved balance, only evidence gathering for the owner vision (short runs of about 5 minutes, a hatch party after each, several runs per session; about 15 eggs per 5 minutes, [docs/119](119-catch-rate-15-per-run.md) / BD-418). The BD-426 row is in PR #242 and is the tracker entry.

## What is logged (server only, anonymous)
- `run_end`: `duration_s`, `reason` (Death, ManualExit, Disconnect, Predation, Other), `food`, `food_is_estimate`, `food_raw`, `eggs_food`, `weather_s`, `eggs`, `nests`, `crystals`, and `starter` (BD-1163, docs/225: `true` only on the starter run of a brand-new save, absent on every other run, so the report can compare the first run with the later ones).
- `session_end` (when a player leaves): `total_s`, `runs`, `hub_s`, `run_s`. Hub time is every second the player's `Location` attribute is not `Island`.
- No UserId, name, profile data or session id is logged or stored; sessions live in server memory only, nothing is written to a profile. Only whitelisted fields exist (`tools/verify_telemetry.py` asserts it).
- **`food` is DERIVED** (`eggs / FoodCatchRate`, flagged `food_is_estimate`). Weather and potion multipliers raise eggs, so it overstates (the 2026-10-17 Studio run printed 4,125 for about 3,710 real food). It is kept for comparison with older logs only.
- **BD-575 real numbers**: `food_raw` is the raw food points eaten in the run, summed from the pickups FoodService already commits (before the admin food multiplier, the weather and the potions); `eggs_food` is the eggs the food alone earned at x1 (food x `FoodCatchRate`, before the weather and potion multipliers); `weather_s` is the seconds of the run spent inside a weather event (from an event-driven log of the `WeatherId` changes, capped at the run length); `duration_s` is the run length. A field that was not tracked is absent, never guessed (older lines have no `food_raw`).
- Cost: FoodService reads the flag once per tick, adds the claimed pickup values per player and calls `TelemetryService.noteFood` once per player per tick, memory only (a small table per player keyed by run id; never an attribute, remote or profile). With the flag off nothing runs: no require, no call, no table. Eggs, nests and crystals are the committed settlement outcome, read after `commitRunSettlement` succeeds.

- **BD-649 to BD-653 (2026-10-18, [docs/167](167-reference-and-playtest-tools.md) section 5b):** also logged, same flag, same anonymity: `visit` at join, `join` once the save is loaded (BD-1166), `count` roll-ups (`movement_rejects`, `rate_limited` per service, `script_errors`, `shop_purchases`, `hatches`, `fusions`), `script_error` text lines (scrubbed, 12 per server) and, in `session_end`, `first_run_s`, `first_food_s`, `first_egg_s`, `first_hatch_s`, `first_shop_s`, `server` (random per server start) and `at`. Count and error lines have their own bucket (20 a minute, 300 a server).

## First-session funnel (BD-1166, 2026-11-10)

Status: **Review / test. CURRENT BUILD: same flag (`RunTelemetryEnabled`), off by default, on only in the playtest profile. Offline tests only: not run in Studio, no real players yet.** It answers two questions of the first playtest ([docs/221](221-po-plan-team-and-research-2026-11-10.md) sections 3 and 4): where do new players drop off in the first minutes, and do they come back.

New fields in `session_end` (a field that is not known is absent, never guessed):

| Field | Meaning | Where it comes from |
| --- | --- | --- |
| `first_food_s` | seconds from joining to the first food bite (already there since BD-653) | server food tick |
| `first_run_end_s` | seconds to the first run that ENDED (settled). `first_run_s` stays the first run that STARTED | settlement report |
| `first_hatch_s` | seconds to the first egg hatched (already there). It is the moment the server pays the egg out; the reveal starts on the screen right after | server claim |
| `first_shop_open_s`, `first_index_open_s` | seconds to the first shop screen and the first Index screen | client screen beat |
| `quit` | where the player was when they left: `Hub`, `InRun`, `HatchScreen`, `Results`, `Shop`, `Index`, `Menu` | server `Location` plus the screen beat |
| `bounce_60`, `bounce_180` | true when the whole visit was shorter than 60 s / 180 s (the two Roblox bounce windows) | session clock |
| `idle_s` | seconds between the last thing the player did (ate, hatched, bought, opened or closed a screen, started or ended a run) and leaving | session clock |
| `new_profile` | true for a brand-new save, false for a returning player | save load |
| `return_days` | days since the previous visit as one of `0`, `1`, `2-7`, `8+`; absent for a new save and for a save that has no stored day yet | save load |
| `friends` | how many friends were in the same server at join (0 to 12), never who | `Player:IsFriendsWith`, in its own thread |

New line `join` (once per visit, when the save is loaded): `new_profile`, `return_days`, `server`. It exists because `session_end` is missing when the server closes first.

How it works, and what keeps it safe:

- **Screen beat.** `src/client/FunnelBeat.client.luau` reads the `Screen` attribute that Bootstrap sets on `BeDinoUI` and sends ONE word to the new RemoteEvent `FunnelBeat` when the kind of screen changes: `Closed`, `HatchScreen`, `Results`, `Shop`, `Index` or `Menu` (`RunTelemetry.screenBeat` is the one table). The server (`src/server/FunnelService.luau`) drops anything that is not exactly one string of at most 16 bytes; `RunTelemetry.beat` drops any word that is not on the list, a beat less than 0.1 s after the last one and everything after 600 per visit. The beat changes no gameplay state and nothing is sent back. Audit row: [docs/151](151-remote-audit-2026-10-17.md). With the flag off the client script stops on its first line and the remote does not exist. The Fusion menu is its own screen and is NOT reported yet (it counts as the place behind it).
- **Return day.** The ONE stored field is `lastSessionDay` in the profile: whole days since 1970 (UTC). It is additive and lazily created, written inside the load transaction that already writes the session lease (no extra save request), and only while the flag is on, so the default build never writes it. It is never validated on load, so a bad value can not block a save; a value that is not a sane whole number reads as "not known". A Build 020 server ignores the field (`verify_rollback.py`, `verify_profile_golden.py` stay green).
- **Friends.** `FunnelService.countFriends` asks at most 12 other players, in its own thread inside a `pcall`; a failing friends service counts nobody. The id needed for that call is used for the call only.
- **No ids, no names.** `TelemetryService` still contains no `UserId`, DataStore, profile, attribute write or client call (`tools/verify_telemetry.py`). Every string value in the new lines is one of a fixed set of words.
- **Settlement.** The run-end step is marked inside the deferred, `pcall`-wrapped report (BD-1096 unchanged; `verify_settle_guard.py`).
- **Roblox onboarding funnel.** For a brand-new save the steps Joined, First bite, First run ended, First egg hatched are also sent with `AnalyticsService:LogOnboardingFunnelStepEvent` (deferred, in a `pcall`), so the Creator Hub funnel chart fills by itself. Not verified against the live API.

**Signal map** (which telemetry field watches which Roblox Home signal of docs/221 section 4): bounce under 60 s / 180 s -> `bounce_60`, `bounce_180`, `quit`, `first_food_s`, `first_hatch_s`; play days -> `return_days`, `new_profile`; co-play days -> `friends`; session quality -> `total_s`, `runs`, `idle_s`, `first_run_end_s`. Click-through is only in Creator Analytics.

`python tools/playtest_report.py` prints a section "First visit and coming back" from these fields.

**Not verified:** no Studio run, no phone, no real players, no live Analytics call. The first hatch time is the server payout, not the picture on the screen. A player whose client never loads the UI is reported as `Hub`.

## How it is sent
`src/shared/RunTelemetry.luau` (pure: shape, clamping, rate limiter), `src/server/TelemetryService.luau` (observer) and one read-only hook in the settlement callback in `Bootstrap.server.luau`. Each event is printed as `[BD-TELEMETRY] {json}` to the server log and also sent with `AnalyticsService:LogCustomEvent` inside a `pcall` (log-only when the API is missing). Rate limit: 30 events per minute per server and 200 per session.

Flag: `Config.RunTelemetryEnabled` = false in source; `tools/release_profiles.py` requires false in the default profile and sets true in the playtest profile.

## Report
Export the server log (Studio output or the Creator Hub log) and run `python tools/telemetry_report.py server.log [--json]`. It prints one row per run (food/min, eggs/min, eggs per 500 food, minutes in weather, `vs target (15 eggs / 5 min)`; a `~` marks derived food), then runs, median run length, food per minute (docs/119 estimate: about 120-140), eggs per 5 minutes (target about 15), end reasons, nests and crystals per run, runs per session and the hub share of session time. Runs under 20 s are excluded from rates. The owner-side checks from BD-426 (first egg about 60 s, menus under 30 s between runs) still need client timings and are not covered here.

## Telemetry can never block a settlement (BD-1096, 2026-10-18)
Studio round 5 ([docs/197](197-studio-round5-verification.md)) saw one run stay in `Ending` after a "Script timeout" showed up in `TelemetryService.runSettled`. **CURRENT BUILD:** `runSettled` now only copies three numbers and hands the report to `task.defer` inside a `pcall`, so an error, a yield or a long loop in a report cannot touch the settle thread. `RunLifecycle` calls the settlement callback in a `pcall`, and an **Ending watchdog** (`Config.EndingWatchdogSeconds` 20, `EndingWatchdogMaxSeconds` 60) force-settles a run still in `Ending` once (same run id, the ledger pays nothing twice; a clean "save failed" answer is left to the lease renew tick). The objective hook after a committed settlement and the food-tick telemetry call are also in a `pcall`. Proof: `tools/verify_settle_guard.py` (mocks that error, yield forever and loop; four mutants). Not tested: real Studio / real timeouts.
