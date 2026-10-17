# First look at the jump / leap / land / Water-surge poses (2026-10-17)

Branch `claude/pose-first-look` (PR into main). **CURRENT BUILD BEHAVIOR**, desktop Studio only, no phone, no second client.
Rows: BD-250, BD-251, BD-249 (Review / test), new rows BD-555, BD-556.

## What was looked at and how

* Build: `python tools/build.py --profile playtest` (LowPolyDinos, CaveHub and ClassMovement on) of origin/main plus PR #395 (the `character` rig fix; its CI was still pending so the branch is merged into this one). One Studio window of my own, Play, memory-only profile, one player. `RenderStepped` counted 60 frames/s before the capture series. Captures are Studio `screen_capture` only; the camera was set back to Custom after each series.
* **The Studio keyboard tool did not reach the game** (W, Space and E left `MoveDirection` at 0 and no leap started), and mouse clicks stopped landing after the first few. So the player was driven by a script that does what the game scripts do: `Humanoid:Move` for walking, `Humanoid.Jump` for Space, for E the same steps as `requestLeap` (RequestLeap remote, jump state, 72 stud/s forward velocity for 0.7 s, `LeapPredictAt` stamp), and the `ClassDash` remote plus a jump for the Water dash. The real `LowPolyAnimator` and `LowPolyPose` then ran unmodified. A treadmill (the root is put back to the same x/z every frame, velocity kept) kept the walking dino in front of the side camera.
* **Frame log:** a `RenderStepped` logger recorded, per frame, humanoid state, root height over the ground, the rotation of every part's weld and the lowest vertex of the feet. Frame-to-frame values below are degrees per 16 ms frame.
* **Stills of phases that last 0.1 s** (crouch, push-off, landing squash, surge) cannot be hit by a capture request, so they are shown as a "pose sheet": clones of the live visual placed on a stage, each posed with the live `LowPolyPose` module and the animator's own offset formula at a chosen phase and progress (images 04 to 06, 10, 11, 15, 16). These are stills of the pose maths on the real models, not screenshots of the animator running. The live-play shots (01 to 03, 07 to 09, 12 to 14) freeze the dino in the air (anchor the root, the animator keeps posing) or catch it walking.
* Weather events (a Blood Moon, a storm, rain) kept starting and tinting the pictures; they were stopped with the admin `stopWeather` remote before each series (the rain in the Reduce Motion shot was not).

## Shot table

Look rating = how it reads for a 7 to 10 year old (1 to 5, honest). PASS = nothing wrong found, ODD = plays but reads oddly or has a small defect.

| # | Image | Species / action | Result | Look | Notes |
|---|---|---|---|---|---|
| 01 | [01-compy-walk-side.jpg](01-compy-walk-side.jpg) | Compy, walk, side | PASS | 4 | Alternating legs, small arm swing, tail counter-swing, head peck. Max leg 29 deg, arm 16, tail 10, head 6; per-frame delta never above 5.9 deg. Feet -0.05 to +0.29 stud against the ground. |
| 02 | [02-compy-walk-front.jpg](02-compy-walk-front.jpg) | Compy, walk, front-left | PASS | 4 | Same run from the other side. A foreground food item hides part of the dino in 01. |
| 03 | [03-compy-leap-air.jpg](03-compy-leap-air.jpg) | Compy, leap, in the air | PASS | 4 | Body pitched forward, legs and arms tucked, tail up. Calm and readable. |
| 04 | [04-compy-phases-sheet-1.jpg](04-compy-phases-sheet-1.jpg) | Compy phases 1 to 7 (rest, crouch end, push-off end, air jump, air leap, land start) | PASS | 4 | Crouch dips the body and folds the legs; push-off stretches upright with the legs trailing; tuck. Feet 0.14 above the ground in the crouch, -0.01 at push-off. |
| 05 | [05-compy-phases-closeup.jpg](05-compy-phases-closeup.jpg) | Compy close-up of crouch, push-off, tuck | ODD | 3 | Small dark gaps show at the hip and tail root when a limb rotates (the hollow inside the mesh), seen only at 14 studs. |
| 06 | [06-compy-phases-sheet-2.jpg](06-compy-phases-sheet-2.jpg) | Compy landing squash (p 0 / .25 / .6), push of a leap, defeat end | PASS | 4 | Landing squash is soft. Defeat: the dino tips onto its side with legs spread, head down, no gore; feet -0.16 stud into the ground in that final pose. |
| 07 | [07-pteranodon-walk.jpg](07-pteranodon-walk.jpg) | Pteranodon (Fly), walk | PASS | 5 | Wings folded against the body, tiny shuffle, legs alternate. Wing angle stays 70 to 75 deg (the fold), per-frame wing delta 1.5 deg max. |
| 08 | [08-pteranodon-jump-air-side.jpg](08-pteranodon-jump-air-side.jpg) | Pteranodon, jump, in the air, side | PASS | 5 | Wings open and raised, legs tucked, head up. Friendly. Wings go from folded to open in about 0.15 s with no pop (log). |
| 09 | [09-pteranodon-jump-air-front.jpg](09-pteranodon-jump-air-front.jpg) | Pteranodon, jump, in the air, front | PASS | 5 | Same moment from the front. |
| 10 | [10-pteranodon-phases-sheet-1.jpg](10-pteranodon-phases-sheet-1.jpg) | Pteranodon phases 1 to 6 | PASS | 4 | Folded rest, folded crouch, wings starting to open at push-off, spread in the air; the leap glide holds the wings flatter. |
| 11 | [11-pteranodon-phases-sheet-2.jpg](11-pteranodon-phases-sheet-2.jpg) | Pteranodon phases 4 to 8 (landing) | ODD | 3 | The landing fold is smooth in the sheet, but in play the first landing frame snapped the wings (see "The Fly wing pop"). |
| 12 | [12-pteranodon-reduce-motion-air.jpg](12-pteranodon-reduce-motion-air.jpg) | Pteranodon in the air, Reduce Motion ON | PASS | 4 | Wings stay folded and still, no pose. Log: wing angle constant 71.6 deg, every other part 0.0 deg through walk, jump and leap. |
| 13 | [13-mosasaurus-walk.jpg](13-mosasaurus-walk.jpg) | Mosasaurus (Water), walk | ODD | 4 | A chunky lizard walk on four flippers. Flippers dip up to 0.3 stud into the ground (feet -0.30 stud min, rest -0.06). |
| 14 | [14-mosasaurus-surge-live.jpg](14-mosasaurus-surge-live.jpg) | Mosasaurus, dash loop | ODD | 3 | A surge was running but this frame caught it near the start; the surge is hard to tell from a walk step. |
| 15 | [15-mosasaurus-surge-sheet-1.jpg](15-mosasaurus-surge-sheet-1.jpg) | Mosasaurus surge, jump p .2 / .5 / .8, leap p .35 | ODD | 3 | The surge reads weakly: flippers pull 33 deg, tail kick 22 deg, body 0.31 stud forward; a child will see the splash and the movement, hardly the pose. See BD-556. |
| 16 | [16-mosasaurus-surge-sheet-2.jpg](16-mosasaurus-surge-sheet-2.jpg) | Mosasaurus surge leap p .35 / .5 / .65, defeat | ODD | 3 | The leap snaps the head down slightly; defeat rolls the body, fine. Same weak read as 15. |
| 17 | [17-pteranodon-jump-air-after-fix.jpg](17-pteranodon-jump-air-after-fix.jpg) | Pteranodon in the air, build with the fix | PASS | 5 | Unchanged look in the air (the fix only touches the landing hand-over). |

## Numbers from the frame log (60 frames/s, real LowPolyAnimator)

| Run | Phases seen (state at the time) | Worst per-frame change | Feet vs ground |
|---|---|---|---|
| Compy walk | idle to walk, continuous | 5.9 deg (leg) | -0.05 .. +0.29 |
| Compy jump | crouch 0.33 to 0.41 s (already 2 to 5 studs up), push 0.41 to 0.53, tuck, land 0.30 s | 11.9 deg (leg) | -0.13 at touch-down |
| Compy leap (72 studs/s, 0.73 s flight) | same sequence | 14.1 deg (leg) | -0.05 to -0.45 |
| Compy drop from 9 studs, no jump | smooth ramp, no pop | 12.7 deg | -0.56 (hard landing) |
| Pteranodon walk | wings 70 to 75 deg (folded) | 1.5 deg (wing) | -0.03 .. +0.19 |
| Pteranodon jump | wings open 72 to 5 deg in 0.15 s, flap 5 to 29 deg, then landing | **17 deg (wing) at landing; up to 61 deg on a short hop** | -0.29 at touch-down |
| Mosasaurus walk | flippers 33 deg | 6.8 deg | -0.30 |
| Mosasaurus surge (jump, JumpPower 0) | one 0.40 s surge, flippers 33, tail 22, body +0.31 stud | 6.9 deg | stays on the ground |
| Reduce Motion ON, Compy, Pteranodon | walk, jump, leap | 0.0 deg for every part (Fly wings hold the fold, 71.6 deg constant) | n/a |

## Findings

1. **The Fly wing roll pop is real, and worse than reported.** The landing started from a fixed "wings open, flap 0" pose. After a normal jump the air flap (up to 0.35 rad, 20 deg) snapped to 0 in the landing frame (17 deg in one 16 ms frame, as reported). After a hop that lands before the wings opened (a few frames in the crouch or early push-off) the wings went from folded to open in ONE frame: 57 to 61 deg in 5 of 10 hops of my test (one more at 30). Caveat: in my setup the dino was snapped to the ground mid-jump (cause not found; probably a correction against the treadmill's position writes), which is what produced the short hops, so how often a child sees this (a tiny step, a bump, a stair) is unknown; the mechanism is real for any very short air time. Both are fixed in this PR: the animator hands the landing the flap angle and the wing-open amount the last phase ended on (`Pose.airFlap`, `Pose.wingOpen`, `ctx.flap`, `ctx.wing`). Same test on the fixed build, 20 hops: worst frame 3.4 to 8.2 deg.
2. **Jump and leap: the crouch and push-off play after take-off** (BD-555). The humanoid only reports Jumping once the dino has left the ground, so the crouch (legs fold +28 deg), push-off (legs extend to -26 deg) and tuck (+40 deg) all play in the first 0.4 s while it is already rising 2 to 8 studs: legs fold, unfold and fold again about 700 deg/s. Not scary and it reads as a quick scramble, but it is not the intended anticipation. Not small, not fixed here.
3. **Water surge reads weakly** and Mosasaurus flippers dip 0.3 stud into the ground while walking (BD-556). Hard landings sink the feet up to 0.5 stud for about 2 frames; that is the humanoid's own hip compression, it also happens with Reduce Motion on.
4. **Nothing looks broken or scary for children.** No clipping through the body, no snapping other than item 1, no gore in the defeat, Reduce Motion rests every pose. The recommendation is to keep the action poses ON in the playtest profile (fix 1 is in this PR; 2 and 3 are polish).

## Not covered (honest gaps)

* The real E key and Space press (keyboard tool did not reach the game); the leap and dash were scripted as described above. Fly and Water leaps were seen on the pose sheet only, not logged live. The Water dash velocity from the server (`ClassDash`) did not move the dino in my setup (horizontal speed stayed 0), so the surge was seen without the forward travel and its splash was not in a frame.
* Water with Reduce Motion ON (the offline verifier covers it), Armored class, Plush/Clay/Bricks defeat skins (no models exist), remote players and NPC predators, phone, a second client, frame time on a phone.
* The ledge walk-off of a Fly dino (state Freefall at once) was not reproduced; the nearest test (a 4 stud step) started the crouch first and opened the wings in 0.1 s without a pop.
