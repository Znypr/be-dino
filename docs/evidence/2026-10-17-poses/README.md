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

## Follow-up: BD-555 jump fix (PR claude/bd555-jump-calm)

Same method as above, one Studio window per build (main before, the fix after), Play, 60 fps, a `RenderStepped` log of the rotation change of every part weld, `ChangeState(Jumping)` plus `Humanoid.Jump` (a bare `Jump = true` from a script did not lift the dino). Compy, 1.5 s per jump, includes the landing.

| Case | Before (main) worst frame | After worst frame | Leg direction changes before / after |
|---|---|---|---|
| Jump standing | 13.8 deg (leg) | 5.1 deg (arm) | 3 / 0 |
| Jump moving (Move(), no visible extra speed) | 12.6 deg (leg) | 5.2 deg (arm) | 3 / 0 |
| Jump with the leap flag | 12.9 deg (leg) | 6.4 deg (arm) | 3 / 0 |

| # | Image | Result | Look | Notes |
|---|---|---|---|---|
| 18 | [18-compy-jump-air-after-bd555.jpg](18-compy-jump-air-after-bd555.jpg) | PASS | 5 | Compy 0.3 s into a jump (root anchored in the air for the shot): legs and arms tucked, tail up, head up, no crouch pose. |

## Follow-up: BD-556 Water surge swim wave, flipper stroke, hip-dip cover (PR claude/bd566-water-surge)

**CURRENT BUILD BEHAVIOR after this PR (offline verified; Studio look PENDING until the lead frees Studio).**

| Part | Before | After |
|---|---|---|
| Tail | one kick, 20 degrees (jump) / 30 (leap) | wave, yaw 26 degrees, lags the head by 2.3 rad |
| Body | no yaw | wave, yaw 5 degrees, lag 1.1 rad |
| Head / neck | pitch lunge only | lunge plus wave, yaw 14 degrees, lag 0 / 0.4 rad |
| Flippers | one pull, 33 degrees, held | rowing stroke (pitch +-19 degrees, roll flare), back pair 1.0 rad after the front pair |
| Cycles | 1 | 1 undulation (jump, 0.40 s) or 1.4 (leap, 0.55 s) |

Offline numbers (`tools/verify_motion_poses.py`, real `LowPolyPose` and real `LowPolyAnimator`): worst turn of any part 7.7 degrees per 60 Hz frame in the pose maths, 7.2 through the animator (jump), 6.5 (leap); Reduce Motion: every weld identity through a jump and a leap surge. New checks 556.surge_wave (phase lag fitted from the real samples grows head, neck, body, tail), 556.surge_amp, 556.surge_smooth, 556.hipdip, 556.drive_surge, 556.drive_hipdip; 14 new `--selftest` breaks, all caught.

Hip dip: `Pose.hipDip` lifts every part by the compression for 0.3 s after touch-down (local dino only; a ray 4 times a second when settled, one per frame during the window, none in flight or under Reduce Motion). Not checked offline: the real compression numbers and that the lift looks right on a hard landing.

### Studio frame log (2026-10-17, 15:02 to 15:17, one window of my own, Play, memory-only profile)

Build: `python tools/build.py --profile playtest` of main with #409 and #410 (the dash hold). Set-up honesty: `EquippedSpeciesId` was forced to `mosasaurus` from a server script (every 0.1 s) and `Dinosaur.refreshForPlayer` re-rendered, so the visual is the REAL Mosasaurus (`LPClass` Water, 7 posed parts) and the class logic is Water (WalkSpeed 18.7, JumpPower 0). The run was started with `RequestStartRun`. The Studio keyboard tool does not reach the game, so the dash was driven as the client script does on Space: `Humanoid.Jump = true` for 0.1 s plus the `ClassDash` remote. A Heartbeat logger (60 frames/s) recorded the rotation of every part weld (Euler XYZ of the inverse of `Weld.C1`), the root position and velocity.

**(No image at the time of this log; the pictures were taken later, see "Pictures taken" at the end.) The Studio window never rendered** (RenderStepped fired 0 times, `ViewportSize` 1 x 1 and every `screen_capture` timed out, in Edit and in Play, in two fresh windows, on screen 3 and briefly elsewhere). It looked like a frozen render surface, not a code problem; the logs below come from Heartbeat, which ran at 60 Hz. The surge IMAGE was owed then; it exists now (images 19 to 23 below).

| Measurement | Result |
|---|---|
| Dash displacement (horizontal, flat ground, 2 trials, #410 hold) | 14.6 and 15.3 studs (nominal 16.8), peak planar speed 36.2 studs/s |
| Worst turn of any weld in one frame, whole dash | 6.9 degrees (tail, t = 0.72 s, after the surge ends: the idle/walk sway); the surge itself stays under 8 |
| Peak angles, real Mosasaurus | tail yaw 24, head yaw 11, body yaw 5 degrees; front flippers pitch 15, back flippers pitch 19, roll 9 to 15 |

Travelling wave, seconds after the dash request (degrees, yaw for head/body/tail, pitch for the front-left flipper):

| t | head | body | tail | flipper FL |
|---|---:|---:|---:|---:|
| 0.05 | 0.3 | -0.4 | -2.9 | 0.8 |
| 0.10 | 8.3 | 0.6 | -13.1 | 11.3 |
| 0.15 | **10.8** | 3.7 | -4.9 | 14.7 |
| 0.20 | 3.4 | **5.0** | 14.4 | 4.7 |
| 0.25 | -6.9 | 2.7 | **24.4** | -9.4 |
| 0.30 | **-10.9** | -0.9 | 17.0 | -14.9 |
| 0.35 | -3.8 | -1.3 | 3.9 | -3.5 |
| 0.40 | -0.1 | 0.0 | 8.6 | 6.0 |

The positive peak runs head (0.15 s) then body (0.20 s) then tail (0.25 s): a wave travelling head to tail, as designed, and the flipper rows both ways. The first Water jump (before the animator was fed `Humanoid.Jump`) showed only idle sway: with the remote alone the surge pose does not play, the animator keys on the jump input / state as the real Space press does.

### Hip dip on a hard landing (16 stud drop, rest gap root-to-floor 3.000)

The real hip compression is **0.51 to 0.53 stud** for one frame (state Landed). Measured with the lift in (animator one frame behind, see below):

| t | state | root gap | lowest visual corner over floor | body weld lift (Y) |
|---|---|---:|---:|---:|
| 0.282 | Freefall | 3.530 | 0.487 | -0.042 |
| 0.299 | Landed | 2.489 | **-0.553** | -0.042 |
| 0.316 | Landed | 2.569 | 0.006 | 0.438 |
| 0.333 | Running | 2.741 | 0.093 | 0.358 |
| 0.349 | Running | 2.853 | 0.029 | 0.185 |
| 0.383 | Running | 2.956 | -0.049 | 0.006 |

So the lift (0.44 stud at its peak) holds the feet at or just above the floor from the second landing frame on (without it the lowest corner would be about 0.4 stud under the floor at t = 0.316 and 0.2 at 0.333). **One frame is not covered:** the touch-down frame itself (-0.55 for 16 ms), because the animator runs in Heartbeat and only sees the compressed root position that frame; the weld change shows from the next frame. A fix would be to predict the dip from the fall speed; not done, it is one frame. The first Studio run showed the touch-down frame can still read as airborne for the animator, so rays are now cast while FALLING too (none while rising); `556.drive_hipdip` has a case for it (a mutant proves it).

## Pictures taken (BD-556, 2026-10-17 20:50 to 21:05, Studio rendering about 11 fps)

Build: `origin/main` (1a690653, which has #409, #410, #566 and the BD-555 jump calm), profile `playtest`, one Studio window of my own in Play, memory-only
profile. Set-up honesty: `EquippedSpeciesId` was forced to `mosasaurus` from a server script every 0.1 s and a toggle of `EquippedBig` made the server re-render the
visual, so this is the REAL Mosasaurus (`LPClass` Water, 4 flippers, WalkSpeed 18.7, JumpPower 0). The run was started with `RequestStartRun`. Weather was stopped
(`AdminAction stopWeather`) for the shots.

**How a 0.4 s pose was photographed (the phase cannot be hit by chance at 11 fps).** The dino was pinned in place (a Heartbeat that puts the root back at (0, 5.05, 30) every
frame, so the dash velocity written by the client does nothing visible) and `Humanoid.Jump` was pulsed every 0.55 s, which is what the animator reads as the jump
input (the real `LowPolyAnimator` and real `LowPolyPose` ran). A watcher read the real tail / flipper welds each frame and, the moment a threshold was crossed,
set the `LowPolyAnimator` script `Disabled = true`, which freezes every weld at that frame; the shot was taken, and the script was re-enabled. So each "frozen" picture is
a real frame of the real surge, held still. Nothing was posed by hand, and no pose maths was run outside the game.

| # | Image | Moment | Verdict | Notes |
|---|---|---|---|---|
| 19 | [19-mosasaurus-surge-top-wave-frozen.jpg](19-mosasaurus-surge-top-wave-frozen.jpg) | top view, frozen when tail yaw crossed 20 degrees (measured 23.3; head -3.7, body +3.8) | PASS (the wave reads) | Seen from above the surge is a clear head-to-tail S-curve: head swung right, body angled, tail swept left. This is the picture the old straight-body surge could not give. |
| 20 | [20-mosasaurus-surge-side-flippers-frozen.jpg](20-mosasaurus-surge-side-flippers-frozen.jpg) | side view (camera 13 studs to the right), frozen at flipper pitch 18.4 degrees and tail yaw 14.2 | PASS for the flippers, weak for the wave | The front flipper is swept back and the rear flipper forward (the rowing stroke), tail raised a little, head tilted. From the side the yaw wave is foreshortened: a child sees the flipper stroke and the splash, not the S-curve; use 19 and 21 for the wave. |
| 21 | [21-mosasaurus-surge-top-wave-2-frozen.jpg](21-mosasaurus-surge-top-wave-2-frozen.jpg) | top view, same freeze as 20 | PASS | Second frame of the wave, smaller bend (tail 14 degrees): head right, tail left-down. |
| 22 | [22-mosasaurus-rest-top-control.jpg](22-mosasaurus-rest-top-control.jpg) | CONTROL, top view, no surge playing | control | The root was anchored; the animator did not see a jump (humanoid state stayed Running), so the body is straight. Compare with 19 and 21. |
| 23 | [23-mosasaurus-hard-landing-frame.jpg](23-mosasaurus-hard-landing-frame.jpg) | side view, low camera, 2 frames after touch-down from a 16.5 stud drop (root frozen at y 4.78, rest 5.05, humanoid state Landed then Running) | PASS | The four flipper tips and the feet sit ON the grass, not in it, with the hip-dip lift in. The touch-down frame itself (not covered, see above) cannot be photographed this way. |

Not obtained or not claimed:
* **The real Space key did not move the dino.** `user_keyboard_input` Space (key press and a 250 ms hold) produced no dash and no displacement (0.00 studs) in this window,
  whereas `Humanoid.Jump = true` did (the `JumpRequest` path fires `ClassDash`). The Studio window is never given keyboard focus on purpose (no foreground steal), which is the likely reason.
  So the live Space path is still unchecked by a real keypress; the animator and dash were driven through `Humanoid.Jump`.
* **A frame of the moving dash.** Unpinned, a dash travels about 16 studs in 0.35 s in the direction the camera faces (the capture tool re-points the camera, so a fixed shot lost the dino).
  A moving dash frame was not taken; the numbers above and in the BD-572 evidence stand.
* **The surge on a phone-size or touch screen**, and Reduce Motion in a picture (the weld identity is asserted offline).
* The touch-down frame of the hard landing (16 ms, -0.55 stud) is still unlit by the lift, as already noted.
* Observed while flying the camera: a green and a purple wedge appeared in two screen corners in the low side view (23), probably a scene object close to the camera (not checked), not the dino.

