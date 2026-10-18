# 187 Food map grid and a smart test bot (owner intake 2026-10-18)

Status: **SPEC, nothing built.** Rows BD-1047 to BD-1049 in [docs/07](07-kanban.md).

## What the owner saw and asked
In the playtest window the dino **wiggled a lot**. The owner guessed it is looking for food, and said that is "not a real simulation": a real player sees the food on the ground and walks to it. Idea: a top-down **grid map** of the world (for example 1000 x 1000 cells, or whatever is reasonable) holding a number per cell: 0 = no food, 1 = the smallest food, up to the biggest food. A simple path algorithm then walks the same route a smart player would. The same map would also let us **place the food more thoughtfully**: it should look random on the floor but be spread out better than now.

## What the wiggle is (checked in the code, 2026-10-18)
- **The game contains no bot.** There is no auto-play, wander or "find food" code in the shipped game or the playtest profile. The only scripted movers are the wild predators (`NpcPredatorService`) and the Studio-only trailer director (`DemoDirector`, off in every committed build).
- So the wiggle in a Studio window is almost certainly **our own Studio test helper** steering the dino with simple "walk to a point" commands (and the idle sway animation). I could not confirm which helper from here; if it was a person, it is not wiggle code at all. Either way the owner is right: **it is not a faithful player simulation.**

## How food is placed today (`src/server/FoodService.luau`)
- The arena is split into sectors (`Config.FoodSectorCount`). Each sector gets one cluster centre, jittered at random with a fixed seed (`Config.FoodSeed`), and `FoodClusterItems` items are scattered inside a cluster radius. About 2,400 foods in all.
- Each item's kind is a weighted random roll: berry 70, fruit 20, egg 7, amber 3 (points 1 / 4 / 15 / 50). A starter patch near spawn is fixed.
- Items avoid water, steep ground, rocks and trunks. Each item respawns after `FoodRespawnSeconds`.
- Weakness (owner point): one cluster per sector with random jitter gives clumps and empty gaps with no design behind them. Nothing measures the spread.

## Proposal (PROVISIONAL, LEAD decision, owner delegated 2026-10-16)
### A. Measure first (BD-1049)
A tool that reads the real food positions and prints: nearest-food distance for 2,000 random ground points (min / median / max), empty zones larger than N studs, and a **heatmap picture** (top-down, brighter = more food, colour = best food kind). The owner sees the problem as a picture before anything changes.

### B. Food map grid (BD-1047)
- A small data file holds the **designed food map**: a grid (start with 128 x 128 cells over the arena; 1,000 x 1,000 is far finer than a 4-stud food item needs and would be a huge file, so the resolution is a tool setting). Each cell holds 0 (none) or a food kind 1..4 (berry, fruit, egg, amber), plus the special food as 5 only when that flag is on.
- A generator makes the map with rules, not pure dice: minimum distance between items (blue-noise spacing), a few designed hot spots (a fruit grove, an egg meadow, a lonely amber on a hill), gentle density from spawn outward, guaranteed food within N studs of the player's spawn and of the Home exit, none in water or on rocks. A seed still makes it deterministic.
- `FoodService` reads the map instead of the sector/jitter code. Same total count, same points per kind, same respawn rules; the spawner keeps the existing ground, water and obstacle checks as a safety net. Existing Food attributes and the catch rules do not change.
- The heatmap picture of A is regenerated from the map and saved as the evidence.

### C. Smart test bot (BD-1048, Studio-only, never shipped)
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
