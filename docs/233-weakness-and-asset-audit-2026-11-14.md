# 233 Weakness and missing-asset audit, 2026-11-14

Owner request 2026-11-14: "identify any weaknesses of the game like missing assets and create them, like using chatgpt or blender etc". Also: the menus must "compete with the top roblox experiences" (BD-1189, docs/232).

Sources: the generated catalogue `docs/catalog/Home.md` (70 gaps), `src/shared/AssetSlots.luau`, the art batch docs [196](196-art-batch1-food-bucket-tier-icons.md) and [216](216-art-batch2-shop-mutation-chomp-other-icons.md), the P0 backlog rows, and the Studio look of 2026-11-14 (`docs/evidence/2026-11-14-toybox-studio/`). Labels: **CURRENT BUILD** unless marked.

## 1. The biggest weakness: art is drafted but never reaches the game

- **About 250 icon candidates have waited for a pick since 2026-10-18/19**: art batch 1 (44: food, paint bucket, Emerald / Gold / Diamond tier badges) and batch 2 (208: aura and trail shop icons, shop tabs, Shiny / BIG / mutated badges, Chomp and health hearts, crystal packs, notices, glyphs incl. the Golden Drumstick, 6 rarity badges, 7 cave stations, Index tabs, bonus nest). The lead recommendations are written in 196 and 216; nothing was uploaded.
- **Owner pictures that only need an upload**: Meadow Glow and Tidal Halo aura icons (`resources/ui/v2/items/aura-*-v1.png`, made by the owner in ChatGPT).
- Effect: the shop, the fusion ladder, the hatch, the HUD and the Index fall back to code-drawn shapes or plain text, which is the "vibe coded" look the owner sees.

## 2. Missing with no draft at all

| Gap | Count | Where it shows | Best tool |
| --- | ---: | --- | --- |
| Dino portraits (square, one per species) | 31 | Index cards, hatch reveal, shop eggs, fusion | Studio renders of the V3 models (the lineup the owner chose), transparent, 512 px; today only rough magenta-key cutouts exist (`resources/ui/v2/dinos/v3/`) |
| Pattern icons for the Index | 8 | Index Patterns tab | Blender: the real pattern on a small egg or swatch (the patterns are shader masks, so a render shows the real thing) |
| Legendary aura art (Crystal Shop BD-1178) | 1+ | the top shop card | ChatGPT icon in the batch-2 style plus a Blender ring render |
| Biome pictures | 6 | world / teleport pages | Studio shots of each biome from the real map |
| Landmark and statue pictures | 7 | world pages | Studio shots of the placed models |
| Wind (nothing sways) | code | the whole world | small `WindConfig` + Roblox `GlobalWind`; not an asset |

## 3. Game weaknesses that are not assets (from the P0 board)

- Menus: hand-placed layouts, text on studs, mixed buttons (BD-1189 pilot in progress, then every menu).
- Never measured on a phone (BD-085, BD-322) and never run with friends (BD-317): the owner's device and publish steps.
- Camera rattle on bumpy ground (BD-164) and a loud run-end sound (BD-166) are still Backlog.
- Mutation end-to-end audit not done (BD-154).

## 4. Plan, ranked (one helper at a time)

1. **Lead picks and upload of the drafted art (now).** Apply the written recommendations of 196 and 216 as LEAD decisions (owner delegated), cut nothing new, upload as Decals, look up the image ids in Studio, bind with `tools/bind_assets.py`, docs/77 lines, one picture of what was picked. The owner can overrule any pick by letter.
2. **Dino portraits** from the V3 models in a copy of Place1 (Studio render, clean background, same camera per class), 31 + the 5 new species of BD-1187.
3. **Pattern icons** (8) as Blender renders; **Legendary aura** art.
4. **Biome / landmark / statue** shots, only where a screen shows them.
5. Wind as a small code task.

Not done: nothing in sections 2 to 4 is made yet; every item gets a picture for the owner before it is bound.
