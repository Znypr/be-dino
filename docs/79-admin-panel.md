# 79 Owner admin panel (BD-120)

Owner request 2026-10-14: an admin panel only for the owner, for private playtests ("admin abuse" style): a slider for how much food is worth and buttons to spawn weather events.

## What it does
- **Admin** button top-left (or **F2** on desktop) opens the panel. Only the owner sees it.
- **Sliders** (sent when you let go):
  - Food worth x0.5 to x10. Multiplies the points of every food pickup, so it speeds up both growth and run eggs (eggs still follow 40 per 500 food and the existing per-run caps).
  - Growth speed x0.5 to x5. Stacks on top of potions, weather and mutations (still inside the existing x8 growth clamp).
  - Run speed x0.5 to x3. Multiplies walk speed during a run; the movement guard reads the same speed, so fast players are not flagged.
- **Weather**: pick 1 min, 3 min or 10 min, then tap any of the 7 events to start it now for everyone. **Stop weather** clears it; the next random event then comes a full interval later. Forced events give the same loot, growth and event-mutation eggs as natural ones.
- **Reset sliders** puts all three back to x1.
- All changes affect every player on that server and last until the server shuts down. Nothing is saved to profiles as a setting; what players earn while it is on (eggs, growth) is saved as normal.

## Who is an admin (server side)
`src/shared/AdminRules.luau` `isAdmin`, checked by `src/server/AdminService.luau` when a player joins:
- the user who owns the experience (`game.CreatorId`, user-owned), or
- rank 255 (owner) of the owning group (group-owned experiences), or
- any id in `Config.AdminUserIds` (empty by default), or
- everyone in an unpublished Studio copy (GameId 0), including local test servers.
`Config.AdminPanelEnabled = false` turns it off for everybody. Before a public release decide whether to keep it on (owner-only) or turn it off.

## Security
- One `RemoteFunction` `BeDinoRemotes.AdminAction`. The handler rejects non-admins first, rate limits (0.15 s), allows only `set`, `startWeather`, `stopWeather`, `reset`, at most 3 arguments, clamps/snaps every number (NaN and infinity rejected) and accepts only weather ids from `ProgressionConfig.Weather`.
- The `IsAdmin` player attribute only decides whether the client builds the panel; the server checks its own table, so a spoofed client gains nothing.
- AdminService never touches ProfileRepository or DataStores (checked by `tools/verify_admin.py`). Every action is printed to the server output with the admin's name.

## Evidence
- `python tools/verify_admin.py --runner luau` (in CI): authorization matrix, slider clamping/snapping, weather length bounds, forced weather and stop against `WeatherClock`, plus static checks (authorize-first, no persistence, Bootstrap wiring, client waits for `IsAdmin`).
- Full CI command list and `python -m unittest discover -s tests` pass locally (2026-10-14).

## Not tested yet (needs Studio)
- Panel layout, slider dragging with mouse and touch, phone size.
- That the owner is recognised in the published playtest experience (depends on whether "newbuild" is owned by the user account or a group).
- Weather visuals and HUD timers for a forced event; lighting reset after Stop.
- Run speed changes against the movement guard during real play.
