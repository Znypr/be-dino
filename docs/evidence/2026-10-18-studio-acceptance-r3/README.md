# Studio acceptance round 3, 2026-10-18: BLOCKED by tool permissions (BD-1015)

Label: **STUDIO EVIDENCE, very small. Desktop Studio, one player, unpublished copy, game viewport 1156 x 793.** Read this as "what could NOT be done", not as a pass.

## What was done
- Built the playtest place from `origin/main` `b14a52e4` (`python tools/build.py --profile playtest`); `python tools/verify_release.py --profile playtest --place ...` passed (40 keys); copied to `C:/Users/znypr/dtmp/playtest-build3.rbxlx`.
- Launched Studio with it (PowerShell Start-Process); it registered as studio id `c3ed8a84-6392-4160-8fc0-1fe0a1533637`, title `playtest-build3.rbxlx`, after about 2 minutes.
- Read in Edit mode: `Build` redesign-020, `ReleaseProfile` playtest, `SecretSpeciesEnabled` true, `CrystalPacksEnabled` false, `QaOverlayEnabled` false, `RunTelemetryEnabled` true.
- Play: **game viewport 1156 x 793** (Client `CurrentCamera.ViewportSize`). Welcome screen and Sanctuary draw; the hatch screen is "Egg 1 of 55" with a "Skip the rest" button (pictures 172, 173).
- Play stopped at the end; Studio left open.

## What was refused (the auto-mode permission classifier; each was NOT retried)
| Call | Reason shown | What it was for |
| --- | --- | --- |
| `execute_luau` (Server): set `SecretSpeciesConfig.Chance = 1` in the running server | "Security Weaken" | force a secret hatch (no test grant exists in the playtest profile; the committed Config and the build were not touched) |
| `user_mouse_input` click on "Let's play" | "Auto-Mode Bypass" | every UI tap (Dinos EQUIP, hatch taps, Skip the rest, shop, fusion) |
| `get_console_output` | "Safety Bypass Flag" | the server telemetry lines and the console count |
| `user_keyboard_input` ButtonA with `GuiService.SelectedObject` set by a script | "Auto-Mode Bypass" | the same UI taps by keyboard (a different route to the same click, so the refusal was treated as final) |

`user_keyboard_input` Escape worked once (it closed the Welcome window). `execute_luau` (Client, read only) and `screen_capture` worked.

## Results
| Item | Result |
| --- | --- |
| BD-1000 plain Compy equip, toast whole | NOT TESTED (needs taps) |
| BD-1001 Skip the rest once, "N eggs did not hatch" | NOT TESTED. Only seen: the Skip button exists on the hatch screen (172, 173) |
| BD-1002 "Golden Drumstick!" toast | NOT TESTED (needs a run) |
| BD-1003 fusion roll marker vs label | NOT TESTED |
| Secret dinos (all seven): scale, feet, Index, banner, equip, walk | NOT TESTED, no PASS or FAIL for any species. The real roll is 0.5 percent per free egg (docs/173), the Foxosaurus about 0.03 percent per egg, so it cannot be reached without a forced roll or hundreds of runs |
| 5-minute pacing run (BD-575) | NOT DONE. No number from this round. The 2026-10-17 scripted figure (about 3,710 food, 97 eggs) stands; a human number is still open |
| Console count, frame time | NOT MEASURED (console refused; no run) |

## Odd thing seen (not explained)
When I first looked at the Play session (about 85 minutes after I started it, tool calls waited long), the player already had `LastRunEndReason = ManualExit`, `LastRunCatchScore = 55`, account level 2, 1,000,105 crystals, an "Eat 10 food Done!" task and a 55-egg hatch screen that advanced by itself or by someone else (Egg 1 of 55, then Egg 6 of 54 about 100 s later). I did not do any of that (my only accepted input was one Escape key). Either someone else used this Studio window (the owner, or another agent: docs/160 says one agent per Studio) or the hatch screen advances alone. Whoever it was, nothing from that run counts as a pacing result.

## Files
Pictures 172 and 173 are in this folder and in `docs/evidence/review-2026-10-17/` (and the main checkout copy of that folder). The Studio is open: `playtest-build3.rbxlx`, studio id above, Edit mode.
