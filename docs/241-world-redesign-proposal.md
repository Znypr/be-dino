# 241 World redesign proposal: map and food (BD-1208), 2026-11-15

Owner 2026-11-15: "apply the same vision logic redesign with everything we learned from the video studies and design studies and ChatGPT's guide to redesign the maps and food with grid etc. to the 3d actual game too, the map looks bad, the food looks bad" and "first make proposed changes as images like you just did with the new style tiles".

Status: **proposal pictures for owner approval.** Nothing in the game has changed. The ChatGPT pictures are concept art (generated from our own Studio screenshots and the rules below), not Roblox output; the map plan is a planning diagram.

## 1. What is wrong today (Studio, playtest build, `docs/evidence/2026-11-15-world/current/`)

- **Map** (`map-from-above.jpg`): a flat square plateau with square cut-off edges; small props sprinkled evenly everywhere (a polka-dot look); no paths, no readable zones, no landmark you can steer by; a lone dark gate frame in the open; distant haze.
- **Food** (`food-close.jpg`): tiny low-poly gems and drumsticks sitting in flat glowing halo discs, like stickers on the grass; they do not match the approved chunky food icons; the halos read as UI dropped into 3D; berries and fruit are hard to tell apart.
- The food *grid* (docs/187, BD-1047) already fixed the spread (empty blocks 20% -> 0.2%), but not the look or the map structure.

## 2. World rules (the 3D counterpart of the UI style tile, docs/240)

| Id | Rule | Source |
| --- | --- | --- |
| W1 | A natural rounded island with a beach and soft cliffs; never a square edge | owner feedback, top games |
| W2 | One spawn plaza in the middle (hatchery, shops) with wide sand paths out to every zone and a ring road | docs/202 stalls, docs/114 s8.4 #5 clear routes |
| W3 | Readable zones, each with its own ground colour and plants: meadow, broadleaf forest, pine hill, palm beach + lagoon, volcano corner | docs/114 s5.8 biomes |
| W4 | One big landmark per zone, visible from far (giant tree, waterfall, lagoon arch, volcano, fossil skeleton) | docs/202 "readable from the far side of the map" |
| W5 | Plants and trees in intentional clumps with open grass and clearings between; replace, don't add | docs/114 s8.4 #5, s8.5 grouped placement |
| W6 | Food looks like the approved icons come to life: chunky, rounded, glossy, big silhouette; berries on bushes, fruit under trees, eggs in nests, amber in rocks | owner icon picks, docs/196 |
| W7 | No flat halo discs: a soft round shadow plus a gentle sparkle; rarer food near rocks and landmarks so it feels like a find | docs/87 calm feel |
| W8 | Food in small patches along paths and in meadows (the BD-1047 grid), open grass between patches | docs/187 |
| W9 | Clear daylight, no haze; dino and food are the visual priority; everything grounded | docs/114 s8.4 #4, #6, s8.1 |

## 3. Proposal pictures

- `map-plan-v1.png` (made by `tools/map_plan_sketch.py`): top-down plan on the WorldLayer grid: spawn plaza, five zones, spoke paths and a ring road, five landmarks, food patches.
- `proposed-island-chatgpt.png`: the same overhead view repainted to the rules.
- `proposed-food-chatgpt.png`: the same ground view with the new food.
- `before-after.jpg`: today vs proposal side by side.

## 4. How it would be built (after approval; flag-gated, PROVISIONAL)

1. Terrain: island shape + zone ground colours as `WorldLayer` layers (`biome`, `height`), baked from the plan; paths as a sand layer.
2. Placement: trees and plants from a `treeKind` layer with clump rules and `layer_stats` targets per zone (docs/187 E), landmarks placed by hand in the plan.
3. Food models: new 3D food from the approved icons (generate_mesh or Blender, then cleanup; never code-built, docs/114 s8.1), bushes / fruit trees / nests / amber rocks as hosts; FoodService keeps its rules and the BD-1047 grid.
   - 2026-11-16 (BD-1238): the hosts part is built: `FoodHostsEnabled` moves the V3 map's food to the bushes, trees, rocks and landmark edges already on the toon island (`tools/food_hosts.py`, `tools/verify_food_hosts.py`, decision in docs/115); no nest meshes placed (the V3 egg mesh carries its own nest, and new parts would break the phone budget).
4. Each step checked with Studio pictures from the same three cameras as today, plus the phone budget (docs/107).
