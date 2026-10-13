# BD-053 / BD-054 / BD-052: hill movement, phone touch layout and single Home

**Status: implemented in code, offline-verified, Review / test.** Branch `claude/bd-053-054-mobile`, 2026-10-13, on top of GitHub main Build 020 (`18856b4`). This is **not** Studio or physical-phone acceptance. Status lives only in the [Kanban](07-kanban.md); acceptance details stay in [45 sections E and F](45-owner-feedback-shop-hud-world-weather-tasks.md). Milestone 1 is a private playtest on the owner's **Android phone**; Robux features stay off. Every tuning number added here is marked `PROVISIONAL` in `Config.luau`.

## BD-053: sliding and failure to climb hills

### Root cause

It was not the Humanoid slope limit, the walk speed or the anti-cheat. It was the **torso collider** that `Dinosaur.attach` welds under every dinosaur.

- Build 020 created `DinoCollider` as a 2.4-stud-tall box whose underside sat only **0.2 studs above the floor** under the root. `Dinosaur.render` then grew its footprint to `2.6 × scale` by `3.2 × scale` studs as the dinosaur grew, but kept the height and position fixed.
- On a slope of angle θ, the ground under a footprint corner is `halfDiagonal × tan θ` higher than the ground under the root. With a 0.2-stud gap, a baby dinosaur's box hits the hill above about **5.5°**. At full size plus BIG (scale 4.8) it hits above about **1.2°**.
- The authored island (`IslandLayout.height`) is steep almost everywhere: the steepest point is 41.8°, about half the island is above 21°, and only about 17% is below 7°. In an offline sample of terrain poses, the old box wedged into the ground in **84%** of poses at scale 1 and **97%** at scale 4.8 (91% combined in `verify_movement_mobile.py`).
- When the box wedges into the uphill face, physics pushes the whole assembly up and back. That lifts the Humanoid off its floor sensor, so it loses walking control and gravity slides it back downhill. Growing makes it worse: grown dinosaurs "can't climb anything".

What I ruled out:

| Suspect | Finding |
| --- | --- |
| `Humanoid.MaxSlopeAngle = 46` | No authored slope reaches it (max 41.8°), so raising it would not help. It stays at 46. |
| Visual meshes (packaged, authored and runtime) | All are `CanCollide=false`, `Massless=true` (`ResourceModels`, `RuntimeMeshes`, `AuthoredCreatures`, `DinosaurVisual`). |
| HipHeight / rig | The default R15 and R6 floor offsets are both 3 studs, and the collider math uses the live root size and HipHeight. |
| Custom controller forces | There are none. Movement is the stock Humanoid. Only Leap sets velocity, and only on the server, for 0.7 s. |
| `MovementGuard` corrections | The vertical envelope (≥ JumpPower 50 studs/s plus burst) already allowed a 46° climb at base speed. Its rubber-band resets were a symptom of the collider popping the assembly, not the cause. |

### Fix

- `MovementEnvelope.collider(scale, groundHeight)`, a shared pure function, keeps the growing footprint (BIG colliders still block trees, arches and boulders at torso height). It lifts the underside to `halfDiagonal × tan(MaxSlopeAngle) + DinoColliderSlopeMargin`, so the box clears a plane tilted to the Humanoid's own slope limit in **any** direction.
  - Scale 1: footprint 2.6 × 3.2, underside 2.48, top 3.68.
  - Scale 4.8: footprint 12.5 × 15.4, underside 10.6, top 12.5.
- `Dinosaur.luau` now welds the collider with a rigid `Weld` named `ColliderWeld`, so growth moves the box by editing `C0` instead of leaving it at the old offset. Humanoid setup uses `Config` directly; `MaxSlopeAngle` is unchanged.
- **The anti-cheat uses the same envelope.** `MovementEnvelope.plausible` takes `maxClimbRate(speed) = speed × tan(MaxSlopeAngle)` as one floor of the vertical budget, next to JumpPower and the capped fall speed (`MovementGuardMaxVerticalSpeed = 120`, formerly a literal). A dinosaur at SpeedCap (22 × 2.2 = 48.4 studs/s) climbing a 46° slope needs 50.1 studs/s, just above JumpPower, so this change is what keeps that climb legal. The services that share the check (Food, Predation, Progression) inherit it. `MovementGuard` lost an unused `allowed` variable; its tick, tolerance (3×, +4 studs) and correction behavior are unchanged.

New `Config` keys sit next to `MaxSlopeAngle`: `DinoColliderWidth`, `DinoColliderLength`, `DinoColliderTopPerScale` (PROVISIONAL), `DinoColliderMinHeight` (PROVISIONAL), `DinoColliderMinClearance`, `DinoColliderSlopeMargin` (PROVISIONAL, 0.35 studs) and `MovementGuardMaxVerticalSpeed`.

## BD-054: touch zones and safe insets

### Approach

Layout math moved into a new pure module, [`src/shared/TouchLayout.luau`](../src/shared/TouchLayout.luau). `Bootstrap.client.luau` keeps only a focused `scales()` that applies the result.

- **Safe area.** `BeDinoUI.ScreenInsets = CoreUISafeInsets` is set explicitly, and the layout uses `gui.AbsoluteSize` (the inset canvas) instead of `camera.ViewportSize`. Notches, the Android gesture bar and the Roblox top bar are therefore excluded before any placement happens.
- **Input style.** `UserInputService.PreferredInput == Touch` decides touch vs desktop, inside a `pcall` that falls back to `TouchEnabled`. The layout recomputes when `PreferredInput` changes.
- **Reserved Roblox zones** follow the PlayerModule defaults:
  - DynamicThumbstickFrame: left 40% of the lower two thirds.
  - TouchJump: a 70 px button when the shorter side is 500 px or less, 120 px otherwise. The whole bottom-right corner from the jump button to the screen edges is reserved.
  - The live `TouchGui` `JumpButton` and thumbstick frames are measured (`AbsolutePosition` relative to our gui) and unioned in. Their creation, moves and resizes trigger a deferred re-layout.
  - Every zone gets a `TouchSafeMargin` (8 px, PROVISIONAL).
- **Phone layout** (for example 800×360):
  - Top-left: status HUD, kept above the thumb zone. Build badge and Studio notice sit under it.
  - Top-centre: navigation rail between HUD and wallet. It uses one row, or a 2×3 grid on narrow phones. Buttons have the icon above a short label and are at least 44 px.
  - Top-right: crystal wallet.
  - Right column above the jump corner: weather on top, buffs, and **LEAP nearest the right thumb**.
  - Bottom-centre: **HOME** between the thumbstick zone and the jump corner.
  - Tablets get larger buttons, with icon-left labels when buttons are at least 120 px wide.
- **Desktop** keeps the Build 020 rail, HUD, wallet and modal geometry; the tests assert the legacy formulas. Two things change:
  - BD-052 moves Home to bottom-centre.
  - The timers stack drops to the bottom-right corner that Home used to occupy.
  - The Studio-only preview notice now narrows so it no longer overlaps the wallet at 1024 px.
- Minimum targets: touch buttons are at least `TouchMinTargetPx` (44 px, PROVISIONAL), and HUD text stays at 11 px or more (`TouchMinHudScale` 0.62, PROVISIONAL). 44–48 dp is a QA target, not proven usable until physical testing.

Layout overlays from the real module (blue = interactive, yellow = info, brown = reserved Roblox zones) are in [evidence](evidence/2026-10-13-bd053-054-movement-mobile/): `layout-800x360-touch.png`, `layout-640x360-touch.png`, `layout-1280x720-touch.png` and `layout-1920x1080-desktop.png`.

## BD-052: single Home with confirmation

- The **HOME** entry is removed from the navigation rail. The single bottom-centre button reads **HOME** (with the home icon) during a run, **EXPLORE ISLAND** in Sanctuary and **SAVING...** while ending.
- Tapping HOME opens "**Return to Sanctuary?** Your current run will end and rewards will be banked." It shows the catches and growth being banked, with **RETURN / CANCEL**. On touch both buttons are at least 46 px after modal scaling. CANCEL, the scrim and Escape close the modal without any request.
- The modal auto-closes if the run ends some other way (eaten or died) while it is open.
- **Server:** the 3-second stay-still channel is deleted. `Config.ExitChannelSeconds` and `ExitMoveCancelDistance` are removed, along with the `ExitChannelEndsAt` attribute, `startExitChannel` and `cancelExit`. `RequestEndRun` now calls the existing idempotent `RunLifecycle.tryEnd(player, character, "ManualExit")` directly. That is the same terminal path as death and predation: the first caller flips `Active → Ending`, `commitRunSettlement` dedupes by `runId`, and Home in Sanctuary or after death is a no-op. The 0.75 s request cooldown is kept. `ProfileRepository` is untouched.
- **PvP fairness (PROVISIONAL):** without the channel, Home could become an instant escape. The server therefore refuses Home while an active, unprotected dinosaur that could eat you (PredationService's 1.10× size rule) is within `HomeThreatRadius` (30 studs). It sets `LastExitStatus = "predator_nearby"`, and the client shows "A bigger dino is too close to go home!". Running away remains possible. Owner review of this rule is requested.

## Offline evidence

The new script `tools/verify_movement_mobile.py` is added to CI after `verify_gameplay`.

- **Slopes:** the steepest authored slope is 41.8° (below 46° − 2°). Collider corners clear a 46° plane in 24 directions at scales 1, 1.5, 2, 3, 4 and 4.8. In real-terrain poses (51×51 grid, 8 yaws, perimeter-sampled footprint, scales 1 and 4.8) the new collider touches terrain **0%** of the time and the legacy box **91%**. The legacy number is kept as a sensitivity probe.
- **Guard:** for both `MovementGuard` (3×, +4) and the service checks (2×, +2), at base speed and SpeedCap, for dt of 0.05–1 s, the following are accepted: climbs and traverses at 46° (including vy = 0 samples), falls up to 120 studs/s and jumps. Horizontal teleports, 30-stud/0.1 s flights and a 75° wall climb at SpeedCap are rejected. The existing vertical-teleport probe is kept.
- **Touch layout:** tested on 8 phone canvases (640×360, 667×375, 732×412, 760×360, 800×302 top-bar-reduced, 800×360, 844×390, 915×412), 6 tablet/large canvases (1024×768, 1280×720, 1280×800, 1366×1024, 1920×1080, 2400×1080) and 5 desktop canvases, plus an oversized measured TouchGui case. Every element is inside the safe canvas, no elements overlap each other, nothing intrudes on the thumbstick or jump zones, every touch target is at least 44 px, Home is at least 88 px wide and exactly centred, and the weather tile stays visible. On 800×360: Home 128×44, nav 53×52, LEAP 210×44.
- **Home lifecycle** (`verify_gameplay.py`, real `RunLifecycle` with stubs):
  - Malformed requests are ignored.
  - One request settles immediately (`Settled`, reason `ManualExit`, exactly one settlement).
  - A second Home in Sanctuary and a death after Home do not settle again.
  - Home is refused while a 10× bigger dinosaur is 29 studs away, and allowed once it is 35 studs away or when the only nearby dinosaur is similar in size.
- The full suite passes: binding checks, `verify_sources` (229 sources), all `verify_*` runners, `measure_identity_storage`, `bind_artwork --check`, `build.py` and `unittest` (37 tests). The `build/` artifacts are rebuilt.

**Not covered offline:** engine contact physics, Humanoid floor detection, real TouchGui pixel geometry, `PreferredInput` availability, physical DPI and thumb reach, FPS. The checks below cover those.

## Lead Studio checks (before the owner's phone test)

1. Play Solo, start a run and walk straight up each of the four mountains as a fresh Compy. Then repeat after growing (eat food) to around scale 4 and with a BIG dinosaur equipped. Expected: steady climb, no backward slide, no jitter, `MovementRejectCount` stays 0.
2. Idle on a slope for 10 s. Expected: no drift (above 46° only, sliding is expected Humanoid behavior).
3. Inspect `DinoCollider` with a selection box: it should sit inside the torso and lift as the dinosaur grows. Walk into a tree, the arch pillars and large boulders: the body is still blocked.
4. Device emulator, landscape 800×360 class Android device: the rail, HUD, LEAP and HOME do not overlap the thumbstick or jump button. Also check the 1280×720 tablet class and a desktop window.
5. Home: confirm and cancel. Confirm while a bigger second client is nearby (refused with a toast), then far away (returns at once). Results and hatch flow appear once. Settlement is not duplicated (`LastSettledRunId`).

## Owner Android test checklist (private playtest)

Use landscape, publish the private test place from this branch's build, and join on the Android phone.

1. **Layout at rest (Sanctuary).** Growth and catches are at the top-left. The DINOS / EGGS / FUSION / AURAS / POTIONS / SETTINGS buttons are along the top. Crystals are top-right. Weather, buffs and LEAP are on the right side. **EXPLORE ISLAND** is bottom-centre. Nothing sits under your left thumb area or on the round jump button. All text is readable without zooming. Screenshot it.
2. **Every button is tappable** with your thumb on the first try: each top button opens its menu, and X closes it. Note any button you missed.
3. Tap **EXPLORE ISLAND**. Move with the left thumbstick while repeatedly pressing jump with the right thumb. You should not hit LEAP or HOME by accident.
4. **Hills.** Walk straight up a mountain slope, then diagonally, then sideways across it. You should keep climbing smoothly with no sliding back. Stop on a slope for 10 seconds: you should not slide.
5. Eat food until clearly bigger (several size steps) and repeat step 4. Big dinosaurs should still climb.
6. Jump and **LEAP** uphill and downhill. You should not be snapped backwards (no rubber-banding).
7. Tap **HOME**. The popup should read "Return to Sanctuary? Your current run will end and rewards will be banked." with RETURN / CANCEL. Tap **CANCEL**: you stay in the run. Tap HOME again, then **RETURN**: you return at once (no 3-second wait) and see the results or hatching once.
8. Back in Sanctuary, tap the bottom button again: it reads EXPLORE ISLAND and starts a new run. It never gives rewards twice.
9. Rotate or lock the phone, or open and close the Android notification shade, then come back. The layout is still correct.
10. Report: phone model, any overlap or hard-to-tap button (screenshot), any spot where you slid or could not climb (screenshot with your position), and whether the text size felt OK.

## Open risks

- **Physics are verified offline only.** Contact behavior with the raised collider, smooth-terrain voxel facets (resolution 4) and Humanoid floor sensing need Studio and phone confirmation.
- **Smaller obstacles pass through the body.** The raised collider means grown dinosaurs' bodies no longer collide with obstacles lower than the slope clearance (about 10 studs at scale 4.8). Low rocks and jump stones visually clip into big dinosaurs' bellies instead of blocking them. Trees, arches and fences still block. If unwanted, the follow-up is a slope-aligned or capsule collider.
- **Per-tick tolerance is loose.** At base speed the pre-existing per-tick burst lets a 75° climb pass a single 0.1 s check. The Humanoid's MaxSlopeAngle is the physical stop. A sustained-window vertical check would tighten this.
- **Touch geometry is assumed, not measured on a device.** The reserved zones assume Roblox's default touch controls in the same safe-area canvas. Live TouchGui measurement is unioned in, but the coordinate assumption (`AbsolutePosition` deltas) needs device confirmation. Custom or classic thumbstick settings and the `PreferredInput` API are guarded but untested.
- **Small labels on phones.** Nav labels are 10–12 px; the icons carry the meaning. Validate readability on the owner's phone.
- **Home refusal near predators** (30 studs) is a provisional fairness rule that needs owner approval. The toast notification may sit over the top rail on phones.
- **Merge conflicts.** Bootstrap edits touch the nav entry list, `scales()`, the exit modal and the heartbeat. The parallel Fusion Menu hook may conflict on the rail entry line.
