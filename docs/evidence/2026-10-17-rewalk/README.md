# Post-#392 re-walk, Fly / Water in a run, pattern dino (2026-10-17, numbers only)

**CURRENT BUILD BEHAVIOR** measurement. Desktop Studio, one window of my own, Play, memory-only profile, one player. Build: `python tools/build.py --profile playtest` of main `1dc02fba` (which contains #392). The first session ran with the display asleep (numbers only). After the owner came back a second session (`rewalk3-demo.rbxlx`, built from this branch, one window of mine) re-measured the glide with the fix and took the pictures listed in "Pictures"; it ran at **15 frames/s render** (Heartbeat stayed 60/s), below the 30 fps the lead asked for, so the pictures are fine but timings by `task.wait` were sampled on Heartbeat instead.

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

## 4. Glide re-measured with the fix (BD-593, second session)

Pteranodon `05_horizontal_bands`, island run, real Space key held, velocity sampled on every Heartbeat (60/s, the render rate was 15/s):

| Case | Before the fix (first session) | With the fix |
|---|---|---|
| Fastest fall with Space held, normal gravity 250 | 45 to 58 studs/s | **16 to 17 studs/s** in three consecutive hops (the cap is 12; the sample is taken after the physics step adds one gravity step of 4.2) |
| Same, Space released (control) | 40 to 54 studs/s | 33 and 46 studs/s (free fall) |
| Budget: gravity set to 45 on the client so one fall lasts 1.5 s | not possible | fall held at the cap for **0.78 s** of the sampled window, then 29 studs/s: the budget of 1 s per airtime ends and the dino falls freely again |

A drop from 120 studs up was refused by the server (the dino was put back on the ground), so the budget was measured with the low gravity instead; the pure budget logic is also checked offline (`tools/verify_class_movement.py`). The hover cap is untouched (design call).

## Pictures

| # | Image | What |
|---|---|---|
| 01 | [01-hub-first-screen.jpg](01-hub-first-screen.jpg) | hub first screen after the Bootstrap split: rail with icons, crystal plate, EGGS plate, TAP TO GO, Leap, weather tile |
| 02 | [02-eggs-screen.jpg](02-eggs-screen.jpg) | Eggs screen: 5 empty nest slots, "Eggs waiting: 8", OPEN, AUTO |
| 03 | [03-hatch-egg1.jpg](03-hatch-egg1.jpg) | hatch screen, egg 1 of 8 cracking (Cream / Teal, no pattern) |
| 04 | [04-hatch-pachycephalosaurus-round-spots.jpg](04-hatch-pachycephalosaurus-round-spots.jpg) | hatch result: Round Spots visible on the low-poly model |
| 05 | [05-hatch-pteranodon-bands.jpg](05-hatch-pteranodon-bands.jpg) | hatch of the Pteranodon: pink and purple horizontal bands |
| 06 | [06-hatch-spinosaurus-freckles.jpg](06-hatch-spinosaurus-freckles.jpg) | Legendary banner, Spinosaurus with freckles |
| 07 | [07-dino-index.jpg](07-dino-index.jpg) | Dino Index, "Collected 9 of 22 (40%)" |
| 08 | [08-dino-details-wavy-t-rex.jpg](08-dino-details-wavy-t-rex.jpg) | Dino Details, Wavy Stripes T-Rex with its traits |
| 09 | [09-potion-shop.jpg](09-potion-shop.jpg) | Potion Shop, six offers |
| 10 | [10-settings-look.jpg](10-settings-look.jpg) | Settings, Look tab |
| 11 | [11-pteranodon-bands-hub.jpg](11-pteranodon-bands-hub.jpg) | equipped Pteranodon in the hub, bands on the model |
| 12 | [12-fly-glide-air.jpg](12-fly-glide-air.jpg) | Fly dino in the air with Space held (thunderstorm tint and haze; the wings look folded in this frame, I did not check the open-wing pose) |
| 13 | [13-mosasaurus-diamond-scales-hub.jpg](13-mosasaurus-diamond-scales-hub.jpg) | equipped Mosasaurus, magenta and teal diamond scales |
| 14 | [14-water-dash-ruler.jpg](14-water-dash-ruler.jpg) | after the Water dash, ruler every 1 stud (long ticks every 5); dark because of the storm, the dino is a silhouette at tick 14 |
| 15 | [15-run-complete.jpg](15-run-complete.jpg) | Run Complete card (a 20 s run, 0 eggs) |

## Pattern by eye

The pattern reads clearly on the low-poly models: the Pteranodon bands (04/05/11), the Mosasaurus diamond scales (13), the T-Rex wavy stripes (08), the Pachycephalosaurus round spots (04) and the Spinosaurus freckles (06). Nothing is blank or a cube; colours are the genes' colours. One oddity: in 12 the Fly dino shows as a translucent purple silhouette; that is the weather tint, not checked further.

## Not done

* The wing pose of the Fly dino during the glide (picture 12 caught folded wings) and the Water surge look (BD-556) are not judged.
* The Water dash picture is too dark to judge the pose.
* The Studio `Failed to upload TexturePack` errors were not investigated further.
