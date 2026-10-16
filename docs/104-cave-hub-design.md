# 103 The Cave: a big Sanctuary hub with real shops (design, 2026-10-16)

**Status 2026-10-16: Phase 1 first half built (BD-279 `src/shared/CaveHubLayout.luau` + `tools/verify_cave_hub.py`, BD-280 `Config.CaveHub=false` + one geometry source, both with the flag OFF so shipped behaviour is unchanged). The terrain shell (BD-281), props, travel and UI are NOT built. Every size, count and number here is PROVISIONAL.** Owner direction 2026-10-16 (verbatim intent below). Feel rules: [docs/87](87-vision-and-feel-guide.md). Copy and art rules: [docs/72](72-ui-copy-and-asset-standards.md). 3D model rule and art rule: [AGENTS.md](../AGENTS.md). Part budget and culling: [docs/91](91-world-performance-culling.md) (BD-168). Effect textures: `src/shared/EffectAssets.luau`. Tasks live only in [the Kanban](07-kanban.md) (BD-279 to BD-294 added by this doc; BD-254 is superseded by this plan).

Labels: **OWNER TARGET** = from the owner. **DECISION** = made by the lead on the owner's behalf, the owner may overrule. **CURRENT BUILD** = what ships now.

## 0. Owner direction (OWNER TARGET, 2026-10-16)
> The Sanctuary is a really small confined space that does not make sense. It should be a BIG CAVE: holes in the ceiling for natural light shafts, a lava waterfall, some moss, mostly stone and rocks on the floor. There must be ACTUAL SHOPS in it (potions shop, fusion, crystal/aura/trail style shop, egg nests, index/collection etc.): physical places the dinos walk to, with the space large enough that shops and areas are not cramped and dinos can walk around. When the player clicks a menu button (Potions, Fuse, Shop, Eggs/Nests, Index...) they TELEPORT to that place in the cave instead of just opening a menu; the menu belongs to the place. Anything that is a menu should be a physical place with 3D assets (statues, shop stalls/stands, signs, tables, counters, banners, lanterns, crates, etc.).

## 1. CURRENT BUILD (what this replaces)
- `src/server/Arena.luau` builds the hub as a `Sanctuary` model: `SanctuaryGround` 110 x 6 x 95 studs at `Config.SanctuaryCenterZ = 521` (past the north arena boundary, `ArenaHalfWidth = 416`), a flat `NestPlaza`, four `HubFence` walls, two trees, five cylinder `EggNest` parts and a `SanctuarySign` with a SurfaceGui. `src/server/Leaderboards.luau` moves the sign up and parents leaderboard boards to it.
- `src/shared/SpawnGeometry.luau` hard-codes the hub floor (`HubFloorY = 6`, half extents 55 x 47.5) and `hubPoint()`; `src/shared/BiomePlacement.luau` keeps `Sanctuary = {minX=-55, maxX=55, minZ=473, maxZ=569}` free of props. `tools/verify_spawn.py` checks these numbers.
- Run states on the character attribute `RunState`: `Sanctuary` -> `Active` -> `Ending` -> `Settled` -> (respawn in the hub, `RunLifecycle.prepareSanctuary`). `RequestStartRun` only works in `Sanctuary`; `RequestEndRun` only in `Active` (with the predator-nearby refusal). `FallRecovery.teleport` is the only server-side character move (it takes network ownership for 0.25 s to avoid the client race).
- The left rail (`Bootstrap.client.luau` ~line 1051) has six buttons: DINOS -> `collection`, EGGS -> `eggs`, FUSION -> `openFusion()`, SHOP -> `auras` (tabs: auras, trails, conditions, crystal eggs), POTIONS -> `potions`, SETTINGS -> `settings`. All open a modal over the HUD at any time, in the hub and during a run. The bottom-centre `HomeButton` is EXPLORE ISLAND in the hub and HOME (confirm, then `RequestEndRun`) in a run. `results` and `hatch` are modals that follow a run end; the hatch reveal is 2D/viewport UI.
- Hub props are never culled by `WorldCulling.client.luau`; the hub currently costs about 20 parts.
- PR #147 (BD-254, unmerged, `claude/sanctuary-polish`) adds `src/shared/SanctuaryDecor.luau` (pure decoration table, 150-part budget, generated statue/nest/egg meshes, kit bushes and flowers) and `tools/verify_sanctuary_decor.py`. Section 12 says what to salvage.

## 2. The cave in one picture (DECISION)
A wide, round-ish cavern, mostly grey-blue stone, lit by four warm light shafts from ceiling holes and the orange glow of a lava waterfall at the far end. The player arrives in the middle on a mossy stone plaza. Around the plaza, each menu is a real place: a potion stall under a shaft, a glowing fusion forge beside the lava, a crystal style shop in a crystal grotto, the egg nests in a warm alcove, a hall of dino statues for the Index, a quiet lantern nook for settings, a stone leaderboard wall, and the bright cave mouth that leads out to the island. Everything is calm, rounded and readable; the lava is cozy, not scary.

### 2.1 Footprint and coordinates
- The cave keeps the hub's place in the world: north of the island, centred on `x = 0`. **New `Config.SanctuaryCenterZ = 580`** (was 521) so the bigger floor clears the island terrain (`ArenaHalfWidth + 8 = 424`) and the north boundary ring rocks (`z = 421`).
- **Floor**: an irregular blob inside a 260 x 220 stud box: `x` in [-130, 130], `z` in [470, 690]. Floor top at **y = 6** (same `HubFloorY`, so `SpawnGeometry`, fall recovery and the respawn drop keep working). The floor is not flat: gentle 1-2 stud undulations, with every station pad and every path flat (slope < 8 degrees), so a WATER-class dino (docs/101: no jump) can reach every station.
- **Ceiling**: 38 studs high at the walls rising to 62 studs over the centre. Cave wall thickness at least 8 studs (nothing visible outside, no light leak except through the holes).
- **BiomePlacement.Sanctuary** becomes `{minX=-140, maxX=140, minZ=460, maxZ=700}` (nothing from the island kit may intersect it). The old box lies inside the new one, so nothing new is cut from the island.
- Scale reference: a grown dino (`s = 4`) is about 12 studs long; the cave is 20 dino-lengths across, so walks between stations take 4-8 s at hub walk speed and the space reads as big without feeling empty.

### 2.2 Zones (all sizes PROVISIONAL)
Offsets are from the cave centre `(0, 6, 580)`; `+z` is away from the island (deeper into the cave), `-z` is toward the island.

| Zone | Centre offset (x, dz) | Pad size (studs) | What it is | Menu it owns |
|---|---|---:|---|---|
| **Heart** (spawn plaza) | (0, 0) | 36 x 36 round | Mossy round plaza, the biggest light shaft straight above it, a low stone ring to sit on. Arrival point for respawns and the "Back to the middle" option. | none (HUD only) |
| **Island Gate** (run exit) | (0, -92) | 30 wide mouth | The bright cave mouth: daylight, a worn stone arch, two moss-covered boulders, the "ISLAND" sign. Walking through it or pressing EXPLORE ISLAND starts a run (the server moves the player to the island spawn as today). | EXPLORE ISLAND |
| **Egg Nests** (hatchery) | (62, -40) | 34 x 30 | A warm alcove: five stone nest bowls on a raised ledge, straw, a small warm shaft above, three hanging lanterns. The hatch reveal plays here. | EGGS (eggs, hatch, batchSummary, results "OPEN EGGS") |
| **Potion Stall** | (-64, -36) | 30 x 26 | A wooden market stall with a striped canopy, a counter with the four real potion models (docs/77 `potion_model_*`), crates, a hanging "POTIONS" board, bubbling cauldron prop. Second light shaft above. | POTIONS |
| **Fusion Forge** | (0, 72) | 40 x 34 | Right of the lava waterfall: a stone anvil-altar with a glowing ring on the floor (the fusion "wheel"), three stone pedestals for the ingredient preview, chains, embers. Lit by the lava. | FUSION (openFusion) |
| **Style Grotto** (crystal shop) | (74, 30) | 36 x 32 | A crystal grotto: big soft-glow crystals (lavender/teal), a stone counter with egg stands (Conditions tab eggs), a trail/aura "mirror" pedestal where the player's own dino preview shows the equipped style. | SHOP (auras, trails, conditions, crystal eggs) |
| **Hall of Dinos** (index) | (-78, 36) | 40 x 30 | A gallery: six statue plinths with small dino statues (existing `landmark_dino_statue` mesh scaled 0.4, plus new poses later), stone banners with species silhouettes, a big open "book" lectern. | DINOS (collection, detail) |
| **Lantern Nook** (settings) | (-34, 66) | 16 x 14 | A quiet corner with a bench, a lantern, a little gong (sound), a moss cushion. | SETTINGS |
| **Fame Wall** (leaderboards) | (40, 68) | 24 wide wall | The current leaderboard SurfaceGuis move here, onto a carved stone wall with a stone frame per board. | no rail button; walk-up only |
| **Lava Falls** | (-10, 100) back wall | 40 wide, 48 tall | The spectacle: lava pours from a crack 40 studs up into a round pool with stepping stones; the pool is fenced by low rocks so nobody can walk in (decorative, no damage; docs/87: gentle). | none |

Paths: a 12-stud-wide flat stone path from the Heart to every station (star shape) plus a 10-stud ring path linking neighbours; no station centre is closer than 48 studs to another. Loose rocks, stalagmites and moss patches sit between paths, never on them.

### 2.3 Spawn, respawn and the run exit
- **Spawn / respawn**: `SpawnGeometry.hubPoint()` stays the Heart centre `(0, 11, 580)`; the invisible `SpawnLocation` moves with it. After a run settles, the player respawns at the Heart as today, then the results modal shows. **DECISION:** "OPEN EGGS" on the results card teleports to the Egg Nests and opens the eggs screen there (same flow, new place).
- **Run exit (Island Gate)**: `RequestStartRun` unchanged (server checks `RunState == Sanctuary`, `DinoAttached`, world ready). Two triggers: the EXPLORE ISLAND button (works from anywhere in the cave, no teleport first) and walking through the gate's trigger volume (a `Touched`-free server-side distance check in the hub tick, 2 studs past the arch, with a 1.5 s "Leaving..." countdown ring that cancels if the player steps back; Reduce Motion shows a plain bar). No run can start from a station pad by accident.
- **Home during a run**: unchanged (`exit` confirmation, `RequestEndRun`, predator-nearby refusal). The cave never adds a second exit path.

## 3. How it is built (no code-built models)
AGENTS.md 3D rule: models are not built from code. The cave uses three kinds of pieces:

1. **Cave shell = Roblox Terrain voxels** (floor, walls, ceiling, ceiling holes, lava pool basin). Terrain is the engine's sculpting tool, not a model: it costs no parts, collides for free, casts real shadows (ceiling blocks the sun, holes let it through), and takes the `Rock`, `Basalt`, `Slate`, `Ground`, `Grass`/`LeafyGrass` (moss patches) and `CrackedLava` (pool) materials. **DECISION:** the shell is written by the server from a pure layout table (`src/shared/CaveHubLayout.luau`, like `IslandLayout` -> `IslandTerrain`) so the layout is testable offline and identical in every build; the owner may then hand-smooth it in Studio with the terrain tools and save it in the place file (a `CaveHubLayout.Baked = true` flag skips the server fill when a baked shell is present). Why not big generated shell meshes: generate_mesh outputs are single closed objects with one texture at about 4-10k triangles; a 260-stud shell would be too low in texel density and would need its own colliders. Rock mesh *pieces* on top of the terrain give the detail instead.
2. **Rocks, stalagmites, moss, crystals = generated meshes** (Roblox generate_mesh in the owner's Studio, published to the owner's account, listed in [docs/77](77-asset-registry.md), loaded through `ImportedResources.loadGeneratedWorld` into `ReplicatedStorage.GeneratedWorld` like the BD-206 props, with `rock_mossy_boulder`, `rock_pillar`, `rock_crystal`, `rock_lava`, `rock_pebbles`, `bush` reused where they fit). Each prop = 1 MeshPart (collision `Box` or `Hull`, never `PreciseConvexDecomposition`) plus at most one invisible box collider where the hull is wrong for walking.
3. **Station props = generated meshes** (stall, counter, crates, lanterns, banners, plinths, forge, cauldron, bench, gong, signs). Signs carry a `SurfaceGui` with the station name in the game font (text is UI, allowed). Potion bottles reuse the four published potion models.

Fallbacks (nothing is ever missing): an unloaded mesh keeps a plain invisible collider so paths stay walkable, and a station whose props failed still has its pad, sign and prompt. The cave flag (section 11) off = the current hub, untouched.

### 3.1 Part and triangle budget (phones, BD-168)
The hub is never culled (players stand in it with 11 others), so it has a hard budget of its own, checked offline:

| Group | Parts (max) | Triangles (max) |
|---|---:|---:|
| Terrain shell | 0 | voxels (measure; target under 1.5 M voxel faces visible from the Heart) |
| Rocks, stalagmites, stalactites, moss, crystals | 170 | 400 k |
| Station props (8 stations + gate + wall) | 120 | 300 k |
| Lava falls (sheet, pool, stones, emitters' parts) | 12 | 20 k |
| Lights, light-shaft cones, signs, prompts, pads | 48 | 10 k |
| Invisible colliders | 60 | - |
| **Total** | **410** | **730 k** |

Compared with the island's 7,400 parts (docs/91) this is small; what matters on a phone is the 12 player dinos plus effects, so the FX budget in section 5 is the real limit. `tools/verify_cave_hub.py` counts the layout table against these numbers; the Studio part count (`workspace.BeDinoArena.Sanctuary` descendants) is checked in the admin panel readout before acceptance. Phone target: 30 fps steady at the Heart with 12 players, measured on a real device (never claimed from Studio).

## 4. Lighting (soft, calm, docs/87)
- **Daylight through holes**: four round ceiling holes (radius 7, 5, 5, 4 studs) over the Heart, Potion Stall, Egg Nests and Style Grotto. With `Lighting.Technology = ShadowMap` (current) the terrain ceiling shadows the cave and sun comes through the holes; a **light-shaft cone** per hole (a generated tapered cone mesh, `ForceField`-free, `Transparency 0.86`, `Neon` off, warm cream colour, no shadows) makes the shaft visible. Dust motes: one small `ParticleEmitter` per shaft (`sparkSheet`, 4/s, tiny, slow). Reduce Motion: motes off, cones stay.
- **Fill**: the cave must never be dark (children, readability). Each station gets one warm `PointLight` (range 28, brightness 0.5, colour 255/214/170) hidden in a lantern or the shaft; the Heart gets two. `Lighting.Ambient` is global and shared with the island, so cave darkness is only the ceiling shadow; a `ColorCorrection` is **not** added for the cave (it would tint the island).
- **Lava glow**: three orange `PointLights` (range 36, brightness 0.45, colour 255/140/70) behind the falls and at the pool, plus a `SurfaceLight` on the pool face. The forge ring: one `PointLight` amber 0.35 range 18, pulsing slowly (period 4 s, amplitude 0.08; static under Reduce Motion).
- **Crystals**: `Neon` is too hard; crystals use `SurfaceAppearance`-free `Glass` material with a soft inner `PointLight` (lavender/teal, brightness 0.3, range 16).
- **Weather**: the cave is outside the island weather volume; `WeatherVisuals` already skips the hub by `Location == Sanctuary` (verify in BD-286); rain never falls indoors; aurora is visible through the holes (free, nice).
- Budget: at most 16 lights in the whole cave, none casting shadows except the sun.

## 5. Lava waterfall FX (existing textures only)
Textures come from `EffectAssets.Requested`: `flameSheet` (`rbxassetid://105817278245256`, 4x4 random frame), `smokeSheet` (`rbxassetid://109810080362045`, one-shot), `sparkSheet` (`rbxassetid://71657118485647`), `swirl` (`rbxassetid://84584423423015`, loop). No new texture is required for v1; a Blender "lava crust" tile is optional later (docs/77 line first).

| Layer | Piece | Settings (PROVISIONAL) | Phone |
|---|---|---:|---|
| Lava sheet | generated "lava fall" mesh (40 x 48 x 6, ripply front) | `SurfaceAppearance`-free, colour 255/120/40, `Material = Neon` **off**; instead `Glass` 0.1 transparency with an orange `Texture` whose `OffsetStudsV` scrolls 0.9 studs/s (TweenService loop); Reduce Motion: scroll stops, glow stays | 1 part |
| Pool | terrain `CrackedLava` basin + a flat `Glass` disc (0.35 transparency) with the `swirl` texture rotating slowly | rotation 0.1 rev/s | 1 part |
| Splash | `ParticleEmitter` at the pool rim, `smokeSheet` as steam, pale orange, 8/s, size 4-7, life 2.2 s, speed 2 up | 4/s |
| Embers | `ParticleEmitter`, `sparkSheet`, 6/s, size 0.3-0.6, life 3 s, drift up and toward the Heart (wind 0.5) | 3/s |
| Lip flames | `ParticleEmitter` on the crack, `flameSheet`, random frame, 5/s, size 2-3, `LightEmission 1` | 3/s |
| Heat shimmer | none (no distortion effects for this audience) | - |
| Sound | a quiet low bubbling loop (volume 0.18, through `Sfx.Master`), a brief for the owner; agents cannot hear it | - |

Total about 25 particles/s desktop, 10/s phone, all under one `LavaFalls` folder with an `FxBudget` attribute read by the admin panel. Nothing in the pool hurts a dino (the rim rocks block walking in; a hidden collider is the real fence).

## 6. Stations: menu -> place -> props
Each station is one entry in `CaveHubLayout.Stations` with: `id`, rail destination, pad centre and radius, **arrival spots** (six 3-stud points on the pad rim, section 9), sign text, the props list, and the UI it opens. Copy follows docs/72 (one or two words, big letters).

| Station id | Rail button / UI name | Sign text | Props (generated meshes unless noted) |
|---|---|---|---|
| `nests` | EGGS -> `eggs` (+ `hatch`, `batchSummary`, results "OPEN EGGS") | NESTS | 5 x `nest` (existing mesh 102765517629578) on a stone ledge, straw mat x5, lantern x3 (hanging), warm shaft cone, low rock fence x4, "NESTS" stone sign |
| `potions` | POTIONS -> `potions` | POTIONS | market stall (canopy + counter, one mesh), 4 potion models (docs/77), crate x3, barrel x1, cauldron with bubbles (`smokeSheet` 3/s, lavender), hanging board sign, lantern x2 |
| `fusion` | FUSION -> `openFusion()` | FUSE | forge altar (anvil-stone with glowing seam), floor ring (flat disc mesh, amber glow), pedestal x3, chain hooks x2, ember emitter (`sparkSheet` 4/s), "FUSE" iron sign, crate x2 |
| `style` | SHOP -> `auras` (tabs stay inside the UI) | SHOP | crystal cluster large x2, crystal cluster small x5, stone counter with 5 egg stands (Conditions preview eggs), mirror pedestal (a round stone plinth where the player's equipped aura/trail is shown on a dino statue clone), gem chest, "SHOP" crystal sign, lantern x2 |
| `index` | DINOS -> `collection` / `detail` | DINOS | statue plinth x6 with `landmark_dino_statue` at 0.4 scale (later: one statue per class, BD-294), stone banner x3 (SurfaceGui species silhouettes = existing dino icons), lectern "book" mesh, bench x2 |
| `settings` | SETTINGS -> `settings` | QUIET SPOT | bench, lantern on a post, small gong on a stand, moss cushion x2 |
| `fame` | (walk-up only) | TOP DINOS | carved wall frame x3 holding the existing leaderboard SurfaceGuis, torch-lantern x2 |
| `gate` | EXPLORE ISLAND (HomeButton) | ISLAND | stone arch (one mesh), mossy boulder x2 (existing), wooden arrow sign "ISLAND", flower patch x3 (kit `world_flowers_a`) |

**DECISION, Settings:** Settings keeps its rail button **and** gets a place; pressing it teleports like the others, because the owner said every menu is a place. The in-run settings (Reduce Motion, sound) stay reachable in a run through the same button without teleport (section 8). **DECISION, Fame Wall:** no rail button (not a menu today); the boards simply move from the old sign to the wall.

## 7. Teleport behaviour (server-validated)
New remote `HubTravel` in `BeDinoRemotes`, payload `{station: string}`; a `HubTravelResult` attribute on the player (`arrived:<id>`, `busy`, `not_home`, `unknown`) tells the client what happened. Rules, all enforced on the server in a new `src/server/HubTravel.luau`:
1. Only when `character:GetAttribute("RunState") == "Sanctuary"`, `ProfileState == Loaded`, `DinoAttached == true`, humanoid alive, and the player really is inside the cave footprint (`SpawnGeometry.inHub`). Any other state: ignored, `not_home`. A teleport can therefore never pull a dino out of a run, into a run, or across the island (no cheating out of a predator, no skipping the Home confirmation).
2. `station` must be a key of `CaveHubLayout.Stations`; rate limit one request per 0.8 s per player; a request during a pending fade is dropped (`busy`).
3. The move uses `FallRecovery.teleport` (ownership handoff) to a **free arrival spot** of the station (section 9), facing the station's sign. The player's `HubStation` attribute is set to the id (cleared when they walk more than the pad radius + 4 studs away, checked in the existing fall-recovery tick, no extra loop).
4. Camera: the client keeps `CameraType.Custom`; after the move it rotates the camera to the station's `cameraYaw` over 0.35 s so the stall is in view (Reduce Motion: instant). No cinematic camera, no zoom.
5. **Fade**: the client shows a short cream-coloured fade (0.18 s out, 0.18 s in) with a soft "pop" cue (through `Sfx`, quiet). **Reduce Motion: a single 0.08 s cross-dissolve, no cue.** The fade never blocks input for more than 0.5 s and never covers a modal.
6. **Walk there option** (DECISION): a Settings toggle "Teleport to shops: ON / OFF" (default ON). With it OFF, a rail button does not teleport: it draws a soft dotted **moss trail** on the floor from the dino to the station (a `Beam` with the `ribbonSoft` key fallback sprite, fading over 12 s) and shows a small "Walk to the Nests" toast; the station opens on arrival like any walk-up (section 8). Children who like to walk, and anyone who finds teleports confusing, still get there.
7. **Menu buttons during a run** (DECISION): no teleport is possible (rule 1). POTIONS still opens the potion menu during a run (drinking a bought potion mid-run is an existing feature) and SETTINGS still opens settings. DINOS, EGGS, FUSION and SHOP are shown **dimmed** in a run with a one-line hint "At home" when tapped; they do nothing else. This keeps runs free of shop modals (docs/87: one idea per screen) and makes "the menu belongs to the place" true. Open question 2 asks the owner to confirm.
8. Server log line per teleport (station, player, result) for the playtest; no DataStore writes.

## 8. UI at a station
- **Arriving by teleport**: the station UI opens as the fade clears (the same `open(destination)` / `openFusion()` as today, so every existing screen is reused unchanged). While it is open the dino stands at the arrival spot; the camera does not change.
- **Arriving on foot**: each pad has a `ProximityPrompt` on the sign (hold 0, action text = the station name, `MaxActivationDistance 10`, touch-friendly 96 px) **and** a dwell rule: standing inside the pad radius for 0.5 s opens the UI once (`HubStation` attribute changes on the client). Leaving the pad resets the dwell so walking past never spams menus.
- **Closing**: closing the UI returns full control at the same spot; nothing teleports back. A small "Back to the middle" chip appears on the HUD while `HubStation` is set (teleports to the Heart, same validation). 
- **Nests / hatch**: the hatch reveal stays the existing 2D/viewport sequence (5 s per egg, skippable); the nest alcove is the backdrop. Later (BD-294) the nest meshes can wobble in sync with the reveal; not required for v1.
- **Mirror pedestal (Style Grotto)**: while the SHOP UI is open, the player's own dino preview on the pedestal shows the aura/trail being hovered or equipped (client-only clone, no server state). Optional in v1.
- The rail marker (`ActiveTab`) already highlights the open destination; it also highlights the station the player is standing at.

## 9. Multiplayer (12 players)
- **No blocking**: in the hub, player characters use a collision group `HubDinos` that does not collide with itself (dinos pass through each other in the cave only; the island keeps today's collisions). Big dinos cannot wall off a stall.
- **Arrival spots**: six per station on the pad rim; the server picks the first spot with no other player within 3 studs, else the least crowded, else the pad centre. Players already on the pad are never moved.
- **No queues**: menus are per player and the stall never runs out of counter space, so nobody waits; the "ANY shop UI" is personal. Two players at one stall simply stand next to each other. Egg nests are per player too (each player sees their own eggs in the UI; the five nest meshes are shared scenery).
- Spawn protection is a run concept; the cave is a no-combat zone (docs/101 section 7) and `CombatService` ignores characters with `RunState ~= Active`.
- Teleport traffic: 12 players x at most 1 request per 0.8 s is trivial; `HubTravel` never replicates positions by itself (Roblox character replication does).

## 10. Accessibility and phones
- Rail buttons keep their size (172 x 54 at rail scale); dimmed in-run buttons stay at least 44 px tall on phones.
- Station prompts are large tap targets (ProximityPrompt UI at 96 px, or the custom prompt style if one exists) and the dwell rule means a child never has to find a button at all: walk up, it opens.
- Signs use the game font at 2+ studs letter height, readable from 40 studs; names are one or two words.
- Reduce Motion: no fade cue, no particle motes, no camera turn, no pulsing lights, static lava scroll. Everything is still identifiable by shape and colour.
- The cave floor is light grey-blue so dark dinos read; the lava side is warm, the crystal side cool: a child can tell where they are by colour alone.

## 11. Migration plan (feature flag, fallback)
- `Config.CaveHub = false` (new flag). Off: `Arena.build` builds the current `Sanctuary` model exactly as today, old `SanctuaryCenterZ`, old `SpawnGeometry` numbers; `HubTravel` is not created and the rail behaves as today. On: the cave.
- Geometry values that both paths need (`SanctuaryCenterZ`, hub half extents, floor Y) move into `CaveHubLayout.hub(config)` with the old values when the flag is off, so `SpawnGeometry`, `BiomePlacement.Sanctuary`, `Leaderboards.start` and `tools/verify_spawn.py` read one source. The old `SanctuarySign` is kept while the flag is off (`Leaderboards` reparents its boards to the Fame Wall when on).
- Saves: no profile change. `RunState`, settlement, nests and eggs are untouched; the cave only moves where the player stands.
- Build order: Phase 1 ships the flag and layout with the old hub still default; Phases 2-4 land behind the flag; the owner flips it in a playtest build after the Phase 5 device test. Rollback = flag off.
- Studio safety: `tools/verify_cave_hub.py` fails CI if any station pad leaves the floor blob, any two stations are under 48 studs apart, any path slope exceeds 8 degrees, a prop sits on a path, or the budget in section 3.1 is exceeded.

## 12. BD-254 and PR #147: superseded, what to salvage
BD-254 asked for "a rounder Sanctuary"; the owner's cave direction replaces that goal. PR #147 (`claude/sanctuary-polish`) stays unmerged and is closed as superseded; salvage into the cave:
- The **pure decoration table + offline verifier pattern** (`SanctuaryDecor.layout()` / `partCount()` / `tools/verify_sanctuary_decor.py`) becomes `CaveHubLayout` + `tools/verify_cave_hub.py`.
- The generated **statue / nest / egg** placements (ids 82545380144820, 102765517629578, 80664439797104) move to the Hall of Dinos and the Egg Nests alcove.
- Hidden-fence idea, flower patches and the "fallback to old nests if a mesh fails" rule.
- Its Studio evidence folder stays as history. The invisible fences and hedge ring are not carried over (the cave walls replace them). The box-dino half of BD-254 is already BD-225/BD-232 (low-poly species meshes).

## 13. Asset list (generate_mesh prompts, sizes, counts)
All are **Roblox generate_mesh in the owner's Studio**, matte low-poly, soft rounded forms, muted saturated palette, no text baked in (signs get SurfaceGui text). Size = fitted bounding box in studs (long side first). Each published asset gets a docs/77 line with its real id; never an invented id. Count = instances in the cave. Existing = already published.

| # | Key | generate_mesh prompt (short, ready to paste) | Size (studs) | Count |
|---|---|---|---:|---:|
| 1 | `cave_stalagmite_s` | "Low-poly cave stalagmite, rounded cone, grey-blue stone with faint teal moss at the base, matte, game asset" | 3 x 6 x 3 | 18 |
| 2 | `cave_stalagmite_l` | "Low-poly thick cave stalagmite cluster of three rounded cones, grey-blue stone, matte" | 7 x 12 x 7 | 8 |
| 3 | `cave_stalactite` | "Low-poly hanging stalactite, rounded tapering cone pointing down, grey-blue stone, matte" | 3 x 9 x 3 | 24 |
| 4 | `cave_rock_round` | "Low-poly rounded cave boulder, smooth lumpy grey-blue stone, matte" | 6 x 4 x 5 | 20 |
| 5 | `cave_rock_flat` | "Low-poly flat cave rock slab, rounded edges, grey stone with a bit of green moss on top, matte" | 8 x 1.5 x 6 | 14 |
| 6 | `cave_moss_patch` | "Low-poly soft moss patch, lumpy green cushion with tiny lighter tips, matte, flat underside" | 5 x 0.8 x 4 | 24 |
| 7 | `cave_moss_hang` | "Low-poly hanging moss curtain, soft green drooping strands, matte" | 4 x 5 x 1 | 10 |
| 8 | `cave_light_cone` | "Soft tapered cone volume, smooth, plain white, no texture detail, for a light shaft" | 14 x 40 x 14 | 4 |
| 9 | `cave_lava_fall` | "Low-poly lava waterfall sheet, rippled front surface, bright orange with darker crust streaks, matte emissive look" | 40 x 32 x 6 (BD-295: was 48) | 1 |
| 10 | `cave_lava_rim_rock` | "Low-poly dark basalt rim rock with glowing orange cracks, rounded, matte" | 5 x 3 x 4 | 10 |
| 11 | `cave_stepping_stone` | "Low-poly round flat stepping stone, dark basalt, rounded edge, matte" | 4 x 0.8 x 4 | 7 |
| 12 | `hub_stall_potion` | "Low-poly wooden market stall with a striped purple and cream canopy, wooden counter and two posts, cozy, matte, game asset" | 14 x 10 x 7 | 1 |
| 13 | `hub_cauldron` | "Low-poly round iron cauldron on three legs with purple liquid, cute, matte" | 3 x 3 x 3 | 1 |
| 14 | `hub_crate` | "Low-poly wooden crate, rounded edges, light wood, matte" | 2.5 x 2.5 x 2.5 | 7 |
| 15 | `hub_barrel` | "Low-poly wooden barrel with two bands, rounded, matte" | 2.5 x 3 x 2.5 | 3 |
| 16 | `hub_lantern_hang` | "Low-poly hanging lantern, round paper lantern with a warm glow, short chain, matte" | 1.5 x 2.5 x 1.5 | 9 |
| 17 | `hub_lantern_post` | "Low-poly wooden lantern post with a round warm lantern on top, matte" | 1.5 x 6 x 1.5 | 6 |
| 18 | `hub_sign_stone` | "Low-poly carved stone sign board, flat front face, rounded corners, grey, matte" | 8 x 4 x 1 | 8 |
| 19 | `hub_sign_arrow` | "Low-poly wooden arrow signpost pointing right, light wood, rounded, matte" | 5 x 5 x 0.8 | 2 |
| 20 | `hub_banner` | "Low-poly hanging cloth banner, soft blue with a cream border, slightly wavy, flat, matte" | 3 x 7 x 0.3 | 5 |
| 21 | `hub_forge_altar` | "Low-poly stone forge altar, a chunky rounded anvil-shaped rock with a glowing amber seam, matte" | 8 x 5 x 5 | 1 |
| 22 | `hub_forge_ring` | "Low-poly flat round stone ring with carved runes and an amber glowing groove, flat, matte" | 12 x 0.5 x 12 | 1 |
| 23 | `hub_pedestal` | "Low-poly round stone pedestal, rounded top, grey, matte" | 3 x 3.5 x 3 | 9 |
| 24 | `hub_counter_stone` | "Low-poly curved stone shop counter with five small round egg stands on top, grey-blue, matte" | 14 x 3.5 x 4 | 1 |
| 25 | `hub_crystal_l` | "Low-poly big crystal cluster, four soft-glow lavender and teal crystals, rounded tips, matte translucent look" | 8 x 12 x 8 | 2 |
| 26 | `hub_crystal_s` | "Low-poly small crystal cluster, three lavender crystals, rounded tips, matte" | 3 x 4 x 3 | 5 |
| 27 | `hub_gem_chest` | "Low-poly open treasure chest with soft-glow gems inside, rounded, matte" | 4 x 3 x 3 | 1 |
| 28 | `hub_lectern_book` | "Low-poly stone lectern with a big open book on top, rounded, matte" | 3 x 4 x 3 | 1 |
| 29 | `hub_bench_stone` | "Low-poly rounded stone bench, cozy, with a bit of moss, matte" | 6 x 2 x 2 | 4 |
| 30 | `hub_gong` | "Low-poly small bronze gong hanging on a wooden stand, cute, matte" | 3 x 4 x 1 | 1 |
| 31 | `hub_cushion_moss` | "Low-poly round moss cushion, soft green, matte" | 2.5 x 0.8 x 2.5 | 2 |
| 32 | `hub_wall_frame` | "Low-poly carved stone picture frame, rectangular, rounded corners, grey, matte" | 8 x 10 x 1 | 3 |
| 33 | `hub_gate_arch` | "Low-poly worn stone archway, rounded, with moss on top, cave entrance, matte" | 30 x 20 x 6 | 1 |
| 34 | `hub_straw_mat` | "Low-poly round straw nest mat, warm yellow, soft, matte" | 6 x 0.5 x 6 | 5 |
| 35 | `hub_nest_ledge` | "Low-poly curved stone ledge platform with a low back wall, grey with moss, matte" | 32 x 3 x 10 | 1 |
| - | existing: `nest`, `landmark_dino_statue`, `rock_mossy_boulder`, `rock_crystal`, `rock_pebbles`, `bush`, `potion_model_*` | docs/77 ids | - | 5 / 6 / 8 / 4 / 10 / 6 / 4 |

Totals: 35 new meshes, about 250 placed instances (within the 290 prop parts of section 3.1). Generate in three batches (rocks and moss, lava and lights, station props) so each batch is reviewed on a contact sheet before the next (same gate as BD-199). The mesh generator ignores "glow"; emissive looks come from lights and materials at placement.

## 14. Phased, kanban-ready task list (BD-279 to BD-294)
Everything behind `Config.CaveHub = false` until Phase 5 passes. Pure modules in `src/shared` with `tools/verify_*.py` tests (same pattern as `verify_sanctuary_decor.py`, `verify_spawn.py`).

**Phase 1, layout and shell (no visible change with the flag off)**
- BD-279 `CaveHubLayout` pure module: footprint blob, floor height function, ceiling, holes, stations (pads, six arrival spots, sign, camera yaw), paths, prop rows (key, position, yaw, scale), budgets. `tools/verify_cave_hub.py`: stations inside the floor, >= 48 studs apart, paths flat (<= 8 degrees), no prop on a path, every station reachable from the Heart on flat ground (WATER class), part/triangle budget, old hub numbers when the flag is off.
- BD-280 Flag + one geometry source: `Config.CaveHub`, `CaveHubLayout.hub(config)` feeding `SpawnGeometry`, `BiomePlacement.Sanctuary`, `Leaderboards`; `verify_spawn.py` and `verify_biome` style tests pass in both flag states.
- BD-281 Cave shell terrain writer (`src/server/CaveTerrain.luau`): voxels from the layout (floor, walls, ceiling, four holes, lava basin, moss patches), `Baked` skip; Studio evidence: screenshot from the Heart, part count, voxel count, walk from the Heart to every pad with a Compy and a (no-jump) Plesiosaurus stand-in.

**Phase 2, assets and atmosphere**
- BD-282 Mesh batch A (rocks, stalagmites, stalactites, moss, light cones; rows 1-8): owner generates with the prompts above, publishes, docs/77 lines, `WorldGeneratedMeshes.Assets` keys; contact sheet review.
- BD-283 Mesh batch B (lava and station props; rows 9-35): same flow; potion models reused.
- BD-284 Prop placement from the layout (`Arena` cave branch, generated meshes only, invisible colliders, fallbacks), admin "Hub parts" readout; evidence screenshots per station.
- BD-285 Lava falls FX: sheet scroll, pool swirl, three emitters with existing textures, lights, Reduce Motion variant, `FxBudget` attribute; sound brief for the owner (unheard by agents).
- BD-286 Lighting pass: holes + cones + dust, station fill lights, crystal lights, 16-light cap, check weather stays outside, before/after screenshots at the Heart and at the forge.

**Phase 3, teleports and station UI**
- BD-287 `HubTravel` server: remote, validation rules 1-3 of section 7, arrival-spot picking, `HubStation` attribute, rate limit; `tools/verify_hub_travel.py` (pure spot picking and validation table: in-run, ending, settled, outside hub, unknown station, rate limit).
- BD-288 Client travel: rail buttons call `HubTravel` in the hub, fade/cue, camera turn, Reduce Motion variant, open the UI on `arrived`, "Back to the middle" chip; results "OPEN EGGS" goes to the nests.
- BD-289 Walk-up and walk-there: prompts, dwell rule, Settings toggle "Teleport to shops", moss-trail beam; in-run rail behaviour (POTIONS and SETTINGS open, others dimmed "At home").
- BD-290 Island Gate: arch trigger with 1.5 s countdown and cancel, same `RequestStartRun` path; Home flow unchanged test (`RequestEndRun` refusal still works; no new exit).

**Phase 4, multiplayer and polish**
- BD-291 `HubDinos` collision group (hub only), six arrival spots under load, Fame Wall boards; Studio test with 4+ clients at one stall, then the existing multi-client script with 12.
- BD-292 Station signs and copy (docs/72), hub HUD tweaks (dimmed buttons >= 44 px on phones), ProximityPrompt touch size; phone-landscape screenshots.

**Phase 5, acceptance**
- BD-293 Real phone and 12-player test: fps at the Heart and the forge, memory, teleport round trips, Reduce Motion run-through; owner playtest by feel (docs/87 checklist); flag flip only after this passes.
- BD-294 Later polish (Backlog): per-class statues in the Hall, nests wobbling with the reveal, mirror pedestal live preview, Blender lava crust texture, ambient cave sound bed.

Dependencies: 263 -> 264 -> 265; 266 -> 268 <- 267; 268 -> 269/270; 264 -> 271 -> 272 -> 273/274; 271 -> 275; 272 -> 276; everything -> 277; 278 after 277.

## 14.1 Built so far and layout changes found by the verifier (2026-10-16)

**Studio QA 2026-10-16 (BD-281):** terrain occupancy is now `sd / Res` (Studio put the old floor at 8, not 6); ceiling holes are radius 12 / 8 / 8 / 7; cave-only terrain colours Cobblestone, Limestone (walls and ceiling) so the hall is warm, not dark teal; the lava recess is capped under the 38 stud back-wall ceiling (the 48 high sheet is BD-295); leaderboard boards stand behind the Fame station when the flag is on. Evidence: `docs/evidence/2026-10-16-cave-shell/`.
`tools/verify_cave_hub.py` (BD-279) found that the section 2.2 offsets broke their own rule, so the real layout in `CaveHubLayout` differs from the table above. The code is the source of truth; offsets are (x, dz) from the cave centre:
- Heart (0,0) r18; Island Gate (0,-80) r15 (was -92: pad left the floor); Nests (66,-38) r17; Potions (-66,-38) r15; Fusion (0,48) r20 (was 72); Style (84,34) r18; Index (-84,34) r20; Settings (-48,76) r10 (was (-34,66) r8: 34 studs from Fusion); Fame (48,76) r12 (was (40,68): 40 studs from Fusion). Smallest station gap is exactly 48.
- Lava pool is (-4,86) r11 with the fall sheet on the back wall at (-4,100); it was moved so no pad touches it and it stays inside the floor. Lava props trimmed to 6 rim rocks + 4 stepping stones so the lava group stays within its 12 parts.
- Floor blob: a gently wobbling squarish ellipse (125 x 105.5 base) inside the 260 x 220 box; pads and paths are exactly flat (max measured slope 1.8 degrees), the rest undulates 0..1.5 studs (max 14.6 degrees).
- Paths: 8 star paths (12 wide) plus an 8-segment ring (10 wide), ending at the pad edges. 6 arrival spots per station on the rim of the side facing the Heart, all facing the sign; props live on the far side.
- Budgets counted from the layout: 287 parts / 402 k triangles (limit 410 / 730 k); 239 prop rows; 15 lights counted for the 16-light cap.
- One geometry source: `CaveHubLayout.hub(config)` gives centre z, floor y, half extents and the biome rect. `SpawnGeometry` (so `FallRecovery`/`MovementGuard`), `Arena` and `Leaderboards.start` read it. Flag off = z 521, floor 6, half extents 55 x 47.5, biome 473..569, byte-for-byte as before (checked against a snapshot in `verify_cave_hub.py`). `BiomePlacement.Sanctuary` is still the old literal: nothing reads it at runtime and BD-281 must make it follow `hub(config).biome` when the flag is on.

- BD-281 (2026-10-16): terrain shell rules in `CaveTerrainRules` + writer `CaveTerrain` (flag off, no Studio evidence yet). `CaveHubLayout.Biome` is now {-150..150, 450..710} so the 12 stud rough shell fits; `BiomePlacement.useHub` applies it when the flag is on. The lava pool basin is terrain 2 studs deep, the `lava_pool_disc` prop would cover it. Cobblestone and CrackedLava get cave-only terrain colours.

- BD-286 / BD-295 / BD-296 (2026-10-16, flag off): lighting is `CaveLightingRules` (pure) + `CaveLighting` (server FX and lights) + `CaveAtmosphere` (client, only while inside). The shaft beams are plain 0.9 transparent cylinder Parts marked `IsLightingFx` (lighting FX, not model art; BD-282's cone mesh replaces them); lights sit on Attachments under Terrain (no extra parts); 16 lights in all; the gate arch light is 2.0 (the others 0.3-0.6). The lava sheet is now **40 x 32** (was 48) with a 26 high crack band, because the back-wall ceiling is only about 38-44 over the floor; `lava_pool_disc` is **18 wide** (the basin is 22) and **not walkable**. The cave wall stays Limestone, colour 196/172/150: Sandstone, Slate and Rock colours are the island's (set globally by BiomeMap), and Rock/Slate looked dark and cold in Studio. Evidence: `docs/evidence/2026-10-16-cave-lighting/`.

## 15. Open questions for the owner
1. **Cave size**: 260 x 220 studs with 48+ studs between stations. Big enough, or bigger (the island is 832 studs across)?
2. **Rail buttons during a run**: DECISION keeps POTIONS and SETTINGS usable in a run and dims DINOS, EGGS, FUSION and SHOP ("At home"). OK, or should every button simply be hidden in a run?
3. **Settings as a place**: the Lantern Nook (section 6). Fine, or keep Settings as a plain HUD menu with no teleport?
4. **Teleport default**: teleport ON by default with a "walk there" toggle. Or walk by default for first-time players, with teleport unlocked after the tutorial?
5. **Lava**: purely scenic (no damage, fenced by rocks). Confirm no "hot floor" gameplay.
6. **Station order around the plaza**: nests and potions near the entrance (most used), fusion by the lava, style shop in the crystal grotto, index opposite. Swap anything?
7. **Hatch reveal place**: keep the 2D/viewport reveal with the nest alcove as backdrop (v1), or should the physical nest crack open in the world (bigger task, BD-294)?

## 15.1 Answers (lead decisions, 2026-10-16; the owner may overrule)
1. Cave size: 260 x 220 is good.
2. In a run the rail dims DINOS / EGGS / FUSION / SHOP with "At home"; POTIONS and SETTINGS stay usable.
3. Settings stays a plain HUD menu button (not a teleport place) for quick access. The Lantern Nook station stays as a scenic spot; its `rail` is still "settings" in the layout but BD-288 must not teleport for it.
4. Teleport to shops defaults ON, with a Settings toggle.
5. Lava is scenic only (no hot floor, no damage).
6. Station order stays as built above.
7. Keep the existing 2D hatch reveal.

## 16. Lead decisions made on the owner's behalf (summary)
- Shell = terrain voxels from a pure layout (testable, phone-cheap), dressing = generated meshes only; nothing code-built is visible.
- One flag `Config.CaveHub`, old hub is the fallback, no save changes, teleports only inside `RunState == Sanctuary` and only via `FallRecovery.teleport`.
- Every rail button is a place; POTIONS/SETTINGS stay usable in a run; shop-type buttons dim in a run.
- Teleport default ON, with a walk-there toggle and walk-up prompts/dwell so no child needs the buttons.
- Lava is scenic, fenced, gentle; four warm light shafts; at most 16 lights; hub budget 410 parts / 730 k triangles; FX 25 particles/s desktop, 10/s phone.
- BD-254 / PR #147 superseded; its pure-table pattern and generated nest/statue/egg placements are reused.

## 16. Lead decisions on the open questions (2026-10-16, made on the owner's behalf; owner may overrule)
1. **Cave size:** 260 x 220 studs is good; revisit only after the 12-player phone test.
2. **During a run:** the rail dims DINOS, EGGS, FUSION and SHOP with "At home"; POTIONS and SETTINGS stay usable.
3. **Settings:** stays a plain HUD menu button for quick access (not a teleport place). The Lantern Nook is decoration only.
4. **Teleport:** shop teleport is ON by default, with a Settings toggle to walk there instead (moss-trail guide).
5. **Lava:** scenic only, fenced, no damage.
6. **Station order:** as in section 3 (Heart in the middle, shops around the ring); adjust after the first walk-through.
7. **Hatch reveal:** keep the existing 2D/viewport sequence in v1; a physical nest-cracking reveal is a later idea.
