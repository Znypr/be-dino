# Session and run telemetry (BD-426)

Status: **Review / test. CURRENT BUILD BEHAVIOR: off by default; on only in the playtest profile.** Not owner-approved balance, only evidence gathering for the owner vision (short runs of about 5 minutes, a hatch party after each, several runs per session; about 15 eggs per 5 minutes, [docs/119](119-catch-rate-15-per-run.md) / BD-418). The BD-426 row is in PR #242 and is the tracker entry.

## What is logged (server only, anonymous)
- `run_end`: `duration_s`, `reason` (Death, ManualExit, Disconnect, Predation, Other), `food`, `food_is_estimate`, `eggs`, `nests`, `crystals`.
- `session_end` (when a player leaves): `total_s`, `runs`, `hub_s`, `run_s`. Hub time is every second the player's `Location` attribute is not `Island`.
- No UserId, name, profile data or session id is logged or stored; sessions live in server memory only, nothing is written to a profile. Only whitelisted fields exist (`tools/verify_telemetry.py` asserts it).
- **Food is an estimate** (`eggs / FoodCatchRate`, flagged `food_is_estimate`) because food points are consumed inside FoodService, which this task must not change. Eggs, nests and crystals are the committed settlement outcome, read after `commitRunSettlement` succeeds.

## How it is sent
`src/shared/RunTelemetry.luau` (pure: shape, clamping, rate limiter), `src/server/TelemetryService.luau` (observer) and one read-only hook in the settlement callback in `Bootstrap.server.luau`. Each event is printed as `[BD-TELEMETRY] {json}` to the server log and also sent with `AnalyticsService:LogCustomEvent` inside a `pcall` (log-only when the API is missing). Rate limit: 30 events per minute per server and 200 per session.

Flag: `Config.RunTelemetryEnabled` = false in source; `tools/release_profiles.py` requires false in the default profile and sets true in the playtest profile.

## Report
Export the server log (Studio output or the Creator Hub log) and run `python tools/telemetry_report.py server.log [--json]`. It prints runs, median run length, food per minute (docs/119 estimate: about 120-140), eggs per 5 minutes (target about 15), end reasons, nests and crystals per run, runs per session and the hub share of session time. Runs under 20 s are excluded from rates. The owner-side checks from BD-426 (first egg about 60 s, menus under 30 s between runs) still need client timings and are not covered here.
