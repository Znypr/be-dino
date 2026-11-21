# 243 Menus like the top Roblox games: study and proposal (2026-11-17)

Owner 2026-11-17: "not all ui menus really look like the top famous roblox experiences, i want you to study like top 5 roblox famous games and their menus, like steal an egg, grow a garden, etc. we need menus looking like that, full indepth".

Status: **study + spec + backlog.** The owner's message is the decision (newest owner statement wins over the cream pick of 2026-11-14); the body style is a LEAD decision (docs/115, BD-1252). Nothing in the game changed because of this page yet. It corrects [242](242-full-benchmark-2026-11-16.md) row 11, which called menus "covered": they follow our own style tile ([240](240-cohesion-style-bible.md)), not the top games.

**Full proposal sheet** (owner 2026-11-17: "build full proposal sheet of new menus"; decision aid, our own art only): `docs/evidence/2026-11-17-menu-study/menu-proposal-sheet-v2.jpg` (every window, section 4b), generator `tools/menu_study_mock.py`. First board (3 windows): `menu-mock-v1.jpg` in the same folder. Today's windows for comparison: `docs/evidence/2026-11-17-final-checks/phone-828x374-potion-shop.jpg` (PR #627; panel D of the board), `docs/evidence/2026-11-15-cohesion/current/index.jpg`.

## 1. What I looked at (and what not)

Stills only, watched in the built-in browser, nothing downloaded, no third-party picture in this public repo.

| Game | Source | Menus seen |
| --- | --- | --- |
| Steal an Egg (SAE) | the owner's own shots in `be-dino-reference-shots` (local only): Dino Index, Auras, Fuse Machine, Shop, Trail Shop, Sell Pets, Sell Eggs, Pet Index, Boss Mastery, Dr Scramble | 10 windows |
| Grow a Garden (GAG) | YouTube n3WqE8Pzf8M t=112 (old seed shop), pqqBkvkAbpg t=201 (fall 2025 "Sell your pets!") | seed shop, sell window, HUD |
| Pet Simulator 99 (PS99) | YouTube mg_tER6-zms t=330, 600 | HUD, Exclusive Shop window |
| Bubble Gum Simulator INFINITY (BGSI) | YouTube yc5wXJvGP4Q t=400 | season rewards window |
| Steal a Brainrot (SAB) | YouTube P0W_sV66aw0 t=60-420 | HUD only (it keeps menus to a minimum) |
| Adopt Me! | not re-watched this time; [242](242-full-benchmark-2026-11-16.md) AM-A/AM-B notes used | egg popup, odds panel |

Not judged: animation of windows opening (stills only), sound, phone sizes of the other games.

## 2. The menu grammar the top games share

Ten rules that hold in at least four of the six games. "Be Dino today" is the playtest build of 2026-11-17.

| # | Top games do | Seen in | Be Dino today | Gap |
| --- | --- | --- | --- | --- |
| G1 | **The window is smaller than the screen** (about 55-75 % wide) and the world stays visible around it, no dark cover | SAE, GAG, PS99, BGSI | Windows fill the screen (compact: 1250 of 1274 px) over a scrim | High |
| G2 | **Each menu has its own header colour** (SAE: blue Index, lavender Auras, magenta Fuse, green Shop; GAG pink sell; PS99 orange event) with a glossy stripe, big white outlined title on the left, an icon beside it | SAE, GAG, PS99, BGSI | One header colour per place (green shop, grey settings); title fine | Med |
| G3 | **A dark or themed body** (SAE dark studs, GAG chocolate wood, BGSI patterned blue) so the colourful cards pop | SAE, GAG, BGSI | Cream body and cream cards (docs/240 R1 forbids dark plates) | **High** (this is the main look difference) |
| G4 | **Cards are filled with their rarity colour** (SAE whole card, BGSI frames, GAG rarity word in colour) and the item art is big | SAE, BGSI, GAG, PS99 | Cream cards for every rarity; rarity is a word or chip | High |
| G5 | **Every card has its own action button** (Equip, price pill, Unequip) in green; the window's main action is the biggest | SAE, GAG, PS99 | One green button per screen (R3); the Potion Shop already has one per card | Med |
| G6 | **Tabs are big square icon tiles outside the window** (GAG left strip, SAE right Eggs/Pets/World) or pills above its top edge (BGSI) | GAG, SAE, BGSI | Tabs are flat chips inside the window | Med |
| G7 | **Huge outlined progress**: "Unlocked: 14/55" with a fat bar, "COMPLETE! 6/6" bars, region reward boxes | SAE, PS99, BGSI | Index has "Found 1/22 * 5 more: +50" in a thin footer | Med |
| G8 | **Live info in the header**: restock timer, currency chip, "Ends in 19 days" | GAG, PS99, BGSI, SAE | Potion Shop has "New in 1 min" as a chip; other windows none | Low |
| G9 | **Locked things are silhouettes** ("???" on a coloured card) | SAE, PS99 | Silhouettes on cream (BD-1230) | Low (colour only) |
| G10 | **Something breaks the frame**: a 3D icon over the top-left corner, a "Brand New!" ribbon, the X on the corner | PS99, SAE | Nothing breaks the frame | Low |

What we already match: red square X, chunky outlined font, price on the button, rarity words, real item art, kid-safe shop rules (no Robux lines, odds shown).

**Do not copy** (kid-safe and owner rules, unchanged): Robux packs, countdown pressure on paid offers, crossed-out prices, "Sell" of a player's dinos for money without a confirm.

## 3. Why we drifted

Our Toybox kit (`resources/ui/v2/toybox/final/`) already IS this grammar: dark stud tile, dark panel frame, coloured glossy headers (blue, green, purple, amber, red), rarity cards with studs (`card-common` ... `card-mythic`), coloured buttons. The cohesion pass ([240](240-cohesion-style-bible.md) R1 "no dark plates", owner pick "bright cream A" 2026-11-14) laid cream panels and cream cards on top of it, so every window became the same calm cream page. That fixed the "vibe coded" mix, but it moved us away from what top games look like.

**Mismatch, resolved:** docs/240 R1 + R3 + the cream pick (owner 2026-11-14) vs this request (owner 2026-11-17). The newer owner statement wins for menu windows; cream stays for small text plates (HUD, toasts, chips). Recorded in docs/115 (BD-1252).

## 4. Proposal (mockup board A-C)

- **A Dino Index:** blue header, a biome card on the left with its "find all" reward, rarity-filled dino cards (locked ones as "???" silhouettes on their colour), the selected dino large on the right with CLAIM ALL and Variants, a fat "Found: 14 / 55" bar; Colours / Patterns as tiles outside the window.
- **B Potion Shop:** purple header, crystals chip and restock line in the top row, six rarity-filled cards each with its own green price button, Potions / Auras / Trails / Crystals as big tiles left of the window.
- **C Fusion:** one page that explains itself with pictures (3 slots, lines to the result, one big FUSE!).
- Every window: about 65-75 % of the screen wide, dark studded body, header colour per menu, red X, world visible.

### 4b. The full sheet: every window (v2)

| # | Window | Header | What changes against today |
| --- | --- | --- | --- |
| 1 | Dino Index | blue | rarity-filled cards, ??? silhouettes, region card with its reward, CLAIM ALL, fat "Found 14 / 55"; Colours / Patterns tiles outside |
| 2 | Dino detail | blue | the dino big on its rarity card; Class / Size / Looks as dark plates with icons; copies bar; EQUIP green + FUSE purple |
| 3 | Eggs and nests | amber | five nest cards with live state (Ready! / 3 min / Empty / Locked); the egg big; one huge OPEN EGG |
| 4 | Shop (landing) | green | one FEATURED banner (Rainbow Egg, crystals price, "New in 2 h"); Eggs / Auras / Trails / Colours as big coloured tiles |
| 5 | Egg chances | amber | one row per rarity in its colour with "1 in N" in big numbers; rare ones as silhouettes; OPEN 1 / OPEN 3, Exact % |
| 6 | Potion Shop | purple | rarity-filled potion cards, a price button on each, crystals + restock line on top; shop tabs as tiles left |
| 7 | Auras | red | big aura art on rarity cards; EQUIPPED grey, EQUIP green, price green, Locked dark |
| 8 | Trails | blue | the same card grammar, price under each picture, OWNED grey |
| 9 | Fusion | purple | the rule told with pictures: 3 slots, lines, the result, one FUSE! |
| 10 | Home (Sanctuary) | green | the dino big, three facts with icons, a giant EXPLORE!, OPEN EGGS, Change dino |
| 11 | Run complete | amber | the trophy, "You found 3 eggs!" with the eggs as pictures, four number plates, OPEN EGGS + HOME |
| 12 | Defeat | amber | "Your eggs are safe!" first in green, eggs shown, crystals kept, PLAY AGAIN |
| 13 | Settings | dark | calm on purpose: rows as dark plates with icons, green sliders; Sound / Look / Controls / Help tiles |
| 14 | Food guide | green | food big on cards from plain to rare, "+N grow" in green, one tip plate, GOT IT! |
| 15 | Buy confirm | amber | small window, the only one that dims the world; the egg as a picture, price, BUY / CANCEL |
| 16 | Codes and gifts | purple | white type box + GO!, the group gift as a golden card |

Not windows, so not on the sheet: the hatch (a full stage, BD-1179), HUD, toasts and world labels (cream plates stay, rule G3).

Style-tile changes this needs (docs/240, done with BD-1252): R1 becomes "dark studded body, cream only for text plates", R3 becomes "one green button per card, the window's main action biggest", R4 becomes "rarity colour fills the card".

## 6. Asset audit for the new menus (owner 2026-11-17: "make sure to not use placeholder assets, find out which assets we have and which we might have to redo with chatgpt")

Every picture the proposal sheet uses, checked against docs/77, AssetSlots / ProgressionConfig ids and a look at the files. Side-by-side of the weak ones: `docs/evidence/2026-11-17-menu-study/icons-today-vs-candidates.jpg`.

**A. Final, in game, keep (no redo)**

| Pictures | Made by | Where |
| --- | --- | --- |
| Toybox kit: 7 headers, studs tile, panel frame, 6 rarity cards, 8 buttons, red X | Blender, owner picked draft A 2026-11-13 | `resources/ui/v2/toybox/final/`, AssetSlots `toybox_*` (docs/77 rows still say "not uploaded": stale, the ids are bound) |
| 12 potion icons | owner ChatGPT | `resources/ui/v2/items/potion-*.png` |
| 3 auras (Meadow, Tidal, Royal) | owner ChatGPT | `items/aura-*-v2.png`, AssetSlots `aura_*` |
| 6 station icons, 6 rarity badges, 4 crystal sizes, Index Colours / Patterns tabs | owner uploads 2026-11-14 | AssetSlots `station_*`, `rarity_*`, `crystals_*`, `index_tab_*` |
| 4 class badges, trophy, home, fusion, heart, star, level, crystal glyph, weather | owner ChatGPT / earlier icon sets | `resources/ui/v2/icons/` |
| 5 egg pictures (dirty, normal, rainbow, astra, cracked), nest | Blender renders | `resources/ui/v2/stage/eggs/`, `icons/egg-nest*` |
| 4 food pictures | owner ChatGPT batch 1 | `items/food-*-v1.png` |
| V3 dino cutouts | owner (Place1 v3) | main checkout `resources/ui/v2/dinos/v3/` (not in git yet: add them before the cards use them) |
| 7 mutation badges | Blender (BD-190) | `icons/mutation-*-v1.png` |

**B. Placeholder-looking, replace with the ChatGPT candidates we already have (owner picks, then upload and bind)**

| Pictures | Today | Ready candidates (docs/216, owner style) | Recommended |
| --- | --- | --- | --- |
| 10 trail icons (white, fern, tidal, ember, violet, electric, frost, solar, nova, astra) | flat Blender symbols (cloud, leaf, bubbles, flame, rings, sun, star) | `candidates/art-batch2/shop-trail-*-A..D.png` | **A** (a swoosh with its motif, reads as a trail) |
| Shop tabs Auras / Trails / Colours / Eggs | flat Blender symbols | `shop-tab-*-A..D.png` | **A** for tabs, **C** (on a tile) for the Shop landing tiles |
| Shop landing tiles (Eggs, Auras, Trails, Colours) | Blender scenes on a flat colour | same `shop-tab-*-C.png` | **C** |

**B done 2026-11-17 (owner picks: "trail Ds, shop tabs Cs, auras Ds"; B gold coin rejected):** 10 trails D (`icons/trail-*-v2.png`), shop tabs and landing tiles C (`icons/shop-tab-*-v2.png`, `icons/shop-tile-*-v2.png`, tabs and tiles share one picture), 3 auras D (`items/aura-*-v3.png`). Converted to RGBA (palette PNGs never load), uploaded, image ids bound (AssetSlots, ProgressionConfig.TrailIconAssetIds), docs/77 rows. Studio: `docs/evidence/2026-11-17-menu-study/studio-trails-D.jpg`, `studio-shop-tiles-C.jpg`, `studio-auras-D.jpg` (all 17 load). Left in group B: the **Crystals** tile and tab are still the flat Blender picture (no candidate in this set: use the owner's `crystals_m` upload or make one, group C below). Unused uploads: the A versions of the trails and tabs (uploaded first, before the owner's pick; not bound).

**C. Missing: make new with ChatGPT (owner's account, same style prompt as docs/216: glossy, thick dark outline, transparent PNG, one icon per picture at 1024 px)**

| Needed by | Picture | Prompt idea |
| --- | --- | --- |
| Settings tabs | Sound (speaker), Look (paint palette), Controls (game pad), Help (question bubble) | four tab icons, same family as the station icons |
| Codes window | a gift box with a ribbon (window icon) and a treasure chest (group gift) | gift box closed; chest half open with amber glow |
| Dino Index | 6 region pictures (Meadow, Beach, Forest, Marsh, Volcano, Cave) for the region card | small square landscape vignette per biome, low-poly island style (or Studio renders of our own world) |
| Crystal Shop | the Crystals tab / tile in the same C style (crystals on a tile) | three amber crystals on a rounded tile, like the C tab set |
| Shop featured banner | a wide banner background (sky + confetti) behind the featured egg | 3:1 banner, no text |
| Big trail / shop cards | the picked trail / tab icons once more at full size (candidates are about 360 px stretched to 512) | "the chosen icon alone, 1024 px" (docs/216 size warning) |

Code-drawn things that stay code (allowed, docs/72): the "?" on a locked card, bars, number plates, the dark tint on a locked silhouette.

**Build order with art:** the window frame, header colours, dark body and rarity cards use only group A, so they start now. Trail cards, shop tabs and tiles switch to the picked group-B pictures once uploaded; until then those screens keep today's icons behind the flag-off path (no placeholder is shown in the new look: Trails and the Shop landing join the new look only after the pick).

## 5. Backlog (priority order, nothing built yet)

| Row | What | Why first |
| --- | --- | --- |
| BD-1252 (P1) | Update docs/240 R1/R3/R4 for menu windows (decision recorded in docs/115) and re-judge the matrix rules | Every other row builds on the new rules |
| BD-1253 (P1) | Window size: 65-75 % wide on desktop and phone, world visible, no scrim; same frame for every window | Biggest single difference (G1) |
| BD-1254 (P1) | Dark studded body + per-menu header colour + rarity-filled cards in the kit (Layout.panel / card helpers), behind a new flag `MenusTopLookEnabled` | G2, G3, G4: most of the look |
| BD-1255 (P2) | Tabs as icon tiles outside the window (Shop, Index, Eggs) | G6 |
| BD-1256 (P2) | Index: fat "Found x / y" bar, biome reward card, CLAIM ALL | G7 (ties to BD-1230 milestones) |
| BD-1257 (P3) | Header live info (timers, currency chip) and one frame-breaking icon per window | G8, G10 |

Phone rule stays: every window and tab tile checked at 634x344 and 828x374 (BD-1241 method), targets at least 44 px.

## 7. Built (2026-11-17, owner "Yes, build it"): first slice behind `MenusTopLookEnabled` (playtest on)

Studio pictures (playtest build, 1274x481): `docs/evidence/2026-11-17-menus-top-look/` (go-home-confirm, run-complete, run-complete-eggs, home-sanctuary, settings, eggs, dino-index, fusion, potion-shop, auras, shop-landing).

| Rule | Done | How |
| --- | --- | --- |
| G1 world visible | partly | the cover behind a window is light (0.82 instead of 0.42); the window is still as wide as before on short screens (needs BD-1253 sizing, after PR #627's frame margins) |
| G2 header colour per menu | yes | `Kit.TopLookHeader` / `Kit.useTopLook` (green Shop and Home, purple Potions and Fusion, blue Dinos, amber Eggs, Run complete and Go home?, dark Settings, green Food guide) |
| G3 dark studded body | yes | ToyboxLayout draws panels, cards, chips and words dark with white outlined text inside `ModalScrim` / `FusionScrim` only; HUD, toasts and cues stay cream |
| G4 rarity fills the card | Index, Potions, Auras (already), Shop tiles | DinoIndexList, PotionToyboxPage, ShopTiles; Trails cards next |
| G5 a button on every card | Potions, Auras, Shop tiles | green OPEN on each Shop tile |
| G6 tabs outside | not yet | BD-1255 |
| G7 fat progress | not yet | BD-1256 |
| G8 / G10 | not yet | BD-1257 |

Known gaps seen in the pictures: Shop landing and the first-eggs "Great job!" page still lay out for the old 824 px width (content sits left on a wide screen), toasts still cover a window's button (BD-1249), the Crystals tile keeps its old picture (section 6).
