# BD-1248 plaza shops v2 evidence (Studio, 2026-11-17)

Owner 2026-11-16: the plaza stalls are "not what famous roblox experiences do with their 3d shops and texts"; concept sheet `concept-sheet-v1-chatgpt.png` approved "Yes, build them".

- `ref-eggs.png`, `ref-potions.png`, `ref-shop.png`, `ref-dinos.png`: one reference per shop, cut from the approved sheet, background on magenta.
- `before-spawn-view.jpg`, `before-overview.jpg`: main (BD-1221 stalls): wooden stall, grey stone sign arches, the word twice (sign face + floating word).
- `after-spawn-view.jpg`, `after-overview.jpg`: same cameras with `PlazaShopsV2Enabled` (playtest profile build).
- `shop-eggs.jpg`, `shop-potions.jpg`, `shop-shop.jpg`, `shop-dinos.jpg`: close-up of each shop from the plaza side.

Built: one Roblox `generate_mesh` MeshPart per building (egg house, mushroom potion hut, crystal stall, fossil-skull hut, about 8 k triangles each) and one generated wooden signboard (1.5 k triangles) stretched wide; the word and icon are a SurfaceGui on the board face (FredokaOne, thick dark outline). Shopkeepers: compy, triceratops, stegosaurus, T-rex (LowPolyDinoAssets) playing the authored idle loop and the happy clip, client only. Two egg tries were rejected (docs/77).

Prompts checked in play (character RunState Active): POTIONS "Open", EGGS / SHOP / DINOS "Open at HOME", no object name on the prompt, no BillboardGui in the plaza folder.

Part counts (Studio PC, server count, BaseParts with XZ distance <= 300 from (0, 30), same method as BD-1245): before 4,307, after 4,299 (plaza folder 20 -> 16 parts). Plus 28 client-only shopkeeper parts (7 per keeper; client count after 4,514). Not a phone check.
