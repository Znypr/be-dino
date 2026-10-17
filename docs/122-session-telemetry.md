# Session and run telemetry (BD-426)

Status: **Review / test. CURRENT BUILD BEHAVIOR: off by default; on only in the playtest profile.** Not owner-approved balance, only evidence gathering for the owner vision (short runs of about 5 minutes, a hatch party after each, several runs per session; about 15 eggs per 5 minutes, [docs/119](119-catch-rate-15-per-run.md) / BD-418). The BD-426 row is in PR #242 and is the tracker entry.

## What is logged (server only, anonymous)
- `run_end`: `duration_s`, `reason` (Death, ManualExit, Disconnect, Predation, Other), `food`, `food_is_estimate`, `food_raw`, `eggs_food`, `weather_s`, `eggs`, `nests`, `crystals`.
- `session_end` (when a player leaves): `total_s`, `runs`, `hub_s`, `run_s`. Hub time is every second the player's `Location` attribute is not `Island`.
- No UserId, name, profile data or session id is logged or stored; sessions live in server memory only, nothing is written to a profile. Only whitelisted fields exist (`tools/verify_telemetry.py` asserts it).
- **`food` is DERIVED** (`eggs / FoodCatchRate`, flagged `food_is_estimate`). Weather and potion multipliers raise eggs, so it overstates (the 2026-10-17 Studio run printed 4,125 for about 3,710 real food). It is kept for comparison with older logs only.
- **BD-575 real numbers**: `food_raw` is the raw food points eaten in the run, summed from the pickups FoodService already commits (before the admin food multiplier, the weather and the potions); `eggs_food` is the eggs the food alone earned at x1 (food x `FoodCatchRate`, before the weather and potion multipliers); `weather_s` is the seconds of the run spent inside a weather event (from an event-driven log of the `WeatherId` changes, capped at the run length); `duration_s` is the run length. A field that was not tracked is absent, never guessed (older lines have no `food_raw`).
- Cost: FoodService reads the flag once per tick, adds the claimed pickup values per player and calls `TelemetryService.noteFood` once per player per tick, memory only (a small table per player keyed by run id; never an attribute, remote or profile). With the flag off nothing runs: no require, no call, no table. Eggs, nests and crystals are the committed settlement outcome, read after `commitRunSettlement` succeeds.

## How it is sent
`src/shared/RunTelemetry.luau` (pure: shape, clamping, rate limiter), `src/server/TelemetryService.luau` (observer) and one read-only hook in the settlement callback in `Bootstrap.server.luau`. Each event is printed as `[BD-TELEMETRY] {json}` to the server log and also sent with `AnalyticsService:LogCustomEvent` inside a `pcall` (log-only when the API is missing). Rate limit: 30 events per minute per server and 200 per session.

Flag: `Config.RunTelemetryEnabled` = false in source; `tools/release_profiles.py` requires false in the default profile and sets true in the playtest profile.

## Report
Export the server log (Studio output or the Creator Hub log) and run `python tools/telemetry_report.py server.log [--json]`. It prints one row per run (food/min, eggs/min, eggs per 500 food, minutes in weather, `vs target (15 eggs / 5 min)`; a `~` marks derived food), then runs, median run length, food per minute (docs/119 estimate: about 120-140), eggs per 5 minutes (target about 15), end reasons, nests and crystals per run, runs per session and the hub share of session time. Runs under 20 s are excluded from rates. The owner-side checks from BD-426 (first egg about 60 s, menus under 30 s between runs) still need client timings and are not covered here.
