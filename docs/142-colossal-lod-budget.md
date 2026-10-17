# 142 Colossal ancient trees: LOD swap, cull radius, budget, colliders and grounding (BD-475)

Written 2026-10-17 (branch `claude/bd475-colossal-lod`). **Status: built and verified OFFLINE (Review / test). No Studio, no phone, nothing uploaded, no asset id.** Labels: **CODE** (what the source does), **MEASURED** (an offline run of the real code, command given), **ESTIMATE** (arithmetic on the offline estimate, can be 30% off), **PROVISIONAL** (a number to re-tune after the BD-085 phone pass). Handbook: [114](114-handbook.md). Spec: [139](139-giant-dino-vegetation-scale.md) s8, s9, Q12. Art: [140](140-tree-quality-test.md) "Colossal ancient trees". Task: BD-475 in the [kanban](07-kanban.md).

## 0. Summary

1. **With empty ids the game does not change at all.** No colossal model carries the new attribute, the client list of colossal trees stays empty, the kit colliders, the 5-ray grounding and the plain cull radius stay in use for every prop. The shipped repo has no id filled (`tools/verify_colossal_lod.py` asserts it).
2. **A tree is only used when BOTH ids are pasted** (LOD0 and its `_lod1`). A LOD0 without its LOD1 keeps the stand-in (BD-474 used LOD0 alone).
3. Once both are pasted: the client swaps LOD0 (near) and LOD1 (far) by distance without a jump, the cull radius is a config value (default = today's), a cap limits LOD0 trees and the triangles, the invisible trunk colliders are as thick as the real trunk, and the trunk stands on the lowest ground under its footprint.
4. **Budget (offline estimate, playtest profile, phone):** worst-spot scene 452,134 triangles today (stand-ins) against 450,023 with fake ids (default radius). Details in section 4.

All shared rules are in `src/shared/ColossalRules.luau` (pure math, no Instances). The server (`Arena`), the client (`WorldCulling`), `tools/verify_colossal_lod.py` and `tools/estimate_world_budget.py` run the SAME functions.

## 1. LOD swap and the pivot offset

- **CODE:** `Arena.generatedProp` adds the LOD1 mesh as a second part (`ColossalLod1`) of the same Model, fitted to the SAME height as LOD0 (their bounding boxes differ by up to 1%). The Model carries `ColossalKey`, `ColossalTris0`, `ColossalTris1`. `WorldCulling` parents exactly ONE of the two parts at a time (the other is `Parent = nil`), so the scene and the part budget count one mesh per tree.
- **Pivot:** each FBX pivot is its own bounding-box bottom centre, so the trunk base is NOT at the pivot, and it sits at a different place in LOD0 and LOD1 ([140](140-tree-quality-test.md): broadleaf (3.08, -0.87) vs (3.67, 3.4), conifer (-0.67, -3.04) vs (-4.16, -6.17), palm unchanged). `ColossalRules.lod1Offset` moves the LOD1 part by `base0 x scale0 - base1 x scale1` so the two trunk bases coincide. **MEASURED:** the uncompensated jump is up to 5.56 studs (conifer at 110 studs), compensated 4e-16 (verifier B4). The numbers (`size`, `base`) are stored in `WorldGeneratedMeshes.Colossal`.
- **UNVERIFIED:** the sideways sign. The FBX export is `axis_forward = -Z, axis_up = Y`, so Blender (x, y, z) should arrive in Roblox as (x, z, -y); `ColossalRules.BlenderYToStudZ = -1` is that assumption. If the swap jumps sideways after the first upload, flip the sign (one number). It cannot be checked before an upload.
- **Distances (PROVISIONAL, `Config.WorldCulling.Colossal`):** LOD0 nearer than 110 / 150 / 220 studs (phone / tablet / desktop), LOD1 beyond; 15% hysteresis (the existing `Hysteresis`) so a tree on the border does not flicker. The swap distance is measured horizontally to the trunk base (a 100-stud tree is not "50 studs up").

## 2. Cull radius (Q12)

- `Config.WorldCulling.Colossal.<class>.radius` is the studs a colossal tree stays parented. **Default = the normal radius (190 / 280 / 440), i.e. today's behaviour.** `ColossalRules.settings` clamps it to `[normal radius, ceiling]` with ceiling 420 phone / 560 tablet / 800 desktop (docs/139 s9, Q12).
- Per Q12 the larger radius ships ONLY when the BD-085 phone numbers pass. Until then the trees fade out instead of popping: they turn transparent over the last 20% of the radius (`Fade = .2`, client-local `Transparency`; camera occlusion owns `LocalTransparencyModifier`, so they never fight over one property) and are gone exactly at the radius. `Fade = 0` is a plain pop.
- A tree beyond the normal radius only gets in while the part budget has room (colossal trees are decided after the ordinary props, nearest first) and while the triangle budget allows.

## 3. Budget: LOD0 cap and triangle budget

`ColossalRules.assign` runs nearest first. It allows at most `lod0Max` trees at LOD0, shows the rest at LOD1, and drops a tree when `triBudget` triangles or the part budget are used up.

| Class | normal radius | colossal radius (default / ceiling) | LOD0 nearer than | LOD0 trees at once | triangle budget |
| --- | ---: | ---: | ---: | ---: | ---: |
| Phone | 190 | 190 / 420 | 110 | 1 | 12,000 |
| Tablet | 280 | 280 / 560 | 150 | 2 | 24,000 |
| Desktop | 440 | 440 / 800 | 220 | 4 | 48,000 |

The phone matches docs/139 s9 ("1 at LOD0 + 5 at LOD1"). The triangle budget is about what the stand-ins cost inside the normal radius (phone: 7 trees x 1,630 = 11.4k). All of it PROVISIONAL until BD-085.

## 4. Numbers: before and after, with fake ids (offline estimate)

`python tools/estimate_world_budget.py --runner luau.exe` and `python tools/verify_colossal_lod.py --runner luau.exe`. Playtest profile, density 1.25, seed 1404. Stand-in = 1,630 triangles per tree (ESTIMATE of the generated mesh, docs/107); LOD0 4,154 / 4,052 / 3,834, LOD1 925 / 927 / 966 (MEASURED in Blender, [140](140-tree-quality-test.md)). Of the 31 colossal placements 9 are dead trees with no ancient mesh (they stay stand-ins in both worlds), so 22 trees change. "Fake ids" = every entry treated as uploaded.

| Phone, playtest | Before (stand-ins today) | After (fake ids, default radius) | After (fake ids, ceiling radius 420) |
| --- | ---: | ---: | ---: |
| All 22 ancient-mesh trees in range (upper bound) | 35,860 (all 31 colossal: 50,530) | at most 11,320 at any spot | at most 11,681 at any spot (budget 12,000) |
| Worst-spot scene, (-160, -160): colossal trees in range | 3 trees = 4,890 | 3 at LOD1 = 2,779 | 12 at LOD1 = 11,112 |
| **Worst-spot scene triangles (estimate)** | **452,134** | **450,023** (-2,111) | 458,356 (+6,222) |
| Same, LOD0 slot always full (worst case of the cap) | n/a | 453,148 (+1,014, +0.2%) | n/a |
| Trees at LOD0 at once (any spot) | n/a | at most 1 | at most 1 |

- **Tablet / desktop** (worst spot): stand-ins 9,780 / 35,860 against 8,785 / 23,720 (default radius), at most 2 / 4 trees at LOD0, no spot above 23,966 / 33,407 in any mode (default radius, LOD0 slots full, ceiling radius).
- **Parts:** each ancient tree adds one LOD1 part at join and two more collider boxes (3 instead of 1). Loaded at join 8,640 -> 8,706 (cap 9,150); phone worst-spot scene parts 3,434 -> 3,487 even at the ceiling radius (cap 3,980). Only one mesh per tree is ever parented on the client.
- **Honest limits:** at a spot with 1 to 4 trees in range and a tree nearer than the LOD0 distance, fake ids cost up to +1.8k triangles on a phone against the stand-ins (the highest delta at any spot, default radius), because one LOD0 tree (4,154) costs more than its stand-in (1,630). That is the price of showing one detailed tree; the cap bounds it. The ceiling radius is +6.2k at the worst spot: it should stay off until a real phone run (BD-085). None of this is a phone measurement.

## 5. Trunk colliders

- **Problem (CODE before):** the kit collider of a size-l tree is a 2.0 to 2.25 stud box times the placement scale, while the new trunks are 17 to 28 studs wide: in all 22 placements the box is thinner than the trunk, so a dino could walk into the outer trunk.
- **Now:** `ColossalRules.colliders` builds three stacked square boxes from the stored `trunk = {diameter at ~15% height, bare trunk height}` scaled by the fitted height: widths 1.1 / 1.0 / 0.9 x the diameter (the round trunk is inside the box), total height = the bare trunk height capped at 45 studs (docs/139 s8 rule 3, a maxed dino can stand under the lower canopy), centred on the real trunk base (not the pivot). `Arena.kitProp` takes them instead of the kit colliders for ancient trees only. Colliders are invisible and never culled.
- **MEASURED (verifier B6, B9):** widest box 28.0 studs; box width equals the stored trunk width times the tier factor for all 22 placements; no box reaches into a path corridor (the placement keeps trunk centres 14+ studs clear); solid/solid overlaps with the new trunks 1 (a small conifer at (-360, 124) beside the colossal conifer at (-348, 116); the grammar keeps colossal trees clear by the old thin collider; the real fix is a `BiomePlacement` version bump that keeps them clear by the real trunk, which changes today's layout, so it is NOT done here).
- **Not covered:** the palm trunk curves and leans (up to 7.5 studs at the top); the box stack is straight. The buttress roots (30 to 42 studs) have no collider.

## 6. Grounding

- **Problem:** the footprint radius for plants is `min(1, 0.04 x size)` (a 1 stud ring), the bottom went to the HIGHEST of five rays. On a 24 stud trunk on a slope the downhill side floated by up to `diameter x tan(slope)`.
- **Now:** nine rays (centre + 8 around) at the real trunk radius, centred on the trunk base (rotated by the prop yaw), and the bottom goes to the LOWEST hit minus the `RootSink` 0.15. Nothing floats; the uphill side is buried, as a tree on a slope is. Too few hits (under 5) or an answer more than 14 studs from the layout height keeps the layout height. **MEASURED (verifier B7):** a 20 degree slope under the 104 stud broadleaf trunk gives about 8 studs of relief; every ray is at or above the bottom. Other props keep the existing rule unchanged.

## 7. What to do when the ids exist

1. Paste LOD0 and its `_lod1` id for the same family (`python tools/bind_assets.py tree_colossal_broadleaf_v3=<id> tree_colossal_broadleaf_v3_lod1=<id> ...`, see [120](120-pending-owner-uploads-checklist.md)). A single id does nothing.
2. Studio check (Review / test): trees stand on the ground on slopes; no jump when walking from 90 to 130 studs (if it jumps sideways flip `BlenderYToStudZ`); the trunk collider matches the visible trunk; the fade at the radius; `player` attributes `CullColossal` (LOD0/LOD1/total and triangles) and `CullParts`.
3. Phone run (BD-085) with the default radius. Only if it passes, raise `Config.WorldCulling.Colossal.Phone.radius` towards 420 and run it again.

## 8. Verification

`python tools/verify_colossal_lod.py --runner luau.exe` (in CI): A empty ids, B1 swap thresholds, B2 radius clamp, B3 fade, B4 pivot compensation, B5 LOD0 cap and triangle budget, B6 colliders, B7 grounding, B8 shipped config, B9 geometry, C budget; plus the existing world verifiers (`world_art`, `world_budget`, `world_overlap`, `vegetation_layers`, `gameplay`, `camera_occlusion`) and `tests/test_world_generated_meshes.py`. Not Studio evidence.

## 9. Handbook check (docs/114)

- 8.1 item 9 (pivot at the bottom centre, collision separate and never culled): kept; the trunk centre is offset from the pivot and the collider follows it.
- 8.1 item 8 (budget): numbers above; the colossal share never exceeds the stand-ins in total.
- 8.1 item 10 (no invented ids): none; all ids stay empty.
- Calm and polished (section 0): no pop at the cull border (fade) and no jump at the swap (pivot shift); both unseen in Studio.
