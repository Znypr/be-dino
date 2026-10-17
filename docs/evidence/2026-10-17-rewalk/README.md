# Post-#392 re-walk, Fly / Water in a run, pattern dino (2026-10-17, numbers only)

**CURRENT BUILD BEHAVIOR** measurement. Desktop Studio, one window of my own, Play, memory-only profile, one player. Build: `python tools/build.py --profile playtest` of main `1dc02fba` (which contains #392). The display was asleep, so **no picture exists**: every result is a number or a text read from instance properties. Paused by the owner before the last re-test (see "Not done").

How it was driven: the walk scripts of `tools/qa/regression_walk` run as `ModuleScript`s (`loadstring` is not available on the client; a server snippet copied each script into `ReplicatedStorage` and the client `require`d a fresh copy). `VirtualInputManager` is blocked, but **`user_mouse_input` (x, y = the viewport position the step prints in its NEEDS line) and `user_keyboard_input` do reach the game even with the display asleep**, so every NEEDS click was done by hand and the step re-run. Plain build for part 1; for parts 2 and 3 the same build with `DemoDirectorEnabled = true` patched into the built place only (the committed Config is unchanged), used to bank 5 Uncommon and 3 Legendary Normal eggs through the real hatch path (`DemoTrigger hatchParty`), then hatched through `ClaimChest` and equipped through the real `EquipSpecies` remote.

## 1. Walk after the Bootstrap split (#392)

| Step | Result | Notes |
|---|---|---|
| 1 First screen | PASS | viewport 1140x785, 30 frames in 0.5 s, welcome card opened by itself, LET'S PLAY clicked, menu closes, build badge `BUILD redesign-020`. HUD rectangles all present, none overlapping or off screen: rail 169x347 at (14,188), crystals 236x43 at (883,8), EGGS plate 190x58 at (18,650), home 221x54 at (459,650), timers 259x199 at (860,505); SIZE bar, goal hint, next goal, "Tell us!" hidden at home as designed. |
| 2 Leave through the gate | PASS (see Output) | run Active, Location Island, SIZE bar, HOME button. The walk printed FAIL only because of the Studio errors below. |
| 3 Eat | PASS | 12 eggs, plate EGGS 12, growth 51 (food x10 admin) |
| 4 Leap | ODD | remote only; server accepted, cooldown shown (LEAP 59 s) |
| 5 Rain | PASS | |
| 6 Go home, Run Complete | PASS (HOME fired by remote) | settled, ManualExit, 12 eggs banked, `+30 Crystals` |
| **7 Eggs screen and hatch** | PASS by hand | Eggs screen: 5 of 5 nest slots, "Eggs waiting: 12"; OPEN started the hatch screen; eggs claimed one at a time (`Egg 1 of 12` Compy, `Egg 2 of 12` Raptor ...); Common on AUTO then restored to SHOW through `SetRevealSkip`. The walk step itself restarts when a hand click changes the screen, so the auto-open part was done by remote, not by the button. |
| **8 Equip** | PASS | parasaurolophus: WalkSpeed/zoom/camera checks pass, 8 of 8 box corners on screen |
| **9 Potion buy and use** | PASS | Swift Sip bought (20 crystals) and used, "Speed potion 5 min, Speed +20%" on the HUD |
| **12 Settings** | PASS | all four tabs, Calm motion ON saved (`calm=true`), switched OFF again and saved |
| Dino Index | opens and lists | "Dino Index", 22 species, "Collected 3 of 22 (13%)", undiscovered cards read "???" / "Not discovered", FUSION button |
| Dino Details | opens and lists | from the Fusion menu "My dinos" list (6 dinos) the `i` button opened "Freckles Raptor": traits, odds, original egg, cosmetics text |

**Output errors.** Game errors: none. Studio itself printed about 40 `Failed to upload TexturePack (... PublishService AssetUpload failed ... HTTP 429 / Internal)` errors at the start of every Play: they match the 38 `SurfaceAppearance` objects under `Resources` (all with PBR maps), which Studio tries to package in an unpublished place. They never appeared in an earlier evidence file; I did not find out whether it is new or only newly seen, nor whether it is the Studio build or the place. It makes the walk's "no new errors" check FAIL; I filtered that one text for the rest of the walk.

## 2. Fly and Water dinos in a real run

| Check | Fly (Pteranodon) | Water (Mosasaurus) |
|---|---|---|
| Real equip path | `EquipSpecies pteranodon` + variant key: `equipped`, class Fly | same: `equipped`, class Water |
| Walk speed / jump power | 26.40 / 55.00 (match `ClassMovement`) | 18.70 / 0.00 (match) |
| Eating | 7 pickups in 20 s, growth 0 to 5.6, 1 egg | 9 pickups, growth 2.2 to 7.95, 1 egg |
| Eggs counted | catch 1, `LastRunEggCount` 1, 1 waiting | catch 1, `LastRunEggCount` 1, 2 waiting |
| Class movement | **glide does not work** (below) | dash by the Space key: **14.5 studs**, first movement 0.11 s (nominal 16.8) |

**Finding (fixed in this branch): the Fly glide and hover cap never acted.** The character is owned by its client (`FallRecovery` sets the owner); a server script wrote `AssemblyLinearVelocity.Y = 80` on it and the root rose **0.00** studs. The Fly hover loop of `ClassMovementService` is a server velocity write, so it does nothing. Measured with the glide held (real Space key, held 1.8 s): fastest fall **45 to 58 studs/s** against the intended cap of 12; peak root height 9.9 to 10.7 against the cap of 6.5. Fix: `ClassGlide.client.luau` now applies the glide on the client through the new pure `ClassMovement.glideStep` (BD-593; `tools/verify_class_movement.py` adds a free-fall simulation and mutants). The **hover cap is deliberately not moved**: it compares the ROOT height (3 to 4 studs standing) with 6.5, so turning it on would cut the Fly jump to about 3.5 studs, below the Ground jump (5). That is a design call, not done.

## 3. Pattern dino

Plain build, Raptor "Freckles" equipped through `EquipSpecies` with its variant key: `LPLookKey` `raptor|08_freckles|...`, every one of the 7 parts `LPLod = texture`, body `TextureContent` is an `EditableImage` 256x256 with 6,318 of 65,536 pixels blue (the freckles), 7,540 distinct colours. `LowPolyImagesLive 42`, `LowPolyImagesPinned 35`, **`LowPolyImagesMiB 4.88`**, cache misses 42, **denied 0**, `PatternImagesLive 5`. Demo build: Mosasaurus `07_diamond_scales`, body `EditableImage` 256x256, 14,542 distinct colours, `LowPolyImagesMiB 2.44`, denied 0. Pteranodon `05_horizontal_bands` was equipped the same way (look key not printed). The EditableImage path ran, the budget attribute is set.

## Not done (owner paused the work)

* Re-test of the glide with the fix (the place `rewalk2-demo.rbxlx` was built and opened, nothing measured). Expect: with Space held the fall is held at 12 studs/s for 1 s per airtime.
* Pictures owed (display asleep): hub first screen, Run Complete, Eggs screen, hatch of a Pteranodon with bands and a Mosasaurus with diamond scales on the model, Dino Index, Dino Details, Potion Shop, Settings, a Fly glide in the air, the Water dash.
* A look by eye at the pattern on the low-poly model.
