# BD-075 objectives panel: Studio pictures (2026-10-17)

Label: **CURRENT BUILD BEHAVIOR, private Studio copy only.** `Config.ObjectivesEnabled` is still `false` in every committed build; the flag was flipped to `true` only in the unpublished build `C:/Users/znypr/dtmp/objpanel.rbxlx` (`python tools/build.py`, origin/main `f21900c2`, default profile, memory-only profile, test wallet). One Studio window (opened 12:37:45, closed 12:42:00), Play, no errors beyond the known UIBlox `FoundationProvider` warnings.

How it was driven: the Edit-mode copy of `ServerScriptService.Server.Bootstrap` got a private `ServerStorage.ObjDebug` BindableFunction (NOT committed) that calls the REAL `ObjectiveService.record` (a snippet's own `require` is a second module copy with no repository, so `record` returned false there). Progress came from `record("food_eaten", 4)`, then `("food_eaten", 6)`, then `("run_end", 1)`. The Goals panel needed a first egg: `PrivateState.set(LastRunEggCount, 3)` through the same hook. Clicks were real mouse clicks by instance path (header, CLAIM). Window resized with SetWindowPos until `Camera.ViewportSize` read 1156 x 841 (BeDinoUI 1156 x 783) and 836 x 390 (BeDinoUI **836 x 332**).

| # | Picture | What it shows |
| --- | --- | --- |
| 01 | [desktop folded](01-desktop-folded.jpg) | one 44 px line, "Eat 10 food" and chip "4/10", left of the GOALS header, same top edge, no overlap |
| 02 | [desktop open](02-desktop-open.jpg) | TASKS, "New tasks in 20 min", 3 tasks with bars, counts and "+10 crystals"; the open Goals panel would sit to the right of it |
| 03 | [desktop claimable](03-desktop-claimable.jpg) | Eat 10 food at 10/10: green CLAIM (100 x 44), the prize under the name |
| 04 | [desktop after claim](04-desktop-after-claim.jpg) | real claim through `ObjectiveAction`: wallet 1000000 -> 1000010, the next tutorial task "Finish your first run" in the list, claim answer in the header (shows the defect below) |
| 05 | [836x390 folded](05-phone-836x390-folded.jpg) | pill under the rail, between the badge and the GOALS header; weather chip and LEAP still visible and clear |
| 06 | [836x390 open](06-phone-836x390-open.jpg) | open sheet 300 x 204: covers the GOALS header, weather chip and LEAP while open (the documented allowance); clear of the rail, wallet, EGGS plate, Admin and EXPLORE ISLAND |
| 07 | [836x390 claimable](07-phone-836x390-claimable.jpg) | two finished tasks, two CLAIM buttons |
| 08 | [836x390 folded, ready](08-phone-836x390-folded-done.jpg) | folded line with the green "Done!" chip |

Rects (BeDinoUI px): desktop pill (568, 92) 300 x 44, open (568, 92) 300 x 206, GOALS header (875, 91) 260 x 44; 836 x 332 pill (355, 72) 300 x 44, open 300 x 204.

## Found in Studio and fixed in this PR
- **Claim answer was cut** ("+10 crys..." in picture 04): it was drawn in the 38% title slot. It now takes the wide right-hand label for 2.5 s (`verify_objectives_panel.py` asserts it there). Not re-shot; the pictures here are the "before" for that one label.

## Seen, not fixed
- Open rows have no divider; the prize line of one row sits close to the name of the next (03). Polish.
- Not covered: a real phone (touch, thumbstick, 44 px by finger) is BD-078 / BD-085; Studio's mouse stands in. BD-074 hooks were not on main, so progress was injected with the private hook above.
