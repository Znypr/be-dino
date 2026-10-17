# BD-531 phone landscape fit and BD-532 Random Egg tile (2026-10-17)

Branch claude/phone-fit-531-532 (code, PR #383), Studio evidence added on claude/evidence-phone-big. **Studio status: DONE 2026-10-17 (see "Studio results" below); the paragraph that follows is kept as history.**

## Studio results (2026-10-17, after the Studio restart)

Build: `python tools/build.py --profile playtest --output C:/Users/znypr/dtmp/captures.rbxlx` of origin/main + PR #383's branch (phone-fit merged in), own Studio window, Play, memory-only profile, admin = the Studio user. The window was resized with SetWindowPos (Studio's MCP cannot set a device) until `Camera.ViewportSize` read 836 x 390 (BeDinoUI.AbsoluteSize **836 x 332**) and 667 x 375 (**667 x 317**); `TouchEnabled` stays false, so the touch-only branches did not run (real phone = BD-085). Before every capture `RenderStepped` counted 60 frames in 1 s and the viewport size was read. Images are Studio `screen_capture` only; clicks are real mouse input (`user_mouse_input` takes GUI-space coordinates, y without the 58 px top bar). Run: Admin Food worth x10, Mutation chance x10, Volcanic Bloom (the tallest weather chip), then eating food.

| Item | 836 x 390 | 667 x 375 |
| --- | --- | --- |
| Hub HUD (Admin, Goals header, goal line, weather chip, LEAP, EGGS plate) | **PASS**, 0 overlaps, [picture](after-836x390-hub-hud.jpg) | **PASS** for the named pieces; 1 overlap of a transient button: "Back to the middle" x weather/LEAP column 4 x 44 px, [picture](after-667x375-hub-hud.jpg) (BD-538) |
| In-run HUD, EGGS plate visible, Admin beside it | **PASS**, 0 overlaps (only the "+1.2" growth pop-up crossed the SIZE bar for a moment), [picture](after-836x390-run-hud.jpg) | **PARTIAL**: plate and Admin fine; SIZE bar x weather chip 9 x 30 px, [picture](after-667x375-run-hud.jpg) (BD-538) |
| Eggs screen, OPEN and AUTO with no scroll | **PASS**: `BodyScroll.CanvasSize` = (0, 0), [picture](after-836x390-eggs-screen.jpg) | **FAIL (minor)**: no vertical scroll, but a horizontal one (canvas 836 design px x 0.8 = 668 > 644), 5th nest slot cut, hint clipped, [picture](after-667x375-eggs-screen-horizontal-scroll.jpg) (BD-538) |
| Go Home confirm | **PASS**, [picture](after-836x390-go-home-confirm.jpg) | buttons inside the body vertically **PASS**, same horizontal canvas as Eggs, [picture](after-667x375-go-home-confirm.jpg) (BD-538) |
| BD-532 Random Egg tile "Coming soon" | **PASS** (full-size view 1156 x 841): [landing tile](bd532-shop-landing-eggs-tile-coming-soon.jpg), [Eggs tab, grey COMING SOON](bd532-shop-eggs-tab-coming-soon-grey.jpg), [after a tap: no confirm, balance unchanged](bd532-shop-eggs-tab-after-tap-no-confirm.jpg) | not captured |

Also seen at both sizes: the "Tell us!" button (8, 276 / 8, 261, 120 x 48) is drawn on top of the lower-left of an open menu, here over the rarity and condition chips of the Eggs egg card (BD-524 family, in BD-538). The goal line reads "Level 2:..." (ellipsised at the 169 px wallet width) in the hub.

### Key GUI rects (AbsolutePosition x, y; AbsoluteSize w x h; canvas = BeDinoUI)

Hub, 836 x 332 (weather on): EGGS plate (8, 8) 130 x 40; rail (147, 8) 502 x 60; wallet (659, 8) 169 x 31; NextGoal (659, 43) 169 x 20; GoalsPanel header (659, 65) 169 x 44; weather + LEAP column (618, 117) 210 x 115; AdminToggle (136, 276) 120 x 48; TellUsButton (8, 276) 120 x 48. Overlaps: 0.

In run, 836 x 332: EGGS plate (8, 8) 130 x 40; rail (147, 8) 502 x 60; wallet (659, 8) 169 x 31; SizeBar (293, 72) 250 x 34; weather + LEAP column (618, 76) 210 x 157; HomeButton (350, 280) 135 x 44; AdminToggle (136, 276) 120 x 48; Toasts (198, 80) 440 x 186. Overlaps: 0.

Eggs screen, 836 x 332: modal (8, 4) 820 x 323; BodyScroll (12, 58) 812 x 266, CanvasSize (0, 0); nest slots at y 86, 65 px tall; OPEN (192, 201) 596 x 65; AUTO (192, 269) 124 x 47 (bottom 316 of the window bottom 324).

Go home, 836 x 332: modal (8, 4) 820 x 323; GO HOME (302, 269) 233 x 47; CANCEL (546, 269) 233 x 47; X (746, 9) 76 x 45.

Hub, 667 x 317: EGGS plate (8, 8) 130 x 40; rail (147, 8) 334 x 60; wallet (490, 8) 169 x 31; NextGoal (490, 43) 169 x 20; GoalsPanel (490, 65) 169 x 44; weather + LEAP column (449, 117) 210 x 100; BackToMiddle (214, 173) 240 x 48; AdminToggle (136, 261) 120 x 48; TellUsButton (8, 261) 120 x 48.

In run, 667 x 317: rail (147, 8) 334 x 60; SizeBar (208, 72) 250 x 34; weather + LEAP column (449, 76) 210 x 142; HomeButton (282, 265) 105 x 46; AdminToggle (136, 261) 120 x 48. SizeBar x column overlap 9 x 30.

Eggs screen, 667 x 317: modal (8, 4) 650 x 309; BodyScroll (12, 49) 644 x 261, CanvasSize (836, 0) = 668 x 261 absolute; OPEN (200, 169) 462 x 86; AUTO (200, 258) 104 x 46.

Go home, 667 x 317: GO HOME (255, 258) 195 x 46; CANCEL (460, 258) 195 x 46; X (590, 8) 64 x 44; same BodyScroll as above.

Shop Eggs tab (1156 x 783): `BuyEggComingSoon` "COMING SOON" (436, 456) 554 x 46, grey background (0.24, 0.23, 0.29), `Active` true (it swallows the tap, no confirm opens).

## Original pending note (history)

Studio status was PENDING at the time of writing:

Branch claude/phone-fit-531-532. Studio status was PENDING at the time of writing: The Studio window of this agent never rendered (Camera.ViewportSize 1 x 1, `screen_capture` "Connection closed" / timed out): the Studio log shows `RenderSchedulerState: Pushing throttle render state` never popped, and the lead found that every new Studio window since about 10:00 opens with its main window disabled by a hidden dialog and the viewport undocked. So the property readings and the after pictures below are NOT taken yet; the lead runs them after the Studio restart. The "before" pictures are the round 2 pictures (836 x 390 window, mouse, not touch) in [../2026-10-17-stuck-BD-148/](../2026-10-17-stuck-BD-148/README.md), images 20 to 30.

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


## BD-538 fix at 667 x 375 (branch claude/fix538-small-phone): offline DONE, Studio pictures PENDING

Studio was in use by another agent, so no Studio window was opened for this change. Offline (real `TouchLayout` / `PhoneScale` in Luau, 667 x 375 and 836 x 390 minus a 0 / 36 / 44 / 58 px top bar, hub and run, touch and mouse):

| Residual (667 x 317 before) | Cause | Fix |
| --- | --- | --- |
| "Back to the middle" (214,173) 240 x 48 overlapped the weather/LEAP column (449,117) by 4 x 44 px | the chip was a fixed bottom-centre button (`HubTravelClientRules.ChipBottom`) | `TouchLayout.chip`: bottom centre, else slid left of the column and the Goals header; Bootstrap publishes `ChipRect`, `HubTravelClient` follows it |
| SIZE bar (208,72) 250 x 34 overlapped the weather chip (449,76) by 9 x 30 px (the goal hint under it, 360 wide, reached further) | `HudV2.layout` centred both on the canvas | `TouchLayout.sizeBar` / `sizeHint`: centred, else both slide left together to 4 px before the column |
| Eggs screen and Go home scrolled sideways (836 px canvas at 0.8 = 668 px in a 644 px body; 5th nest slot and hint cut) | `ModalCompact` gave the scroller a 836 design px wide canvas whenever the panel was narrower than 850 | `PhoneScale.modal.fit` = (panelW - 8) / 836 (0.964 at 667 x 317, 1 at 836 wide and desktop); `BodyFit` UIScale on the scroller, Y-only scroll, canvas X = 0; screens get `bodyHeight()` = innerH and `bodyScale()` = scale x fit |
| "Tell us!" over the egg card's chips at both phone sizes | stays visible under an open menu | `PlaytestFeedback.showButton({menuOpen, compact})` hides it while the ModalScrim is up on a canvas under 500 px tall; desktop unchanged |

Verifiers that now fail if these come back: `verify_movement_mobile` (zero overlaps incl. SIZE bar, hint, chip; every action >= 44 px; a probe that the centred bar and chip would touch the column; desktop rects unchanged; static wiring), `verify_phone_scale` (`scrollX` false, innerW >= 836, body inside the screen width, floors with the fitted scale, OPEN / AUTO / GO HOME / CANCEL >= 44 px), `verify_hud`, `verify_feedback`.

Studio pictures to take once the lead says "Studio free" (one window, BeDinoUI about 667 x 317): `after2-667x375-hub-hud.jpg`, `after2-667x375-run-hud.jpg`, `after2-667x375-eggs-screen.jpg`, `after2-667x375-go-home-confirm.jpg`. STATUS: pending.
