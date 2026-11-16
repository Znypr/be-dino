# World fill: path and ground detail, something to do in every view (BD-1245, BD-1246)

Owner 2026-11-16, spawn screenshot: "game still looks empty", then "Yes, build all". Flags `GroundDetailEnabled` and `ThingsToDoEnabled` (playtest profile ON, default OFF; both need World V3, the toon island and vegetation v2). Studio PC test build (`python tools/build.py --profile playtest`), not a phone.

| Picture | What it shows |
| --- | --- |
| before-path-view.jpg / after-path-view.jpg | The owner's complaint view: from the plaza edge down the forest path to the big tree, same camera. After: worn earth edge along the path, mossy edge stones and pebbles, berries along the path, the signpost with the zone names. |
| before-spawn-view.jpg / after-spawn-view.jpg | The spawn point on the plaza. The plaza itself is unchanged (stalls, plaza paving); the change starts where the paths leave the plaza. |
| set-signpost-forest.jpg | Forest spoke: signpost with "Forest / Meadow / Beach" (the first thing down the main path), food along the path. |
| set-egg-nest-meadow.jpg | Meadow spoke: twig nest with two cracked dino eggs, edge stones, pebbles, a log. |
| set-campfire-pine.jpg | Pine spoke: campfire in a stone ring with log seats. |
| set-log-bridge-beach.jpg | Beach spoke: little log bridge at the lagoon edge. |
| set-fossil-dig-volcano.jpg | Volcano spoke: fossil dig (skull, ribs, shovel in sand). |
| fossil-dig-v1-REJECTED-tub.jpg | The first fossil dig came out as a blue tub with a skull; regenerated (v2 is used). |

All nine meshes are Roblox `generate_mesh` models made in the project's own test Studio from text prompts (ids in `src/shared/WorldFill.luau`, lines in docs/77). Nothing is code-built; the signpost words are a BillboardGui (UI text).

## Numbers (Studio server, BaseParts with XZ distance <= 300 from (0, 30), same method as BD-1239)

| | Before (flags off) | After (flags on) |
| --- | --- | --- |
| All parts | 4,479 | 4,313 |
| Food parts | 2,747 | 2,747 |
| World fill pieces + set pieces + colliders | 0 | 95 |
| Single ground cover clumps (whole island) | 808 | 483 |

The client count of BD-1239 (4,672) includes client-only parts; this table uses the server count both times. Offline, `tools/verify_world_fill.py` gives the same direction (255 clumps dropped, 95 pieces added within 300 studs: net -160).

Food: 79 berries and fruit moved inside the food map grid (the BD-1047 cells) from the 180-300 stud band of their own zone to clusters of three along the first stretch of each spoke path; the same 3,600 foods, the same count of every kind in every zone, starter patches untouched (checked offline). FoodGlow reaches 175 studs instead of 130.

Not verified: phone frame rate and look, how a child reads the sign, the earth spots (terrain voxels make them a little hexagonal).
