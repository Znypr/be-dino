# Animation strip and model check: example outputs (2026-10-18)

Made by `tools/animation_strip.py` (BD-641) and `tools/check_model_for_roblox.py` (BD-643), described in [docs/171](../../171-animation-strip-and-model-checker.md). Everything here is MEASURED, not watched or played: nobody looked at these clips moving, and nothing was tried in Studio. Re-make all of it with the script `tools/blender/make_test_walker.py` plus the commands in docs/171. Total size about 2 MB.

## animation/ (key-frame strips and plain-word reports)

| Folder or file | What it is | What the numbers said |
|---|---|---|
| `walk_ok_*` | a tiny box-legged test walker, 24-frame walk cycle, made clean on purpose | no "check" anywhere. Implied travel speed 1.2 units per second. |
| `walk_loop_*` | same walker, last frame shifted 15% of a cycle | **loop continuity: check, a pop at the loop point** |
| `walk_dup_*` | same walker, last frame repeats the first | **loop continuity: check, last frame repeats the first** |
| `walk_jerk_*` | one frame where the left foot flips up for a single frame | **jerkiness: check, frame 9** |
| `walk_sink_*` | both feet dip below the floor for three frames | **ground penetration: check, 6.7 percent of body height** |
| `walk_slide_*` | body moves at 60 percent of the foot speed | **foot sliding: check, feet move at 66 percent of body speed** |
| `walk_phase_*` | right leg 0.3 of a cycle behind instead of 0.5 | **left/right foot timing: check** |
| `cockatoo_Walk/`, `cockatoo_Idle/`, `cockatoo_Jump/` | the real BD-621 cockatoo test model (`assets/blender/creatures/Cockatoo_HQ.blend`), one run per action | see below |
| `cockatoo_Walk_from_fbx/` | the same Walk, read from `Cockatoo_HQ_rigged_anim.fbx` | same verdicts as the .blend, so the FBX route works |
| `real_files/` | files that are NOT character animation: a creature rig with no action, an FX file whose action animates smoke materials, an FX flipbook file | the tool says "no action" or "no bone or object motion" for the first two. The flipbook file (`fx_motifs_v1`) gets numbers that mean nothing (they are particle flipbooks, not a body): shown only so nobody is surprised. |

Cockatoo (real file, 24 fps, side view; picture `animation/cockatoo_Walk/Cockatoo_HQ_strip.png`, also `docs/evidence/review-2026-10-17/35-animation-strip-cockatoo-walk.png`):

- **Walk** (1.25 s loop): last frame repeats the first, so a loop plays that pose twice (a small hitch; cut the last frame or the first). Planted feet slide: the cycle moves the feet back at about 1.2 studs per second, and that speed varies by 57 percent during the stance. 1.2 studs per second is 0.16 body heights per second, much slower than the game's walk speed, so at game speed the feet would skate. The mesh dips 2.2 percent of body height below the ground at frame 11. Left and right feet are exactly half a cycle apart and swing the same size (ok). Easing is soft (ok).
- **Idle**: same repeated last frame. The feet hardly move, so the walk rules are skipped (n/a).
- **Jump** (run with `--one-shot`): loop not judged. The mesh dips 9.9 percent of body height below the ground at frame 8 (the crouch). Walk rules skipped (feet are off the ground most of the clip).
- Not judged: whether the walk looks like a cockatoo, whether the hop feels good, the timing of the crest. A person looks at the strip.

## video/

`bar_ok` and `bar_pop`: a block sliding back and forth, encoded to mp4 with ffmpeg; `bar_pop` has the last frame replaced. The video route only measures pixels: loop seam, pops, held frames, frame rate and length. The pop clip gives "POP at the loop point: 3.4x" and "pops: 1 sudden change at frame 23". Everything that needs joints says n/a.

## models/ (pre-upload checks)

| File | What it checked | Result |
|---|---|---|
| `creatures_all_17_report.txt` | the 17 legacy `assets/blender/creatures/fbx/creature_*.fbx` | 16 FAIL, 1 WARN (the egg). The failure is the same in all 16: several closed pieces (about 9 to 18 per file) are wound inside out (their signed volume is negative). Every file also warns: pivot in the middle of the model, not at the feet, and no material. Triangles are fine (about 900 to 2,000 per file, limit 21,844). **Not proven in Studio**: these are not the shipped low-poly dinos, and the owner has not said they look wrong. |
| `real_WorldKitV3_*`, `real_WorldKitV2_Food`, `real_shock-dome` | the world kit .blend files and one FX FBX | warnings only for the V3 kit (n-gons, doubled vertices, a few mixed face directions); the V2 food .blend has 1 FAIL (inside-out closed pieces in the mush models). The shock dome passes except "no material". |
| `world_fbx_folders_summary.txt` | every FBX in `assets/blender/world/fbx`, `fbx_v2`, `fbx_v3` (127 files, one line each) | `fbx`: 41 of 41 clean. `fbx_v2`: 4 clean, 44 warnings, 6 failures (the four `food_mush_*` and two `world_tree_pine_*`: inside-out pieces). `fbx_v3`: 7 clean, 22 warnings, 3 failures (the three `cave_rockform_*`, one inside-out piece each, plus n-gons). Most warnings: the pivot is not at the bottom centre, and n-gons the exporter did not cut. The owner called the food fine in Studio, so a FAIL here means "look at it in Studio", not "it is broken". |
| `real_Cockatoo_HQ_report.txt` | the cockatoo .blend and its two FBX | all three: no FAIL. 17,668 triangles in 10 parts (biggest 5,688, limit 21,844 per part), 7.0 studs tall against the Compy's 6.60, names fine, colour from vertex colours (no UV map needed). Warnings: vertices doubled in place on the feather parts, and (FBX only) turns on the parts that come from the importer's axis change and the pose. |
| `fixtures_report.txt` | six small test meshes: good, flipped, ngon, heavy, names, scaled | PASS, FAIL, WARN, FAIL, FAIL, WARN: each defect is caught by its own line. |

Compy size used for the comparison: 3.49 wide, 6.60 high, 7.69 long studs, read from `src/shared/ScaleLadder.luau` (`species.compy`, measured in Studio at spawn). 1 Blender unit = 1 stud (docs/56).

## Honest limits

- Tools measure numbers. They cannot say if a walk feels good, a model is pretty, or a pivot is where the animator wants it.
- The limits in both tools are judgement calls kept in one table each (`THRESHOLDS`, `LIMITS`) with a reason beside every line. Only the 21,844 triangles, 2,048 studs, 4 bone influences and 100 character name limits are Roblox's own numbers; the file size guard is a conservative guess.
- No Studio, no phone, no upload was done.
