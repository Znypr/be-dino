# 250 Biome overhaul and biome rotation (plan, 2026-11-23)

Owner 2026-11-23:
- "research different bioms and how popular roblox experiences show them, then plan different bioms and work with chatgpt to create a dashboard with a biome overhall, where different vegetation and atomosphere is created"
- Earlier the same day: "instead of having differnet biomes on the map, how about every few minutes - similar to steal an egg where there is night and everything is closed up and reset - we have an event where the map is updated from 1 biome to another, which mean during biome events different dinos are hatchable or so. like we go from a desert biome, to a quick storm, which updates the map to a jungle biome or so."

Status: PLAN, owner picks done (section 7). Colours, timings and boosts stay PROVISIONAL until Studio tuning. Board: the Design Board, Map page ("Biome overhaul").

## 1. What popular Roblox games do (research 2026-11-23)
Sources were web guides and wikis. Numbers they disagreed on are left out.

| Game | Biome model | Timed change | Tie to rewards |
|---|---|---|---|
| Grow a Garden | One plot, weather layered on top (rain, frost, blood moon, aurora) | Night about 10 min; rare weathers, some with a warning | Each weather gives a crop mutation with a sale multiplier |
| Steal an Egg | 9 biomes gated by speed (forest to cosmic) | Night every few minutes: countdown, then everyone is reset to the start | Eggs grow 30x faster at night; the farthest biome gives the best pets |
| Creatures of Sonaria | Named regions plus a global season cycle (about 2 min per season) | Weather about 5 min (rain, blizzard, heat wave, ash fall) plus disasters | Weather changes growth, egg speed and food; event creatures return later |
| Fisch | Islands; seasons of many hours, weather by chance | Rainbow follows rain; starfall is rare | Rare weather gives luck x10 or unlocks items; totems let players call weather |
| Adopt Me | Whole-map seasonal reskin (winter, Halloween) | Weeks | Event pets |
| Steal a Brainrot | Admin weather (lava, a red sky) | 15 to 20 min | Money multiplier |

Lessons we take:
1. **Reskin, don't rebuild.** Keep the layout, paths, plaza, cave, food spots and colliders. Swap terrain colours, vegetation, sky, fog, light and particles (Adopt Me).
2. **The change is an event.** A warning banner with a timer comes first, then a short storm hides the swap, then a title card (Grow a Garden warnings, Steal an Egg countdown).
3. **Kids should see 2 to 3 biomes per visit.** So a biome lasts minutes, not hours.
4. **Never lock a dino behind a missed biome.** A biome boosts its featured dinos. Every dino stays hatchable everywhere (Sonaria brings event creatures back).
5. **One icon and one short line per boost.** No x150 multipliers.
6. **Cheap first.** Atmosphere presets and terrain colours are cheap; a vegetation kit per biome is the expensive part.

## 2. The biomes
These are concept sheets from ChatGPT (`docs/evidence/2026-11-23-biome-overhaul/`). All are the same island in the same toy style.

| Biome | Look | Signature pieces | Weather pool | Featured dinos (proposal) |
|---|---|---|---|---|
| Sunny Meadow (home) | Warm golden light, flower fields | Round fruit trees, flowers, butterflies | clear, rain | Triceratops, Pachycephalosaurus, Compy |
| Jungle | Layered canopy, misty teal light, fireflies | Giant leaves, vines, ferns, mossy rocks, buttress trees | rain, thunderstorm | Raptor, Parasaurolophus, Brachiosaurus, Microraptor |
| Desert Canyon | Red-orange mesas and arches, hot haze, dust | Round flowering cacti, dry grass, bleached fossils, dunes | clear, heat wave, sandstorm | Stegosaurus, Gallimimus, Ankylosaurus |
| Frozen Tundra | Snow, ice crystals, cool blue light, snowfall | Snow pines, ice spikes, frozen pond, snow mounds | blizzard, northern lights | Therizinosaurus, Pteranodon, Ichthyosaurus |
| Volcano | Dark rock, glowing lava, ash, red-orange sky | Charred trees, lava streams, glowing crystals | volcanic bloom, earthquake | Tyrannosaurus, Spinosaurus, Baryonyx |
| Misty Swamp (rare special, later) | Purple-green dusk, fog, glowing mushrooms | Mangroves, lily pads, glow mushrooms | rain, blood moon | Elasmosaurus, Plesiosaurus, secret species |

## 3. Rotation
- **Order:** a fixed loop (Meadow, Jungle, Desert, Tundra, Volcano), so players can learn what comes next. The swamp shows up rarely, as a surprise (lesson 6 of the research).
- **Timing:**
  - Length: 8 min per biome.
  - Warning: 30 s before the change, "STORM INCOMING" with the next biome's icon.
  - Storm: 20 to 25 s, themed by where it is going (sandstorm into desert, blizzard into tundra, ash storm into volcano, warm rain into jungle, pollen breeze into meadow).
  - Title card: "JUNGLE TIME!".
- **Clock:** server time, the same on every server (`os.time()` modulo the loop). Then a player who rejoins lands in the same biome, and the HUD can show the time left.
- **Weather:** the existing weather events (docs/84) keep running inside a biome, drawn from that biome's pool.
- **HUD:** the existing weather chip becomes the biome chip: biome icon, name, time left, and the next biome icon.

## 4. What changes and what stays
| Changes per biome | Stays the same |
|---|---|
| Terrain material colours (`Terrain:SetMaterialColor`, instant) and a few material swaps (grass to sand or snow) | Island shape and height, paths, plaza, cave hub and shops |
| Vegetation visuals: each placed plant or rock slot shows that biome's mesh (`VegetationV2.visualFor(id, biome)` already takes a biome) | Placement positions and colliders, so collisions, food hosts and NPC paths never move |
| Sky, sun and ambient colour, fog, colour grade, bloom, particles | Food positions and food values |
| Ambient sound and music bed | Dino stats, growth and the economy |
| Featured dinos (hatch boost), biome egg look | Every dino hatchable everywhere |

Client-side swap: the server sets `CurrentBiome`, `NextBiome` and `ChangeAt` attributes. Each client swaps visuals in batches while the storm fog hides the island. One kit is visible at a time, so the phone part budget stays as it is today.

## 5. Atmosphere presets
ChatGPT proposed hex colours, fog, grade, bloom, particles and sound per biome. They are on the board and become `BiomeLooks` (a sibling of `WeatherLooks.luau`). Studio checks every preset against the readability rule: the near area (25 studs) stays clear.

## 6. Slices (backlog rows BD-1314 to BD-1318)
1. **S1, clock and atmosphere (BD-1314)** (cheap; it proves the feel): biome clock, HUD chip, warning and title card, the storm transition from the existing weather rigs, terrain colour swap, sky, fog and grade presets for 5 biomes. No new meshes.
2. **S2, vegetation kits (BD-1315)**: per-biome visuals for the existing slots (trees, bushes, cover, rocks), made in Blender, Hunyuan or generate_mesh from ChatGPT sheets. Coordinate with the tree-variety session (jungle kit first).
3. **S3, hatching (BD-1316)**: featured dinos per biome get a hatch boost (proposal: x2 chance), a biome badge on the egg card, and every dino stays available.
4. **S4, polish (BD-1317)**: storm sound and music per biome, biome food skins, landmark variants (snow-capped volcano, desert arch).
5. **S5, rare special (BD-1318)**: the Misty Swamp as a surprise biome with its own dino.

## 7. Owner decisions (2026-11-23, all four picked as recommended)
1. **Whole island** in one biome at a time. Today's five side-by-side zones go away once S1 ships.
2. **8 minutes** per biome.
3. **Featured dinos get a boost** (about x2 chance). Every dino stays hatchable in every biome.
4. **No reset:** the storm only reskins the island, and players keep playing where they are.
