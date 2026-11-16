# Dino rig follow-up (BD-1217, docs/242 benchmark gap 2), 2026-11-16

Flag `Config.DinoRigClipsEnabled`: off in the default build, ON in the playtest profile. Built playtest place
(`python tools/build.py --profile playtest`), opened in a separate test Studio (GameId/PlaceId 0), Play mode, local client.
Nothing in the owner's Place1 was touched.

## 1. Feasibility: a real skinned rig needs the owner

| Route | Result |
|---|---|
| Rebuild per-species meshes in Blender | The V3 meshes are not in the repo; only the published Roblox Models (`src/shared/LowPolyDinoAssets.luau`) and the owner's Place1 have them. Their vertices can be read in Studio (`EditableMesh`, docs/169 s6), so a Blender copy could be rebuilt. |
| Upload a skinned FBX through Open Cloud | **Fails today.** docs/169 s6 (cockatoo run): the API upload makes Motor6Ds in the wrong places, no `Bone` and no animation; only a parts model arrives correctly. A skinned MeshPart (bones + weights) is only made by the Studio 3D Importer, by hand, signed in as the owner. |
| Studio MCP `auto_setup_avatar` / `generate_animation` | R15 human avatars and R15 animations only. A quadruped, a long-neck or a flyer is not an R15 body; the result would also have to be published as a new asset by the owner. |

So a fully skinned dino needs, **from the owner, per species**: (a) the V3 model exported from Place1 as FBX (or OK to rebuild it
from the published mesh in Blender), (b) one Studio 3D Importer import of the rigged FBX (Rig: Custom) and a publish of the result
as a Model, and (c) either Animation Editor uploads of the clips (animations cannot be uploaded through Open Cloud) or OK to drive
the bones from code (`Bone.Transform`, the same Luau-data route as today). 28 species = 28 imports.

## 2. Built instead: the best non-skinned upgrade

- **Authored loops** for idle (4 s), walk and run (one stride each): `tools/blender/dino_clips.py` -> `src/shared/LowPolyClips.luau`
  (`Clips.Gait`, wrapped monotone Hermite, seamless) and `assets/blender/anim/DinoClips.blend` (`loop_idle`, `loop_walk`, `loop_run`).
  `src/shared/LowPolyGait.luau` plays them instead of the sine poses for head, neck, tail, arms and legs. The walk / run clock is the
  animator's step phase, which advances with the real planar speed; speed blends idle -> walk -> run. Right legs run half a stride
  later, diagonal pairs of a quadruped move together, Armored steps are 0.8 as long. Water dinos, wings and flippers keep the sine poses.
- **Jump and land clips** start on the humanoid state change (take-off, touch-down) on top of the procedural tuck and squash, and each
  plays to its own end (a landing during the jump clip overlaps the two; cutting one off popped 12 degrees in a frame).
- **Follow-through**: underdamped springs. Turning swings the tail out of the turn and the head into it; rising drags the tail tip
  down, falling lifts it; a landing kicks the tail down and the head into a nod that springs back past rest and settles.
- **Default R15 `Animate` off**: the local character's `Animate` is disabled and its tracks stopped (and any track it still starts)
  while the dino is shown. Movement is the Humanoid's, not Animate's: walking, running and jumping all worked in Studio.
- **Reduce Motion**: every weld at exact rest, springs reset, no hop clips (verify_motion_poses 1217.drive_reduce).

## 3. Studio (real animator, real V3 models, six species)

Six species were cloned on a plain platform with `LowPoly.clone` and driven by the unmodified animator (its NPC path, 20 Hz):
compy (biped, arms), triceratops (quadruped), brachiosaurus (long neck), pteranodon (flyer, Fly class), ankylosaurus (Armored),
elasmosaurus (long neck with flippers).

| Picture | What it shows |
|---|---|
| `01-walk-six-species-a.jpg`, `02-walk-six-species-b.jpg` | walk at 10 studs/s: legs apart, alternate left / right, tails swayed |
| `03-run-six-species.jpg` | run at 24 studs/s: head low, arms pumped, tail up and wider strides |
| `04-turn-follow-through.jpg` | turning left at 2.5 rad/s: tails swing out of the turn |

Weld angles read in Studio (degrees, pitch range; tail yaw range):

| Species | walk legs | run legs | walk tail yaw | run tail yaw | idle tail yaw |
|---|---|---|---|---|---|
| compy | -24..24 (arms -12..12) | -28..28 (arms -26..8) | -11..11 | -14..14 | -7..6 |
| triceratops | -24..24 | -28..28 | -11..11 | -14..14 | -7..7 |
| brachiosaurus | -24..24 | -28..28 | -11..11 | -14..14 | -7..7 |
| pteranodon | -24..24 (wings folded) | -28..28 | -11..11 | -14..14 | -7..6 |
| ankylosaurus (Armored) | -19..19 | -22..22 | -11..11 | -14..14 | -7..6 |
| elasmosaurus (flippers keep the sine row) | flippers -8..7 | flippers -14..14 | -11..11 | -14..14 | -6..7 |

Turning at 2.5 rad/s: tail yaw +10 (follow-through 8.6 + sway), head yaw +5 on every species.

Player's own compy, a real jump (head / tail pitch every 0.05 s; tail > 0 = tip down): tail 1, 5, 14, 24, 25 at the top, 19, 13 while
falling, 2 at touch-down; then head -1, -5, -4, 0, +3 (the nod springs back) and settles. `Animate` disabled = true,
R15 tracks playing = 0.

Blender proxy contact sheets and numbers (`tools/animation_strip.py`): `blender-loop_walk-*`, `blender-loop_run-*`, `blender-land-*`:
loop seams ok (1.12x and 0.83x), easing ok, joint speed ok, nothing under the ground.

## 4. Checks

- `tools/verify_motion_poses.py`: the whole animator suite now runs twice (flag off as shipped, flag on) plus 7 new `1217.*` checks
  (loops by speed, hop clips by state, follow-through, Animate, Reduce Motion, no weld over 8 degrees per frame in idle -> walk ->
  run -> turn -> jump -> land -> stop for Ground, Armored and Fly). `--selftest`: 46 deliberate breaks, all caught.
- `tools/verify_lowpoly_clips.py`: the loops are seamless (value and slope), bounded, never turn body / wings / flippers; the pure
  LowPolyGait blends, phases, Armored steps, run posture, Reduce Motion, springs and junk inputs; the flag ships false.

## Not verified

Phone; a mid-air Studio picture (MCP capture timing; the jump is shown by the measured series above); remote players' jumps on a
live server (hop clips run for the local player only; remote dinos get the loops and the follow-through); the feel, which the owner judges.
