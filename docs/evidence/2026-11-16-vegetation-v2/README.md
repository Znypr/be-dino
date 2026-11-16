# BD-1239 vegetation v2 (2026-11-16)

Owner 2026-11-16, playtest screenshot: "vegetation looks cheap ... it should have more personality and fit the game". Approved the ChatGPT concept sheet: "Yes, build all".

## Source
- `concept-sheet-v1-chatgpt.png`: the approved sheet. It has **18** objects (not 20): 3 broadleaf trees, 2 pines, 2 palms, 3 berry bushes, 2 flower clusters, 2 grass clumps, 2 ferns, 2 mossy rocks.
- `refs/sheet-magenta.png` and `refs/ref-*.png`: the sheet keyed from chroma green to magenta (#FF00FF), cut into one reference picture per object. The key only removes the pure key green (the leaf greens are far from it), so the leaves stay.
- `generated-vegetation.json`: the 18 published Model ids (Roblox Studio `generate_mesh`, text prompts written from each reference, published to the owner's account by the generator), the triangle cap and the reference of each.

## Models
- `lineup-all-18-studio.jpg`, `lineup-close-studio.jpg`: all 18 in Studio.
- `grape-bush-v1-REJECTED-tree-shape.jpg`: the first grape bush came out as a little tree on a trunk; regenerated as a dome (id 133674054493602). The rejected one (109635881503721) and a first red bush whose job timed out are published but not used.
- Real triangle counts (EditableMesh face count in Studio): trees 1,498-2,498, pines 900, palms 1,200, bushes 700-800, flowers 500, grass 400, ferns 500, rocks 600-700. The meshes they replace: bush 2,000, broadleaf 2,984, jungle giant 4,994, palm 2,498, pine 2,358, mossy boulder 1,490.

## In game (playtest profile, my own Studio window, build/BeDino-veg2-*.rbxlx)
- `before-*.jpg`: main 783560dd. `after-*.jpg`: this branch. Same camera each time: `*-spawn-plaza` = the owner's view from spawn at the plaza; `*-zone-<meadow|forest|pine|beach|volcano>` = one view per World V3 zone.
- Plaza signs: the NESTS / POTIONS overlap came from the floating sign words (BillboardGui), which were 180 x 54 **pixels** at any distance, so far words stayed big and covered nearer ones. They are now sized in studs and shrink with distance (`after-spawn-plaza.jpg`).

## Numbers (Studio PC, not a phone)
| | before | after |
|---|---|---|
| client parts within 300 studs of spawn (XZ) | 5,103 | 4,672 |
| WorldKit parts (whole island) | 2,679 | 2,076 |
| ground cover placements | 1,373 | 770 |
| trees / shrubs / rocks | 228 / 647 / 50 | 228 / 647 / 50 |
| island prop triangles within 300 studs (same props, real face counts) | 1,319 k | 845 k |

Still above the docs/107 phone rule of thumb (about 3,000 parts in range); the rest is food, the plaza and the landmarks. No phone check yet.
