# Studio acceptance for the friends-playtest build, 2026-10-18 (BD-663)

Label: **STUDIO ACCEPTANCE ATTEMPT: BLOCKED AT STEP 2. No playtest feature was tested in Studio. No PASS or FAIL is claimed for any feature, and no picture was taken.** Nothing in the game was found broken. The blocker is the way the Studio tools work, not the game.

## What worked (offline, real results)

* `python tools/build.py --profile playtest` on main `77f03e31` (clean tree) built `build/BeDino-Build020-playtest.rbxlx` (463 scripts, 34,414,076 bytes; git-ignored, not committed). One warning, the known one: `DeveloperProducts` still lists old Robux product ids (inert, packs stay off).
* `python tools/verify_release.py --profile playtest --place build/BeDino-Build020-playtest.rbxlx` passed: 37 keys enforced, Studio-only guards intact. This includes both paid flags false and all debug/test/QA flags false.

## What did not work

| Step | Result | Exact observation |
| --- | --- | --- |
| `list_roblox_studios` | OK | Exactly one window: `cockatoo-scratch.rbxl`, id `13674288-7ef4-4518-8f1b-3d6939a2fcae`. |
| `get_studio_state` | OK | Mode Edit; DataModels available: Edit only. |
| Open the built place with Ctrl+O | **IMPOSSIBLE with the tools we have** | `user_keyboard_input` only accepts `datamodel_type` "Client" and answered `Client datamodel is not available in Edit mode`. Its keys go to the running game's input, not to Studio's menus or the Windows file dialog, so it could not press Ctrl+O even in Play mode. `user_mouse_input` has the same limit. `execute_luau` (Edit) runs inside the open place and has no supported call to open another place file. |
| Read-only check of the open place | OK | `game.Name` = `cockatoo-scratch.rbxl`, `GameId` 0, `PlaceId` 0, `ReplicatedStorage.Shared` does **not** exist. So the open place is not Be Dino at all; testing in it would show nothing about the playtest build. |

Per the task rule ("if opening a file this way is impossible, stop and report instead of improvising") I stopped here. I did not press Play, did not run any script that changes the scratch place, did not touch any window, and took no screenshot (a screenshot of the scratch place would be misleading). Studio was left as I found it: scratch place open, Edit mode, nothing changed.

## Feature table (all NOT TESTED)

| Feature | Result | Why |
| --- | --- | --- |
| Spawn and movement | NOT TESTED | playtest place not open |
| Eating food and growth | NOT TESTED | same |
| Short run to settlement, reconnect-safe run end | NOT TESTED | same |
| Egg hatch reveal | NOT TESTED | same |
| Dinos menu | NOT TESTED | same |
| Fusion menu (6 Base to Gold) and its numbers | NOT TESTED | same |
| Objectives panel | NOT TESTED | same |
| Combat (bite) | NOT TESTED | same (`CombatEnabled` is not among the playtest profile's rules; check in a rendering run whether it is on) |
| Fast travel, cave hub teleport and return | NOT TESTED | same |
| Weather events | NOT TESTED | same |
| Shop (packs must not look buyable) | NOT TESTED | same; the offline guard is `verify_release` (`CrystalPacksEnabled` false) |
| Console errors and warnings | NOT TESTED | no playtest place loaded |
| Frame time (Studio desktop numbers only) | NOT TESTED | same |

## Ways to unblock (for the lead or owner)

1. **Easiest:** the owner or lead opens `build/BeDino-Build020-playtest.rbxlx` once by hand in a Studio window on the virtual monitor (File > Open from File; choose Don't Save for the scratch place). Then an agent runs the 13-step walk in [tools/qa/regression_walk/README.md](../../../tools/qa/regression_walk/README.md) plus this task's feature list. Rebuild from the main commit being tested first; build outputs are git-ignored.
2. Give agents a tool that can drive Studio's own menus (a Studio plugin with a "load this file" action, or a command-line launch of Studio with the file, run by the lead, which opens a NEW window and needs the same virtual-monitor placement as before). Both are lead decisions, not agent improvisation.
3. When a playtest place is open in a rendering window, [docs/55](../../55-playtest-release-runbook.md) section 3 and [docs/145](../../145-session1-readiness-2026-10-17.md) section 5 list what to check. The walk scripts need hand clicks for taps (`VirtualInputManager` is blocked in `execute_luau`, per the 2026-10-17 run).
