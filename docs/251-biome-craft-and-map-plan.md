# 251 Biome craft: what a natural biome needs, and the map plan (2026-11-23)

Owner 2026-11-23: "study how biomes are built in video games, what types of vegetation, deco, stones, etc is overall needed for a lightweight but convincible, natural, cohesive and immersive map overall. based on yt videos and repos and online documents. study the current design language and vision of the be dino game. plan improvements to make great maps for different biomes, use chatgpt to come up with concepts and examples".

Status: **PLAN.** Nothing in the game changed. It is the craft layer under [250](250-biome-overhaul-and-rotation.md) (which biomes, the rotation, the atmosphere swap). Numbers marked PROVISIONAL wait for Studio and phone checks. Evidence: `docs/evidence/2026-11-23-biome-craft/`.

## 1. What research says (sources in section 10)

### 1.1 The layers every believable biome has
| Layer | Job | Rule |
|---|---|---|
| Hero / landmark | where am I, where do I go | One per view; 3 scales: big ones you steer by, mid ones block the view, small ones set the pace (Breath of the Wild "triangle rule") |
| Canopy trees | the biome's silhouette | 3-4 variants are enough for a forest (8 with dead and young ones) |
| Mid trees, trunks, dead trees | depth at eye level | Trunk density sells a forest more than canopy; dead trunks are cheap filler |
| Shrubs | hide trunk-to-ground seams, frame paths | at tree feet and path edges, never as lone balls |
| Ground cover | no bare floor in plant areas | forest floor = ferns and low leafy plants, not tall grass |
| Flowers / accents | one saturated accent per area | in drifts along edges, not dotted |
| Rocks S / M / L | geology, ground the scene | 2 main sizes plus pebbles that taper a pile into the ground; sunk into the terrain |
| Debris | life and story | logs, stumps, branches, bones, cones |
| Ground / terrain | does most of the work | 3 materials per biome in irregular patches; path shoulders; soil under crowns |
| Atmosphere, particles, sound | mood for free | per biome fog and light grade, one ambient particle, one sound bed |

### 1.2 Placement rules
- **Cluster, never scatter.** Tight groups of 3, 5 or 7 around one dominant piece, with bare ground between (Game Developer forests; Kingkade 3D Roblox building tips; ChatGPT). Even spacing is the number one immersion breaker.
- **Hero + satellites:** a big tree or rock, 2-4 smaller pieces around it at 2-7 studs (Unreal PCG hierarchical spawning; ChatGPT).
- **Nature's logic:** water first, then plants around it; rocks collect downhill and weeds grow at them; denser and taller plants in damp, sheltered low ground; bare windy ridges; plants tilt with the slope (Far Cry 5 world rules, Game Developer forests).
- **Edges:** blend ground and plant density over 8-15 studs where habitats meet; break clean path edges with 2-5 studs of dirt or gravel shoulder; keep trunks 6-8 studs off the main path (ChatGPT).
- **Negative space:** clearings and open ground are part of the design. Open share per biome in section 3.
- **Hide seams:** rocks sink 15-35 % into the ground; shrubs and ground cover hide trunk feet (80.lv chaparral). In Be Dino! the terrain is the ground: no baked discs or rings (section 2.2).
- **Variation:** random yaw, small leans (0-5 deg), independent width and height scale, 3 tints per mesh (70 / 25 / 5 %).

### 1.3 Cohesion
- One palette per biome, one shape language for the whole game (chunky, rounded toy), shared leaf and bark looks across a kit (Far Cry: all trees shared leaf atlases and one bark).
- Warm foreground, calmer and cooler background; contrast at the focal point (80.lv chaparral, Game Developer composition).
- Each region its own colour story: green pastoral, icy blue, warm gold desert (Genshin).
- "If you can get away with 23 trees, don't make 25" (Firewatch, GDC): fewer, better assets.
- Swap the signature plant per area so places feel different (80.lv chaparral).

### 1.4 Lightweight tricks (Roblox)
- Official budget guidance: under 1,000 draw calls and 1,000,000 triangles on the baseline device; reuse meshes and textures; resize, rotate and overlap for variety (Roblox performance docs). Ours is tighter: phone about 3,000 parts and 250 k triangles in range (docs/114 s8, docs/107).
- `Terrain:SetMaterialColor` recolours a material instantly; custom terrain material slots (Expanded Terrain, up to 62) give each biome its own ground looks. Unclear whether `SetMaterialColor` tints custom slots: test in Studio first.
- Atmosphere (Density, Haze, Color, Decay, Offset) replaces the Lighting fog; one fog system only.
- SLIM far-distance models cut triangles and draw calls but need static models: they do not fit meshes swapped at runtime. Use SLIM only for pieces that never swap (cliffs, horizon), or one static set per biome.
- One cluster = one mesh (a grass clump, a pebble group), not 10 parts. Collisions only on trunks and big rocks. Shadows off on tiny pieces.

## 2. Be Dino! design language today

### 2.1 The rules we keep (handbook)
- Feel: "calm, bubbly, friendly, and a little magical" ([87](87-vision-and-feel-guide.md)). Friendly low-poly, soft rounded forms, saturated but harmonious, no muddy greys; dinos and food are the heroes; 25-30 studs around the dino stay clear in any weather.
- World rules W1-W9 ([241](241-world-redesign-proposal.md)): rounded island, plaza in the middle with sand paths, readable zones, one landmark per zone, clumps with open grass, no halo discs, clear daylight.
- Owner art rules 2026-11-23 ([250](250-biome-overhaul-and-rotation.md) s8): everything grows from the ground; no pots, stands, base plates, stone rings, pebbles or grass discs at plant feet; no painted fire or glow in meshes (glow = lights, Neon, particles); desert and volcano sparse, jungle dense and layered, tundra in pine stands.
- Final art is made in Blender, by generate_mesh / Hunyuan from approved sheets, or by the owner; never code-built ([CLAUDE.md](../CLAUDE.md), docs/114 s8.1).

### 2.2 Where the island stands (Studio, `docs/evidence/2026-11-23-map-relief/before-after.jpg`)
Good: readable sand paths, bright friendly colour, the toy plant family (VegetationV2, 19 meshes), rolling hills (BD-1309), tree ages from sapling to giant (BD-1309), soft pines (BD-1311).

ChatGPT art-director score: **5.5 / 10** (target for the approved concepts 8.5-9). Ranked problems, checked against our own pictures:
1. **One flat neon-green ground** everywhere: no soil, gravel, sand margins or darker ground under trees.
2. **Polka dots:** props spread evenly; few real groups, few empty areas.
3. **Trees look like separate toys:** trunks stand on the grass with no roots, ground cover or rock at the foot; similar silhouettes.
4. **No geology:** no outcrops, low cliffs or banks; the only rock mass is the volcano.
5. **Weak framing:** giant trees fill the foreground; no one dominant silhouette per view.
6. **Paths and horizon:** clean hard path edges; the sea horizon is empty and the island edge reads flat from the air.

Our own extra finding: the placement grammar ([BiomePlacement](../src/shared/BiomePlacement.luau)) already has clump fields, groves, clearings and per-biome weights, so items 2 and 5 are tuning plus a cluster rule, not a rewrite. Items 1, 3, 4 and 6 need terrain work and a few new shared meshes.

## 3. The biome recipe (one table per biome, PROVISIONAL)
Densities = placed pieces per 50 x 50 studs away from the plaza and main path (averages, placed in clusters, never evenly). Open = share of visually open ground. "V" = visual variants (tint, scale, combos), not new meshes. Target per biome: 8-14 biome meshes plus the shared core kit (section 6). Source: ChatGPT kit tables, cut to our rules; the full answer is in the evidence folder.

| Layer | Sunny Meadow (open 40-55 %) | Jungle (open 15-25 %) | Desert Canyon (open 65-80 %) |
|---|---|---|---|
| Hero (0-1) | ancient orchard tree; mossy waterfall ledge | giant banyan with roots and vines; mossy waterfall cliff | sandstone arch; mesa pillar |
| Canopy | fruit dome tree, wide oak (1-3) | giant broadleaf, umbrella tree (3-6) | flat acacia, oasis palm (0-1) |
| Mid tree | young fruit tree, round birch (2-4) | curved jungle palm, young jungle tree (3-5) | blooming cactus, twisted mesquite (1-2) |
| Shrub | berry bush, leafy mound (4-7) | fern bush, flower shrub (6-10) | prickly pear, sage mound (2-4) |
| Ground cover | grass tuft cluster, low broadleaf (10-18) | big fern clump, heart-leaf plant (12-22) | dry grass fan, low agave (2-5) |
| Accents | daisy drift, wildflowers (8-15) | hibiscus, orchid spray (5-10) | cactus bloom, desert daisy (1-3) |
| Rocks | pebble group, mossy boulder, 3-mass outcrop (3-6) | moss pebbles, wet boulder, root-wrapped outcrop (4-8) | red pebbles, sandstone stack, eroded boulder (5-9) |
| Debris | fallen twig, leaf litter (2-4) | mossy fallen trunk, leaf litter (4-7) | dry driftwood, tumbleweed (2-4) |
| Ground | green grass, brown soil, golden sand margins | moss green, dark moist soil, grey-green rock | golden sand, terracotta sandstone, gravel |
| Signature | open meadows ringed by orchard groups, flowers at wood edges | tall canopy groups, roots, vines, big ferns; deep but never a solid wall | giant rock silhouettes, wide sand, plants sheltered by rocks |

| Layer | Frozen Tundra (open 45-60 %) | Volcano (open 65-80 %) | Misty Swamp (open 30-45 %) |
|---|---|---|---|
| Hero (0-1) | ancient snowy pine; frozen waterfall | low friendly cone; stepped basalt cliff with a real lava channel | giant swamp tree; root arch over a channel |
| Canopy | snowy pine, frosted spruce (2-5) | sparse red-leaf tree, regrowing charred tree (0-1) | drooping swamp oak, tall cypress (2-4) |
| Mid tree | young snow pine, frost birch (1-3) | twisted burnt tree, short charred tree (1-2) | young mangrove, leaning cypress (2-4) |
| Shrub | snowberry bush, low juniper (1-3) | red-leaf bush, dark leathery shrub (1-3) | pillowy wet bush, cattail thicket (5-8) |
| Ground cover | snow grass, frost moss (3-6) | ash grass, green regrowth tuft (1-4) | lily pads (water only), wet sedge (8-14) |
| Accents | violet winter flower, ice crystal cluster (2-4) | orange flowers, amber crystals (solid, lit by lights) (1-3) | violet mushrooms, swamp orchid (4-8) |
| Rocks | snowy pebbles, slate boulder with snow cap, icy cliff slab (4-7) | basalt pebbles, fractured boulder, lava-channel outcrop (7-12) | wet pebbles, half-sunk boulder, flat slab (2-5) |
| Debris | pinecones, fallen snowy branch (1-3) | charcoal log, cooled slag (2-5) | half-sunk log, leaf raft (4-7) |
| Ground | powder snow, pale ice, cold grey rock | charcoal basalt, scorched soil, warm ash | dark wet soil, muted moss, shallow water |
| Signature | pine stands with snow under them, wide open snowfields, ice by the water | dark rock with a few orange light pockets, green life returning | rooted trees on banks, dark water, soft purple mushrooms, a dry readable path |

Desert and volcano carry 35-50 % fewer pieces than the jungle and fill space with bigger formations, not scatter.

## 4. Placement recipes per biome
| Biome | Clusters | Slope, clearing and path rules |
|---|---|---|
| Meadow | orchard groups of 3 / 5 trees, 5-7 shrubs or flowers at their edges; one big tree anchors each clearing | flowers along paths and tree lines, open grass in the middle; soil patches under big crowns |
| Jungle | interlocking groups of 5 / 7 / 9: one big canopy tree, 2-3 smaller trees, dense fern satellites | tall trees on raised ground, ferns in low sheltered spots; no vines lower than about 7 studs over a path |
| Desert | plants alone or in 3s; rocks in groups of 3 / 5; the mesa or arch is the hero | rocks on ridges and outer path bends; cacti on the sheltered side of rocks; wide open sand flats near the plaza |
| Tundra | pine stands of 5 / 7 / 9 mixing ages; lone ancient pines at clearing edges | bare windy ridges; snow drifts against trunks and rocks are terrain, not mesh discs; ice near water |
| Volcano | rock groups of 3 / 5 / 7 around one dark formation, a few crystals and hardy plants | big formations on high ground and the island edge; glow only in a few pockets; no lava on paths |
| Swamp | rooted trees in 3 / 5 along water, 5-7 wet plants at their feet | mangroves on banks and low ground; lily pads only on water |

Because the whole island changes biome at once (docs/250 s7), edges are between **habitats inside one biome** (bank, ridge, path shoulder, clearing), not between biomes: the same shore becomes a beach, a jungle estuary, an oasis, a frozen shore, a volcanic coast or a wet bank.

Mapping to the code we have:
- Clumps, groves, clearings, per-biome layer weights and tree growth exist (`BiomePlacement`, `VegetationV2.TreeGrowth`). Keep our tree growth (0.45-2.6x, BD-1309, owner asked for size variety) over ChatGPT's narrower 0.85-1.2x.
- New: a **cluster rule** (hero + satellites in odd groups), **per-biome slot occupancy** (a desert hides most slots), a **tint variant** per placement, and **path shoulders** as a terrain layer.
- Occupancy has a catch: docs/250 keeps colliders per slot. A slot hidden in the desert must also drop its collider (the biome is global, so the server can switch it), or players hit invisible trees. Food hosts (BD-1238) must stay on visible slots: the food map is regenerated per biome or hosts fall back to open ground.

## 5. Terrain and atmosphere (feeds BiomeLooks, BD-1314; PROVISIONAL)
ChatGPT targets read from the approved concepts, not engine samples. Every preset still passes the 25-stud clear-view rule and the docs/114 "no milky daylight" rule in Studio.

| Biome | Terrain (3 materials) | Sky / fog / ambient | Particle | Sound bed |
|---|---|---|---|---|
| Sunny Meadow | grass #6DCF59, soil #B98959, sand #F3D795 | #83D8FA / #D4F3FC / #B3CDAA | a few butterflies | birds, breeze |
| Jungle | grass #3DAE68, soil #654B37, rock #647F65 | #75CBB7 / #9DCEC1 / #83A69A | floating motes | tropical birds |
| Desert Canyon | sand #EBC17B, sandstone #CB7951, gravel #B99A73 | #8DC9F2 / #F6D8B1 / #D4B091 | dust specks | dry wind |
| Frozen Tundra | snow #E9F4FF, ice #A9D9F0, rock #A9BAC4 | #AEDCF8 / #D9EAF4 / #AABACB | light snowflakes | winter wind |
| Volcano | basalt #49434A, scorched soil #73534B, ash #83706F | #D89B83 / #BD8D7E / #AE7C70 | ash flecks | distant rumble (soft) |
| Misty Swamp | mud #6D6250, moss #66856A, rock #4B5650 | #B7C3C8 / #A6B6B7 / #8E9D93 | spores | frogs, water |

Ground variation needs **painted material patches** (soil under crowns, gravel shoulders, sand margins, rock on slopes over about 30 deg), not only a colour swap. The patch masks are baked once (WorldLayer) and each biome maps the same three masks to its three materials.

## 6. Shared core kit (biggest jump for the least work)
Ranked by ChatGPT, checked against our gaps. Each piece serves every biome through tint and a biome variant.

| # | Piece | Fixes gap | Note |
|---|---|---|---|
| 1 | Modular low cliff / embankment, stepped, buried lower edge | 4 geology | static: a SLIM candidate |
| 2 | Buried outcrop, 3 joined rock masses | 4, 2 | anchors plant clusters |
| 3 | Tree root flare as part of each tree mesh (roots taper into the soil) | 3 | part of the trunk, never a disc |
| 4 | Second mid-height tree, irregular crown, narrow trunk | 3, 5 | per biome variant |
| 5 | Grass tuft cluster, bent blades, one mesh | 1 | replaces bare ground, cheap |
| 6 | Asymmetric shrub (two unequal masses) | 2 | breaks the ball look |
| 7 | Fern / broadleaf ground cluster | 3 | jungle, meadow, swamp floor |
| 8 | Pebble group, 5-9 stones, no base | 1 | on path shoulders and rock feet only, never at a plant foot |
| 9 | Fallen trunk / branch | 2 | debris for every biome |
| 10 | Distant ridge and sea-stack silhouettes | 6 horizon | static, low detail, a SLIM candidate |

First batch: 1, 2, 5, 8 plus the terrain patches. The tree root flare (3) goes into the tree remodel of BD-1311.

## 7. Concepts
- `docs/evidence/2026-11-23-biome-craft/jungle-vs-desert-chatgpt.png`: the same path as a layered jungle and as a sparse desert canyon (ChatGPT concept, not Roblox output).
- The approved six-biome look stays `docs/evidence/2026-11-23-biome-overhaul/biome-grid-chatgpt.jpg`.

## 8. Plan (board rows)
Order: systems before meshes (ChatGPT and the research agree: terrain and placement beat 30 more props).
1. **BD-1320 Ground patches:** baked soil / gravel / sand / slope-rock masks and path shoulders on the World V3 island, mapped to 3 materials per biome; test whether `SetMaterialColor` tints custom slots. Before/after from the three docs/241 cameras.
2. **BD-1321 Cluster placement:** hero + satellite rule in odd groups, per-biome open share and slot occupancy (with colliders and food hosts), 3-tint variants per placement. Food maps regenerated. Phone part count before/after.
3. **BD-1322 Shared core kit batch 1:** outcrop, low cliff, grass tuft cluster, pebble group (section 6 items 1, 2, 5, 8) from a ChatGPT sheet via the generate_mesh / Hunyuan routes, close-up check per piece (owner art rule).
4. **BD-1323 Horizon:** sea stacks and distant ridge silhouettes around the island, static, low detail.
5. Then the per-biome kits of **BD-1315**, Jungle and Desert first: they prove dense versus sparse. Tundra, Volcano, Swamp reuse the proven systems.

## 9. Gate for every biome slice
1. **Screenshot test:** with sky, UI, weather and dinos hidden, a player names the biome from one picture. If only the ground colour and trees changed, it fails.
2. Close-up per new piece: grows from the ground, no pot, plate, ring or disc, matches the kit palette and chunkiness (docs/250 s8).
3. Density and open share inside the section 3 ranges; no even scatter in the aerial picture.
4. 25 studs clear around the dino; dino and food readable.
5. Phone: parts and triangles in range within docs/107; draw calls checked on a real phone before release.
6. ChatGPT art-director score 8+ against the approved concept, then our own same-size crop comparison.

## 10. Sources
Talks and videos (summaries and write-ups; no YouTube transcripts could be read):
- Jane Ng, "The Art of Firewatch" GDC talk (free on the GDC YouTube channel), via PC Gamer: https://www.pcgamer.com/why-less-is-more-when-it-comes-to-firewatchs-beautiful-trees/
- Guerrilla, "Between Tech and Art: The Vegetation of Horizon Zero Dawn" (GDC YouTube): https://classcentral.com/course/youtube-between-tech-and-art-the-vegetation-of-horizon-zero-dawn-165825 and GPU placement: https://www.guerrilla-games.com/read/gpu-based-procedural-placement-in-horizon-zero-dawn
- Kingkade 3D, "10 building tips you need to know in Roblox Studio" (transcript summary): https://sozai.app/transcript/10-building-tips-roblox-studio/index.md
- Breath of the Wild CEDEC talk (triangle rule, gravity): https://gist.github.com/idbrii/e39fe96279aa1670319bfa521d907399 and https://80.lv/articles/the-design-secrets-of-breath-of-the-wild/

Articles:
- Art tips for building forests: https://www.gamedeveloper.com/art/art-tips-for-building-forests
- Composition in level design: https://gamedeveloper.com/design/composition-in-level-design
- Stylized chaparral environment: https://80.lv/articles/creating-a-stylized-chaparral-environment-in-ue4/
- Stylized desert in UE5: https://80.lv/articles/designing-a-stylized-desert-environment-in-ue5-zbrush-substance
- Far Cry reusable assets and vegetation: https://80.lv/articles/far-cry-games-reusable-assets-and-vegetation-workflow
- Far Cry 5 procedural world: https://blog.playstation.com/2018/03/22/the-procedural-world-generation-of-far-cry-5/
- Environment language: https://80.lv/articles/defining-environment-language-for-video-games/
- Roblox terrain tips: https://devforum.roblox.com/t/tips-for-terraining-in-roblox-studio/258795 and https://devforum.roblox.com/t/how-to-make-your-smooth-terrain-landscapes-more-immersive/252172

Repos and docs:
- Red Blob Games, maps from noise (elevation x moisture, blue-noise density): https://www.redblobgames.com/maps/terrain-from-noise/
- Bridson Poisson-disc sampling: https://www.cs.ubc.ca/~rbridson/docs/bridson-siggraph07-poissondisk.pdf
- Unreal PCG Biome Core (blend ranges, priorities, hierarchical spawning): https://dev.epicgames.com/documentation/en-us/unreal-engine/procedural-content-generation-pcg-biome-core-and-sample-plugins-overview-guide-in-unreal-engine
- Godot ProtonScatter (negative domains, surface projection): https://github.com/HungryProton/scatter
- Roblox: Terrain class https://create.roblox.com/docs/reference/engine/classes/Terrain.md, custom terrain materials https://create.roblox.com/docs/parts/custom-terrain-materials.md, Atmosphere https://create.roblox.com/docs/environment/atmosphere.md, streaming https://create.roblox.com/docs/workspace/streaming, SLIM https://create.roblox.com/docs/workspace/streaming/slim.md, performance design https://create.roblox.com/docs/performance-optimization/design.md

ChatGPT (art-director critique, kit tables, presets, core kit ranking, concept picture): chat "Biome art direction critique", 2026-11-23; text summary in `docs/evidence/2026-11-23-biome-craft/README.md`.
