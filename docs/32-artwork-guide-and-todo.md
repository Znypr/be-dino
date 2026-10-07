# Be Dino artwork guide and small production checklist
Updated 2026-10-08. Current artwork planning for redesign/resources-and-core-fixes.

## Authority and sources
Znypr's latest explicit requests take precedence over historical prototype restrictions. This guide consolidates artwork decisions; it does not approve game balance, monetization, or new gameplay.
Read docs/01-project-brief.md, docs/03-game-design.md, docs/05-asset-pipeline.md, docs/25-redesign.md, docs/28-ui-overhaul.md and docs/30-build017-and-progression-roadmap.md for context.
The original three-species/no-shop/Gold-only slice is historical. Later requests include crystals, auras, potions, leap, weather, a larger catalog and Diamond after Gold. Implemented code and live Studio acceptance are separate.
Catalog values/names currently come from src/shared/ProgressionConfig.luau. Do not invent product benefits in artwork.

## Vision, audience and goals
A compact, social Roblox dinosaur survival-and-collection game: eat food, grow, encounter other players, bank rewards, hatch eggs, collect/equip dinos, then start another run.
Art should make this loop understandable quickly and make rewards feel collectible.
Audience assumption: younger Roblox players, roughly ages 8-13, based on Znypr's creator community; not a measured game demographic. Adults/parents should also understand labels and purchases.
Friendly prehistoric fantasy, clear silhouettes, cheerful chunky forms. No gore, frightening realism, sexual content or misleading reward art.
Design for desktop and phone. Artwork must work without reading tiny detail or relying only on color.
Use owned/original assets and already available tools; do not introduce paid asset dependencies.

## Two compatible visual layers
1. Illustrated item art: match resources/ui/v2/icons/dinos.png and its siblings. Stylized dimensional 3D render, saturated colors, dark contour, rounded bevels, controlled bright highlights, friendly proportions.
2. Functional symbols: reuse resources/ui/v2/scalable SVG/geometry assets for navigation, timers and status. Do not redraw these as expensive illustrated items.
UI panels, labels, buttons, rarity frames and animations remain reusable Roblox components governed by UITheme; artwork does not flatten a menu into an image.

## Layered artwork rule (supersedes flattened aura thumbnails)
Znypr requests separate reusable effect rings and fossil centerpieces. Use one shared fossil PNG and independent transparent ring PNGs. Original combined Meadow/Tidal drafts remain historical references, not the preferred source format. Do not generate a new fossil for every aura.
For depth, display the same full ring in two clipped UI containers: upper half behind the center, lower half in front. Share ring position, scale and fade; configure clipping split and center size/offset independently. Do not spin a static perspective ellipse as if it were world-space 3D VFX. Glow/details within current ring PNGs are baked; optional future particle overlays should be separate.
See resources/ui/v2/layers/README.md and layout.json. All assets are generated drafts, not yet uploaded/integrated/Studio verified. The standalone fossil was regenerated and differs in size from the initial composite; use configuration to align it, not a claim of exact pixel extraction.

## Reusable potion and counter parts
Potion bottle artwork is saved without baked emblems. Overlay existing speed/bolt or leaf/growth symbols in UI. Use the same bottle artwork across rarity tiers; frames, rarity labels, duration and quantity remain live UI. Do not regenerate six independent bottles for the six catalog products.
Catches uses one neutral ivory footprint source, repeated through ImageLabels when a grouped mark is needed; do not use Gold/Diamond mutation badges for catch units. See layers/item-layouts.json for starting overlay settings.

## Consistency rules
- One individual asset per file and per generation. Never deliver a sheet of multiple items as the runtime source.
- Square transparent PNG master, ideally 1024x1024 or larger. Preserve genuine alpha; no baked checkerboard, solid background or opaque outer glow rectangle.
- Center subject with about 10-15% safe margin. Keep all spikes, bottle tops, rings and sparkles inside the canvas.
- Shared camera: gentle three-quarter view, slightly above subject; shared lighting: soft upper-left key, bright material highlights, readable darker contour.
- Bold silhouette readable at 48-64px; avoid fine text, excessive glitter, thin strands and noisy surface details.
- Do not bake text, prices, multipliers, quantities, rarity labels, buttons or product badges into the art. Live UI owns them.
- Prehistoric identity: leaves, fossils, dinosaur footprints, amber/crystal accents. Avoid generic medieval equipment unrelated to the game.
- Base palette: emerald/leaf green, cream/ivory, amber/gold and dark outline. Extend deliberately: Meadow green #62EC70, Tidal cyan #50D6FF, Royal purple #B46AFF from current aura config.
- Rarity and mutation are separate. A purple rarity frame does not mean Diamond; Gold/Diamond badges do not identify a new species.
- Speed and growth potions share bottle shape/camera/lighting; speed uses a clear bolt/movement emblem, growth uses a leaf/food-growth emblem. Tier variants preserve identity.
- Aura thumbnails depict effects, not a promised new dinosaur. Use a simple neutral fossil/footprint centerpiece and a readable effect ring. Runtime VFX must later match the thumbnail.
- Dino portraits and egg-type previews should come from actual game models whenever available, rather than invented species or egg rewards.
- Gold and Diamond are shared mutation treatments/badges. Keep silhouettes compatible; distinguish material (warm metal versus cool faceted crystal), not color alone.
- Reuse existing logical IDs. The existing amber art is named Crystals to players; do not create a competing currency icon.
- Original compositions only. Reference UI hierarchy/style, never extract another game's art.

## Existing assets to reuse
Seven illustrated V2 originals: dinos, egg, amber/crystals, home, trophy, fusion, shield.
Twenty scalable symbols: amber, aura, blizzard, check, clock, dinos, egg, fusion, growth, home, leaf, leap, lock, potion, rain, shield, speed, thunder, trophy, weather.
Legacy symbols include shop, settings, gift, play and close. Existing actual-model dinosaur portraits and UI components are also available.
An illustrated Gold fusion icon already exists; a separate compact Gold mutation badge serves a different purpose.
Distinct Index/inventory symbols are optional UX improvements, not prerequisites to ship the core loop.

## Small prioritized artwork TODO
| Order | Logical ID / asset | Description and use | Status |
|---|---|---|---|
| 1 | aura_meadow_v1 | Meadow Glow: leaf-green luminous ring with small leaves around a neutral fossil/footprint centerpiece. Common aura shop thumbnail; friendly and restrained. | Generated layer draft: resources/ui/v2/layers/aura-meadow-ring-v1.png + shared fossil |
| 2 | aura_tidal_v1 | Tidal Halo: cyan flowing water-like ring, same center/composition and lighting as Meadow. Rare aura thumbnail. | Generated layer draft: resources/ui/v2/layers/aura-tidal-ring-v1.png + shared fossil |
| 3 | aura_royal_v1 | Royal Nova: separate purple cosmic ring with a few gold accents and star glints; reuse shared fossil in UI. Legendary aura thumbnail, stronger but readable. | Generated layer draft: resources/ui/v2/layers/aura-royal-ring-v1.png |
| 4 | potion_speed_v1 | Cyan bottle base; existing speed/bolt emblem is a separate overlay. Shared master across speed tiers. | Generated draft: resources/ui/v2/layers/potion-speed-base-v1.png |
| 5 | potion_growth_v1 | Matching green bottle base; existing leaf/growth emblem is a separate overlay. Shared master across growth tiers. | Generated draft: resources/ui/v2/layers/potion-growth-base-v1.png |
| 6 | mutation_gold_v1 | Compact golden dinosaur-footprint badge with thick outline; collection, detail and hatch mutation labels. | Generated draft: resources/ui/v2/layers/mutation-gold-v1.png |
| 7 | mutation_diamond_v1 | Matching footprint made of pale cyan faceted diamond, crisp edges and restrained sparkles; future Diamond mutation. | Generated draft: resources/ui/v2/layers/mutation-diamond-v1.png; mechanic not verified |
| 8 | catches_v1 | Neutral ivory footprint source; repeat in UI for a grouped catches mark, with live Catches label. | Generated draft: resources/ui/v2/layers/catches-mark-v1.png |
| 9 | inventory_v1 | Prehistoric leaf-and-leather satchel for owned consumables/items. | Optional after item art |
| 10 | index_v1 | Fossil field guide/book with dinosaur emblem, distinct from Dino selection. | Optional if navigation separation is needed |

Deferred until actual products exist: luck boost art, Robux bundle contents and finisher thumbnails. Do not spend the first batch on speculative offers.
Separate export task: render new dino/egg/model and mutation previews when their actual models are ready.

## Production, adjustment and tracking
Generate one asset at a time. Core aura, potion, mutation and catches artwork drafts are generated. Next is owner upload/binding, component assembly and Studio visual verification. Inventory/Index remain optional; no speculative art generation is required. The first draft establishes item-art style; reuse its proportions, camera, outline and lighting for subsequent assets.
Save composed item art under resources/ui/v2/items/ and reusable layer masters under resources/ui/v2/layers/, with versioned names. Preserve existing art. Record each exact prompt in a sibling JSON manifest.
Generated bitmap artwork can be revised through image editing; it is not a layered/vector source. Theme changes control UI frames/text separately and cannot recolor arbitrary bitmap details safely.
Store sources in GitHub; upload accepted runtime PNGs under the Roblox experience owner and record real IDs in the shared asset/theme binding. Never fabricate IDs.
Status sequence: Todo -> Generated draft -> Reviewed -> Uploaded -> Integrated -> Studio verified. Generated does not imply Uploaded or Integrated.
Review true alpha, silhouette at small size, clipping/safe margins, identity and style consistency. Verify actual image permissions/readability in published Studio tests before completion.
