# 216 Art batch 2: shop, mutation, chomp and other icon candidates (2026-10-19)

Status: **candidates only. Nothing is uploaded, nothing is bound, nothing is in the game, nothing was seen in Studio.** The owner picks, then the lead uploads (Decal-to-image-id step, [docs/120](120-pending-owner-uploads-checklist.md)). Task row: BD-1151. Follows [docs/196](196-art-batch1-food-bucket-tier-icons.md) (batch 1). Owner request 2026-10-19: "use ChatGPT for new asset icons in the shops, trail icons, mutations, chomp, and others we are still missing".

## What was made
15 ChatGPT sheets in 4 chats (owner's ChatGPT in his Edge, via Claude in Chrome), 4 ideas for each of **52 icons = 208 candidates**. ChatGPT was told to read the handbook (docs/114 sections 4 and 5, GitHub link in every first message) and every prompt also pastes the key style rules. It did read it (it quoted the aura colours and the amber-crystal rule back). Each chat got the owner's class icon sheet as the style picture.

Columns on every sheet (A to D) are four design ideas, rows are the icons. The same columns were asked for in each category, so the pick is easy: **A = the symbol alone, B = in a round gold coin, C = on a tile / plaque / with a footprint, D = with a glow or sparkles** (details per sheet in `docs/reference/art-batch2-prompts.txt`).

| Category | Icons (4 ideas each) | Evidence picture (review-2026-10-17) |
|---|---|---|
| **Shop** | 3 auras (Meadow Glow, Tidal Halo, Royal Nova), 10 trails, 4 shop tabs (Auras, Trails, Eggs, Conditions) | **521** (all 17) |
| **Mutations** | Shiny, BIG, "mutated dino" marker (the 7 weather badges are untouched) | **522** |
| **Chomp (combat)** | Chomp (bite button), Health heart (full / half / low / heal), Big hit, Alert "!" | **522** |
| **Others** | 4 crystal packs (S, M, L, XL), 4 notices (level up, done, mutation egg, warning), 4 small glyphs (crystal, chevron, arrow, Golden Drumstick), Index tabs (Patterns, Colours), Bonus nest | **523** |
| **Others** | 6 rarity badges (Common to Mythic), 7 cave stations (Nests, Potions, Fusion, Style, Index, Settings, Fame wall) | **524** |

Master contact sheet of all 208 (with 64 px copies and flags): **520**. The 15 sheets with a letter and number ruler (A, B, C, D across; 1, 2, 3 down): **525 to 539** (combat, crystals, glyphs, indexbonus, mutations, notices, rarity1, rarity2, shop-auras, shop-tabs, shop-trails1, 2, 3, stations1, stations2).

Files: sheets `docs/reference/art-batch2-<sheet>-chatgpt-v1.jpg` (saved as JPG q95, not PNG: 15 PNGs were 29 MB; the picture is the same), prompts `docs/reference/art-batch2-prompts.txt`, cut pictures `resources/ui/v2/candidates/art-batch2/` (208 transparent 512 px PNGs, colour-reduced to 256 colours to keep the repo small; see "Next" for the real upload size). Ids: `shop-aura-<meadow|tidal|royal>-<A-D>`, `shop-trail-<white|fern|tidal|ember|violet|electric|frost|solar|nova|astra>-<A-D>`, `shop-tab-<auras|trails|eggs|conditions>-<A-D>`, `mutation-<shiny|big|mutated>-<A-D>`, `combat-<chomp|health|hit|alert>-<A-D>`, `crystals-<s|m|l|xl>-<A-D>`, `notice-<level|done|mutegg|warning>-<A-D>`, `glyph-<crystal|chevron|arrow|drumstick>-<A-D>`, `index-<patterns|colours|bonusnest>-<A-D>`, `rarity-<six levels>-<A-D>`, `station-<nests|potions|fusion|style|index|settings|fame>-<A-D>`.

## ChatGPT chats to delete (owner's history)
1. "Generate aura icon sheet": the SHOP chat (auras, trails, tabs; 5 sheets). My first message starts "Chat name: BeDino Art Batch 2 - SHOP icons".
2. "Generate mutation icons sheet": the MUTATION chat (1 sheet).
3. "Combat HUD Icons": the CHOMP chat (1 sheet).
4. "Crystal Pack Sheet Generation": the OTHER chat (crystals, notices, rarity x2, stations x2, glyphs, index tabs and bonus nest; 8 sheets).
No other chat was opened and no stray chat was started. The tab was closed at the end.

## What went wrong on the way (so the next batch is quicker)
- **ChatGPT first reached for the Figma connector** (it asked "Allow ChatGPT to use Figma?" for its Generate Image tool). That was not allowed; my next message said "use your own image tool, no Figma", the question went away and a normal painted sheet followed.
- In three chats the first answer was "the image generator is not available here" (once it started a code-drawn vector draft; I pressed Stop and nothing of it was kept). Sending "Please try again now: call your built-in image generation tool ... Do not draw it with code or vectors" worked every time. Later sheets in the same chat worked on the first try. So: always open each chat with that sentence in the first message and expect to send the retry once.
- Screenshots of the owner's Edge sometimes time out for 30 s while ChatGPT draws; polling the page text instead is reliable.
- The old cut tool lost icons when objects touch (stacked coins) and ate white clouds. `tools/cut_icon_sheet.py` now cuts by drawn pieces per grid cell when the object count is not exact (cuts the touching coins at the quietest line) and uses a stricter background tolerance (14 instead of 26). Batch 1 was cut with the old tool; its pictures are unchanged.

## Checks (cut tool flags, and my own look at the 64 px copies on the contact sheets)
- 208 of 208 backgrounds removed. EMPTY 0, MUDDY 0, BG-NOT-CLEAN 0. **CLIPPED 1: `station-style-C`** (the plaque ropes touch the top of the sheet: not usable). GAP-CLEARED on 16 pictures where a ring has a hole in it (aura rings, trail D ring, gear): that is wanted (the hole is transparent).
- **Glow versions leave a cream halo.** Where ChatGPT drew a soft glow (column D of the notices, `glyph-chevron-C`, `glyph-drumstick-C`, `index-*-D`, `station-*-B`, `station-index-B`) a flat-background cut cannot keep the soft edge, so the glow becomes a hard cream blob. On a dark panel that looks dirty. Do not pick these; the plain A, B, C versions are clean. Rarity, mythic and a few others have a faint light fringe too: a re-cut with a slightly stronger edge shave fixes it.
- **Looks like another icon:** `rarity-legendary-A` (gold gem) is almost the amber crystal currency, which the handbook section 5.3 keeps for money only, so use the legendary B or C (crown frame). `glyph-crystal-*` is the same gem as the pack icons on purpose. `notice-done-A` and `notice-level-A` are both gold stars (the chevron separates them at 32 px, at 24 px check it). `shop-trail-violet-*` has round orbs, not rings; next to Tidal Wake's bubbles it differs only by colour.
- **Busy at 64 px:** `crystals-xl-*` (vault), mythic frames, `station-*-C` plaques (thin ropes). They still read as "pile of gold", "fancy red gem", "wooden sign", but they are the first to look at in Studio.
- Mismatch to note: docs/109 D1 says Mythic is a "rainbow pearl", handbook 5.2 says Mythic is red #F73930. I drew red with a rainbow shimmer, which fits both.

## Recommendation (best, then second, and why)
| Icon | Best | Second | Why |
|---|---|---|---|
| Aura Meadow / Tidal / Royal | **A** of each (stone footprint in the ring) | C (egg in the ring) | A is the same look as the two owner icons already in `resources/ui/v2/items/` (`aura-meadow-v1`, `aura-tidal-v1`), so Royal Nova (the only aura with no picture) matches; **shop-aura-royal-A** is the one actually missing. D (ring alone, see-through middle) is the one to put over a dino as an effect picture. |
| 10 trails | **A** (swoosh with its motif) | B (in a gold coin) | A is clearly a trail and each has its own colour and motif. B is the most even set if the cards should look like one family. C (footprint) is the same footprint on all ten, so they look alike at 64 px. Note: the 10 Blender trail icons already exist and are bound; these are richer alternatives, owner's taste. |
| Shop tabs Auras / Trails / Eggs / Conditions | **A** for the tab, **C** (tile) for a landing tile | B | The tab strip needs the plain symbol; C is a ready little scene for the landing tile. Crystals tab: use `glyph-crystal-B` or `crystals-m-A`. The existing Blender tabs and tiles are bound; this is an alternative. |
| Shiny | **mutation-shiny-A** | B | Gold four-point star with rainbow glints; not the same as the weather badges. |
| BIG | **mutation-big-B** | A | Footprint with a growth arrow reads "bigger"; green coin gives it colour (A is a brown, dull footprint). |
| Mutated dino marker | **mutation-mutated-A** | C (pill tag) | Egg with droplet, bolt and flame around it says "weather mutation" without text; C fits a card corner. |
| Chomp | **combat-chomp-A** (happy dino head biting a star) | B (round button) | Calm teal and orange, no teeth, not alarm red; the button shape is drawn by code now, so the symbol alone fits. D (cooldown ring) is only a picture of a ring; the real ring should be code. |
| Health heart | **combat-health-A, B, C** as the full / half / low set | D (heal) | One matching trio for the HP bar (red, half, orange low). |
| Big hit / Alert | **combat-hit-B** (white bubble with star, as docs/101 asks) and **combat-alert-A** (orange bubble with "!") | hit-A, alert-B | Match the planned "hit bubble" and "predator noticed you" marks. |
| Crystal packs S / M / L / XL | **A** of each | D (tile) | Pouch, bag, chest, vault: size is obvious. Amber only, no blue. |
| Notices | **A** of each (level star, done star, mutation egg, warning) | B | Clean, no glow halo. Warning is friendly orange-red, not scary. |
| Small glyphs | **crystal-A, chevron-A, arrow-A, drumstick-A** | crystal-B, arrow-B | They read at 24 px. The chevron is symmetric, so the game can turn it. |
| Rarity badges (6) | **B** (shield with frame) | A (gem alone) | The frame gets fancier up the ladder, so rarity is clear without colour only. Not `legendary-A` (looks like the money crystal). |
| Cave stations (7) | **A** (round stone medallion) | D (symbol alone) | Same cream-stone and moss look for all seven. Not `station-style-C` (clipped), not the B glow versions. |
| Index tabs / Bonus nest | **index-colours-A, index-patterns-A, index-bonusnest-A** | B | Patterns A is an egg with a skin pattern; if that is confusing next to the Eggs tab, take B (in a coin). |

## Not done (and why)
- **Nothing uploaded or bound.** No asset id exists. After the owner picks: upload as Image in Studio (docs/120), `tools/bind_assets.py`, one docs/77 line per chosen picture, Studio look at 64 px and on a phone.
- **Not drawn by ChatGPT here:** the 8 Pattern Index tiles (separate tile task, BD-1039); the 7 weather mutation badges (approved final, untouched); potion icons (12 exist, bound); Gold and Diamond tier badges (they exist; batch 1 has matching Emerald/Gold/Diamond sets); 5 potion rarity frames (9-slice, needs a special layout), toast plate (9-slice); Rainbow sheen texture (Blender render); Golden Drumstick **mesh** (3D).
- **Listed, recommended, not made:** 31 dinosaur pictures (better as 3D renders of the low-poly dinos, one lighting setup: BD for the dino pictures are a Blender job); 6 biome pictures, 4 landmark pictures and 3 statue pictures (render them from the world models or screenshots, a ChatGPT picture would not match the models); "tired / stamina" icons (the code has no stamina: nothing to draw).
- **Slots with no art yet that this batch covers:** `aura_royal`, `rarity_*` (6), `notify_level`, `notify_star`, `notify_mutation_egg`, `notify_warning`, `notify_crystal`, `objective_chevron`, `objective_arrow`, `hud_heart`, `hud_bite`, `hud_hit_bubble`, `crystals_s/m/l/xl`, `station_*` (6), `fame_plaque`, `golden_drumstick_icon`, `index_tab_patterns`, `index_tab_colours`. The `hud_class_1..3` slots are old (class badges exist as `class_*`). No slot was filled.
- Not checked in Studio or on a phone. 64 px readability was only judged on the contact sheets.

## Next
The owner picks from pictures 520 to 539; **size warning:** one icon on a sheet is only about 360 x 360 px, so the 512 px pictures are already stretched a little. That is fine for choosing and for a 64 to 128 px UI slot, but for a big card (shop card, Fusion) ask ChatGPT for the chosen icon alone on a 1024 px canvas (same prompt line, one object, flat background), cut it with the tool, then upload and bind ([BD-1151](kanban/rows/BD-1151.md)). Batch 3 candidates: the dino and biome/landmark/statue pictures as Blender renders, potion rarity frames and toast plate (special 9-slice sheets), Rainbow sheen, Pattern tiles.
