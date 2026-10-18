# Cockatoo through the Blender to Roblox pipeline (BD-659 / BD-621), 2026-10-18

The real cockatoo (`assets/blender/creatures/Cockatoo_HQ.blend`, 10 parts, 17,668 triangles) was exported with `tools/blender_export_roblox.py` in three variants, uploaded with `tools/roblox_asset_upload.py` (owner's Open Cloud key, 3 uploads, all moderation Approved), loaded in the scratch Studio `cockatoo-scratch.rbxl` with `InsertService:LoadAsset` (Edit mode), and measured. Status: **TEST MODEL, not bound anywhere**, nothing in the owner's Place1 was touched. The key was never printed or written.

## Uploaded assets (owner's account, test models)

| Variant | Command | FBX | Asset id | Size |
|---|---|---|---|---|
| parts only | `python tools/blender_export_roblox.py <blend> --out Cockatoo_parts.fbx` | 0.57 MB | **116310176815729** | 3.36 x 7.43 x 4.66 studs (x, up, z) |
| with rig | same plus `--rig` | 0.58 MB | **89600501756470** | see below (shape is wrong) |
| rig and animations | same plus `--anim` | 0.85 MB | **102247452194822** | same as the rig variant |

All three were exported BEFORE the two exporter fixes below (turned 180 degrees, leftover pose). Delete them in Creator Hub > Inventory when no longer needed (the owner's choice).

## What survived (measured in Studio)

| Question | parts only | with rig | rig and animations |
|---|---|---|---|
| Arrives as | Model "Model" > Model "Cockatoo_parts" > 10 MeshParts | Model > Model "Cockatoo_rig" > 10 MeshParts + RootPart + Folder InitialPoses (33 CFrameValues) + AnimationController + 10 Motor6D | identical to "with rig" (same mesh ids, same structure) |
| Height | **7.43 studs** (ground to crest tip; 7.34 with the rest-pose fix; the owner's "about 7 studs" holds), width 3.36, depth 4.66 | bounding box 5.70 high (feet end up above the legs, see below) | same |
| Scale | correct (1 Blender unit = 1 stud with `global_scale 0.01`) | correct | correct |
| Part names | **all 10 kept**: Body, Head, Crest, Tail, ArmL, ArmR, LegL, LegR, FootL, FootR | kept | kept |
| Part rotation | all parts rotation 0 | all 0 | all 0 |
| Pivots | **kept**: `PivotOffset` is set so `GetPivot()` is the Blender origin (the joint). Measured against the module `Joints` table, 8 of 10 within 0.001 stud; LegR 0.20 and FootR 0.23 off because the saved .blend had a leftover pose (bone LegR moved 0.2) | pivots are NOT consistent: the Foot is 0.93 ABOVE the leg (should be below), the Crest is rotated about the head joint (offset 1.18 long but turned), the Body pivot is (0, 0.3, -1.9) instead of (0, 1.9, -0.3) (Y and Z swapped). Head, Tail and Arms are right relative to the Body | same as rig |
| Facing | **turned 180 degrees about Y**: the cockatoo faces +Z (Roblox front is -Z) and left and right are swapped (ArmR at x = -1). Cause: FBX `axis_forward = -Z` while the model faces +Y in Blender (Blender's own front is -Y). Fixed in the exporter (`--faces +Y` sets forward `Z`) | same turn | same turn |
| Vertex colours | **kept in the mesh**: read with `AssetService:CreateEditableMeshAsync`: Body 5,174 colour entries, 24 distinct (cream 241,229,198 dominant), Head 4,414 (eye brown, beak grey), Crest 343 (6 yellows and creams), FootL 298 (3 greys) | kept (RigBody 24 distinct, RigCrest 6) | kept |
| `MeshPart.Color`, `TextureID`, `Material` | default grey (163,162,165), empty, Plastic; so the colours live only in the mesh. Whether Roblox multiplies the mesh colours with the grey part colour was NOT seen (the scratch Studio window is minimised, screen_capture is dark) | same | same |
| Motor6D | none (the snippet builds them from the pivots: 9 joints, rest error 0.00002 stud) | 10 created (BodyMotor6D is a joint from Body to Body, the real ones hang Head > Crest, Body > Tail/Arms/Legs, Leg > Foot) but the part placement does not match the joints (above) | same as rig |
| Bone / Animator | none | none (AnimationController only, no Animator) | none |
| Animation data | none | none | **none**: no KeyframeSequence, no Animation instance, nothing for Idle / Walk / Jump. The extra 0.27 MB in the FBX is not turned into an asset by the API upload |
| Scripts inside | none (the snippet also stops if it finds one) | none | none |

## Studio numbers check of the animation module (parts variant, turned back 180 degrees as the fixed export gives)

`assets/blender/creatures/CockatooAnimations.luau` run as a ModuleScript in Studio (Edit mode, anchored parts, forward kinematics `apply`), 10 time points per animation, parts returned to rest afterwards:

| Animation | Max joint rotation by part (degrees) | Overall | Body height change |
|---|---|---|---|
| Idle (3.0 s) | Body 1.0, Head 9.1, Crest 9.3, Tail 5.0, Arms 4.3, Legs 1.0, Feet 1.0 | 9.3 | 0.043 stud |
| Walk (1.0 s) | Body 4.7, Head 3.0, Crest 9.6, Tail 12.6, Arms 12.1 and 12.8, Legs 26.4 and 24.4, Feet 28.3 and 24.2 | 28.3 | 0.116 stud |
| Jump (1.4 s) | Body 9.5, Head 9.7, Crest 17.9, Tail 26.9, Arms 75.8, Legs 25.7, Feet 24.2 | 75.8 | 1.580 studs (1.626 to 3.206) |

Pivot error against the module `Joints` table with the model turned: 0.000 for 8 parts, 0.200 and 0.227 for LegR and FootR (the leftover pose). The module works on the part names only; it needs no imported rig or animation.

## Defects found and fixed in the tools (this PR)

1. **Exporter turned the creature 180 degrees.** `tools/blender_export_roblox.py` used `axis_forward="-Z"`. Now the forward axis comes from `--faces` (default `+Y`, the way the cockatoo faces in Blender), which gives FBX forward `Z`. Test: `test_forward_axis_turns_a_plus_y_creature_to_minus_z`. The new export was made locally (`build/pipeline-test/fixed/`) and its joint origins match the module `Joints` table exactly; it was NOT uploaded again (3 upload limit), but the Studio turn above is mathematically the same as the fix.
2. **Leftover pose exported.** The saved .blend had the pose bone LegR moved 0.2 (the right leg and foot arrived 0.2 higher) and the Idle action assigned at frame 1 (its tail key is a 5 degree yaw; whether that also reached the mesh was not checked); the parts-only export uses the evaluated pose. The exporter now unassigns actions and resets all pose bones first (`reset_to_rest_pose`, test with stand-ins). The `--anim` export still bakes all three actions (0.85 MB, unchanged size).
3. `tools/studio/render_insert_snippet.py` got `--joints Head=Body,Crest=Head,...` (test `test_render_joints_table`) so the Joints table no longer has to be pasted by hand; the snippet comment about "FBX axes make it face -Z" was corrected.

## What to do next

- Use the **parts only** export with the snippet's joints and the Luau module. It is the only variant that arrives with correct part names, pivots and vertex colours.
- Do not use `--rig` / `--anim` through the API upload for now. Roblox builds its own Motor6D rig from the bones and places the second level bones wrongly (Foot above Leg, Crest turned); animations do not arrive at all. To get animation assets, the Studio Animation Editor / 3D Importer by hand is the only known way, or run the module from a script.
- Re-upload the fixed `parts` export once (one asset) to confirm the facing in Roblox, then delete the three test assets.
- Open question for a picture: do vertex colours show without a texture on a grey MeshPart? Needs a frame from a non-minimised Studio.
