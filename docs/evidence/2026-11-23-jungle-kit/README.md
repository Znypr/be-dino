# BD-1315 jungle kit (2026-11-23)

Biome overhaul (docs/250, owner 2026-11-23): the whole island is one biome at a time, swapped by a storm every 8 minutes. Placements,
colliders and food hosts stay put; only the mesh shown on each placed slot changes. This is the jungle kit (S2), the first per-biome kit.

## Contract with S1 (BD-1314, the biome clock, not built yet)
`VegetationV2.kitVisual(biomeId, kitId, roll, layer?)` (pure, in `src/shared/VegetationV2.luau`) returns the visual key for a slot in that
biome's kit, or nil to keep today's `visualFor(id, subBiome, roll)`. "meadow" = today's map (nil everywhere, so the #664 pines and
oak). "jungle" = the kit below. Every other biome returns nil until its kit exists. A slot on the `log` layer (a dead tree lying down)
keeps its look. S1 reads the `CurrentBiome` workspace attribute and does the client swap; this change reads no attribute and swaps
nothing, so the game looks exactly as before.

## The kit
| slot | jungle look |
|---|---|
| every standing tree (broadleaf, pine, palm, dead) | buttress canopy tree 60%, twisty vine tree 25%, flower palm 15% |
| round bushes | elephant ear / monstera mound |
| mushroom clumps (4-12 studs) | elephant ear 50%, fern 30%, mossy stump 20% |
| ferns, horsetail | fern a (70%) or elephant ear; fern b |
| flowers | red hibiscus 60%, hibiscus flowers 40% |
| grass | ferns |
| boulders | mossy rock 65%, spiral mossy rock 35% |

New meshes (Roblox generate_mesh in the style of the Jungle panel of `docs/evidence/2026-11-23-biome-overhaul/biome-grid-chatgpt.jpg`,
ids and real triangle counts in `generated-jungle.json`): canopy tree (1,500), elephant ear (800), monstera (900), hibiscus (500), stump
(800). Ferns and mossy rocks reuse the approved vegetation v2 ones.

## Pictures (my own test Studio, playtest build)
- `round1-lineup.jpg`, `round1-small-close.jpg`, `round2-lineup.jpg`: candidates. Rejected under the owner's cohesion rule (no pots or
  odd objects, one family look): the potted elephant ear (`round1-elephant-ear-in-pot-REJECTED.jpg`), a spiky yellow fern, a ball with a
  leaf hat, a blue pudding boulder, a rock like a cake pot, a fern on a dirt bulb (ids in `generated-jungle.json`).
- `compare-forest-meadow-top-jungle-bottom.jpg`, `compare-meadow-meadow-top-jungle-bottom.jpg`: the same cameras, meadow kit on top, the
  jungle kit on the bottom. The jungle pictures come from a test-only swap in my Studio (each placed slot re-skinned through `kitVisual`);
  the game has no swap until S1. Light, fog and colours are still the meadow's: the jungle atmosphere is S1.
- `preview-jungle-v1-too-many-stumps-REJECTED.jpg`: first mapping, where every mushroom clump became a big stump; now mostly leafy plants.

Not verified: phone, and the real client swap (S1). Triangles: the jungle kit's meshes are 500-1,500 each, like the meadow kit's.
