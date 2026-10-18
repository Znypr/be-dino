# 171 Animation strip and model checker (BD-641, BD-643)

Written 2026-10-18 (owner request, tools 3 and 4 of 8). Two offline tools for things the lead cannot see: how an animation moves, and whether a 3D model is fit to upload. Both run Blender as a SEPARATE headless process (never the live Blender MCP session, which another agent may be using), and both print plain words. Nothing in `src/`, Studio or the game was changed. Examples and real results: [evidence folder](evidence/2026-10-18-animation-and-model-checks/README.md). Label: **CURRENT BUILD** tooling only; it judges numbers, never taste.

## Tool A: `tools/animation_strip.py` (BD-641)

Turns a clip into a picture and a list of numbers.

```
python tools/animation_strip.py assets/blender/creatures/Cockatoo_HQ.blend --action Walk --out build/anim
python tools/animation_strip.py assets/blender/creatures/Cockatoo_HQ.blend --action Jump --one-shot --out build/anim
python tools/animation_strip.py creature.fbx --action "Rig|Rig|Walk" --count 12 --size 192
python tools/animation_strip.py clip.mp4          # or a .gif, or a folder of numbered images (add --fps 24)
python tools/animation_strip.py walk.blend --no-render --strict    # fast stick-figure sheet; exit 1 if any row says check
```

- **Input:** a `.blend`, `.fbx`, `.obj` or `.glb` with an action (the action playing, or the one with most curves, or `--action NAME`), or a video, GIF or image folder.
- **Picture:** `<name>_strip.png`, N evenly spaced key frames (default 8, 4 per row) with frame numbers. For Blender files they are side renders (Workbench) with a ground line and ticks every half body height, so travel and foot sliding show. The picture faces the way the body travels; a body that stays in place faces right when it faces -Y like the creatures (`--view x|-x|y|-y` forces it). For video, ffmpeg cuts the frames with the `tile` filter. With `--no-render`, or a rig with no mesh, a stick figure is drawn from the bones.
- **Report:** `<name>_report.txt` and the same on screen: a verdict table (ok / check / n/a), tables of joint angles and feet, notes, and the limit with its reason beside every row.

### What it measures (Blender files)

| Row | In plain words |
|---|---|
| frame rate, duration | frames per second and seconds per loop. |
| loop continuity | the step from the last frame to the first, against what the frames either side would give. About 1.0 is seamless. A tiny step means the last frame repeats the first (the loop plays one pose twice); a big one is a pop. Also names a joint that jumps at the seam. |
| joint angle range, joint speed | how far each bone turns from rest and how fast (degrees per second), biggest movers listed. Flags flipped joints and one-frame pops. |
| jerkiness | one frame that accelerates far more than the bone does on average. Names the bone and frame. |
| foot sliding | walk cycles only. A foot counts as planted while it is near the lowest foot point. For a body that travels, the planted foot should not move in the world (share of body speed). For an in-place cycle, the planted foot should go back at one steady speed. Also prints the **travel speed the cycle matches** (units and body heights per second), useful for setting the game walk speed. Skipped (n/a) for standing, jumping or flying clips. |
| ground penetration, floating | lowest point of the meshes (or bones) against the standing ground, as a share of body height. |
| left/right foot timing, swing size | the left foot should be in step or exactly half a cycle apart from the right, planted for the same share, and paired bones should travel about the same distance. |
| easing | peak speed over average speed inside each move: 1.0 is linear and mechanical, 1.57 a sine, over 2.2 snappy. Also counts the key interpolation types (a file with stepped keys gets a check). |

From a video, GIF or image folder only pixel rows run: frame rate, duration, loop seam, pops (one frame changing far more than usual) and held frames. Everything about joints says n/a.

### Limits

All limits are in ONE table, `THRESHOLDS` at the top of `tools/animation_strip.py`, each with its reason. They are judgement calls, not laws. **check means "look at it", not "it is wrong".** For a one-shot clip (jump, attack) use `--one-shot` so the loop row is not judged.

What it cannot judge: feel, weight, appeal, whether it looks like the animal, timing taste. It reads poses at whole frames; sub-frame wobble is not seen. Pixel rows can be fooled (a small object saturates the difference). The foot rules need bones with "foot", "toe", "paw", "ankle", "heel", "claw" or "hoof" in the name, and left/right bones named `.L/.R`, `_l/_r`, `Left/Right`; otherwise they say n/a. FBX files can hold a different rest pose than the .blend, so angles are "away from the imported rest pose". Measured, not watched.

## Tool B: `tools/check_model_for_roblox.py` (BD-643)

A pre-upload check for `.fbx`, `.obj`, `.blend` or `.glb`. One Blender start for any number of files.

```
python tools/check_model_for_roblox.py assets/blender/creatures/fbx/creature_pteranodon.fbx
python tools/check_model_for_roblox.py a.fbx b.blend --out report.txt
python tools/check_model_for_roblox.py model.blend --strict      # warnings also give exit code 1
```

Exit code: **0** no FAIL, **1** at least one FAIL (or a WARN with `--strict`), **2** Blender missing or the file unreadable. It prints a PASS / WARN / FAIL list, then a table of the parts.

| Check | FAIL when | WARN when |
|---|---|---|
| triangles per part | over 21,844 (Roblox's MeshPart limit) | over 80 percent of it |
| size in studs | a side over 2,048 studs | longest side under 2 percent or over 100 times a Compy (unit mistake); scene unit scale not 1. The report always shows width, height, length and the ratio to the Compy. |
| pivot (origin) | - | origin outside the part; a single-part model whose origin is not at the bottom centre (the world kit convention, [56](56-bd049-050-world-art.md)) |
| scale and rotation applied | - | object scale not 1 or object turned (not applied); negative scale |
| face direction | a closed piece is inside out (negative volume), counted per piece | neighbouring faces disagree on the outside |
| loose and doubled vertices, zero-area faces, n-gons | - | any; doubled over 1 percent of vertices |
| open edges | - | never (reported for information) |
| materials and textures | a texture image missing on disk and not packed | no material, an empty slot |
| UV map, overlap, outside 0..1 | - | none (and no vertex colours); over 5 percent overlap; over 1 percent outside |
| vertex colours | - | never (reported: present or not) |
| bone influences, armature, animation | - | more than 4 bones on a vertex; bones that no mesh follows. Reports armatures, bones and actions. |
| file size | over 20 MB | over 10 MB |
| part names | empty, over 100 characters, duplicate, or Blender's `.001` rename | not usable as `part.Name` (spaces, dots, leading digit); names differing only by capitals |

**Compy size** used for the comparison: 3.49 wide, 6.60 high, 7.69 long studs, read at run time from `src/shared/ScaleLadder.luau` (`species.compy`, measured in Studio at spawn). 1 Blender unit = 1 stud, Z up in Blender = Y up in Roblox, creatures face -Y.

Limits are in the `LIMITS` table of the script with a source: "Roblox" (21,844 triangles, 2,048 studs, 4 bone influences, 100 characters) or "project" (everything else, including the file-size guard, which is a conservative guess: check create.roblox.com for the current number).

What it cannot judge: how the model looks, whether the pivot is where an animator wants it (joint pivots on a rigid-part rig are correct and show as "other"), how it looks lit in Studio, whether Roblox imports it without complaint (the upload is the real test). Inside-out is judged by the volume of each closed piece; thin open shells (leaves, wings) cannot be judged that way and only show as "mixed". Doubled vertices on an FBX are counted at the file's position level.

## What they found on real files (2026-10-18; numbers only, nothing opened in Studio)

- **Cockatoo (BD-621, real walk).** Walk: the last frame repeats the first; planted feet slide (the cycle moves them at about 1.2 studs per second, varying 57 percent, which is 0.16 body heights per second, far slower than the game walk speed); the mesh dips 2.2 percent below the ground at frame 11. Left/right timing and easing are fine. Jump: the mesh dips 9.9 percent below the ground at frame 8. Model check: no FAIL, 17,668 triangles in 10 parts, 7.0 studs tall.
- **Legacy creature FBX** (`assets/blender/creatures/fbx/creature_*.fbx`): 16 of 17 FAIL on inside-out closed pieces (9 to 18 pieces per file); the pivot sits in the middle of the model. These are not the shipped low-poly dinos, and nobody has shown they look wrong in Studio.
- **World FBX folders:** `fbx` 41 of 41 clean; `fbx_v2` 4 clean, 44 warnings, 6 failures; `fbx_v3` 7 clean, 22 warnings, 3 failures (inside-out pieces on the mush food, two pines and three cave rocks). The owner approved the food in Studio, so a FAIL means "look at it in Studio", not proof of a fault.
- **No other animation exists in the repo.** Apart from the cockatoo, no `.blend` or `.fbx` holds a character action; dino motion is code ([74](74-dino-motion.md)). The FX `.blend` files hold flipbook actions that animate materials or particle objects; the tool says so or prints numbers that mean nothing for them.

## Tests

`tests/test_animation_and_model_tools.py`. Pure-number tests (names, easing, pixel rules, every model rule on made-up numbers) need nothing. The Blender tests build their own fixtures with `tools/blender/make_test_walker.py` (a box-limbed walker, clean plus one copy per defect: loop pop, repeated frame, jerk, floor dip, sliding feet, uneven legs) and `tools/blender/make_test_models.py` (15 small meshes: good, inside out, unapplied scale, n-gon, loose, doubled, no material, empty slot, UV overlap, no UV, bad names, too heavy, too big, centre pivot, rigged), and check that each defect turns exactly its own row. They are skipped with a clear message when Blender, or ffmpeg for the video tests, is not found (CI on Linux skips them). They take about a minute here.

## Not done

Nothing was uploaded, tried in Studio or heard or watched. The limits are first guesses: tune them when the owner finds a clip the tool calls fine that looks wrong, or the other way round.
