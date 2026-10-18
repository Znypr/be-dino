# Cockatoo HQ Blender test model (BD-621), 2026-10-18

Owner request 2026-10-18: use the cockatoo pictures to build a HIGH QUALITY Blender model, test how close we can get to the reference, with animations (idle, walk, jump), then try to get it into Roblox / Place 1. **Status: TEST MODEL, not bound anywhere.** No game code, config, flag or save data was changed. Not final art: [AGENTS.md](../../../AGENTS.md) says models must come from a real generation or modelling pipeline, and this one is built from a Blender script (see "Honest limits" below). The owner decides whether it is acceptable.

## What exists

| What | Where |
|---|---|
| Blender file (10 separate parts, armature, 3 actions) | [assets/blender/creatures/Cockatoo_HQ.blend](../../../assets/blender/creatures/Cockatoo_HQ.blend) (0.5 MB) |
| FBX, parts + armature + actions Idle / Walk / Jump | [assets/blender/creatures/fbx/Cockatoo_HQ_rigged_anim.fbx](../../../assets/blender/creatures/fbx/Cockatoo_HQ_rigged_anim.fbx) (0.9 MB) |
| FBX, parts only (static, parts keep their joint pivots) | [assets/blender/creatures/fbx/Cockatoo_HQ_static.fbx](../../../assets/blender/creatures/fbx/Cockatoo_HQ_static.fbx) (0.6 MB) |
| Luau animation module (data + functions, same keyframes as the Blender actions) | [assets/blender/creatures/CockatooAnimations.luau](../../../assets/blender/creatures/CockatooAnimations.luau) |
| Build scripts (re-runs the whole model) | `tools/blender/cockatoo_lib.py`, `build_cockatoo_hq.py`, `cockatoo_anim.py`, `cockatoo_rig.py`, `cockatoo_export.py` |
| Luau generator and plain-Luau test | `tools/blender/gen_cockatoo_luau.py`, `test_cockatoo_animations.luau`, `run_cockatoo_animation_test.py` |
| Pictures | this folder, numbered 00 to 05 (also copied to `docs/evidence/review-2026-10-17/` as 107 to 110) |

References used: the turnaround sheet [reference/cockatoo-turnaround-chatgpt-v1.png](../../reference/cockatoo-turnaround-chatgpt-v1.png) (front, side facing right, back; PRIMARY for shape; prompt in the `.txt` next to it), the owner draft [reference/cockatoo-owner-draft.webp](../../reference/cockatoo-owner-draft.webp) (style) and the photo [reference/cockatoo-owner-ref.png](../../reference/cockatoo-owner-ref.png).

## Numbers

Triangles: **17,668 in total**, 10 meshes (each far below Roblox's 21,844 per MeshPart): Body 5,688, Head 4,604, Crest 384, Tail 916, ArmR 1,538, ArmL 1,538, LegR 1,004, LegL 1,004, FootR 496, FootL 496 ([mesh_stats.json](mesh_stats.json) has vertices and boxes). That is above the 8k target low end and inside the 8k to 20k band. For scale: a Compy is about 6 studs long; this cockatoo is **7.0 studs tall** (ground to crest tip) and 4.6 long with the tail. Unit decision: **1 Blender unit = 1 stud** (the same export settings as the world kit: `apply_unit_scale`, forward -Z, up Y, vertex colours as sRGB, normals only). The creature faces +Y in Blender, which becomes the front (-Z) in Roblox. All object scale is 1 and rotation 0; each part's origin is its joint (hip, shoulder, neck, tail base, ankle, crest root) and the part geometry is local to it, so a Motor6D rig needs no extra offsets.

Look: real geometry only. Every feather is a small curved blade with a ridge (about 14 to 20 triangles); the body, head, arms and legs are shingled rows of them over a smooth core. Colours are per-vertex (soft cream, pale yellow wash, yellow tips on the crest, tail and wing, dark grey hooked beak, grey scaly feet and black claws, brown eye with black pupil, dark rim and two white glints). One simple Principled material reads the colour attribute. No painted textures.

## Method (feasibility, one change per picture)

1. Cut the turnaround into three crops with the same scale and laid a **stud grid** (0.5 stud lines, 113 px per stud) over the sheet to read real positions off the picture: [00-reference-stud-grid-side.png](00-reference-stud-grid-side.png). This replaced eyeballing and fixed the biggest early errors (the body is 2.3 studs deep, the head is huge, the tail is a vertical fan, the crest is long blades that point BACK, not up).
2. Built the parts, rendered the same three orthographic views as the sheet and put reference and render side by side after every change ([02-stages-side-view.png](02-stages-side-view.png) shows the side view at stages 1, 3, 6 and final).
3. A/B decisions: crest as a halo of blades around the Y axis (A, kept) against a flat fan (B, edge-on from the side, dropped); rows of rounded scallop feathers (kept) against one big blade per feather group; flat shading against smooth per-feather shading (smooth kept: softer cups); a sphere eye against a banded dome eye (band kept, crisp pupil and iris).
4. Rig: one bone per part (rigid), `Body > Head > Crest`, `Body > Tail`, `Body > ArmL/ArmR`, `Body > LegL/LegR > FootL/FootR`, bones at the joints. Animations are keyed by (pitch, roll, yaw) and offsets in one data file that feeds both the Blender actions and the Luau module.

## Accuracy against the reference: **5.5 out of 10**

Good (matches): overall proportions (huge head on a plump, upright body, small hanging arms with black claws, short thick legs, big 3-toe feet, long backward tail fan, tall yellow crest), colour story (cream, pale yellow, dark grey beak, brown eye), the scalloped layered feather feel, side-view silhouette (about 70 percent overlap by eye), vertical position of eyes, beak, shoulders and feet.

Off (what a reviewer will see):
- **Softness and polish.** The sheet is a smooth ChatGPT 3D render with hundreds of tiny barbs. Ours are about 1,000 hard-edged scallops, so it looks like a clean low-poly bird, not a soft fluffy one. This is the largest gap (about 2 points).
- **Crest shape.** Ours is a symmetric "sunburst" of 25 blades (very wide from the front and the back). The sheet has two horn-like blades up and out plus a dense swept-back fan, and a white pointed tuft; ours has the tuft but it is small.
- **Feet** are thinner than the sheet's chunky scaly feet; no individual scale plates on the toes, claws a little long.
- **Face and beak.** The sheet has a rounded beak with a visible lower bill and a brow ridge over the eye; ours has a plain wedge beak and no brow. The forehead rings of feathers look like stripes from the front.
- **Arms** are two feathered sleeves with claws; the sheet's arm has a visible bent forearm and layered flight feathers.
- **Neck/torso** is a little longer and straighter than the sheet's hunched, shorter neck.
- **Lighting** differs, so the cream looks greyer and yellow olive in shade.

Honest expectation: a hand-modelled version with a sculpt pass could reach 7 to 8 out of 10 in a few days of work; a generator (generate_mesh, or an image-to-3D tool) starts at about 4 to 6 (see the staging results in [../2026-10-18-cockatoo/README.md](../2026-10-18-cockatoo/README.md)).

## Animations (pictures: [03-animation-contact-sheets.png](03-animation-contact-sheets.png))

- **Idle** (3.0 s loop): breathing (body rises 0.045 stud and tilts 1 degree), slow head tilt and turn (7 degrees roll, 6 yaw, one each way), crest bob with follow-through (up to 8 degrees), tail sway (5 degrees), arms drift a little.
- **Walk** (1.0 s loop, two steps): legs swing 24 degrees each way with feet counter-rotating to stay flat in the stance and toes up in the swing, hip lift 0.2 stud in the swing, body bob 0.12 stud twice per cycle, weight shift and yaw 3 degrees, head thrusts forward and back twice, tail sways 9 degrees, arms swing opposite to the legs.
- **Jump** (1.4 s, not a loop): crouch (body down 0.55, legs folded), launch (up 0.75, feet pointing down, wings start to open), apex (up 1.15, wings flared 72 degrees out, tail and crest up), descend, land crouch (down 0.38) and settle. Front-view row of the sheet shows the wings opening.

The motion was checked as pictures of key frames only (no real-time playback), so timing and weight are untested by feel. Walk speed against the game's real move speed is not matched (the stride length is about 1.5 studs per step).

## Roblox side (what can and cannot be done)

- **Luau module** [CockatooAnimations.luau](../../../assets/blender/creatures/CockatooAnimations.luau) (generated, pure data and functions, nothing requires it, no behaviour change): `Parts`, `Parent`, `Joints`, `Data` (the three animations), `sample(name, t)` (Motor6D Transform per part), `rig(model, originCF)` (creates Motor6Ds), `capture(model)` and `poseParts` / `apply(model, rest, originCF, name, t)` (forward kinematics that sets part CFrames directly: works for anchored parts in Edit mode, no physics needed). Curves are cubic Hermite with auto-clamped tangents, like Blender. **Tested in plain Luau 0.741** with stand-ins for Vector3 and CFrame (`python tools/blender/run_cockatoo_animation_test.py`, 9 checks pass: leg swings forward toward -Z, loops close, jump height and arm flare, children follow the body). **Not yet run inside Roblox Studio** (see below).
- **Creator Hub web upload does NOT take models.** The upload dialog at create.roblox.com offers only Decals, Audio and Video; an `.fbx` is shown as "Invalid file type". Models (FBX) go in through Studio's 3D Importer only (or the Open Cloud Assets API, which needs an API key that agents must not handle).
- **Studio was not usable.** The only Studio instance the MCP could see reported "Place is not open", so nothing was inserted into Place 1 and **nothing in Place 1 is unsaved or changed by this work**. No asset id exists. Studio screen captures were not possible either.
- What Roblox can import from the FBX (expected, from the 3D Importer docs, untested here): separate meshes become MeshParts, vertex colours are kept (vertex colour tint shows on a MeshPart), smooth normals are kept, an armature with rigid parts can become a Model with Motor6D joints (rig type Custom), baked actions can become an animation asset. Things that may not work: the importer may merge or rename the three takes; vertex colours need the importer's "use vertex colours" option; a MeshPart has no per-part pivot by default (use the module's `capture`, which reads the real CFrames).
- Phone cost to watch: 17.7k triangles per creature is a lot for 8 to 12 players. A 6k LOD would be a separate task (merge the feather rows, drop the face feathers).

### Manual import, 5 lines for the owner (about 10 minutes)

1. In Studio open Place 1 and the Avatar tab, press Import 3D (or the Asset Manager, Bulk Import) and choose `assets/blender/creatures/fbx/Cockatoo_HQ_rigged_anim.fbx`; keep "Use vertex colours" on and check that the model is about 7 studs tall (if it is 700 or 0.07, change the scale unit in the import dialog).
2. Press Import; if Studio makes a Model with MeshParts named Body, Head, Crest, Tail, ArmL, ArmR, LegL, LegR, FootL, FootR, keep it. (If the rig is not usable, import `Cockatoo_HQ_static.fbx` instead; the animation module needs only the ten part names.)
3. Right-click each MeshPart (or the Model), Save to Roblox, to get the asset ids; write them in docs/77 and in the BD-621 row.
4. Put the Model in `Workspace > Silly secret dinos v3 > Cockatoosaurus` (a Folder per design, row along X with 6-stud gaps, sign at x=-14) and anchor all parts.
5. In a test script: `local A = require(CockatooAnimations)`, `local rest = A.capture(model)`, then every Heartbeat `A.apply(model, rest, originCF, "Walk", os.clock())` where `originCF` is the ground point between the feet.

## Real cockatoo notes (Wikipedia, sulphur-crested cockatoo; the browser could not take screenshots, so text only)

44 to 55 cm long; plumage white with a yellow tinge under the wings and tail; **yellow, expressive, forward-curling crest**; black bill; grey legs; whitish eye ring; eyes nearly black in males, red-brown in females. Real parrots have zygodactyl feet (two toes forward, two back); the sheet shows a raptor-style three-forward, one-back foot, which we followed because the sheet is the target. The sheet's crest points backward in blades, real birds raise it forward over the head when alarmed: a good second crest pose for a later animation.

## Honest limits and rules

- **Built from a Blender script**, not hand-modelled or generated. AGENTS.md (2026-10-15 rule) says code-built models are not good enough for final art; this is a feasibility test the owner asked for, and nothing is bound to it.
- A ChatGPT key-pose helper sheet was offered; it was not made (the browser tool could not take screenshots, which that workflow needs).
- The blend file was saved in this branch only; the owner's own open Blender scene was replaced by this model.

## Next steps

1. Owner decides: keep this as the shape study, or ask for a hand-modelled / generated version.
2. If kept: owner (or an agent with a working Studio window) does the 5-line import, we record asset ids, run the animation module in Studio, rate again with Studio pictures.
3. Improve to about 7 out of 10: softer shading (more, smaller barbs on the chest and head, or a baked normal-like gradient in vertex colours), horn crest plus swept fan, chunkier scaly feet, rounded beak with lower bill, brow over the eye.
4. LOD for phones, then a decision on class (probably Fly like the budgie) and drop weight at integration (BD-606).
