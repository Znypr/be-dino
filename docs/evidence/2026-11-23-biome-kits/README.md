# BD-1315 biome kits: desert, tundra, volcano (2026-11-23)

Owner 2026-11-23: "check out what biomes are planned, what current assets we have in terms of vegetation, terrain, rocks, deco etc and
find any missing, and generate them. use chatgpt for inspiration and guides to create them to guarantee cohesiveness".

## Inventory (docs/250)
Planned: Meadow (home), Jungle, Desert Canyon, Frozen Tundra, Volcano, and the rare Misty Swamp later (S5). Terrain colours and
atmosphere are S1 (BD-1314); this work is the mesh kit per placed slot (S2).

| slot group (kit ids) | meadow | jungle | desert | tundra | volcano |
|---|---|---|---|---|---|
| trees (canopy, conifer, cycad, dead) | yes (#664) | yes | NEW | NEW | NEW |
| bushes | yes | yes | NEW | NEW | NEW |
| mushroom clumps (4-12 studs) | yes | yes | NEW | NEW | NEW |
| ferns, horsetail | yes | yes | NEW | NEW | NEW |
| flowers, grass | yes | yes | NEW | NEW | NEW |
| boulders | yes | yes | NEW | NEW | NEW |
| rock spires | today's | today's | NEW | NEW | today's |
| rock ledges | today's | NEW | NEW | NEW | NEW |
| fallen logs | today's | today's | today's | today's | today's |
Not covered here: terrain colours (S1), the Misty Swamp kit (S5), landmark variants (S4).

## Route
1. ChatGPT style sheets in one chat (own Chrome tab), each made from the approved vegetation v2 sheet plus the biome grid:
   `sheet-desert-chatgpt.jpg`, `sheet-tundra-chatgpt.jpg`, `sheet-volcano-chatgpt.jpg` (screenshots of the ChatGPT result).
2. Roblox Studio `generate_mesh` (free) with prompts written from each sheet; published to the owner's account by the generator.
3. Close-up Studio check of every piece (`*-round*.jpg`, `clean-*.jpg`, `cooled-volcano.jpg`), rejects in `generated-biome-kits.json`.
4. Final kits: `kit-desert-studio.jpg`, `kit-tundra-studio.jpg`, `kit-volcano-studio.jpg`.

## Owner notes applied during the work
- "a plant pot wouldn't make any sense": no pots, stands or plates.
- "you often use stones though at the base ... think about how plants are naturally planted": every plant was regenerated with a clean
  base (terrain is the ground). Rocks and spires sink 12% into the terrain (PropGround.RockSink), which buries a thin rim. One deliberate
  exception: the desert mesa spire keeps a few fallen rocks at its foot (natural talus, as in the ChatGPT desert sheet).
  Natural density: `VegetationV2.KitDensity` keeps only a share of the collider-free small plants per biome (desert and volcano sparse,
  rare flowers and bones; tundra pine stands with few flowers; jungle dense). Trees, boulders, spires and ledges always show: they have
  colliders, so hiding them would leave invisible walls. Desert groves read as acacia savanna with lone saguaros.
- "the flames on top wouldn't look good since they would be flat, not glowing, static": no painted fire, embers, glowing cracks or lava in
  any mesh. The volcano kit is cooled volcanic land (red-crowned trees, charcoal stumps, ash grass, fire ferns, crystals, pumice
  boulders, cooled lava ledges). Real glow (lava, embers) belongs to lights / Neon / particles in S1/S4.

## Code (no visible change until S1)
`VegetationV2.kitVisual(biomeId, kitId, roll, layer?)` returns the key for desert / tundra / volcano too (table `VegetationV2.Kits`);
`VegetationV2.kitHidden(biomeId, kitId, roll, layer?)` says which collider-free slots show nothing in that biome. S1's swap calls both.
`verify_vegetation_v2` checks: every placed slot gets a real key in each kit (logs keep their look; volcano spires keep today's), only
collider-free slots are hidden, desert and volcano are sparse, the jungle hides nothing, every key is used.

## In-game previews (test-only swap in my Studio, the game itself has no swap until S1)
`preview1-desert-*.jpg` (first desert mapping: too many cacti in the groves, fixed), `preview1-tundra-*.jpg`, `preview2-volcano-*.jpg`.
The ground is still the meadow's green and the light is the meadow's: terrain and atmosphere are S1. The big colossal twisty tree is not
re-skinned by my preview script (nested model); S1's swap must cover the colossal layer too.

Not verified: phone, the real client swap, terrain colours under the kits.
