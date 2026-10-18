# 187 Food map grid and a smart test bot (owner intake 2026-10-18)

Status: **SPEC, nothing built.** Rows BD-1047 to BD-1049 in [docs/07](07-kanban.md).

## What the owner saw and asked
In the playtest window the dino **wiggled a lot**. The owner guessed it is looking for food, and said that is "not a real simulation": a real player sees the food on the ground and walks to it. Idea: a top-down **grid map** of the world (for example 1000 x 1000 cells, or whatever is reasonable) holding a number per cell: 0 = no food, 1 = the smallest food, up to the biggest food. A simple path algorithm then walks the same route a smart player would. The same map would also let us **place the food more thoughtfully**: it should look random on the floor but be spread out better than now.

## What the wiggle is (checked in the code, 2026-10-18)
- **The game contains no bot.** There is no auto-play, wander or "find food" code in the shipped game or the playtest profile. The only scripted movers are the wild predators (`NpcPredatorService`) and the Studio-only trailer director (`DemoDirector`, off in every committed build).
- So the wiggle in a Studio window is almost certainly **our own Studio test helper** steering the dino with simple "walk to a point" commands (and the idle sway animation). I could not confirm which helper from here; if it was a person, it is not wiggle code at all. Either way the owner is right: **it is not a faithful player simulation.**

## How food is placed today (`src/server/FoodService.luau`)
- The arena is split into sectors (`Config.FoodSectorCount`). Each sector gets one cluster centre, jittered at random with a fixed seed (`Config.FoodSeed`), and `FoodClusterItems` items are scattered inside a cluster radius. 20 x 20 sectors x 9 items = **3,600 foods** in all (`Config.FoodSectorCount`, `FoodClusterItems`; the code comment about 2,400 is old).
- Each item's kind is a weighted random roll: berry 70, fruit 20, egg 7, amber 3 (points 1 / 4 / 15 / 50). A starter patch near spawn is fixed.
- Items avoid water, steep ground, rocks and trunks. Each item respawns after `FoodRespawnSeconds`.
- Weakness (owner point): one cluster per sector with random jitter gives clumps and empty gaps with no design behind them. Nothing measures the spread.

## Proposal (PROVISIONAL, LEAD decision, owner delegated 2026-10-16)
### A. Measure first (BD-1049)
A tool that reads the real food positions and prints: nearest-food distance for 2,000 random ground points (min / median / max), empty zones larger than N studs, and a **heatmap picture** (top-down, brighter = more food, colour = best food kind). The owner sees the problem as a picture before anything changes.

### B. Food map grid (BD-1047)
- A small data file holds the **designed food map** as a `WorldLayer` (section D). **Owner correction 2026-10-18: a 1,000 x 1,000 grid is NOT a big file** (my first answer was wrong). One hex digit per cell is 1,000,000 characters raw, 500 KB packed two cells per byte, and because the map is almost all zeros (3,600 food pieces) **run-length encoding makes it a few KB**. The arena is 832 studs wide (`ArenaHalfWidth` 416), so 1,000 cells is about 0.83 stud per cell: fine enough for any food. Resolution stays a tool setting (start 256 x 256 to keep pictures small; 1,000 x 1,000 is allowed). Each cell holds 0 (none) or a food kind 1..4 (berry, fruit, egg, amber), plus the special food as 5 only when that flag is on.
- A generator makes the map with rules, not pure dice: minimum distance between items (blue-noise spacing), a few designed hot spots (a fruit grove, an egg meadow, a lonely amber on a hill), gentle density from spawn outward, guaranteed food within N studs of the player's spawn and of the Home exit, none in water or on rocks. A seed still makes it deterministic.
- `FoodService` reads the map instead of the sector/jitter code. Same total count, same points per kind, same respawn rules; the spawner keeps the existing ground, water and obstacle checks as a safety net. Existing Food attributes and the catch rules do not change.
- The heatmap picture of A is regenerated from the map and saved as the evidence.

### D. One generic map class for more than food (owner idea 2026-10-18, BD-1050)
The owner's point: this is not a picture drawn on the map, it is **a small 2D table of hex digits** inside an ordinary class, and it can serve other things too: which tree kind grows where, how big, separating trees better, shaping biomes.
- **`WorldLayer`** (pure Luau, no Instances, like `BiomeMap`): `WorldLayer.decode(text)`, `layer:at(x, z)`, `layer:set(x, z, v)`, `layer:encode()` (run-length encoded hex text a ModuleScript can hold), plus a world-to-cell conversion and `neighbours`. Server and offline tools use the same code, so tests can read it.
- **One layer per job**, each with its own digit meaning: `food` (kind), `treeKind` (0 none, 1 broad, 2 pine, 3 palm, ...), `treeSize` (size band), `biome` (index into `BiomeMap.Order`). A layer is 1 byte per cell in memory (1 MB at 1,000 x 1,000), which is fine on the server.
- **What exists already:** `BiomeMap` is a smooth seeded math field (blobs and noise) and `BiomePlacement` places six kinds of props by that field and a seed. `WorldLayer` does not replace them at once. First step: **bake** the current biome field and the current prop picks into layers (so we can SEE them as pictures and measure clumps), then let a designer-edited layer override the dice where the owner wants control (trees spread better, clearings where wanted, a fruit grove here, a bare ridge there).
- **Built (BD-1047 first half, 2026-10-18):** `src/shared/WorldLayer.luau` and the Python mirror `tools/worldlayer.py`, tests in `tools/verify_world_layer.py`. Cells are 0-based, `ix` west to east, `iz` north to south, square cells (`cellSize = 2 x worldHalfWidth / width`), the world is centred on 0 and a point on the far edge or outside has no cell (`at` gives 0, `set` gives false). Text format `WL1:<width>:<height>:<worldHalfWidth>:<body>`: the body is runs of equal cells; a run of zeros is letters `G..V` (base-16 digits of length - 1), any other run is a hex digit plus `g..v` length digits, so a nearly empty map is tiny. Measured: 3,600 random cells in 1,000 x 1,000 = about 12,000 characters (the information minimum for hex-only text is about 10,000). Nothing in the game reads it yet.
- A tiny text/PNG preview tool (`tools/layer_preview.py`) turns any layer into a coloured picture for the owner.

### E. Compare windows at several sizes (owner idea 2026-10-18, BD-1049 and BD-BD-1051)
The owner's point: once a world property is a grid we can cut it into **blocks of 10 x 10, 20 x 20, 30 x 30 cells** and count what is inside each block. Four big statues in one block while the other blocks hold about one is a bad spread, and we can SEE and MEASURE that. Then zoom out (30 x 30 blocks) and compare blocks with each other again.
- **`tools/layer_stats.py`** works on any `WorldLayer` (food, trees, rocks, statues, biomes): for each block size it prints count per block (min / median / max), the share of **empty blocks**, the **crowded blocks** (more than 2x the median), a **spread score** (variance divided by the mean: about 1 is plain random, much above 1 is clumped, below 1 is evenly spaced) and a heatmap picture per size. Per kind (small trees vs big trees, berry vs amber) and for all kinds together.
- **Design targets, not only complaints:** each layer gets a written target per block size, e.g. "forest biome: 6 to 14 trees per 20 x 20 block, small trees 2x more than big, no empty block inside a forest", "statues: at most 1 per 30 x 30 block, none touching". The tool fails (CI check) when a layer breaks its own target.
- **Compare with real maps (BD-BD-1051, research):** collect reference numbers from real forests and game maps (trees per hectare by forest type, how clumped natural stands are, spacing of rocks, how popular games place pickups) and use them as the starting targets. Real sources are cited in the doc, game maps are read from screenshots only (nothing copied).
- This also protects later work: when a designer edits a layer the same check says right away whether the new spread is worse.

### C. Smart test bot (BD-1048, Studio-only, never shipped)
**Built 2026-10-18: `tools/studio/player_bot.luau` and `tools/studio/run_player_bot.py`, how to run it and the first five-minute numbers are in [194](194-studio-test-bot-and-pace-numbers.md).**
- Lives under `tools/studio/` (like the model insert snippet), run through the Studio MCP in a play session; it is not in `src/` and has no remote.
- Behaviour like a sensible player: read the food list (or the map), pick the **best next food** by value per walking distance, walk a real path (straight line with simple obstacle and water avoidance, using the character's pathfinding), pick it up, repeat; flee or skip near a wild predator; stop to open the egg screen when eggs are waiting; log what it did.
- Used for: the **5-minute person-like run (BD-575)**, the player walkthrough (BD-1045), and food-per-minute measurement (BD-1043 species timing and BD-418 egg rate).
- It makes **no random wiggle**: path, target and timestamps go in the report.

## Order
1. BD-1049 measure the current spread (small, gives the picture).
2. BD-1048 smart test bot (it makes every later Studio run more trustworthy).
3. BD-1047 food map grid (replaces the placement once the picture shows what to fix; needs a Studio look and a phone check of food density).

## Handbook fit
docs/114 s9 food values stay unchanged; growth pacing is untouched (the food map keeps the same food-per-minute unless the owner asks for a change; verified by the bot's measurement). The grid is server data, nothing for the player to read, so docs/72 copy rules do not apply.

## F. First measurement of today's food (BD-1049, 2026-10-18)
**Tools:** `tools/dump_food_layout.py` (re-creates `FoodService` placement offline, no Studio) and `tools/layer_stats.py` (the numbers and pictures), tests in `tools/verify_layer_stats.py`. Run: `python tools/dump_food_layout.py --runner <luau.exe> --seeds 8` then `python tools/layer_stats.py --points build/food_layout_1404.json --png-dir docs/evidence/review-2026-10-17`.

**How close to the real game (CURRENT BUILD vs this model):** the real food uses Roblox's own dice and raycasts against the terrain, which cannot run outside Roblox. The offline copy uses the same rules (20 x 20 sectors, one jittered cluster per sector, 9 foods in radius 7, kind mix 70/20/7/3, the starter patch, safe-spawn disc, pools, slope, same order of dice use) but different dice, so single positions differ from the game. It does not model rejection next to rocks and trunks (a few percent of tries). It gives 3,560 to 3,572 foods per layout (the game aims at 3,600; about 30 find no ground). Eight different dice seeds (1404 to 1411) gave almost the same numbers, so the result does not depend on the dice. **Not verified in Studio:** a Studio dump of the real positions should be compared once (the tool reads the same JSON).

**Result (seed 1404; 8 seeds in brackets), blocks of 10 / 20 / 30 cells = 32 / 65 / 97 studs:**
- **Clumped, yes.** Spread score 3.7 / 2.3 / 1.6 (3.6-3.9 / 1.9-2.5 / 1.2-1.8); plain random scatter on the same ground gives 1.0 / 1.0 / 1.1. Clumpiest at small size, nearly random when zoomed out to 30 x 30.
- **Empty and crowded blocks (10 x 10):** the middle block holds 6 foods, but **20% of the blocks are empty** (random scatter: under 1%) and 37 blocks hold 13 to 23 foods (more than 2 x the middle). At 20 x 20 and 30 x 30 no block is empty and none is crowded (fewest/most 7 / 44 and 31 / 75).
- **Foods are glued in bundles:** the nearest other food is 2 studs away (random scatter: 6.5). Each bundle of 9 is a tight ball with about 40 studs of nothing between bundles.
- **Walking is short:** from a random spot the nearest food is 13 studs away (middle), 26 studs (95 of 100 spots), 39 studs at worst (39 to 46 over 8 seeds); at walk speed 22 studs per second that is 0.6 s, 1.2 s and about 2 s. The island is 98% walkable, so the gaps are the design, not water.
- **Rare kinds are thin:** nearest egg 25 studs (middle), 52 (95th), 78 at worst; nearest amber 39 studs (middle), 80 (95th), 109 at worst (about 5 s of walking; over 8 seeds the worst amber walk was 114 to 194 studs). **Empty zones** (more than 25 studs from any food): 115 small patches, 6% of the ground, many along the outer rim and between bundles; biggest empty circle 45 studs radius (41 to 54 over 8 seeds).
- Pictures: `docs/evidence/review-2026-10-17/195-food-spread-10x10-blocks.png`, `196-...-20x20-...`, `197-...-30x30-...` and `198-food-dots-and-empty-zones.png`.

**What it suggests (for BD-1047, PROVISIONAL, nothing changed yet):** (1) today's food is fine for reaching food but looks like bundles; a minimum spacing between foods (3 to 5 studs inside a bundle, or smaller bundles of 3 to 4) would remove the ball look and the 20% empty small blocks without changing the total. (2) Place eggs and amber per block (for example one amber per 65 x 65 block region with a hole-free rule) so no walk to the next egg or amber is longer than about 60 studs. (3) Keep the written targets small and testable, for example: all kinds, 20 x 20 blocks: no empty block, spread at most 1.3; egg: 95th walk at most 45 studs; amber: worst walk at most 80 studs. (4) Any later change must keep food per minute the same (the bot of BD-1048 measures it).

**Layer size check (BD-1047, 2026-10-18):** today's food baked into a `WorldLayer` (one food per cell, kind 1..4): at 256 x 256 cells (3.25 studs) only 2,769 of 3,571 foods keep their own cell (22% share a cell inside a bundle), at 1,000 x 1,000 cells (0.83 studs) 3,473 do (3% share). So the food layer needs the fine grid (or a minimum spacing of one cell, which the planned generator has anyway); 256 is fine for pictures. As text the 1,000 x 1,000 food layer is 10,863 characters, the 256 x 256 one 5,703. `python tools/layer_stats.py --layer file.txt --kind-names 1=berry,2=fruit,3=egg,4=amber` reads such a file.

## G. The designed food map (BD-1047 second half, 2026-10-18; flag off by default, ON in the playtest profile)
**CURRENT BUILD (offline evidence only):** `tools/generate_food_layer.py` makes a `WorldLayer` of food kinds by rules, `src/shared/FoodLayerData.luau` holds it (12 KB of text, 1,000 x 1,000 cells, every food in its own cell) and `tools/food_layer_data.py` is the copy for the tools. `src/shared/FoodLayer.luau` turns it into items per FoodService sector. `FoodService` reads it only while `Config.FoodLayerEnabled` is true (default false and pinned false in the default release profile; the playtest profile sets it true, docs/157). With the flag false the old sector / jitter placement runs byte for byte (checked by running the old and new service under the same stub for 3 placements: normal, no terrain rays, Kit art, 1 MB of output, identical).

**Version 2 (same day, lead decision: food PACE must stay about the same):** the first version spread single foods 7 studs apart; a rough walker model said a food-seeking player would collect 41% fewer foods, so the foods are now **small clusters of 3 to 5** (mostly 5), 3 to 3.5 studs apart (today's bundles are 9), the clusters spread by blue noise (centres at least 14 studs apart, foods of different clusters at least 6 studs apart). A player who walks to the next visible food still gets several pieces per stop.

**Rules the generator follows (PROVISIONAL, LEAD decision, owner delegated 2026-10-16):** same totals as today (3,600 foods; berry 2519, fruit 722, egg 251, amber 108 = the 70 / 20 / 7 / 3 mix plus the starter patches); clusters placed by best-candidate sampling, then moved so that no ground spot (rim included) is far from food and no 32-stud block is empty; density a little higher around the run start and the Home exit (0, 30) and in two designed hot spots, a **fruit grove** at (-110, 150) and an **egg meadow** at (215, 40); one **lone amber** on each of the 4 mountain tops (nothing else within 18 studs); every other amber cluster also holds an egg and a fruit (rich stops, like today's rich bundles); the other ambers and the eggs chosen so the walk to the next one is short everywhere (cover selection plus smoothing on a 12-stud lattice of ground spots); the two starter patches near (+-15, 24) kept (9 foods each, 3.6 studs apart, 2 berries to 1 fruit, marked `StarterFood`); nothing in water, the safe-spawn disc, on ground steeper than the `normal.Y < 0.62` rule or within one stud of an edge (the same ground rule as `FoodService.groundAt`, evaluated by `tools/dump_food_layout.py` `ground_model`). Deterministic from `SEED` (103, picked from 12 tried); `tools/verify_food_layer.py` regenerates the map and fails when the committed files differ, so a terrain change needs `python tools/generate_food_layer.py --runner ... --write` and a commit.

**How FoodService uses it:** same Food folder, attributes (`Points`, `Sector`, `StarterFood`, ...), points per kind, respawn timing and validation. The ground / water / obstacle raycasts stay as a safety net: a food that fails is moved to the nearest valid spot of a fixed 1 to 4 stud spiral or dropped, and Workspace gets `FoodLayerPlanned`, `FoodLayerRelocated`, `FoodLayerDropped` (read them in Studio: near 0 is expected). A food from the map respawns where the map put it (random moves would undo the spread). An unreadable map falls back to the old placement with a warning.

**Before / after** (BEFORE = the offline model of today's placement, seed 1404 for the spread numbers and the mean of 6 layouts for the pace numbers, see section F for how close it is; AFTER = the committed map; same ground, 256-cell grid so blocks of 10 / 20 / 30 cells are 32 / 65 / 97 studs; `python tools/compare_food_layers.py --runner ... --png-dir docs/evidence/review-2026-10-17`):

| Measure | Before (today) | After (designed map) |
| --- | ---: | ---: |
| Foods in total | 3571 | 3600 |
| Spread score, blocks of 10 x 10 cells (32 studs; random scatter = 1) | 3.66 | 0.82 |
| Spread score, blocks of 20 x 20 cells (65 studs; random scatter = 1) | 2.45 | 0.80 |
| Spread score, blocks of 30 x 30 cells (97 studs; random scatter = 1) | 1.64 | 0.86 |
| Empty small blocks (32 studs), share | 20.1% | 0.2% |
| Crowded small blocks (more than 2 x the middle) | 37 | 7 |
| Nearest other food, middle (studs) | 2.0 | 3.3 |
| Nearest other food, closest pair (studs) | 0.0 | 3.0 |
| Walk to nearest food, middle (studs) | 12.7 | 9.4 |
| Walk to nearest food, worst (studs) | 39.3 | 23.9 |
| Walk to nearest egg, 95th (studs) | 52.2 | 34.0 |
| Walk to nearest amber, middle (studs) | 38.9 | 31.7 |
| Walk to nearest amber, worst (studs) | 108.6 | 70.6 |
| Empty patches (ground more than 25 studs from any food) | 115 | 0 |
| Biggest empty circle (radius, studs) | 45.3 | 0.0 |
| Richest 65-stud square vs the average square (food points) | 4.2 x | 2.1 x |
| 5 minutes, closest-food walker: foods / points | 1072 / 4320 | 908 / 3540 (-18% points) |
| 5 minutes, best-food-per-second walker: foods / points | 190 / 6904 | 181 / 5776 (-16% points) |
| 5 minutes, walker that just runs around: foods / points | 162 / 655 | 154 / 654 (-0% points) |

The three walker rows come from `tools/food_pace.py`, a rough model (22 studs a second, pick-up radius 2.25, respawn 8 s; the seeking walkers start from 12 spots around the run start and are averaged, the runner is averaged over 12 seeds): NOT a real player. The walker that just runs around collects 655 food points in 5 minutes on today's placement, which is the 600 to 700 food of a normal 5-minute run (docs/119), so it is the walker that matches real play; the two seeking walkers collect 5 to 10 times more than a real player does.

**Pace result:** the runner is unchanged (0%). The seeking walkers collect about **15 to 18% less** (closest-food walker: 15% fewer foods, 18% fewer points; best-food-per-second walker: 16% fewer points) because a cluster of 4 to 5 gives fewer pieces per stop than a bundle of 9 and the stops are closer together than the bundles, not more. Trade-off table of what I tried (foods eaten by the closest-food walker, points of the best-food walker and of the runner, each as a share of today; empty small blocks; empty patches; the walker model was re-run for each row, so the shares are good to about 3 points):

| Layout | Closest-food foods | Best-food points | Runner points | Empty 32-stud blocks | Empty patches (> 25 studs) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Version 1: single foods 7 studs apart | 59% | 68% | 100% | 0% | 0 |
| Clusters of 3 to 5, even placement (64 tries a cluster), no repair | 81% | 86% | 98% | 1.3% | 0 |
| same, 24 tries a cluster | 82% | 85% | 98% | 2.1% | 0 |
| same, 8 tries a cluster | 84% | 82% | 86% | 2.6% | 0 |
| Clusters of 4 or 5, random placement (1 try a cluster) | 85 to 91% | 71 to 75% | 97 to 98% | 8 to 13% | 46 to 67 (radius 46 to 50) |
| **Version 2 (committed): clusters of 3 to 5, even placement, gaps and empty blocks repaired, rich amber clusters** | 85% | 84% | 100% | 0.2% | 0 |

**Reading it:** more evenly spread clusters (what the spread targets want) means longer walks between clusters, so the seeking walkers lose about 15%; letting the clusters clump (random placement) would win the foods back but leaves holes of 45 studs and 10% empty blocks, which breaks the spread targets. Version 2 sits at the edge: spread targets met (one empty block in 612, no patch above 25 studs, amber worst walk 71 studs), pace of the seeking walkers about 15 to 18% below today, the runner (the real-play match) unchanged. Seeds 101 to 112 gave the same 80 to 87% for the seeking walkers, so this is the structure, not luck. Further steps would need bigger clusters (the lead capped them at 3 to 5), a few more foods, or a smaller gap between clusters.

Pictures: `docs/evidence/review-2026-10-17/276-food-map-before-after-dots.png` (today left, map right), `277-food-map-design-hot-spots-lone-ambers.png` (grove, meadow, starter patches), `272` to `274` (heat maps at 10 / 20 / 30 cells), `275` (dots and empty zones of the map).

**Written targets** (`tools/targets/food_layer_targets.json`, enforced in CI by `tools/verify_food_layer.py`): exact counts, kind mix within 0.5 points, clusters of 3 to 5 foods (mean at least 4.2) apart by at least 12 studs centre to centre and 5.5 studs food to food, only the 2 starter patches and the 4 lone ambers as other groups, every amber cluster with an egg and a fruit, every food on valid ground, no empty small block (at most 0.5%), spread at most 1.0 at 10 / 20 / 30 cells, no empty zone (25 studs), worst walk to any food at most 28 studs, egg 95th at most 42 and worst at most 55, amber 95th at most 58 and worst at most 72, and the pace band: closest-food walker foods and best-food walker points at least 80% of today, runner within 8%.

**Risk still open (BD-1076):** the seeking-walker pace is 15 to 18% below today in the model; the real pace has to be measured with the smart test bot (BD-1048) in Studio. The default build is unchanged until then. Not verified: Studio (real terrain, rocks and trunks, how the grove, meadow and amber tops look), phone density and frame rate (BD-1075).
