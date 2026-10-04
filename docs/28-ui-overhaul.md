# Build 016: UI and model delivery rebuild

## Why Build 015 did not meet the brief

User screenshots show old procedural dinosaur and tree shells and a permission-error status. EditableMesh/Image data embedded in scripts is not equivalent to imported production art. Run end immediately restarted a run because no sanctuary state existed. The UI was text-heavy, low-contrast, and lacked item-art hierarchy. No claim of Studio verification was justified.

## Screen-by-screen checklist

Implemented means coded and packaged; every row still requires a Roblox Studio interaction check.

| Order | Screen or popup | Elements needed | Art/models needed | Implementation | Studio acceptance |
|---|---|---|---|---|---|
| 1 | Loading | Independent loading removal, profile/error messages | Existing logo/background binding | Existing loader retained | Join without indefinite load |
| 2 | Gameplay HUD | Growth, catches, location, return countdown, side rail | Dino, egg, Gold, sanctuary, shield, amber icons | Rebuilt | No overlap on desktop/mobile |
| 3 | Sanctuary | Equipped hero, safe hub, Explore action | Equipped dino, trees, nests, sign, home icon | New hub and Sanctuary state | End Run returns here; Explore begins once |
| 4 | Dino Index | Rarity cards, discovered count, copies, details | Compy, Triceratops, T-Rex | Rebuilt | Ownership updates after hatch |
| 5 | Dino details | Large 3D hero, rarity, copies, equip state | Same actual packaged dino model | New | Locked/equipped/owned states accurate |
| 6 | Gold Fusion | Selected Gold hero, copy progress, choose action | Gold dino, fusion icon | New | Requires 50 copies |
| 7 | Fusion confirmation | Explicit cost, result, confirm/cancel | Fusion icon | New | One server transaction, no loss on cancel |
| 8 | Growing Eggs | Five slots, live timers, empty/ready states, overflow | Egg model and egg art | Rebuilt | Timer updates without rebuilding previews |
| 9 | Hatch result | Actual committed reward, 3D dino, collection action | Dinosaur model, reward burst | New | Shows server result after commit |
| 10 | Return confirmation | Bank action, stay-still explanation, cancel | Sanctuary icon | New | Movement cancels channel visibly |
| 11 | Run results | Growth, catches, banked reward, sanctuary action | Trophy icon | Rebuilt | Reward updates after settlement |
| 12 | Food guide | Four values, cluster explanation | Berry/fruit visual, egg and crystal art | New | +1/+4/+15/+50 agree with server |
| 13 | Settings | Motion switch, camera reset, help | Shield/settings icon | New, session local | Motion switch disables tweens |
| 14 | Tutorial | Three visual steps, desktop/mobile controls | Numbered instruction cards | Rebuilt | One initial appearance, reopen from settings |
| 15 | Notifications | Growth gain, success/error, return cancellation | Shared styled toast | New | Authoritative status feedback |

## Component and asset checklist

Original reusable PNG icons: dinosaur collection, prehistoric egg, amber crystals, sanctuary hut, footprint trophy, Gold fusion, safety shield. Original component exports: dark panel, coloured header bars, action buttons, rarity cards, close control, progress frame, radial reward burst. Screenshots are archived separately under `resources/references/steal-an-egg`, never packaged into the place.

Runtime UI uses native GUI borders, gradients, patterned layers, FredokaOne outlined text, responsive scales, hover/press tweens, spring entrance, blur and real ViewportFrames. PNG icon art is compiled into a small merged 32px GUI tile representation for permission-free local preview. Full-resolution PNGs are provided for production Roblox image uploads; set logical `UITheme.ImageIds` to use crisp uploaded artwork instead of tiles.

## 3D delivery checklist

| Model | Purpose | Delivery |
|---|---|---|
| Compy | Common player/collection hero | Native triangle Model and OBJ/MTL |
| Triceratops | Rare player/collection hero | Native triangle Model and OBJ/MTL |
| T-Rex | Legendary player/collection hero | Native triangle Model and OBJ/MTL |
| Tree | Branched trunk, faceted layered crown | Native triangle Model and OBJ/MTL |
| Rock | Irregular solid-looking silhouette, separate collision | Native triangle Model and OBJ/MTL |
| Fern | Tapered leaf silhouette | Native triangle Model and OBJ/MTL |
| Egg | Food, growing egg preview | Native triangle Model and OBJ/MTL |
| Amber | High-value food crystal | Native triangle Model and OBJ/MTL |
| Berry, fruit | Model sources; cheap tiny pickups use native parts | Native model and OBJ/MTL |
| Sanctuary | Safe plaza, fence, nest row, sign | Server-authored native environment |

Native triangle models are original OBJ geometry baked into WedgeParts, packaged in ReplicatedStorage.Resources. They render without editable APIs or external asset permissions. They are not optimized MeshParts and have a higher instance cost. Production should import the provided OBJ/MTL as owned MeshParts; that retains the ResourceModels integration while reducing instances. No skeletal rig/animation has been authored. Mobile performance and visual appearance must be checked in Studio before marking production complete.

## Gameplay corrections

- Horizontal placement obstacle checks exclude Terrain so hills do not get rejected as props.
- Pickups are lifted above the surface and imported egg art is scaled to pickup size.
- FoodCount/FoodSpawnStatus expose startup failures rather than silently claiming success.
- A genuine Sanctuary run state is separate from Active. Entering or respawning after settlement starts in the sanctuary, and a validated RequestStartRun enters the island.
- Death and manual exit still use the same idempotent authoritative settlement path. Live save failures block progression.

## Required engine verification

1. Open the exported Build 016 place. Confirm packaged Resources contains ten Models before Play.
2. Join an unpublished test. Sanctuary UI and tutorial appear. Explore enters island once.
3. Inspect workspace FoodCount (>0) and visible berry/fruit/egg/crystal clusters, including slopes and map edges.
4. Collect each type and check growth. Confirm food behind obstacles is blocked.
5. End Run, stay still, verify banked rewards and physical sanctuary return. Move during return and check cancellation.
6. Repeat death, equip, hatch, duplicate requests and Gold fusion checks.
7. Resize to phone and tablet, inspect UI readability/touch controls. Profile with 8–12 simulated players.
8. Import owned MeshParts and full-resolution UI images before production art/performance signoff.

## Completed local validation

- 18 Python tests passed: economy/packaging/resource checks plus native geometry/alpha/reference separation.
- Official Luau parser accepted all 29 scripts.
- Actual Luau FoodService startup executed with raycast stubs: 1,536 valid pickups and terrain excluded from horizontal placement checks.
- Actual RunLifecycle executed with engine stubs: Sanctuary → Active → one settlement → Sanctuary, with malformed and duplicate requests rejected.
- Actual terrain/layout/movement/data modules passed numeric execution checks.

These tests validate source logic and delivery, not Roblox Studio physics, image rendering or device performance. Studio acceptance remains open in every screen row.
