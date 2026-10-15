# 62 Polish: SFX hooks, next-goal HUD line, reveal juice

> **Feel rule (2026-10-15):** sounds must be soft, calm and bubbly, never loud or sharp. See [docs/87](87-vision-and-feel-guide.md); it wins over older loudness values here.

Follows the readiness audit (doc 61, items 2, 4, 5, 10, 11, 15). All numbers and sound ids are PROVISIONAL.

## What was added
- `src/shared/Sfx.luau`: one table of 15 named sounds (hatch_crack, hatch_common/rare/legendary, shiny_bang, big_thud, pickup, run_start, run_end, shop_buy, shop_refresh, weather_start, level_up, fusion_reveal, ui_click). Every `id` is an empty string, so the game stays silent and error-free. `Sfx.play(name)` is a no-op for empty/invalid ids, is pcall-wrapped, honors the SOUND ON/OFF setting (`Theme.HatchSoundEnabled`), reuses 3 pooled `Sound` instances per name under `SoundService.BeDinoSfx` and throttles repeats per sound (`gap`).
- Hooks (one line each) in `Bootstrap.client.luau`: hatch crack/reveal by rarity, Shiny, BIG, food pickup, run start/end (RunState transitions), potion buy, shop refresh toast, weather start, level up, and the shared `button()` helper (ui_click). `FusionMenu.luau` plays fusion_reveal. The button press scale 0.96 already existed in `Theme.decorate`; it now stays at 1 when `Theme.MotionEnabled` is false.
- `src/shared/NextGoal.luau` plus a HUD line under the crystal counter (top-right, clear of the touch thumbstick/jump areas). It shows the best fusion progress across species + pattern, for example `Goal  Gold: 9/50 Compy Wavy`, from the `FusionAction` list (refreshed 2 s after the collection changes, at most 5 pages). If the remote is missing/disabled or nothing is in progress it shows level XP (`Level 3: 50/500 XP`). The server now also publishes the `AccountXP` attribute next to `AccountLevel`.
- Juice (only when motion is on): one pooled full-screen rarity-colored flash, a Shiny/BIG banner (destroyed after 1.4 s), a camera shake capped at 0.15 studs for 0.22 s on legendary/Shiny/BIG (one `BindToRenderStep` while active), and a pooled food pickup number pop.

## Filling in sound ids once the owner uploads
1. Upload the audio pack and note each asset id.
2. In `src/shared/Sfx.luau` set `id = "rbxassetid://<number>"` (a bare number also works) for each entry. Tune `volume`, `rate`, `gap`.
3. Run `python tools/verify_next_goal.py --runner luau`. It currently asserts every id is empty, so update that single assertion when ids land.
4. Rebuild (`python tools/build.py`) and check in Studio. Do not invent ids.

## Evidence
- `tools/verify_next_goal.py` (added to CI): goal selection, ties, level fallback, locked/garbage input, and the pure Sfx helpers (id normalization, throttle, pool slot, rarity names, no-op on empty ids). Existing suites, release verification and unit tests pass offline with Luau 0.741.
- No Studio, phone or Blender run was done. Sound is untested by definition (no ids).

## Pending (Studio / Android)
- Look at the goal line on a phone-size viewport (no overlap with crystals, Roblox menu, thumbstick).
- Confirm the flash, banner and shake read well and the shake does not fight the default camera script.
- Confirm `FusionAction` list returns data in Studio so the fusion goal appears; check frame time during a long auto-hatch batch.
- Verify motion OFF suppresses flash, shake, banner animation and press scale.
