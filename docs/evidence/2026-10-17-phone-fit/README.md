# BD-531 phone landscape fit and BD-532 Random Egg tile (2026-10-17)

Branch claude/phone-fit-531-532. **Studio status: PENDING.** The Studio window of this agent never rendered (Camera.ViewportSize 1 x 1, `screen_capture` "Connection closed" / timed out): the Studio log shows `RenderSchedulerState: Pushing throttle render state` never popped, and the lead found that every new Studio window since about 10:00 opens with its main window disabled by a hidden dialog and the viewport undocked. So the property readings and the after pictures below are NOT taken yet; the lead runs them after the Studio restart. The "before" pictures are the round 2 pictures (836 x 390 window, mouse, not touch) in [../2026-10-17-stuck-BD-148/](../2026-10-17-stuck-BD-148/README.md), images 20 to 30.

## What the before pictures show, read against the code (offline, real `TouchLayout` in Luau)

The BeDinoUI ScreenGui uses `CoreUISafeInsets`, so on an 836 x 390 game view the canvas the layout sees is shorter by the Roblox top bar (the pictures put y 0 of the gui about 56 px down: Admin at y 8 shows at y 66). Assumed canvas: **836 x 332** (390 - 58) and **667 x 317** (375 - 58); the verifiers also run minus 0, 36 and 44 px.

| Piece (836 x 332, phone layout) | rect before | cause |
| --- | --- | --- |
| EGGS plate `hud` | (8, 8) 130 x 40, **visible, not hidden** | the Studio/admin **Admin button** (120 x 48 at a fixed (14, 8) in BeDinoAdminUI, same insets) is drawn on top of it: that is the "missing plate" of [24](../2026-10-17-stuck-BD-148/24-phone-run-start-no-eggs-plate.jpg) and the covered start of the rail in [20](../2026-10-17-stuck-BD-148/20-phone-844x390-hub-hud-overlap.jpg) |
| goal line "Gold ready" | (659, 43) 169 x 20 | fine on its own |
| hub GOALS header (GoalsPanel) | (568, 65) 260 x 44, 1:1 | not known to `TouchLayout`; reaches under the rail |
| weather chip / LEAP column `timers` | (618, 76), weather first | starts under the rail only, so GOALS (y 65 to 109) and the goal line sit on the weather chip (y 76 to 121) |
| Eggs screen body | 402 design px on a 270 px visible body (scale 0.953, header 56, body top 66) | needs a scroll to reach OPEN / AUTO / EXPLORE ISLAND; a 402 px minimum canvas also gave every compact screen a scroll bar |
| Go home confirm | buttons at y 328 (402 - 68 - 6) on a 270 px body | GO HOME / CANCEL below the fold |

After the fix (same canvas, hub): admin (136, 276) 120 x 48 next to Tell us! (8, 276); goals (659, 65) 169 x 44 (wallet width, folded); timers start at y 117 (weather chip 45 px tall, LEAP 44 px) with the speed/buff line hidden because it does not fit; the Eggs screen and the Go home confirm are laid out inside the visible body (`PhoneScale.eggsLayout`, `PhoneScale.exitLayout`).

## Offline checks (all green)

`verify_movement_mobile` (836 x 390 and 667 x 375 minus a 0/36/44/58 px bar, hub and run, touch and mouse: every HUD piece on the canvas, egg plate visible, weather chip visible, no two pieces overlap, Admin and Goals header included), `verify_phone_scale` (Eggs with and without the cracked hint line, and Go home, inside the visible body at those canvases, OPEN / AUTO / GO HOME / CANCEL >= 44 px on screen, no overlap), `verify_hud`, `verify_eggs_screen`, `verify_shop_tiles`, `verify_paid_random_gate`, `verify_doc_ids`, `verify_handbook`, `verify_kanban_merge`, `verify_sources`.

## Studio list (pending; lead, after the restart)

Own place, `python tools/build.py --profile playtest`, window sized until `PlayerGui.BeDinoUI.AbsoluteSize` reads about 836 x 332 (and again about 667 x 317). For each of these read `Visible`, `AbsolutePosition`, `AbsoluteSize` (and the parent's clipping and `ZIndex`) and capture before (main) and after (this branch):

1. Hub HUD: `EggsPlate` (inside the `hud` frame), `AdminToggle` (BeDinoAdminUI), the goal line, `GoalsPanel` header, the weather tile, LEAP, the rail: no two rects intersect.
2. In-run HUD: the same, with the EGGS plate on screen and the Admin button beside Tell us!.
3. Eggs screen (`BodyScroll.CanvasSize` Y = 0, OPEN and AUTO inside the scroller window) and the Go home confirm (GO HOME and CANCEL inside it).
4. Shop > Eggs: the grey "COMING SOON" button (`BuyEggComingSoon`), the landing tile subtitle "Coming soon", and no confirm opening on a tap.
Save pictures here as `before-*.jpg` / `after-*.jpg`.
