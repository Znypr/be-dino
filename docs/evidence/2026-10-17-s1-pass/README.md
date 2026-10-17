# Lead Studio pass, session 1 (docs/145 blocker 5 leftovers), 2026-10-17

Label: **STUDIO EVIDENCE, CURRENT BUILD BEHAVIOR.** Playtest build `redesign-020` from `python tools/build.py --profile playtest` on origin/main `a6e82680` (this PR adds docs and evidence only; no game code changed). One Studio window of its own (opened 12:58, closed 13:14:29), unpublished copy (GameId 0, "STUDIO PREVIEW, progress not saved, test currency"), Play mode, one player (admin). Window 1140 x 785 viewport; `RenderStepped` 60 per second at every check (above the 30 fps rule). **This is desktop Studio, not a phone, not a published server, and one player only.** Raw numbers: [raw-numbers.txt](raw-numbers.txt). Scripts used: [walker-5min.client.luau](walker-5min.client.luau), [cave-weather-probe.client.luau](cave-weather-probe.client.luau).

The four leftovers of [docs/145](../../145-session1-readiness-2026-10-17.md) blocker 5 (5-minute stopwatch run, cave weather-leak cycle, memory read, flag decision) are all done below. Verdict in one line: **no new code blocker found; the cave stays clean in all 7 weather events; the egg pace question is not answered by a script and needs a human run.**

## 1. BD-418: the 5-minute stopwatch run

How: from the hub, the script walks the dino into the Island Gate arch (the same way the regression walk does), then for exactly 300 s `Humanoid:MoveTo` the best visible food (points / (distance + 10)^2, a food counts as eaten when it turns invisible or the dino is within 3 studs; 6 s without progress marks it blocked and jumps). Normal walk speed 22, **no admin boosts** (admin Food worth, Growth, Speed and Mutation values were not touched; weather was NOT started by the admin remote during the run). Species Compy, low-poly. Values read each minute from the character (`CatchScore`, `FoodCatchCarry`, `GrowthScore`, `VisualScale`). Raw food is `GrowthScore / GrowthPerFood (0.1)`, so it is inflated by the thunder growth bonus (x1.1) in minutes 4 and 5; the corrected figure is in the notes.

| Minute | Eggs caught | Raw food (growth / 0.1) | Growth | Size (VisualScale) | Weather | Crystals |
| ---: | ---: | ---: | ---: | ---: | --- | --- |
| 0 | 0 | 0 | 0 | 1.00 | clear | not paid during a run |
| 1 | 25 (+0.03 carry) | 1,043 | 104.3 | 1.76 | clear | |
| 2 | 49 (+0.51) | 2,063 | 206.3 | 2.26 | clear | |
| 3 | 65 (+0.71) | 2,738 | 273.8 | 2.54 | clear | |
| 4 | 85 (+0.59) | 3,410 | 341.0 | 2.80 | **thunder** (eggs x1.4, growth x1.1, speed x1.15) | |
| 5 | **97** (+0.82) | 3,811 (about 3,710 corrected) | 381.1 | 2.94 | thunder | |
| End (HOME tapped at 6:12, 99 eggs) | **99** | | 386.7 | | | **+183** (Run Complete card), **+4 nests**, level 2 |

Crystals are paid when the run settles, not during it (the run has no crystal counter; the map crystal pickups counter `CrystalPickupCount` stayed nil, none collected). Run Complete: "Eggs found 99, +183 Crystals, +4 nests, Growth 386" (`05-run-complete.jpg`). Server telemetry for the same run: `[BD-TELEMETRY] {"event":"run_end","duration_s":372,"reason":"ManualExit","food":4125,"food_is_estimate":true,"eggs":99,"nests":4,"crystals":183}` (duration includes about 70 s of me reading the numbers before tapping HOME).

Pictures: `03-run-30s.jpg` (clear, 21 eggs), `04-run-5min-thunder.jpg` (99 eggs, thunder, HUD "Speed +15%, Growth +10%, Eggs +40%"), `05-run-complete.jpg`.

### What it says (honest reading)

* **The conversion works exactly as configured.** `FoodCatchRate` today is 12/500 = 0.024 (BD-418, PROVISIONAL; read from Config in the running game). Minute 1: 1,043 food x 0.024 = 25.03 eggs; the game shows 25 and 0.03 carry. Under thunder the x1.4 loot multiplier applies on top (97.8 eggs at 3,710 food would be 89 in clear weather).
* **The owner anchors do not match the pace of a bot.** AGENTS.md anchor "500 food -> 40 eggs" is superseded (BD-165, then BD-418 12/500); the working target is "about 15 eggs per normal 5-minute run, about 600 to 700 food" ([docs/119](../../119-catch-rate-15-per-run.md) s1). The scripted walker ate about **3,700 food in 5 minutes (about 740 food/min), 5.3 to 6.2 times the docs/119 estimate**, and caught **97 eggs, 6.5 times the target of 15** (89 in clear weather, 5.9 times). With the old 40/500 anchor the same food would have been about 297 eggs (over the 150 cap).
* **A scripted walker is faster than a child.** It never stops, never turns around, never looks at the UI, always heads to the nearest rich food at full speed, and it jumps when blocked. A child will be slower; how much slower is exactly what is NOT measured. So 97 is an **upper bound for the egg count**, not an estimate of a normal run, and the docs/119 figure (700 food) is neither confirmed nor refuted. Two things that make the walker's number rise on their own: the pickup radius follows the dino's size (`MouthReach.radius(speciesId, scale)` in `src/server/FoodService.luau`; the dino reached 2.9x), and a natural Thunderstorm started at about 3:00 into the run (see below). Raw food per minute was 1,043 / 1,020 / 675 / about 611 / about 365 (the last two divided by the 1.1 growth bonus): the walker slows a lot after the first two minutes, either because the nearby clusters are empty (8 s respawn) or because it got stuck; I did not look at where it was.
* **Almost any 5-minute run meets a weather event.** A random event starts 300 s after the previous one ends and lasts 180 s (`WeatherInterval`, `WeatherDuration`, `WeatherClock`: a cycle of 480 s, the first one 300 s after the server starts), so only a run that fits exactly into the 300 s gap misses it. The HUD "Weather in N min" tile was already counting down at 0:30 and thunder (loot x1.4, speed x1.15, growth x1.1) arrived at about 3:00 (it still had 50 s to go at the 5:00 picture). The "15 eggs in 5 minutes" target of docs/119 does not say whether it includes this; weather multipliers range x1.1 (rain) to x1.75 (blood moon).
* **Telemetry overstates food in weather.** The telemetry's `food` (4,125) is eggs / rate (`food_is_estimate: true`), which ignores the loot multiplier; actual raw food was about 3,710. Reading `LastRunFood`-style logs from the playtest for BD-418 will therefore be 10 to 40 percent too high in weather runs.
* **Crystals and nests are in the owner's illustrative range.** 183 crystals and 4 nests at about 3,700 food, against the examples "about 30 at 500 food, 220 and 6 nests at 5,000 food" (AGENTS.md, illustrative, not a formula).
* **Frame rate and errors:** 60 fps at 30 s, 5:00 and at the end; no script error in the session (only the known UIBlox "FoundationProvider" warnings); the dino grew to 2.94x and the camera stayed readable (`04-run-5min-thunder.jpg`).

What is still missing for BD-418: **a human run.** The owner (or any person who plays like a child) plays two or three real 5-minute runs with no scripts; the number to read is the Run Complete "Eggs found" and the `[BD-TELEMETRY]` line. New row BD-573 holds this. `FoodPickupAtMouth` stays OFF (BD-527); this run was with it OFF.

## 2. Cave weather-leak cycle (BD-383, BD-398, BD-403)

Each event: stand at the Heart spawn in the cave hub (`CaveHub` ON), start it with the admin remote (`AdminAction startWeather <id> 170`), wait 6 to 8 s, read what the weather draws, take a picture; then walk out through the gate and read the same numbers on the island 6 to 7 s later (weather must be back), take a picture; then HOME and the next event. A reading is "clean" when particles on = 0, beams on = 0, no moon, and Lighting, haze, WeatherGrade, bloom and rays equal the clear-weather hub baseline (Brightness 1.30, Exposure -0.60, FogEnd 900, haze 0.04, grade 0, bloom 0, rays 0, with the CaveGrade correction on).

| Event | In the cave hub (picture) | Back outside (numbers; picture) |
| --- | --- | --- |
| Rain | **clean**: 0 emitters, grade 0, same Lighting as clear (`10-cave-rain.jpg`) | 12 emitters (rate 13,812), Brightness 0.90, FogEnd 260, haze 0.50, bloom 0.20 (`11-island-rain-returns.jpg`) |
| Thunderstorm | **clean** (`12-cave-thunder.jpg`) | 12 emitters (18,128), Brightness 1.80, FogEnd 200, bloom 0.50 (first picture hidden by the Run Complete card; numbers only, and `04-run-5min-thunder.jpg` shows thunder on the island from the natural event) |
| Blizzard | **clean** (`13-cave-blizzard.jpg`) | 8 emitters (6,146), FogEnd 110, haze 0.80, saturation -0.40 (`14-island-blizzard-returns.jpg`) |
| Volcanic Bloom | **clean** (`15-cave-volcano.jpg`) | 16 emitters (2,503), saturation +0.15, rays 0.15 (`16-island-volcano-returns.jpg`) |
| Northern Lights | **clean** (`17-cave-aurora.jpg`) | 7 emitters + 42 beams, bloom 1.20, saturation +0.40 (`18-island-aurora-returns.jpg`) |
| Earthquake | **clean** (`19-cave-quake.jpg`) | 5 emitters (239), haze 0.45 (`20-island-quake-returns.jpg`) |
| Blood Moon | **clean**, 0 moon parts (`21-cave-bloodmoon.jpg`) | 6 emitters, 3 moon parts, saturation +0.45, bloom 0.50 (`22-island-bloodmoon-returns.jpg`) |

**Result: 7 of 7 events leak nothing into the hub, and 7 of 7 come back on the island.** The HUD weather tile ("Rain 2 min" and so on) and its growth/eggs line stay visible in the hall (information text, as designed in BD-398); no title card or toast is in the pictures because the events were started while standing in the hall.

Extra checks:
* **Leaving the island with a weather event on** (blood moon, 2 s after tapping GO HOME): `RunState` stays "Settled" for about 2.1 s (the dino is still out on the island and the weather is fully on), then Sanctuary: particles off at once and the grade fades 0.45 -> 0.00 in 0.8 s. Fully gone about 2.9 s after the tap. Not a leak (the dino is still outside during the settle), but the 2 s of full weather after tapping HOME is what a player sees.
* **Not measured:** the quake camera rumble (the camera sample read 0.000 in both places because `execute_luau` holds the camera; BD-403's static verifier covers it), the weather sounds (none bound), a second spot in the hall (only the Heart was used; docs/evidence/2026-10-16-cave-polish-3 has the potion and style stations), Reduce Motion and Weather Off/Lite/Full.

## 3. Memory read (desktop Studio, not a phone)

`Stats:GetTotalMemoryUsageMb()` and `GetMemoryUsageMbForTag` for every tag above 0.5 MB. **Studio runs the editor, the server and the client in one process, so the total is NOT the client's memory**: the client and the server returned the same numbers, and the `Internal` (about 1,930 MB), `LuaHeap` (about 700 MB) and `Script` (270 MB) tags are Studio itself. The numbers still show how much the session moves things. "Content tags" below is my own sum of the render and content tags (Instances, Signals, BaseParts, Graphics*, Sounds, TerrainVoxels, Gui, Animation); it is a rough stand-in for what a client would hold, not a measurement of one.

| Moment | Total (MB) | GraphicsTexture | GraphicsMeshParts | GraphicsParticles | Instances | Gui | Content tags sum | Workspace parts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Join (the player starts in the cave hub) | 3,389 | 59.7 | 4.4 | 15.9 | 164.1 | 28.6 | 418 | 6,387 |
| After the 5-minute run (island, thunder) | 3,704 | 87.6 | 4.3 | 16.1 | 164.0 | 28.6 | 450 | 6,467 |
| Cave hub after the run (clear) | 3,818 | 99.2 | 4.3 | 16.0 | 196.2 | 28.9 | 495 | 6,235 |
| Cave hub after 7 weather events and 7 gate trips | 3,924 | 135.7 | 4.3 | 15.9 | 197.5 | 29.5 | 545 | 6,372 |

Other tags: Sounds 4.5 -> 6.7, TerrainVoxels 7 -> 8, GraphicsTerrain 48 -> 49, GraphicsParts 6.2 -> 6.5, Animation 5.2 -> 12.6, BaseParts 52 -> 54. Workspace attributes: `LowPolyDinosLoaded` 22, `LowPolyDinosFailed` 0, `PatternImagesLive` 0, `PatternImagesPinned` 0; **`LowPolyImagesMiB` was never set (nil)**: no EditableImage was created, so the 80 MiB cap of docs/145 step 11 reads trivially and the EditableImage pattern path was not exercised (the equipped Compy is the "Packaged resource model", `VisualSource`).

Against [docs/107](../../107-offline-mobile-budget.md) s1 and `tools/qa/phone_budgets.json` (a phone, 3 GB, not Studio):
* **Total client memory 1,200 MB:** cannot be compared; the Studio total (3.4 to 3.9 GB) contains the editor. The content-tag sum (418 to 545 MB) is under 1,200 MB but not the same quantity. No verdict.
* **Texture memory (PROPOSED 200 MiB, docs/146):** `GraphicsTexture` 59.7 -> 135.7 MB, under 200 but **it more than doubled in one session** (join 60, after the run 88, after seven weather events 136), consistent with weather and island textures loading and staying. docs/146 predicted 364 to 437 MiB per scene at RGBA8 for every image slot bound; this reading is Studio's loaded textures only. It is the number to watch on the phone run: a long session with all weather seen is the worst case.
* **Parts:** 6,387 at join (docs/107 s2: about 7,625; docs/146: 7,061; cap 9,150), 6,235 to 6,467 later (culling does not remove them; the swing is the food and the weather rigs). Under the cap. The phone rule of thumb (3,000 in range) is a different measure.
* **Low-poly image MiB (cap 24 distinct, 80 MiB budget):** 0 (not exercised, see above).
* **Particles:** 29 enabled emitters in the thunderstorm on the island, 12 at the rain moment; `GraphicsParticles` stays 16 MB.

Remaining for BD-322 / BD-085: the same read on the phone, and a Studio read with several species equipped and a pattern dino (to light up `LowPolyImages*`).

## 4. Flag decision: the playtest profile (`tools/release_profiles.py`)

Values read from `Config` in the running playtest build, and what today's evidence says. "Supported" = something I saw today backs the value; it does not mean tested on a server or a phone.

| Flag | Playtest value | Evidence today | Verdict |
| --- | --- | --- | --- |
| `ReleaseProfile` / `ProfileDataStoreName` | playtest / `BeDino_Playtest_M1_v1` | values read from Config; Studio uses a memory profile, the real store was never touched | config OK; the store is **not testable** offline (blocker 3 and 4 of docs/145) |
| `PlaytestUniverseId` / `PlaytestPlaceId` | 10769812255 / 111259822927673 | values present; which experience this is and whether a non-owner can join is BD-004 | **not supported by Studio**; owner |
| `CaveHub` | true | hub at join, 60 fps, gate walk 7 times (6.1 s each), 5-minute run out and home, 7 of 7 weather events clean, `01`/`02` pictures; look 7/10 on 2026-10-16 | **supported (single player, desktop)**; phone and 12 players open (BD-293) |
| `LowPolyDinos` | true | 22 low-poly dinos loaded, 0 failed, Compy walks and grows to 2.94x with no visual fault in `04`; EditableImage patterns not exercised (`PatternImagesLive` 0) | **mostly supported**; the pattern and "Allow Mesh & Image APIs" path is **not covered today** |
| `ClassMovementEnabled` | true | Compy only (ground class); walk speed 22 and the thunder x1.15 (25.3) read correctly; leap tested in the morning walk (BD-541); Fly glide and Water dash not tried | **not supported today** (neither wrong nor right); the morning walk covered the leap only |
| `WorldArtMode` BiomeKit / `FoodArtMode` Kit / `WorldArtDensity` 1.25 | BiomeKit / Kit / 1.25 | island looks right in `03`, `04`; 60 fps; 6.2 to 6.5k parts, under the 9,150 cap; food visible and eaten | **supported on desktop**; phone open (BD-085) |
| `IdentityPersistentEnabled`, `IdentityFusionPreviewEnabled` | true / true | nothing today: Studio memory profile, no fusion, no rejoin; the Fusion menu opened in the morning walk only | **not supported**; the riskiest "true": it writes real test profiles on the playtest store, odds PROVISIONAL, recovery is store rotation. If one of the flags has to move for session 1, move this one first |
| `RunTelemetryEnabled` | true | printed a correct `[BD-TELEMETRY] run_end` for the real run and the 7 short ones; **food is an estimate and ignores weather multipliers** (4,125 printed, about 3,710 real) | **supported**; keep, and tell whoever reads the log that `food` is eggs / rate |
| `PlaytestFeedbackEnabled` | true | the purple "Tell us!" button shows in the hub (`05`, `10` to `22`); a send was not tried today (docs/145 step 10) | **partly supported** |
| `CombatEnabled` false, `SpecialFoodsEnabled` false, `PerDinoCosmeticsEnabled` false, `FastTravelPerk` false, `HatchV2` false, `HatchV2Preview` false, `QaOverlayEnabled` false, `DemoDirectorEnabled` false, `PaidRandomItemsEnabled` false, `CrystalPacksEnabled` false, `ObjectivesEnabled` false, `FoodPickupAtMouth` false, test grants and harnesses false | all false as intended | read at runtime; the run behaved like the off state (instant predation path, no special food, no pack buttons) | **supported** |
| `NpcPredatorsEnabled` | true (inert without combat) | no predator seen in 5 minutes | unchanged, harmless |
| `StreamingEnabled` | false (not set) | `workspace.StreamingEnabled` false | as decided (ST1, ST4) |
| `AdminPanelEnabled`, `StudioLocalProfilesEnabled`, `StudioTestWalletEnabled` | true (always) | the Admin button shows here because every player is an admin in an unpublished copy; the 1,000,000 test crystals are the Studio wallet | published behaviour (creator only, real wallet) **not testable here** (blocker 4) |

**Which look wrong for session 1?** None is wrong on today's evidence. Two to watch: (1) the **identity / fusion pair** has no evidence at all today and is the one that can damage a profile; (2) **`ClassMovementEnabled`** has not been felt by a Fly or Water class. Both are rolled back by removing one `Rule(...)` line in `release_profiles.py` in one PR (docs/145 step 15), never a hot fix. Not flags but session-1 notes: the egg pace (section 1) and the weather bonus in a 5-minute run.

## 5. Not checked

A phone, a published server, a second player, a Fly or Water class in a run, a pattern dino (EditableImage), the feedback send, the quake camera rumble, Reduce Motion and the weather settings, the hall away from the Heart, any sound, and a human 5-minute run.

## 6. Setup facts for the next lead

`execute_luau` ran in the Client datamodel with `shared` kept between calls; a `task.spawn` thread keeps running after the call returns, which is how the 5-minute walker ran while the calls were used to read it. Every call set `CameraType = Custom` first. The two buttons of a card (GO HOME / CANCEL, BACK TO SANCTUARY / OPEN EGGS) share the same instance path, so `instance_path` clicks the wrong one: click at `AbsolutePosition + AbsoluteSize / 2` with `moveTo` + `mouseButtonClick`. `RequestEndRun` fired from a script opens the Run Complete card, which covers the next picture: set the player attribute `DemoCloseModal` to close it (the hook the walk uses). Studio was placed at x=1920, 1920 x 1040, forced topmost, and released with NOTOPMOST and minimize; only its own process (PID 26048) was ended.
