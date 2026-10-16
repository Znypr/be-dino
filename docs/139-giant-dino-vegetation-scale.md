# 139 Giant dinos vs the jungle: vegetation height layers, camera curve and scale ladder (SPEC)

Written 2026-10-16 (branch `claude/giant-dino-vegetation-scale`). **Status: SPEC ONLY. No game code, art or config changed.** Every number below that is not marked MEASURED or CODE is a PROPOSAL and PROVISIONAL. Labels: **OWNER** (owner said it), **CODE** (what the source does today), **MEASURED** (Studio or offline run, with its source), **ESTIMATE** (derived, can be wrong by 30% or more), **PROPOSAL** (this doc). **OWNER ANSWERS 2026-10-16 (applied in this revision): Q1 keep current growth pacing, Q2 awe only, Q5 Blender is allowed (section 1.1).** Handbook: [114](114-handbook.md). Decisions: [115](115-decisions-log.md). Open conflicts: [116](116-handbook-conflicts.md) (section F points here). Tasks: BD-470..BD-477 in the [kanban](07-kanban.md).

## 0. Summary for the owner (read this first)

1. **The jungle disappears only for a long run.** Size is `s = min(4, sqrt(1 + growth/50))` and growth is 0.1 per food point (BD-386). A normal 5-minute run is about 650 food, so `s` is about 1.5 and a Compy is about 10 studs tall while 84% of today's trees are still taller (a T-Rex, 16 studs, is still shorter than half of them). `s = 2` takes about 11 minutes, `s = 3` about 31 minutes and the cap `s = 4` about 58 minutes (potions shorten this, BIG adds x1.2). If "gigantic at the end" must happen in a 5-minute run, that is a growth-curve question (Q1), not a vegetation question. **OWNER Q1 (2026-10-16): keep this pacing.** A normal 5-minute run stays at about `s` 1.5; gigantic is a rare long-run reward, so the Medium/Colossal bands and the camera curve now matter mainly for long runs and for BIG or potion-boosted dinos.
2. **A colossal tier mostly exists already, but it is too short.** The `giant` layer (the same tree meshes at x2.4 to x4) gives 48 trees between 33 and 99 studs. 75% of them (36) are under 80 studs, and the tallest max-size dino is about 49 studs (T-Rex BIG) to about 53 studs (ESTIMATE, Brachiosaurus BIG): 6 giants are shorter than a BIG-max T-Rex and 11 shorter than the 53-stud planning value. They are also the same low-poly meshes scaled up, so the facets get huge, which is exactly the "miniature" look the owner wants to avoid.
3. **The camera is exactly proportional and blind to species.** Minimum zoom is `12 x s`, no cap except the player's 110-stud maximum, default FOV 70, default Roblox pitch. A Compy fills 39% of the screen height at every size, a T-Rex 61% at every size.
4. **Proposal:** three vegetation bands (Small 4-12, Medium 12-42, Colossal 80-140 studs) with a dedicated colossal mesh family, a species-aware sub-linear camera (formula in section 7: distance from the dino's real height, 0.38 to 0.55 of the screen, hard cap 60 studs, aim at 40% of the body, FOV 70 to 80, optional pitch cap 20 degrees), "trample" collision for giants, and a phone budget that is net-neutral in triangles (colossal REPLACE the 48 giants).
5. **Nine questions are still open (section 14: Q3, Q4, Q6-Q12).** Answered 2026-10-16: Q1 (keep pacing), Q2 (awe only), Q5 (Blender allowed). Because of Q1 the build rows were re-prioritised (section 15): only the Small-band and early-game feel work stays P2; the camera curve, colossal art, LOD, giant collision and the test pass drop to P3.

## 1. The owner problem and the proposal

**OWNER problem (2026-10-16):** a dino spawns small and grows. The owner wants it gigantic at the end so small players feel intimidated, but the bigger it gets, the less the map feels like a jungle.

**Proposal from an outside design review the owner shared (a PROPOSAL, not a decision):**
1. Three vegetation layers. Small: ferns, bushes, flowers, mushrooms, small palms (huge to a new dino, tiny later). Medium: most current trees (outgrown late, the strongest visual evidence of growth). Colossal ancient trees: taller than a max-size dino, massive trunks, high canopies, used sparingly as landmarks. Test mix: about 60-70% small/medium, 20-30% larger, 5-10% colossal, in clusters with open clearings.
2. Camera distance grows with dino size but not proportionally forever. Low-ish angle, close to the body, tall trunks visible in the background, no top-down view at max size.
3. Giants should sometimes feel too big for their surroundings (part of the fantasy), but the world must not look miniature.

### 1.1 Owner answers 2026-10-16 (OWNER) and what they change

| Q | Answer | Effect on this spec |
| --- | --- | --- |
| Q1 growth pacing | **KEEP the current pacing.** A normal 5-minute run stays at `s` about 1.5; gigantic is a rare long-run reward | Section 0 point 1 is now the intended state, not a problem. Only about the top 5% of sessions (30 minutes or more, potions, BIG) ever see `s` of 3 or more, so Medium outgrowing, Colossal trees, the camera curve and giant collision are polish for a rare moment. What still matters for EVERY run is the START: a new dino should feel small in a tall world (Small band, skyline of tall trees, clearings). Priorities were re-cut accordingly (section 15) |
| Q2 intimidation | **AWE ONLY**: size, footsteps, shadow and camera framing. No fear mechanics, no small-dino reactions | Option (b) of Q2 is dropped. Awe cues are listed in section 10.1; nothing makes other dinos flee, wobble or hide, and the optional trample rustle (section 8) is a footstep-class sound, not a threat cue. Matches handbook 0 (calm, friendly) |
| Q5 art pipeline | **Blender is ALLOWED** for colossal and redesigned tree art. Separately the owner approved the script-built V3 trees (broadleaf, conifer, palm) as a scoped exception; the tree test PR (docs/140-tree-quality-test.md) records that | Section 11 is unblocked: generate-then-Blender-cleanup or Blender-authored are both fine for colossal. The "generated meshes only" rule (D8/D15) is therefore NOT in conflict for tree art. Colossal still must be judged by the owner on a screenshot and must not be a scaled-up kit tree |

Q3, Q4 and Q6-Q12 stay open; recommendations below are still only recommendations.

## 2. Goals and non-goals

Goals: (G1) a new dino feels small in a tall green world; (G2) a grown dino feels huge (a rare long-run payoff, OWNER Q1) and the player can see WHY (it passes plants and trees it used to hide behind); (G3) at max size the map still reads as jungle, with ancient landmarks that are still taller than the dino; (G4) the dino and food stay readable (handbook 3, "readable at a glance"); (G5) no new phone risk (docs/107).

Non-goals: no change to eggs, crystals, growth rates or `GrowthPerFood` (OWNER Q1: current pacing is kept); no fear mechanics (OWNER Q2); no new biome; no hiding or stealth mechanic; no flag flip (everything ships behind new flags, default off, handbook 12); no art is made by this PR.

## 3. Measured reality (from code, 2026-10-16 main)

### 3.1 Dino size

| Item | Value | Source |
| --- | --- | --- |
| Scale from growth | `s = min(4, sqrt(1 + G/50))`; `G` = food x `GrowthPerFood` (0.1) x `GrowthMultiplier` (clamped 0.1-8), +2.5 per player kill | CODE `Dinosaur.scaleForScore`, `Config.GrowthPerFood`, `PredationGrowthPoints` |
| BIG trait | x`BigScaleMultiplier` 1.2, so max `s` = **4.8** (3% Rare chance) | CODE `Config.BigScaleMultiplier`, `BigChance` |
| Growth potions | Growth Sip 1.25x, Hearty 1.4x, Prime Feast 1.6x, Behemoth Brew 1.8x (750 s), Titan Tonic 2x (900 s). They speed growth up; they do NOT raise the cap of 4 | CODE `ProgressionConfig` |
| Food per minute | about 120-140 (normal 5-minute run about 600-700 food) | docs/119 (ESTIMATE, needs a Studio log) |
| Reset | `GrowthScore` is set to 0 on entering the Sanctuary and on run start, so the hub dino is `s = 1` | CODE `RunLifecycle.prepareSanctuary`, run start |
| Visual | the low-poly (or legacy) model is `ScaleTo(species scale x s)`; the torso collider grows with `s` | CODE `ResourceVisuals`, `MovementEnvelope.collider` |

Size over a run (normal 130 food/min, no potion):

| Food | Time | `s` | Compy H (studs) | T-Rex H (studs) |
| ---: | --- | ---: | ---: | ---: |
| 0 | 0 | 1.00 | 6.6 | 10.3 |
| 650 | 5 min (normal run) | 1.52 | 10.0 | 15.7 |
| 1,500 | about 11.5 min | 2.00 | 13.2 | 20.6 |
| 4,000 | about 31 min | 3.00 | 19.8 | 30.9 |
| 7,500 | about 58 min | 4.00 (cap) | 26.4 | 41.2 |
| 7,500 + BIG | about 58 min | 4.80 | 31.7 | 49.4 |

Species heights at `s = 1`, low-poly models, playtest profile (`LowPolyDinos = true`):

| Species | LowPoly scale | Bounding box X x Y x Z (studs) | Source |
| --- | ---: | --- | --- |
| Compy | 2.2 | 3.5 x **6.6** x 7.7 | MEASURED, kanban BD-329 (Studio 2026-10-16) |
| Gallimimus | 2.9 | 1.8 x **4.9** x 5.8 | MEASURED, BD-329/BD-337 |
| Tyrannosaurus | 3.66 | 5.6 x **10.3** x 11.3 | MEASURED, docs/108 |
| The other 19 species | 1.7-3.87 | not measured | ESTIMATE: Y is about 2.8-3.0 x `LowPolyDinoAssets.scale` for upright Ground bipeds (Compy 3.0, T-Rex 2.8) and lower (about 1.7) for thin or low bodies. Longest-body planning value: Brachiosaurus (3.87) about 11 studs, which is **about 53 studs at BIG max** |

Axis order in the docs is not labelled; I read it as X width, Y height, Z length (consistent with the Compy and T-Rex shapes). The legacy (non-low-poly) Compy is about 5.5 studs (docs/68: about 22 tall at `s = 4`). BD-471 measures all 22 species in both modes.

### 3.2 Camera

| Item | Value | Source |
| --- | --- | --- |
| Camera | stock Roblox Custom/Classic camera on the Humanoid. No FOV, pitch, `CameraMode` or `CameraMaxAxisAngle` override anywhere in `src` (grep). So FOV is the default 70 (vertical) | CODE `Bootstrap.client.luau` `characterAdded` |
| Min zoom | `CameraMinZoomDistance = 12 x VisualScale`, rewritten every 0.15 s | CODE `Bootstrap.client.luau` (line near 1513), `Config.CameraMinZoom = 12` |
| Max zoom | fixed 110 (player can pull back; Settings can reset it) | CODE `Config.CameraMaxZoom`, `Bootstrap.client.luau` |
| Aim height | `Humanoid.CameraOffset.Y = 2 x (s - 1)` (smoothed at 7/s) plus a vertical low-pass of 0.18 s on the root (BD-164). The root centre is about 3 studs above the floor (R6 assumption from `Dinosaur.groundHeight`, not measured), so the aim is about `3 + 2(s - 1)`: 3 at spawn, 9 at `s = 4` | CODE `Bootstrap.client.luau`, `Config.CameraLiftSharpness`, `CameraVerticalSmoothing` |
| Camera distance at the minimum | 12 / 18 / 24 / 36 / 48 / 57.6 studs at `s` = 1 / 1.5 / 2 / 3 / 4 / 4.8 | derived |
| Share of screen height the dino fills (level camera, `H / (1.4 x D)`) | Compy 0.39, T-Rex **0.61**, Gallimimus 0.29, **at every size** | derived from the table above |
| Occlusion | `CameraOcclusion` fades WorldKit props between camera and dino to 80% transparent (max 8 props / 40 parts, ignores props behind the dino, ground cover under radius 1.2 never fades, off when the camera is more than 80 studs from the dino) | CODE `Shared/CameraOcclusion.luau` (BD-253) |
| Weather coupling | `WeatherVisuals` scales particle volumes by `clamp(cameraDistance / 16, 1, 6)` | CODE `WeatherVisuals.client.luau` |

### 3.3 World and vegetation

| Item | Value | Source |
| --- | --- | --- |
| Map | `ArenaHalfWidth` 416 = **832 x 832 studs**; spawn meadow at (0, 30); hills 9-13 studs; peaks 46 / 58 / 65 / 80 studs; terrain top 120 | CODE `Config`, `IslandLayout` |
| Mode | `WorldArtMode = "Legacy"` by default; the playtest profile sets `BiomeKit`, `WorldArtDensity` 1.25, `LowPolyDinos` true | CODE `Config`, `tools/release_profiles.py` |
| Biomes | meadow 13%, fern 33%, conifer 24%, marsh 8%, badlands 10%, volcanic 11% | docs/68 |
| Tree meshes | Roblox-generated meshes fitted INSIDE the kit extent box (so real height is at or below extent height) | CODE `Arena.generatedProp`, `WorldGeneratedMeshes` |
| Part budget | `PartBudget` 3,800 x density; 1 MeshPart per prop plus invisible collider boxes | CODE `BiomePlacement` |
| Distance culling | client parent-to-nil beyond a radius, nearest first inside a part budget: Phone 190 / 1,400, Tablet 280 / 2,400, Desktop 440 / 5,000; weather `FogEnd` is kept inside the cull radius | CODE `Config.WorldCulling`, docs/91 |
| Phone budget (offline ESTIMATE) | rule of thumb 3,000 parts and 250 k triangles; the phone worst-spot scene is already about 3,312 parts and **about 551 k triangles (ESTIMATE, 1,630 per generated mesh)**, caps 3,980 / 660 k | docs/107 |
| Streaming | `StreamingEnabled` is off; all parts replicate at join (about 7,625) | docs/107 |

Placement run at seed 1404, playtest density (offline, `BiomePlacement.generate` with the real kit; heights are kit extent x placed scale, so they are upper bounds):

| Layer | Count | Height min / p10 / p50 / p90 / max (studs) | Scale range (CODE) |
| --- | ---: | --- | --- |
| Ground cover (grass, flowers) | 1,523 | 1.3 / 2.0 / 2.9 / 4.1 / 4.8 | x1.6-3.0 |
| Shrub (ferns, bushes, mushrooms, horsetail) | 1,259 | 1.1 / 1.7 / 2.8 / 7.0 / 10.2 | x1.1-2.3 |
| Tree | 611 | 5.0 / 8.8 / 15.8 / 28.4 / 41.9 | x0.9-1.6 |
| Giant (same meshes; 2 are rock spires) | 48 | 33.5 / 42.0 / 72.6 / 93.2 / 99.2 | x2.4-4.0 |
| Fallen log | 54 | 7.6 / 8.9 / 12.9 / 18.3 / 21.7 | x0.9-1.5 |
| Rock | 187 | 1.7 / 2.2 / 3.7 / 8.0 / 20.8 | x0.85-1.8 |
| Landmark | 4 | 9.4 / 9.4 / 19.9 / 25.8 / 25.8 | x1.4 |
| Total | 3,686 | | |

168 of the 611 trees (27%) are under 12 studs and would count as Small-band plants under the proposal. Other facts: one tree every 1,130 studs^2 (0.88 per 1,000 studs^2), one giant every 14,400 studs^2; nearest tree to spawn 74 studs (the 56-stud spawn keep-out), nearest giant 161 studs (giants fade in between 150 and 270 studs from spawn); giants by biome: conifer 22, fern 17, volcanic 7, marsh 1, badlands 1. Tree-plus-giant height bands (659 placements): under 14 studs 38.5%, 14-26 40.5%, 26-42 14.3%, 42-62 2.0%, 62 and up 4.7%. Among the 491 placements of 12 studs and up (the proposed canopy-class): 12-26 72%, 26-42 19%, 42-80 6.5%, 80 and up 2.4%.

### 3.4 Collision today

| Item | Value | Source |
| --- | --- | --- |
| Dino torso collider | 2.6 x s wide, 3.2 x s long, top at 2.6 x s above the floor: **10.4 x 12.8 studs at `s = 4`, 12.5 x 15.4 at BIG** (the 26-49 stud body above the torso passes through everything visually) | CODE `Config.DinoCollider*`, `MovementEnvelope.collider` |
| Plants | shrubs and ground cover have NO collider (`colliders = {}`); every dino already walks through them | CODE `WorldKitData` |
| Trees | invisible trunk box, e.g. conifer_l 2.0 studs wide x 12 high at x1, so a giant trunk is **4.8-9 studs wide, up to 48 high** | CODE `WorldKitData`, `Arena.kitProp` |
| Corridors | the six path polylines keep a 14-16 stud half-width clear of blocking props (28-32 studs wide) | CODE `BiomePlacement.Paths` |

### 3.5 What the measurements say

- The dino outgrows the world in this order: ground cover and shrubs (gone by `s` = 1.5-2), then half the trees (`s` about 2-2.5), then 87% of trees for a Compy at max (a T-Rex passes 99.5% of trees at `s = 4`). Table: share of today's playtest placements that are TALLER than the dino:

| Dino and size | H | Shrubs | Trees | Giants |
| --- | ---: | ---: | ---: | ---: |
| Compy s=1 | 6.6 | 11.1% | 96.9% | 100% |
| Compy s=1.41 (500 food) | 9.3 | 2.7% | 87.4% | 100% |
| Compy s=2 | 13.2 | 0% | 62.7% | 100% |
| Compy s=4 | 26.4 | 0% | 12.8% | 100% |
| T-Rex s=1 | 10.3 | 0% | 82.2% | 100% |
| T-Rex s=2 | 20.6 | 0% | 28.3% | 100% |
| T-Rex s=4 | 41.2 | 0% | 0.5% | 91.7% |
| T-Rex BIG s=4.8 | 49.4 | 0% | 0% | 87.5% |

- **Small plants are never "huge" to a new dino today.** Shrubs have a median of 2.8 studs (0.4x a Compy), ground cover 2.9. Only 11% of shrubs are taller than a spawn Compy. The "huge ferns" feeling needs the Small band to be raised, not just kept.
- Trees of 62 studs and up are 4.7% of all tree-plus-giant placements, close to the owner's 5-10%, but only 12 of them (2.4% of the 491 placements of 12 studs and up) reach the proposed 80-stud colossal minimum; the 26-42 "larger" band is 19% (target 20-30%) and 42-80 holds 32 trees (6.5%) that the proposal removes.
- The camera adds no reason to look up: the aim stays near the floor (9 studs at `s = 4`, while a max T-Rex is 41) and the T-Rex fills 61% of the screen at all times.

## 4. Height chart (real numbers, 1 `#` = 2 studs)

```
DINOS (low-poly, playtest profile; s = growth scale)
Gallimimus spawn (s=1)             ## 4.9                    MEASURED
Compy spawn (s=1)                  ### 6.6                   MEASURED
T-Rex spawn (s=1)                  ##### 10.3                MEASURED
Compy mid (s=2, ~11 min)           ####### 13.2
T-Rex mid (s=2)                    ########## 20.6
Compy max (s=4, ~1 h)              ############# 26.4
T-Rex max (s=4)                    ##################### 41.2
T-Rex max BIG (s=4.8)              ######################### 49.4
(Brachiosaurus BIG ESTIMATE ~53)

WORLD TODAY (playtest, seed 1404)
Ground cover (max 4.8, p50 2.9)    ## 4.8
Shrubs (max 10.2, p50 2.8)         ##### 10.2
Hills (relief 9-13)                ###### 13
Trees p50                          ######## 15.8
Trees p90                          ############## 28.4
Trees max                          ##################### 41.9
Giants p50 (min 33.5)              #################################### 72.6
Giants max                         ################################################## 99.2
Highest peak (parameter ~80)       ######################################## 80

PROPOSED BANDS
Small (S) 4-12                     ###### 12
Medium (M) 12-42                   ##################### 42
Colossal (C) 80-140                ###################################################################### 140
```

## 5. Proposed height hierarchy (PROPOSAL, PROVISIONAL)

Derivation anchors: spawn dino 5-10 studs; mid dino (`s = 2`, about 11 minutes) 10-21; max dino 20-41; BIG max 24-49 (tallest planning value 53). The bands are chosen so each layer is passed at a different moment of growth.

| Layer | Height (studs) | Today | What it is | Passed by | Why this range |
| --- | --- | --- | --- | --- | --- |
| G0 Ground cover | 1-5 | 1.3-4.8 | grass, flower tufts, pebbles | `s` about 1 | unchanged; it is texture, not "jungle" |
| **S Small** | **4-12** | shrub 1.1-10.2 (p50 2.8) | ferns, bushes, flower clumps, mushrooms, horsetail, small palms | a Compy at `s` 2.0 (13 studs), a T-Rex at `s` about 1.2 | 0.6x-1.8x a spawn Compy (6.6) so a new dino is IN the plants; at max (26-41) they are 0.1-0.5x. Needs shrub scale about x2.2 (CODE `Scales.shrub` is x1.1-2.3) |
| **M Medium** | **12-42** | trees 5-41.9 (p50 15.8) | most current trees | a Compy at `s` about 4 (26) passes the lower half; only a T-Rex at max (41) matches the top | this is the visible "I outgrew the trees" band. Sub-band **M-low 12-26** (maxed Compy height) and **M-high 26-42** ("larger", maxed T-Rex height) |
| **C Colossal** | **80-140**, trunk 18-32 wide | giant 33.5-99 (p50 73) | ancient trees as landmarks, dedicated mesh family | never | at least 1.5x the tallest max-size dino (53) and 2x a maxed T-Rex (41). Trunk at least 0.8x the widest maxed body (T-Rex 5.6 x 4 = 22 wide, BIG 27) so it reads as MASSIVE next to it |
| Gap | 42-80 | 2% of canopy-class | nothing is placed here on purpose | | a clear jump makes colossal read as a different kind of thing, not as "a big tree" |

Colossal proportions (PROVISIONAL): height 80-140, trunk diameter 18-32 (about 1:4.5, a chunky storybook ratio, not a realistic redwood), canopy base 45 studs or more above the ground (a maxed dino can stand under the lower canopy), crown diameter 60-120, a root flare of 1.5x the trunk radius that is buried 2-4 studs on slopes.

**Mix (PROPOSAL, denominator = canopy-class placements, i.e. trees plus giants; understory and ground cover are counted by ratio instead).** Start 65% M-low (12-26) / 27% M-high (26-42) / 8% C. Today the canopy-class (trees and giants of 12 studs and up) is 72% in 12-26, 19% in 26-42, 6.5% in 42-80 and 2.4% at 80+ (section 3.3), so the change is: lift M-high from 19% to about 27%, remove the 42-80 band, and lift colossal from 2.4% to 5-8% (about 25-40 of roughly 490 placements; the lower bound is the 5% start). Small plants are counted as a ratio: at least 2 S-band plants per canopy-class tree (today 1,259 shrubs for 659 canopy-class, 1.9). The owner's wording is ambiguous about the denominator (Q4).

## 6. Placement rules (PROPOSAL; extends BiomePlacement, grammar version 3)

1. **New layer `colossal` replaces `giant`** (not additive): cell 60, slope at most 22 degrees, blocking, cap about 40 at density 1. The 48 giants (about 78 k triangles at the 1,630 ESTIMATE) become about 25-40 colossal plus M-high trees, so triangles and parts do not grow.
2. **Where:** outer zone only, as today (none within 150 studs of spawn, full strength 270 studs out). From the spawn meadow the nearest colossal tree is 160+ studs away: a 100-stud tree at 200 studs subtends about 27 degrees above the horizon, so a new player sees the skyline long before they reach it. Keep the spawn meadow open (handbook 3 "first egg in about 60 s" sight lines).
3. **Clusters and clearings:** colossal trees come in groves of 2-4 around the existing `Groves` centres (12 today) and a new `ColossalGroves` list (about 8-10 groves); minimum trunk spacing 1.2x the sum of the trunk radii plus 12 studs; inside a grove, medium and small plants thrive under the high canopy. **Clearings:** about 25% of the forest-field area stays free of canopy-class props: generate with the existing `field()` noise (value below a threshold gives a clearing of radius 25-50 studs), colossal trunks stay at least 20 studs outside any clearing centre. Clearings are where a giant dino has room and the camera sees the sky.
4. **Biomes:** conifer highlands (ancient conifer), fern forest (ancient broadleaf), marsh (ancient cycad/palm, optional), volcanic (a burnt dead trunk, optional). None in meadow (open sight lines) or badlands (open, rocky). Three silhouettes at least, readable from afar by outline: pointed conifer, round umbrella broadleaf, fan palm (the three families the tree-quality-test is redesigning).
5. **Corridors and keep-outs:** same path corridors (28-32 wide) and the hub approach keep-out; a trunk must be at least `trunk radius + 8` from any corridor centre-line edge. Nothing from the island kit may intersect `BiomePlacement.Sanctuary`.
6. **Grounding:** the current plant rule samples a 1-stud footprint (`min(1, 4% of size)`), which is meaningless for a 20-stud trunk. Colossal use the lowest of 5 rays at the trunk radius minus a 2-4 stud root flare embed (the rock policy of `PropGround`), and skip slopes over 22 degrees. They must pass `tools/qa/ground_probe` (handbook 8.1 item 4, BD-409) and `verify_world_overlap.py`.
7. **Understory ratio:** at least 2 S plants per canopy-class tree, scaled up per section 5 (`Scales.shrub` about x2.4-5.0, to be tuned on screenshots; ferns become 7-17 studs wide, so non-blocking overlap rules need a re-check).
8. **Determinism:** same seed gives the same layout; `BiomePlacement.Version` goes to 3; `tools/verify_world_art.py` and a new offline `tools/verify_vegetation_layers.py` assert the band shares in section 5, the 42-80 gap, the colossal minimum distance from spawn and the S-per-tree ratio.

## 7. Camera curve (PROPOSAL, PROVISIONAL)

Principle: the camera frames the BODY, not the scale number. Use the dino's real height `H` in studs (bounding box of the visual; until BD-471 lands, `H = H1(species) x VisualScale` with `H1` from the table, default 8). Keep it a minimum-zoom change plus aim and FOV, so the player keeps full control up to the existing 110-stud maximum.

```
smoothstep(x, a, b) = t*t*(3 - 2t), t = clamp((x - a)/(b - a), 0, 1)

f(H)   = clamp(0.38 + 0.17 * ln(H / 6) / ln(40 / 6), 0.38, 0.55)   -- share of screen height the body should fill
FOV(H) = 70 + 10 * smoothstep(H, 10, 40)                           -- degrees, vertical
k(H)   = 2 * tan(FOV(H) / 2)                                       -- 1.40 at FOV 70, 1.68 at FOV 80
D(H)   = min(60, H / (k(H) * f(H)))                                -- camera distance in studs (the new CameraMinZoomDistance)
Aim(H) = 0.40 * H                                                  -- look-at height above the floor; CameraOffset.Y = Aim(H) - rootHeight (about 3)
Elev   = rest 10 + 4 * smoothstep(H, 10, 40) degrees               -- default view angle above the aim (soft target, section 7.2)
ElevMax(H) = 80 + (20 - 80) * smoothstep(H, 12, 30)                -- hard cap: 80 (Roblox default) when small, 20 degrees by H = 30
```

Rationale: at `H` 6.6 (spawn Compy) the result is the same distance as today (12.1); the dino fills 0.38-0.55 of the screen, growing with size so a giant looks more imposing than a small one instead of constant; the distance cap (60) is never reached by a Compy and only binds for a BIG T-Rex; FOV widens to 80 at large sizes so a 100-stud trunk still fits above the dino. Distance grows about `H^0.8`, not `H^1`.

| Dino, size | H | Today D / fill | Proposed D / fill | FOV | Aim | Camera height at rest | Up-view limit above horizon |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| Compy s=1 | 6.6 | 12.0 / 0.39 | 12.1 / 0.39 | 70.0 | 2.6 | 4.7 | 25 |
| Compy s=2 | 13.2 | 24.0 / 0.39 | 20.8 / 0.45 | 70.3 | 5.3 | 8.9 | 25 |
| Compy s=4 | 26.4 | 48.0 / 0.39 | 33.1 / 0.51 | 75.7 | 10.6 | 17.6 | 26 |
| Compy BIG s=4.8 | 31.7 | 57.6 / 0.39 | 36.9 / 0.53 | 78.1 | 12.7 | 21.1 | 26 |
| T-Rex s=1 | 10.3 | 12.0 / 0.61 | 17.2 / 0.43 | 70.0 | 4.1 | 7.1 | 25 |
| T-Rex s=2 | 20.6 | 24.0 / 0.61 | 28.4 / 0.49 | 72.9 | 8.2 | 13.7 | 25 |
| T-Rex s=4 | 41.2 | 48.0 / 0.61 | 44.6 / 0.55 | 80.0 | 16.5 | 27.3 | 26 |
| T-Rex BIG s=4.8 | 49.4 | 57.6 / 0.61 | 53.6 / 0.55 | 80.0 | 19.8 | 32.7 | 26 |

At the normal end of a run (`s` 1.5, OWNER Q1) the proposed curve gives Compy D 16.6 (today 18.0) and T-Rex D 23.7 (today 18.0); the big differences only appear after `s` 2.5.

"Fill" is `H / (k x D)` for a level camera; "up-view limit" is half the FOV minus the rest elevation: how far above the horizon the top of the frame reaches. A 100-stud trunk 100 studs behind a maxed T-Rex has its top at about 24-27 degrees, just inside the limit; a 140-stud trunk does not fit and that is fine (the trunk is visible, the crown is not).

### 7.1 What changes in code (for BD-472, behind a flag `GrowthCameraCurve`, default false)

- `CameraMinZoomDistance` uses `D(H)` instead of `12 x s` (still rewritten from the existing 0.15 s heartbeat, but eased with the same exponential used for the lift, so growth never pops). `CameraMaxZoomDistance` stays 110.
- `Humanoid.CameraOffset.Y` uses `Aim(H) - rootHeight`.
- `FOV` eased to `FOV(H)` (Reduce Motion: snap per growth step, no easing).
- A pure module `Shared/CameraCurve.luau` (numbers only, like `CameraOcclusion`) plus `tools/verify_camera_curve.py`; `H` comes from a `VisualHeight` attribute the server already can compute, or the client bounding box.

### 7.2 Pitch cap (spike, higher risk)

The stock camera has no pitch-limit property; limiting needs either a copy of the PlayerModule with changed pitch constants or a post-camera `BindToRenderStep` that rotates the camera down toward `ElevMax(H)` around the focus point. Both are unverified here and could fight touch drag or cause jitter on phones. Treat it as a separate spike inside BD-472: ship distance, aim and FOV first (they need no pitch control), then add the cap only if it passes a phone drag test. The "rest elevation" is a nicety and is not required for the first version.

### 7.3 Things the curve must not break

- `CameraOcclusion`: it ignores everything farther than 80 studs from the dino (the cap 60 stays below that); it fades only props BETWEEN camera and dino, so background colossal trunks stay solid by design. Foreground colossal trunks (radius 9-16) will fade like other props; keep `MaxProps` 8 / `MaxParts` 40 and check a grove walk-through.
- Weather fog: soft visibility starts 25-100 studs from the CAMERA (docs/84). At D 45-60 the dino itself sits inside the fog start in rain (40) and blizzard (12). This already happens today (D 48 at `s = 4`). See Q9.
- Hub: the hub dino is `s = 1`, but a T-Rex now sits at D 17 instead of 12. Check the cave station cameras (docs/104) once.
- Reduce Motion: no easing, no extra shake.

## 8. Collision rules (PROPOSAL)

1. **Small layer (S, G0): never collide.** Already true (no collider boxes). A giant walks through them with no slowdown, no sound change.
2. **Medium trunks (M):** today they are solid boxes. A `s = 4` dino has a 10.4 x 12.8 torso collider; trunk spacing in a dense grove is often smaller, so a giant can wedge (not measured; BD-476 measures it). PROPOSAL "trample": when `VisualScale >= 3`, that dino's collision group changes to `DinoGiant`, which does not collide with the new `TrunkMedium` group (trunks of M-low and M-high). Colossal trunks stay solid for everyone. The group switch happens with the same attribute the camera reads, and Humanoid movement is client-simulated, so `MovementGuard` needs no change (verify). Optional soft feedback: a small leaf puff and a low rustle, behind Reduce Motion.
3. **Colossal trunks (C): always solid.** They are walls the giant walks around. The collider is a vertical capsule of boxes (3 boxes, tapered) up to the first branch height (45 studs), not the whole tree, so a max-size dino can stand under the lower canopy. Colliders are invisible, never culled (handbook 8.1 item 9).
4. **Corridors:** keep the 28-32 stud corridors; the widest maxed body is 27 wide (BIG T-Rex), so corridors are tight but passable.
5. **Terrain:** hills (9-13 studs) are below a maxed dino and no longer read as hills; the climbing rule (`MaxSlopeAngle` 46) is unchanged, so slopes still block steep walls for the torso collider. Only the 46-80 stud peaks stay larger than the dino (a maxed T-Rex is as tall as the lowest peak).
6. **PvP and bite range:** unchanged (root-to-root range scales with `s`). There is no hiding mechanic; do not add one in this work.

## 9. Performance budget (PROPOSAL; phone is the risk)

The phone scene is already estimated over the rule of thumb (about 551 k triangles against 250 k, docs/107, all offline), so the rule is: **net-neutral or better on parts and triangles, measured on a phone before the flag is on.**

| Budget | Value |
| --- | --- |
| Colossal count | about 25-40 at density 1 (replaces 48 giants), 5% start, tested at 8% |
| Parts | 1 MeshPart + 3 collider boxes each; no extra parts versus a giant (1 + 1) beyond +2 colliders |
| Triangles per tree | LOD0 at most 4,000 (within 150 studs), LOD1 at most 1,000 (150 studs and beyond). The existing generated meshes are about 1,630 (ESTIMATE) |
| Worst case in range on a phone | 6 colossal (1 at LOD0 + 5 at LOD1 = 9,000 triangles), against about 78,000 for today's 48 giants if all were in range |
| Material | opaque faceted low-poly canopy and bark, one shared texture atlas; **no alpha-card foliage** (mobile overdraw) |
| Draw distance | a 100-stud tree must not pop. `WorldCulling` gets a `Landmark` radius for colossal only: Phone 420, Tablet 560, Desktop 800 studs (the normal radius 190 / 280 / 440 is below the distance at which a 100-stud tree is still large). They count toward the part budget first |
| LOD | set `MeshPart.RenderFidelity` (Automatic on desktop, Performance on phones) on the uploaded meshes and test whether engine LOD is enough; if not, swap two meshes by distance in `WorldCulling` (LOD1 shell below 1,000 triangles). Both are to be verified in Studio; I did not test them here |
| Streaming | `StreamingEnabled` is off today and turning it on is a large separate decision (docs/107). Do NOT depend on it. Colossal trees are few, so replicate them at join |
| Memory | one shared mesh per silhouette (3 meshes), reused with scale, yaw and a 0.8-1.0 tint (the existing `BiomePlacement.tint`) |
| Fog and haze | far haze must keep a 100-stud silhouette readable at 400 studs (not a flat wall, handbook 6 and PR #302 "no haze in clear daylight") |

## 10. Interactions

- **Cave/hub:** the hub dino is `s = 1` (growth resets on entering the Sanctuary), so no giant enters the cave (ceiling 38-62 studs) and no colossal tree is needed there. docs/104 s2.1 says "a grown dino (s = 4) is about 12 studs long"; measured it is 26-45 studs long (T-Rex 11.3 x 4), a stale assumption to fix when that section is next edited. The cave approach keep-out (0, 400, radius 40) and `BiomePlacement.Sanctuary` stay clear of colossal trees.
- **Food and crystals:** a berry is 0.7-1.2 studs and an egg 1.5-2 studs; at `s = 4` that is 1/25 of a Compy and 1/40 of a T-Rex. Pickup reach is capped at 5 studs. Readability of food for giants is an open question (Q10), not changed here.
- **NPC predators:** drawn at x1.0-1.3 (BD-312) so a player of `s = 4` is 3x an NPC; unchanged.
- **FX (auras, trails, mutation rings):** sized by `VisualScale`; check they still read at FOV 80 and D 45-60.
- **Weather:** `WeatherVisuals` already scales volumes with camera distance (cap 6); with D up to 60 it reaches 3.75. Fog start is Q9.
- **Tree-quality test (already running, do not duplicate; its doc is docs/140-tree-quality-test.md, owner-approved scoped exception for the V3 trees):** branch `claude/tree-quality-test` (worktree `.claude/worktrees/tree-quality`, uncommitted, no PR yet) redesigns broadleaf, conifer and palm in Blender as `WorldKitV3_Trees.blend` and `assets/blender/world/fbx_v3/world_tree_{broad,pine,palm}_v3.fbx` (scripts `tools/blender/build_trees_v3.py`, `compose_trees_v3.py`). That work judges the style and quality of the MEDIUM trees. This spec does not touch it. The three colossal silhouettes (section 6, rule 4) should be built in the style the owner picks from that test (BD-474 depends on the verdict).

### 10.1 Awe cues (OWNER Q2: awe only; PROPOSAL for the details)

- **Size** is the main cue: the bands in section 5 and the camera in section 7 (a bigger share of the screen as the dino grows).
- **Footsteps:** a soft, heavier footstep that deepens with size (pitch down about 2 semitones per +1 `s`, volume inside the handbook 7 band of 0.15-0.35, at most 2 cues, never louder with size). Unheard until the owner listens. Own dino and nearby dinos only.
- **Shadow:** the contact shadow grows with the dino (PR #303 adds a dino shadow; check it scales with `VisualScale` instead of adding a second one).
- **Camera framing:** section 7.
- Not allowed: other dinos fleeing, wobbling or hiding, screen shake from footsteps, scary audio, growls. Reduce Motion: no extra camera motion.
These are small and are tracked as BD-478 (P3).

## 11. Colossal art (BD-474)

- Three families, one hero mesh each (ancient conifer, ancient broadleaf, ancient palm/cycad), 4,000 triangles at LOD0, 1,000 at LOD1, vertex-colour or one atlas, matte, palette from handbook 5.8 (Grass #84AA54, LeafyGrass #3E7C4E) with a warmer bark.
- **Why not a scaled-up current tree:** a 26-stud conifer scaled x4-5 has facets 4-5x larger, which looks like a toy model, the "miniature" feel. Colossal needs added structure at the new scale: a buttressed root flare, bark ridges, thick branch forks, hanging vines or moss ledges, a layered canopy with gaps, a few lit windows of sky. Silhouette first (readable at 400 studs), detail second.
- Pipeline (OWNER Q5, 2026-10-16): **Blender is allowed** for colossal and redesigned tree art. Handbook 8.1 item 1 still says never code-built for ordinary props, and the V3 trees are a scoped owner exception, so colossal art is hand-authored or generated in Blender, or generated with `generate_mesh` and then cleaned, decimated and LOD'd in Blender (BD-206 plan), whichever the owner likes on a screenshot in island lighting. Pivot at the bottom centre, a separate invisible collider, a [77](77-asset-registry.md) line per asset, no invented asset ids.

## 12. Test plan

Run in your OWN Studio copy (never `Place1.rbxl`, handbook 12), windows on screen 3 without stealing focus. Set size with the admin or `execute_luau` hook that sets `GrowthScore` on the character (`Dinosaur.addGrowth`), species with `SpeciesId`.

| Step | What | Pass |
| --- | --- | --- |
| T1 | **Measure first (BD-471):** `DinoVisual` bounding box of all 22 species at `s = 1` in both modes; real heights of the 14 generated tree/rock meshes after the `Arena` fit; default-camera screenshots at `s` 1, 2, 4 | the ESTIMATE rows in sections 3 and 5 are replaced by MEASURED numbers; band edges reviewed |
| T2 | **Gameplay-camera screenshots**, each at default zoom, in fern forest, conifer highlands (with a colossal grove) and a clearing: species Gallimimus, Compy, T-Rex, Brachiosaurus; sizes spawn (`s` 1), mid (`s` 2), max (`s` 4) and BIG max (4.8); from `tools/qa/capture_window.ps1` | per shot: dino fills 38-60% of the screen height; at mid and max at least one trunk is visible behind the dino in 80% of forest shots; at max the view never looks top-down (camera elevation at most 20 degrees once the cap exists); no shot where foliage hides the dino for more than 0.5 s of a 10 s walk |
| T3 | **Skyline from spawn:** screenshot from (0, 30) and a 10 s run toward a colossal grove at 22 studs/s | a colossal silhouette is visible from spawn; no pop-in (props appear by fade or distance haze, not suddenly) |
| T4 | **Walk-through at max size:** a maxed T-Rex walks the six corridors and the densest conifer grove | no wedge in 10 runs; with trample on, a rustle but no stop; with it off, record the stuck points (decides Q6) |
| T5 | **Budgets (Studio):** `tools/qa/budget_probe.server.luau` + `budget_report.py`, `verify_world_budget.py`, `verify_world_art.py`, `verify_world_overlap.py`, ground probe, new `verify_vegetation_layers.py` and `verify_camera_curve.py` | parts and triangles at or below the pre-change numbers; 0 grounding offenders; 0 overlaps; band shares as in section 5 |
| T6 | **Luminance band** with `tools/qa/luminance.py` in the same shots | island 0.35-0.75 (handbook 6.1) |
| T7 | **Phone:** emulate 844 x 390 landscape in Studio, then a real Android phone in the BD-085 pass: frame time, triangles, draw calls with 6 colossal in range, FOV 80, the touch drag with the pitch cap, culling radius | 30 fps floor holds; no hitch when `s` crosses 3; phone numbers recorded in docs/107; until measured the flag stays off |
| T8 | **Owner look:** the same T2 shots side by side with today's camera for Q7, Q8 | owner picks |

Not verified by this PR: everything. No Studio run, no phone, no sound; every number above is from source, docs or an offline placement run.

## 13. Conflicts with decisions and rows (listed as questions, NOT resolved)

| # | Existing statement | This proposal | Question |
| --- | --- | --- | --- |
| X1 | [87](87-vision-and-feel-guide.md) world line and handbook 8.1 item 3: "a grown dino still feels small next to big trees" | Medium trees are outgrown at `s` 3-4; only colossal stay taller | Q3 |
| X2 | D19 / BD-386 (docs/115): growth made 5x slower; HUD size bar full at about 500 food | "Gigantic at the end" needs a large `s` in a short run; a 5-minute run is only `s` 1.5 | Q1 - **RESOLVED by OWNER Q1 2026-10-16: pacing kept.** |
| X3 | BD-312 (NPC capped at x1.3 because big bodies "filled the camera") and BD-253 (foliage fills the screen and hides the dino); handbook 3 "in control, readable at a glance" | Huge dino fills up to 0.55 of the screen, trunks close to the camera | Q8 |
| X4 | Handbook 0 "friendly: nothing scary; calm" | Owner wants small players "intimidated" | Q2 - **RESOLVED by OWNER Q2 2026-10-16: awe only.** |
| X5 | D8 / D15 (docs/115): generated meshes only; AGENTS art rule: Blender models are TODO until owner uploads | The row asks for colossal tree art "in Blender"; the tree-quality-test builds Blender-scripted trees that the owner earlier called "3D Microsoft Paint" | Q5 - **RESOLVED by OWNER Q5 2026-10-16: Blender allowed.** |
| X6 | BD-049 (Review / test, P1): Blender world kit, grammar with a `giant` layer x2.4-4; BD-167 (Backlog, P1): even more vegetation, more kit pieces | `giant` is replaced by `colossal`; S plants become bigger, so counts may need to drop to keep parts | Q4 |
| X7 | BD-407 (Backlog, P2): numeric scale ladder table and verifier | This spec contains a first measured table; a shared Lua table and verifier are BD-471 | Q10 |
| X8 | Handbook 3 weather: "about 25-30 studs readable around the dino"; docs/84: fog starts 25-100 studs from the camera; D10 soft visibility | Camera sits 40-60 studs from a big dino | Q9 |
| X9 | docs/104 s2.1: "a grown dino (s = 4) is about 12 studs long" | measured 26-45 studs long | note only; fix when 104 is next edited |
| X10 | docs/91 and docs/107 phone budgets (culling radius 190, triangles already over the rule of thumb) | Colossal trees need a larger visible radius | Q12 |
| X11 | BD-164 (camera rattle; vertical low-pass 0.18 s) and BD-054/touch layout | Camera aim, FOV and possibly pitch change; must not bring rattle back | none; covered by T7 |
| X12 | docs/104 hub camera framing per station | T-Rex-class dinos get D 17 instead of 12 in the cave | none; one check in BD-472 |

## 14. Owner questions (Q1, Q2, Q5 answered; Q3, Q4, Q6-Q12 OPEN)

Each has the lead's recommendation; the owner decides. Asked via the dashboard "Needs you" or AskUserQuestion, not in updates (memory rule).

- **Q1. ANSWERED 2026-10-16 (OWNER): keep the current pacing.** A normal 5-minute run stays at about `s` 1.5; gigantic is a rare long-run reward. (Original question: today `s` is about 1.5, `s = 4` takes about an hour; options were keep, steeper early growth, or a higher cap. The lead recommendation (b) was NOT taken.)
- **Q2. ANSWERED 2026-10-16 (OWNER): awe only.** Size, footsteps, shadow and camera framing; no fear mechanics and no small-dino reactions (original options (b) and (c) dropped). See section 10.1.
- **Q3. Is the rule "a grown dino feels small next to big trees" still true?** (a) only for colossal trees (regular trees are outgrown), recommended; (b) keep it for all big trees, which means almost every tree must be 50+ studs and the spawn views change.
- **Q4. The mix.** Do 60-70 / 20-30 / 5-10 count canopy-class placements only (this doc: 65 / 27 / 8) or all vegetation? Start colossal at 5% and test 8% and 10%? Fewer, bigger groves or more, smaller ones?
- **Q5. ANSWERED 2026-10-16 (OWNER): Blender is allowed** for colossal and redesigned tree art; the V3 broadleaf, conifer and palm are a scoped owner-approved exception (docs/140-tree-quality-test.md). Which Blender route (generate then clean up, or hand-authored) stays a per-asset call judged on a screenshot.
- **Q6. Giant collision.** (a) trample medium trunks at `s >= 3`, colossal solid; (b) all trunks solid; (c) trample plus leaf puff and rustle. Recommendation: (c), with the T4 stuck-point data.
- **Q7. Camera risk.** Accept distance, aim and FOV 70 to 80 first; add the pitch cap only if the spike passes on a phone? Or ship distance and aim only? Recommendation: distance, aim and FOV first.
- **Q8. How much of the screen should a max dino fill?** Today Compy 39%, T-Rex 61%. Proposed 38% at spawn growing to 55% at max for every species. (a) accept; (b) fill less (closer to 45%) so the world shows more; (c) fill more.
- **Q9. Weather fog and the big camera.** Should the fog start be measured from the dino (camera distance plus the body length) so a giant is never inside the fog start? Recommendation: yes, a small change in `WeatherLooks`, but it changes the owner-tuned D10 look, so ask.
- **Q10. Scale ladder beyond dinos.** Fold BD-407 into BD-471 (shared table and verifier)? Should food, crystals and their glow grow with the dino (visual only) so a 40-stud T-Rex does not eat 1-stud berries? Recommendation: table yes, food scale decided after T2.
- **Q11. Hills and peaks.** A maxed dino is taller than the hills (9-13) and as tall as the lowest peak (46). Intended ("too big for the surroundings")? (a) yes; (b) raise terrain relief.
- **Q12. Colossal visibility radius on phones.** Larger cull radius for colossal only (420 on phones) at an unmeasured cost, or keep 190 and let them fade into haze (they would pop)? Recommendation: larger radius for colossal only, decided on BD-085 numbers.

## 15. Kanban rows and priority reasoning (revised after OWNER Q1, Q2, Q5, 2026-10-16)

Board position: P0 Backlog is the friends-playtest gate and the phone pass (BD-317, BD-085, BD-322, BD-293, BD-441); nothing here blocks them. The board's own pattern for the skins spec (docs/137 in open PR #297, BD-454..BD-459) is: spec acceptance P1, build P2 after friends session 1.

**What Q1 changes.** The owner KEPT the growth pacing, so a normal run ends at `s` about 1.5 (Compy 10 studs, T-Rex 16) and only sessions of 30+ minutes, potions or BIG dinos reach `s` 3-4.8. The original rows assumed the giant moment was the common end of a run. Honest cost/benefit per row now:

| Row | Before | Now | Why |
| --- | --- | --- | --- |
| BD-470 Spec acceptance (Q3, Q4, Q6-Q12 remain) | P1 | **P2** | Q1, Q2 and Q5, the questions that gated the most expensive work, are answered. The rest are polish decisions for rare moments |
| BD-471 Measure heights and write the scale ladder (absorbs BD-407) | P1 | **P2** | Still useful (the early-game height numbers, BD-407 was already P2), but nothing blocks on it any more and the phone pass (BD-085) measures budgets, not dino heights |
| BD-472 Camera curve (flag `GrowthCameraCurve`) | P2 | **P3** | At `s` 1.5 the curve changes the Compy camera by about 8% (D 16.6 vs 18). It matters most for large species at spawn (T-Rex fills 61% of the screen today, 43-46% proposed) and for the rare long run. Touches camera feel and BD-164 rattle for a small audience; do it only if the owner wants the T-Rex framing fixed |
| BD-473 Vegetation layers | P2 | **P2, scope reduced** | First slice is what EVERY run sees: raise the Small band (4-12, plants taller than a spawn Compy), clearings, remove the 42-80 stud gap, the band verifier, the `colossal` layer replacing `giant` using existing meshes. Colossal art and the M-high lift wait for BD-474 |
| BD-474 Colossal tree art | P2 | **P3** | Blender is allowed (Q5) so it is unblocked, but it is the most expensive row and the payoff is a landmark skyline plus a rare long-run moment. The 12 existing colossal-class trees (80+ studs) already give a skyline; do it after the V3 trees and an owner look at the new layout |
| BD-475 Colossal LOD, culling radius, phone budget | P2 | **P3** | Only needed once BD-474 exists |
| BD-476 Giant collision (trample) | P2 | **P3** | Applies at `s` 3 or more (about 30+ minutes). Do the stuck-point measurement inside BD-477 first; build only if a giant actually wedges |
| BD-477 Test pass | P2 | **P3** | Mostly closes P3 rows; the Small-band screenshots are part of BD-473's own acceptance |
| BD-478 (new) Awe cues for big dinos: size-scaled soft footsteps, shadow scaling check (OWNER Q2) | - | **P3** | Small and cheap, polish only; unheard sound needs the owner's ears |

Result: no P1 rows remain, 3 P2 rows (BD-470, BD-471, BD-473) and 6 P3 rows. Build rows stay Backlog until the matching questions are answered. None may displace P0 work, and none is Done without the T-steps evidence.

## 16. Handbook check (docs/114 s13)

- [x] Vision/feel: vibe words cross-referenced (friendly and calm vs "intimidating" is Q2); no screenshot, marked "not verified".
- [x] Design language: no art made; colossal proposal is low-poly faceted, matte, no alpha-card foliage.
- [x] Palette: biome greens from handbook 5.8; no new colour family.
- [x] Lighting: island bright; luminance gate T6; the cave is untouched.
- [x] Sound: only an optional soft rustle, "unheard", needs owner listening.
- [x] Asset quality bar (8.1): grounded (rule 6), no overlap, scale ladder (this doc), budget (section 9), pivot, collider, registry line (BD-474).
- [x] UI bar: no UI.
- [x] FX bar: none added; FX sizing check under section 10.
- [x] Economy numbers match handbook s9 (growth 0.1, cap 4, BIG 1.2; nothing changed).
- [x] Art rule: no code-drawn final art, flags default off, `Place1.rbxl` untouched, docs only.

## 17. BD-473 first slice: implemented offline (2026-10-16, Review / test)

Status: **CODE and offline verifiers only. No Studio look, no phone** (the lead takes the spawn screenshots from the gameplay camera, BD-473 acceptance). Branch `claude/bd-473-small-band`. Not changed: tree mesh ids (BD-462 V3 swap), tier files, `WorldCulling`, `EffectsLod`, camera, growth.

| Item | What the code does now | Where |
| --- | --- | --- |
| Small band | Every shrub (ferns, bushes, mushrooms, horsetail; the existing kit meshes) is sized from a TARGET HEIGHT of 4.2-12 studs (`u^1.5` skew, median 6.5), width capped at 18 studs. No Small-band plant within 34 studs of the spawn point and each keeps 0.55 of its half-width off the route edge. Tree-foot undergrowth uses the same sizing. The small trees and palms of the tree layer (about 4.7-12 studs) are unchanged | `BiomePlacement.SmallBand`, `smallScale` |
| Clearings | 20 glades, radius 32-51, 25.6% of the eligible forest-biome area (fern, conifer, marsh), greedy random order with a 0.9 spacing so they spread. No tree, colossal tree or fallen log inside; shrubs thinned to 35%. Each is clear of every route, keep-out (the BD-460 spawn meadow included), pool and grove core | `BiomePlacement.Clearing`, `clearings`, `inClearing` |
| No gap | Trees top out at 41.9 studs (26.2 x 1.6); colossal is 80-130; nothing vegetated between 42 and 80 | verifier |
| `colossal` | The old `giant` layer renamed (`WorldKit_colossal` attribute too), sized from a target height of 80-140 with a 100-stud crown cap, trees only (the spire and boulder giants are gone), none in meadow or badlands, none within 150 studs of the spawn. 31 placed (47 giants before), 8.5% of the canopy-class. `colliderReach` widens its keep-clear radius to the offset trunk box (a 1-pair overlap with a boulder showed up at x8) | `BiomePlacement.Colossal`, `colossalScale` |
| Version | `BiomePlacement.Version` 2 -> 3. The layout changes for everyone (same seed 1404, different placements) | |

Height histogram of the offline run (seed 1404, playtest density 1.25, vegetation only: tree, colossal, shrub; height = kit extent x scale, an upper bound):

```
studs      count
<4             0
4-6.6        642 ################################   (a spawn Compy is 4.4-6.6)
6.6-8        358 #################
8-12         359 #################
12-20        198 #########
20-26         64 ###
26-42         70 ###
42-80          0                                        (the gap)
80-100        20 #
100-140       11
shrub   n=1224 min 4.2 p10 4.4 p50 6.5 p90 9.5 max 12.0
tree    n= 467 min 5.0 p10 8.8 p50 15.6 p90 28.4 max 41.9
colossal n= 31 min 80.0 p10 84.5 p50 96.2 p90 117.2 max 129.6
```

Small band plants 1,359 against 363 canopy-class trees = 3.7 per tree (spec: at least 2); 53% of the band is taller than a spawn Compy. `tools/verify_vegetation_layers.py` asserts all of this (in CI).

Budget (offline estimator, before = main `d874050`): phone worst-spot scene **3,643 -> 3,434 parts, 557,976 -> 452,134 triangles**; details in [107](107-offline-mobile-budget.md). Net better because the clearings drop about 140 trees; the Small band itself is count-neutral.

Left for the lead and later rows: Studio screenshots at spawn from the gameplay camera (do the plants read as a jungle, not as clutter or a wall of green; do they hide food), a phone check (BD-085), a look at the facets of the x4.5-8 colossal stand-ins (expected to look toy-like until BD-474), the M-high lift (26-42 share) and colossal art (BD-474), the 65/27/8 mix check (the canopy-class is now 12-26: 72%, 26-42: 19%, colossal 8.5%), colossal LOD/culling radius (BD-475: beyond 190 studs a colossal tree still pops on a phone), collision (BD-476). Colossal grounding on the trunk radius with a root-flare embed (spec s6 rule 6) is NOT done: the existing 5-ray rule still places them.

