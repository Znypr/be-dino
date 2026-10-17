# BD-595 Fly hover cap: Studio measurement (2026-10-17)

**CURRENT BUILD BEHAVIOR** measurement of `main` `265879a4` (contains #422 glide and #424 hover cap). Build: `python tools/build.py --profile playtest`, one Studio window of my own, Play, memory-only profile, one player, island run. The render ran at 15 fps; every number below is sampled on `RunService.Heartbeat` (60/s).

Test aid, NOT in the repo: the built place file was text-patched so `Config.CollectionTestGrantEnabled = true` and `CollectionTestGrantSpeciesId = "pteranodon"` (the config table is frozen at run time). The Pteranodon was then granted by the `TestGrantSpecies` remote and equipped through the real `EquipSpecies` remote (`LastEquipStatus equipped`, `EquippedSpeciesId pteranodon`). Run started with `RequestStartRun` (`RunState Active`, `Location Island`). Pteranodon: `JumpPower 55`, `HipHeight 2`, root size 2 (standing root centre = 3.0 above the feet), gravity 250, rest feet offset 0.000.

**Feet height** = root Y - ground Y (ray down) - (HipHeight + root.Size.Y / 2), the same definition as `ClassMovement.feetHeight`.

Control (cap off, same character, same jump power): the client's local `EquippedSpeciesId` attribute was switched to a Ground species for the control jumps, so `ClassGlide.client.luau` skips the cap, then switched back. The server and `JumpPower` were untouched.

## Numbers

| # | Case | Expected (brief) | Measured | Verdict |
|---|---|---|---|---|
| 1 | Plain Fly jump apex (`Humanoid.Jump`, jump power 55) | about 6.05, unchanged | **6.44 to 6.48** (6 jumps); the real Space key gave 6.46 | **Not as expected.** See finding below. |
| 1c | Same jump, cap OFF (control) | n/a | **6.92** (4 of 4 identical) | the real, uncapped Fly jump |
| 2 | Boosted jump (`Admin_jumpPower` 90, class power 1.1 gives `JumpPower` 99, up speed 101.8) | held at about 6.5 | **6.45 to 6.48** (3 jumps) | PASS |
| 2c | Same boosted jump, cap OFF (control) | n/a | **22.24** (2 of 2 identical) | cap is doing the work: 22.2 down to 6.5 |
| 3 | Leap (E key, `requestLeap` path, jump power 55 again) | exempt, about 10 | **10.21** feet apex, 51 studs forward, `LastLeapStatus leaping` | PASS (a capped leap would be 6.5) |
| 4 | Glide, real Space key held | fall held at about 12 studs/s | plateau **-16.2** studs/s for 8 consecutive Heartbeats, apex 6.46 | PASS (12 cap + one 4.2 gravity step of the post-step sample, the same reading as the BD-593 re-walk's 16 to 17) |

The other fall samples of case 4 (-20.3 up to -32.8) are the free fall after the 1 s glide budget ends or after Space is released; they are not the plateau.

## Finding: a plain Fly jump is trimmed by about 0.45 stud

The brief expected a plain Fly jump to rise about 6.05 (v^2 / 2g with 55 and 250) and the cap (6.5) to sit just above it, so a plain jump would be untouched. In Studio the **uncapped** Fly jump rises **6.92**, because the Humanoid keeps pushing for a few frames after take-off (the offline simulation in `tools/verify_class_movement.py` gives 5.60 at 60 Hz, so it under-predicts the real jump by about 1.3 studs). So the cap, which holds the feet at 6.43 to 6.48, **does cut a plain Fly jump from 6.92 to 6.45** (-0.47 stud, about 7 percent). It is small, the Fly dino still jumps above the Ground dino (jump power 50, not measured here), and a boosted jump is now held, but "a plain jump is untouched" (FH1) is not literally true. The earlier real-key measurement (root peak 9.9 to 10.7 = feet 6.9 to 7.7) agrees with 6.92.

Options (LEAD decision, none applied): (a) keep 6.5 and fix the wording (a plain Fly jump is "about 6.5, trimmed from 6.9"); (b) raise `heightCap` to about 7.0 so a plain jump is untouched (one number; BiteVerticalLimit is 7 centre to centre, so a boosted jump held at 7.0 reaches the edge of it, 6.5 does not); (c) leave as is. I recommend (a): the 0.45 stud is not felt, it adds no number and keeps the bite margin.

## Picture

| Image | What |
|---|---|
| [01-boosted-jump-capped-side.jpg](01-boosted-jump-capped-side.jpg) | Side view of a boosted Fly jump (jump power 99, would reach 22 studs) frozen at its apex: the Pteranodon's feet sit on the green line at 6.5 studs; the white pole carries a red ruler, one tick per stud (long ticks at 0, 5 and 10). The dino was held by anchoring the local root at the apex for the picture only; the ruler and lines are local parts, removed after. Camera: a Scriptable client camera at (30, 8, 32) looking along -X (a second capture with `screen_capture` `camera_position` / `look_at_position` gave the same view from further away, not kept). |

The window was closed after the run (NOTOPMOST, minimised, only my process ended).
