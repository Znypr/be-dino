# 228 UI "Toybox" proposal: shops, HUD, hatch, stall, motion (BD-1177 to BD-1182)

Written 2026-11-12. **Status: DESIGN PROPOSAL, nothing built.** No game code, no Studio, no profile change. The owner asked for new UI designs "based on everything you learned, including animation, shop looks", using popular Roblox games as reference. The owner rejected the first version as "too low quality" and said to look at what the games actually look like. Version 2 was rebuilt from the real reference screenshots. The owner then asked for kanban rows (2026-11-12).

- **Live mockups:** design canvas https://claude.ai/artifact/TXDKNwzG5rmzpCWfS7FW4A (private to the owner; 6 boards, live CSS animation, clickable shop, hatch and stall).
- **Pictures (our own art only):** `docs/evidence/2026-11-12-ui-toybox/01-main.jpg` to `08-motion.jpg`. These are local headless-Chrome renders of the canvas boards. No third-party picture is in the repo (rule in [202](202-ui-standards-from-steal-an-egg-and-ride-a-dino.md) section 0).
- Read with [202](202-ui-standards-from-steal-an-egg-and-ride-a-dino.md) (standards, R1-R15), [212](212-hud-rail-with-words.md), [213](213-shop-card-price-button.md), [72](72-ui-copy-and-asset-standards.md), [87](87-vision-and-feel-guide.md), [114](114-handbook.md) s4-5.

## 1. What the references actually look like (seen in the local shots)
Sources: `be-dino-reference-shots/` (local only): Grow a Garden `gag-1-seed-shop-window.jpg`, owner shot OW-10 (AURAS window), Steal An Egg gallery `reference-212704` to `212837` (Shop, Trail Shop, Pet Index, Sell Eggs, Featured).

| Trait | Seen in | What we had | Proposal |
| --- | --- | --- | --- |
| Panel body | SAE, OW-10: dark charcoal with a Lego **stud** texture | flat #2A2835 | stud-texture panel (art asset, 9-slice) |
| Header | SAE Shop/Trail Shop: bright 2-tone gradient + **diagonal shine stripes**, title left, thick stroke | flat colour bar | glossy striped header per place (amber shop, green potions, blue dinos, purple fusion) |
| Close | every window: square **red gradient X**, white X with stroke | small X | 56-62 px red gloss square |
| Cards | OW-10, SAE Trail Shop: **whole card in tier colour**, studs, cream inner art box, big 3D art, one benefit line, one wide button | small dark cards | same structure; cream box with slow light rays behind our item art |
| Buttons | all: **two-tone gloss** (light top half), 8-10 px corners, black edge, price ON the button | flat | green buy/equip, grey sold out / unequip, crystal icon + number on the button |
| Text | all: heavy rounded font, **4-7 px black stroke** + drop | thin outline | `TextStyle` stroke 3-4 px (Roblox `UIStroke`), drop shadow |
| Side tabs | SAE Sell Pets/Eggs: square tabs on the right, **art spills over the top** | text tabs | side tabs with item art |
| Shop as shelf | Grow a Garden: wood planks, grass stud header, inset brown art slot, "X5 Stock", green price, grey rarity pill | potion list | wooden "Potion Shelf" with "3 left", rarity pill, price button; **no paid restock button** |

Kept from our rules: amber crystals, kid words ("+20% Speed", never "x1.2"), no countdown pressure, no "LIMITED", Reduce Motion for every animation, red only on X.

## 2. The six boards
1. **Toybox kit**: window, words, buttons, rarity cards, HUD pieces.
2. **HUD at home**: six art tiles in a 2x3 grid (Shop, Dinos with a red count dot, Eggs, Fusion, Potions, Home). Wallet pill with the amber crystal spilling out. Egg counter. Weather and potion chips with a drain bar. Two-line news "AURORA SKY!" with coloured words. A crystal flies from the dino to the wallet.
3. **Crystal Shop**: amber glossy header, wallet, red X, "-- AURAS --", 4 tier-coloured cards (Equip / Unequip on the equipped one with a gold glow ring / "470" price / locked Legendary "?" with "Find it in Volcano"), side tabs (Auras, Trails, Eggs, Nests), confirm popup "Buy Royal?" with price and "Not now".
4. **Hatch reveal**: spotted egg on soft rays wobbles, shakes on tap. Then a soft white flash, blue rays, a tilted "RARE!" in the rarity colour, the dino pops in, sparkles, "Charged Compy" with the mutation badge, "3 of 6 for Gold!" bar (BD-1170), Next egg, egg queue strip, Skip the rest.
5. **Potion stall**: big "POTIONS" word, striped awning, wooden body, keeper, potions on the counter, "Pip's Potions" front sign, glowing ground ring, white speech bubble with the E key. Wooden "Potion Shelf" window.
6. **Motion spec**: window opens 0.3 s with a back-out to 103%. Cards 70 ms apart, 0.4 s each, at most 8 staggered. Button sinks 5 px in 80 ms. News drops in at top centre for 2.5 s. A reward flies to the wallet in 0.5 s and the wallet bumps 118%. Legendary+ shimmer every 2.8 s. Everything still under Reduce Motion.

## 3. LEAD notes and open points
- **Art rule ([72](72-ui-copy-and-asset-standards.md)):** the stud texture, glossy header strip, gloss button and red X are UI art. In the mockup they are CSS. In the game they must be drafted image assets (9-slice) through the art flow (brief, 2-3 drafts, pick, export, registry line). They must not be code-drawn final art. BD-1177 covers that.
- **Feel check ([87](87-vision-and-feel-guide.md)):** the references are louder than our vibe. The proposal keeps the build (studs, gloss, stroke) but uses slow rays, no strobe, a soft flash under 0.5 s and no countdowns. The owner judges the result in Studio.
- Art used in the mockups is our own: potions, auras (Royal is still the art-batch2 A candidate), amber, eggs, compy preview, mutation badge, rail icons. A real Legendary aura picture does not exist yet.
- **Not verified:** the canvas inside claude.ai (only local renders were looked at), phone size, Studio, a child.

## 4. Rows
BD-1177 kit (P1, first), BD-1178 Crystal Shop (P1), BD-1179 hatch reveal (P2), BD-1180 HUD tiles (P2), BD-1181 potion stall (P2), BD-1182 motion presets (P2). Each row is flag-off by default and needs Studio and phone evidence before Done.
