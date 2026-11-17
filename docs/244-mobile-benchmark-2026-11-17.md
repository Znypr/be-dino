# 244 Mobile benchmark on the owner's phone (BD-1258 to BD-1270), 2026-11-17

Owner 2026-11-17, after playing the playtest build on a Samsung S23 Ultra: "dino shadows are really low quality, ui is really messy and all over the place. and overlapping often, tiny font sometimes". The owner asked for a comparison with famous Roblox experiences **on mobile**. Later the same evening the owner said: "use my phone instead for current famous games on phone, but prio private servers", "click everything and get a full understanding of the full UI menus, settings, shops, where ui is placed how big", and "prio steal an egg, and ps 99".

This page adds the phone view to [242](242-full-benchmark-2026-11-16.md) (every aspect, desktop stills) and [235](235-top-games-benchmark.md) (retention). It does not repeat them.

## Method and limits (read first)

- **Be Dino (CURRENT BUILD):** the playtest build on the private newbuild place, played by the lead on the owner's phone (3088 x 1440 landscape). Four screenshots: `docs/evidence/2026-11-17-phone-real/bedino-01-loading.jpg`, `bedino-02-spawn.jpg`, `bedino-03-walk-volcano.jpg` and `bedino-04-toast-overlap.jpg` (stored at half size, 1544 x 720; all pixel numbers below are converted to 1440 px height).
- **Top games, on the same phone (owner's account):** Steal an Egg (SAE), Pet Simulator 99 (PS99), Grow a Garden (GAG, in the owner's private server), Steal a Brainrot (SAB), Bubble Gum Simulator INFINITY (BGSI), Adopt Me! (AM). These were launched over adb with `roblox://placeId=...` (the home screen was never captured). I opened every HUD button and each menu tab and captured it with `adb exec-out screencap`. There are 60 captures, stored **local only** in `C:\Users\znypr\Documents\be-dino-reference-shots\mobile-2026-11-17\phone\`, never committed. File names are cited below (for example `sae-phone-02-hud.png`). Nothing was bought: no Robux button, Claim, Rebirth or Play-with-consent button was pressed.
- **Before the phone, YouTube phone recordings** (stills, same local folder): GAG `7dOSBWhSctM` ("I Play Roblox Grow A Garden On MOBILE...", 2025-06-09) at t=300 and t=700; PS99 `IgPxlAGI7mA` ("Pet Simulator 99 Gameplay Walkthrough Part 3 (iOS, Android)", 2025-05-04, a real phone recording) at t=80 and t=100. Desktop-recorded or pre-2025 videos were rejected (`guOxyi6ATkA`, `TeFsGfVab6Q`, `f4KDke0NLKQ` from 2022, `7zk-oXSbBg8` from 2023).
- **Not covered:** Adopt Me in game (its Play button accepts an updated privacy policy, so the owner has to press it), BGSI menus (a fresh profile; my walk got stuck in a tree and the phone was down to 12 % battery), walk-up shops in SAE and PS99 (blind joystick walking hit walls; a 2-minute auto-capture while the owner walked caught no walk). Covered for GAG (the seed stall, `gag-phone-04-shop-shadows.png`). **No sound was heard, and motion was not judged.**
- **Text sizes** are cap heights read off the screenshots with a 20 px ruler, about ±10 %. From our EGGS label (TextSize 30 renders 63 px), TextSize N is about 2.1 x N px of cap height on this phone.

## 1. Real-phone performance (Be Dino playtest, measured over adb by the lead)

| Moment | Result |
| --- | --- |
| Spawn, idle | 60.8 fps |
| Walking | 61.5 fps |
| Walking and turning, 40 s | 60.7 fps (Roblox caps at 60) |
| Memory (PSS) | 1.64 to 1.73 GB |
| Battery temperature | 30.8 °C |

Performance is not the problem. The look and the layout are.

## 2. Topic by topic (SAE and PS99 first, owner priority)

Priority: **P1** = the owner named it or a player sees it in the first minute; **P2** = within a session; **P3** = polish.

### 2.1 HUD frame and safe areas

| Game | What they do on the phone (source) |
| --- | --- |
| SAE | Left-middle: two big word buttons (Shop, Index) and a Slow Mode toggle. Right-middle: a column of 3 square icons (eggs, pets, fishing). Bottom-left: money above the joystick. Bottom-centre: a 2-slot hotbar. Bottom-right: jump, a lock button and the event timer. Top-centre: the server event line only. The middle of the screen is empty (`sae-phone-02-hud.png`). |
| PS99 | Left: a 3-wide icon grid, then currencies, then potions beside the joystick. Right: the quest list and one big green Rewards button. Top-centre: one quest card. Bottom-centre: the pets button. The middle is empty (`ps99-phone-05-hud-clean.png`; video `IgPxlAGI7mA` t=100). The main nav (shop, index, trade, clan, settings) appears as a right-hand rail **only while the pets menu is open** (`ps99-phone-08-pets-inventory-rail.png`). |
| GAG | Top: the Roblox bar plus settings, backpack and tools icons, then SEEDS / GARDEN / SELL word tabs top-centre. Left-middle: 4 word buttons (Shop, Trade, Pass, Guide). Bottom-left: money and Friend Boost. Bottom-centre: a 6-slot hotbar. The middle is empty (`gag-phone-07-hud-ps.png`). |
| SAB | Left: a 2 x 3 grid of square icons with small words under them (Shop, Rebirth, Index, Duels, Trade, Codes). Bottom-left: money. Bottom-centre: a 5-slot hotbar. Top-centre: an event countdown (`sab-phone-02-hud.png`). |
| BGSI | Top-centre: the quest card. Left-middle: 2 resource bars (bubbles, coins). Bottom-centre: a height bar. Nothing else on a fresh profile (`bgsi-phone-03-hud-onboarding.png`). |
| **Be Dino** | Top-centre: POTIONS, the shield badge, the health bar, the SIZE bar and the hint line, all stacked **over the dino**. Top-right: two wide cream plates (crystals, weather) with one short line each. Top-left: EGGS. Bottom-centre: HOME, and Admin (owner only). Right: LEAP and CHOMP (`bedino-02`, `bedino-04`). |
| **Gap** | Every top game gives each corner one job and keeps the middle third free. We put five things in the top centre over the character, and the right-hand plates are mostly empty space. |
| **Fix** | **BD-1258 (P1)**: zones with numbers (the row has the full list). |

### 2.2 Button sizes and spacing (px at 1440 height)

| Game | Measured |
| --- | --- |
| SAE | Shop and Index are 290 x 112, 20 px apart. The right icons are 120 x 120, 45 px apart. |
| PS99 | Left icons about 140 x 140. Rewards is 520 x 140. Menu X is 200 x 190 (`ps99-phone-06-free-rewards.png`). |
| GAG | Rail buttons 335 x 145, 18 px apart. Hotbar slots 260 x 210. |
| **Be Dino** | LEAP and CHOMP 360 x 150 (fine). HOME 450 x 150. The POTIONS row is a 140 px icon plus a word with no plate. The weather and crystal plates are 740 x 160 and 600 x 120 for one short value. |
| **Gap** | Our sizes are fine. The waste is plates far wider than their text. |
| **Fix** | BD-1258 (zones), BD-1259 (plates shrink to their text). |

### 2.3 Font sizes and outlines (cap height at 1440 px)

| Text | px | Style |
| --- | --- | --- |
| SAE Shop / Index | 57 | white, thick dark outline |
| SAE money "$7.7T" | 68 | green, dark outline |
| SAE "Slow Mode" | 33 | white, outline (their smallest) |
| PS99 quest lines | 39 | white, dark outline |
| PS99 currency "71.3m" | 45 | white, dark outline |
| GAG rail words | 48 | white, outline |
| GAG hotbar words | 36 | white on a dark plate |
| SAB rebirth warning | about 20 | tiny (their weak spot, `sab-phone-05-rebirth-small-text.png`) |
| GAG Guide tab words | about 20 | tiny (their weak spot, `gag-phone-13-guide-profile.png`) |
| **Be Dino crystal count "3"** | **27** | dark on cream, no outline |
| **Be Dino weather "Next: 1 min"** | **33** | dark on cream, no outline |
| **Be Dino toast "You found 2 eggs!"** | **33** | dark on cream |
| Be Dino EGGS 6 | 63 | dark on cream |

**Gap:** the top games keep main HUD words at 45 to 68 px, always outlined. Small text appears only inside menus, and the owner noticed it in theirs too. Ours goes down to 27 px on the HUD itself, with no outline. **Fix: BD-1259 (P1)**: no HUD word under 40 px (about TextSize 19), counters and button words at least 50 px (TextSize 24), and a dark outline of at least 2.5 design px on every word over the world.

### 2.4 Toasts and popups

| Game | What they do (source) |
| --- | --- |
| SAE | Server news as one line of outlined text with an icon, straight under the Roblox bar, no card ("A Secret Tideler Egg spawned in Alien Planet!", `sae-phone-12`; "Skyfall is happening in Stormlands! Ends in 2:18", `sae-phone-14`). Menus: a centred modal about 57 % wide with a red X on the corner; category tabs sit **outside** the modal on its right (Featured, Stars, Speed, Money, `sae-phone-03` to `06`). The HUD stays visible. Pets and eggs open as small drawers on the right, not modals (`sae-phone-08`, `09`). |
| PS99 | Short news as red outlined text in the middle of the world, no box ("Speed Potion II has run out!", `ps99-phone-13`). Every menu is a centred white modal about 42 % wide with a big red X, the HUD hidden, and only the currency row left at the bottom centre (`ps99-phone-04`, `06`, `07b`, `09`, `12`). Menus share one header tab strip (teleport, settings, potions and so on). Login and What's New popups come one at a time at join (`ps99-phone-03`, `04`). |
| GAG | Modals with a blurred world behind them, the HUD rail hidden, the X small and red on the header (`gag-phone-08` to `14`). |
| SAB | A compact modal (37 % wide), blurred world, tabs in the header; "Someone is stealing your X" as outlined text above the hotbar (`sab-phone-03`, `04`). |
| **Be Dino** | The toast is a cream card at y 80, which lies **on the SIZE bar and the health bar** (`bedino-04`). ToastSlot's keepClear list does not contain the SIZE bar, the hint, the POTIONS row or the shield. |
| **Gap** | Nobody puts a toast card over their HUD. They use one outlined line in a free lane. |
| **Fix** | **BD-1260 (P1)**: one bottom-centre lane above HOME, outlined text and no card, every HUD rect in keepClear. |

### 2.5 World labels

| Game | What they do (source) |
| --- | --- |
| SAE | Pickups: a small icon chip with a number ("10T", `sae-phone-13`). Signs on the boards themselves. |
| PS99 | Zone signs float ("Fantasy World! World 4"), and the chest label "Void Chest! Requires Key" **runs under the Roblox bar** (`ps99-phone-15`, `16`). |
| GAG | Plant names with mutation lists **overlap the money corner** (`gag-phone-03`). |
| **Be Dino** | "+3 Crystals" is **cut off at the right edge** (`bedino-03`). |
| **Gap** | Overlaps happen in the top games too, but a cut-off word looks broken. |
| **Fix** | **BD-1262 (P2)**: number plus icon only, outlined, clamped inside the safe area and off the HUD rects. |

### 2.6 Character shadow

| Game | What they do (source) |
| --- | --- |
| GAG, SAE, PS99, SAB | No blob: only the engine sun shadow, soft at phone quality (`gag-phone-04-shop-shadows.png`: the stall and the avatar cast plain sun shadows). |
| **Be Dino** | ContactShadow stacks three translucent discs (1.00 / .72 / .46), which read as a dark disc with hard rings (`bedino-02`, `04`, owner: "really low quality"). |
| **Studio test** 2026-11-17 | Raptor stand-ins on grass. A = today's discs: visible rings (`docs/evidence/review-2026-10-17/590`). B = no blob: no contact shadow in the test. C = **one** part with a Top Decal using the built-in `rbxasset://textures/glow.png`, tinted (12, 20, 16), Transparency 0.25: a smooth falloff with no ring (`591`, left). D = the same at 0.10: too dark (`591`, right). Engine shadows with ShadowSoftness 0.2 showed no visible sun shadow for the stand-ins in the edit capture (`592`), so engine-only cannot replace the blob here. |
| **Fix** | **BD-1261 (P1)**: option C. One part instead of three, which is also cheaper on the phone. The texture is part of every Roblox client, so no upload and no new art. A custom Blender blob can come later if the owner wants one. |

### 2.7 Camera distance

| Game | Character height on screen |
| --- | --- |
| GAG | About 30 % (`gag-phone-02`) |
| SAE | About 36 % (`sae-phone-02`) |
| PS99 | About 35 %, higher camera (`ps99-phone-05`) |
| **Be Dino** | About 32 % (`bedino-02`) |

The distance is fine. The problem is the HUD covering the dino (2.1). No row.

### 2.8 Screen kept free

The top games leave the middle third of the screen (x 33-67 %, y 25-80 %) free of HUD. Be Dino covers its top part with SIZE, POTIONS, health, the shield and the hint, and a toast card on top of that when one shows (`bedino-04`). The fix is BD-1258 (the centre box must be empty, checked by test).

### 2.9 Loading screens

| Game | What they show (source) |
| --- | --- |
| GAG | Blurred world behind the logo, a tip line, a block bar "Loading 547/2000", then "Click Anywhere to Play" (`gag-phone-05`, `06`) |
| PS99 | A white BIG Games splash with page dots, then straight in (`ps99-phone-01`) |
| AM | A branded card "LOADING SAVE...", then a title card with Play (`am-phone-01`, `02`) |
| BGSI | "Connecting to server" bar, then the title and one big PLAY (`bgsi-phone-01`, `02`) |
| SAE, SAB | No custom loading screen (`sae-phone-01`, `sab-phone-01`) |
| **Be Dino** | Logo, mascot, a progress plate and a tip plate. Good, but the logo's first letter reads oddly at 1440 px and the two plates touch (`bedino-01`) |

**Fix: BD-1264 (P3).**

### 2.10 Low-poly dino up close

The faceted green dino looks rough at phone distance (`bedino-02`, `03`). This is already the biggest look gap in [242](242-full-benchmark-2026-11-16.md) row 7 and is owned by BD-1216 (V3 dinos). No new row.

### 2.11 Settings (owner asked for a full UI read)

| Game | Settings (source) |
| --- | --- |
| PS99 | A modal: Controls (Hotbar Edit, Security PIN), Main (Music and Sounds sliders, Potato Mode, Other Pets toggles), big pill toggles (`ps99-phone-09`, `10`) |
| SAE | 4 rows: Music, SFX, View Other's Pets, View Your Pets (`sae-phone-11`) |
| Be Dino | Settings with Help (SmallScreens): not captured on the phone today |

Both top games offer a **low-graphics or hide-pets switch** for phones (PS99 Potato Mode, SAE View Other's Pets). Our Effects setting (Full / Lite / Off) is the same idea, so no gap.

### 2.12 The owner's standard: the Steal an Egg shop with Passes open (OWNER TARGET)

The owner sent a screenshot from their own phone, the Steal an Egg shop scrolled to PASSES. It is stored local only as `be-dino-reference-shots/mobile-2026-11-17/owner-phone-current-1.png` (the same screen as `sae-phone-03` to `06`). The owner's words: "really clean nice colors, easy to read, minimal. especially the passes and sub menus like featured or the shop or counters timers should be in our game similar". **This is now the standard for layout, size and look on the phone.**

Measured on the owner's screenshot (3088 x 1440). "% h" is the share of the screen height. "Design px" assumes the phone canvas is about 480 design px tall, so 1 % h is about 4.8 design px. Use Scale values (% h) in Toybox and `Chip.apply`, never fixed px, so the look is the same on every phone.

| Piece | Theirs, measured | % h | Our kit target |
| --- | --- | --- | --- |
| Window | Centred, 1780 x 963 px, top edge at 22 % h | width 58 % of the **screen width**, height 67 % h | Every menu: width 58 % of the screen width (min 540, max 1100 design px), height 67 % h, centred 3 % h below the middle |
| Title bar | Bright diagonal stripes, 150 px tall | 10.4 % h | 10 % h, the screen's colour, stripes in the art |
| Title word | "Shop", white, black outline, 65 px cap | 4.5 % h | 4.5 % h, outline 2.5 design px |
| Close X | Red square with a white X, 115 x 118 px, top-right inside the title bar | 8.2 % h | 8 % h red square, inside the title bar, on the right |
| Body | Dark studded pattern panel | - | Dark patterned body (Toybox skin "dark"), cards stand out on it |
| Section header | "-- PASSES --", yellow or pink, black outline, 55 px cap | 3.8 % h | 3.8 % h, coloured fill, black outline, dashes on both sides |
| Card grid | 2 columns, gap 55 px | gap 3.8 % h | 2 columns on the phone (3 on desktop), gap 3.5 % h |
| Card | 805 x 400 px, bright gradient | 28 % h tall | 28 % h tall, gradient by rarity or theme |
| Card icon | Big 3D icon on the left, about 190 x 225 px | 15.6 % h | 15 % h, left third of the card |
| Card title | "x2 Growth", white, outlined, 50 px cap | 3.5 % h | 3.5 % h, outlined |
| Card line | One line, highlight word in green ("x2"), 45 px | 3.1 % h | ONE line, 3.1 % h, highlight word coloured |
| Price button | Green, 568 x 95 px, price 45 px | 6.6 % h | 6.6 % h, green, **crystal icon + number** (never R$) |
| Gift button | Small purple square beside the price | 6.6 % h | Leave out: no gifting on our paid lines (they stay off) |
| Side category tabs | Right of the window, OUTSIDE it: a 3D icon about 138 px plus an outlined word about 33 px (Featured, Stars, Speed, Money), no plate | icon 9.6 % h, word 2.3 % h | Icon 9.5 % h, word **3 % h** (raised to the 40 px floor of BD-1259), outlined, no plate, 1.5 % h between items |
| Small square tiles | 120 x 120 px coloured squares (egg, paw) | 8.3 % h | Our right-hand column (BD-1258): 8.5 % h squares |
| Left HUD button | "Shop": red, icon plus word, 385 x 128 px, word 60 px cap | 8.9 % h, word 4.2 % h | Left rail word buttons 9 % h tall, word 4.2 % h, outlined, each its own colour |
| Counters | Bottom-left, an icon (112 px) plus a huge bold italic number, 60 to 68 px cap, coloured fill (money green), thick black stroke, **no box** | number 4.4 % h | Crystals and eggs: icon 7.5 % h plus the number at 4.4 % h, italic, coloured fill (crystals amber, eggs cream), black stroke 3 design px, no plate |
| Timer | Bottom-right, an icon plus "in 32s", same style, 45 px cap | 3.1 % h | Weather: icon plus "in 3 min" at 3.2 % h, same style, bottom-right above jump |

Everything has a thick black outline. Titles are 4.5 % h, labels 3.1 to 3.8 % h, and nothing on the HUD is under 3 % h. That matches the BD-1259 floor (40 px at 1440 = 2.8 % h).

**Do not copy:** the "x32 Speed ONLY 48 R$" promo button, Robux prices, pass lines bought with Robux, crossed-out prices and pay-to-skip offers. Our paid lines stay off (docs/43), so every price is in crystals.

**How our screens map onto it:**

| Our screen (`docs/evidence/2026-11-15-cohesion/current/`) | Today | Becomes |
| --- | --- | --- |
| Crystal Shop (`shop.jpg`) | A cream window about 44 % wide; tabs are small cream pills inside (Auras, Trails, Eggs, Crystals); 3 cards per row; small titles with no outline | The standard window. Tabs move to the right side as 3D icons with words: **Featured**, Auras, Trails, Eggs. Section headers ("-- AURAS --"). 2 cards per row on the phone, crystal prices on green buttons |
| Potion Shop (`potions.jpg`) | 6 small cards in 3 columns with tiny text | The standard window, side tabs (Potions, Your potions), cards with "Speed +20%" as the one highlighted line |
| Eggs (`eggs.jpg`) | A cream window with 5 small nest boxes | The standard window. Nests as cards with a timer in the counter style ("in 3 min") |
| Index tabs (`index.jpg`) | Full-screen, tabs across the top (Dinos, Patterns, Colours) | The standard window; Dinos / Patterns / Colours as side tabs on the right |
| Wallet and crystal counter (plates top-right today) | A cream plate 600 px wide for one digit | The counter style, bottom-left, no plate |
| EGGS plate (top-left) | A cream plate | The counter style, under the crystal counter |
| Weather chip (top-right) | A cream plate 740 px wide, "Next: 1 min" at 33 px | The timer style, bottom-right, "in 1 min" |
| HUD buttons (HOME, rail) | HOME bottom-centre; the rail inside the menus | Left rail word buttons (Home, Shop, Dinos, Eggs, Potions) in the standard size |

**Featured tab idea (Crystal Shop):** the first side tab and the page the shop opens on. One big card for this week's new thing (a new aura, trail or egg), with its odds row in kid words for eggs, a crystal price, and "3 days left" in the timer style. Under it, "-- NEW --" with 2 more cards. Rules: crystals only, no crossed-out "worth" prices, no countdown pressure beyond the plain "days left", and it rotates from content we already have (no Robux line). The row is BD-1270.

## 3. Ranked rows (added 2026-11-17, Backlog)

| Rank | Row | Pri | What |
| --- | --- | --- | --- |
| 1 | BD-1258 | P1 | Phone HUD zones: one job per corner, the centre box empty, health inside the SIZE plate |
| 2 | BD-1266 | P1 | Owner standard menu window (Steal an Egg shop look): 58 % width x 67 % h, striped title bar, red X, dark body, section headers, 2-column cards |
| 3 | BD-1268 | P1 | Counters and timers without plates: icon + big bold italic outlined number (crystals and eggs bottom-left, weather bottom-right) |
| 4 | BD-1259 | P1 | Text floor 40 px (TextSize 19), counters 50 px, outlines on every HUD word |
| 5 | BD-1260 | P1 | One toast lane bottom-centre above HOME, outlined line, no card, every HUD rect kept clear |
| 6 | BD-1261 | P1 | Soft blob shadow: one glow.png decal instead of three discs (Studio-tested) |
| 7 | BD-1267 | P1 | Side category tabs outside the window: 3D icon + outlined word, no plate |
| 8 | BD-1269 | P1 | Left rail word buttons in the owner standard size (Shop-button look) |
| 9 | BD-1262 | P2 | World labels short, outlined, clamped to the safe area |
| 10 | BD-1270 | P2 | Crystal Shop "Featured" tab, crystals only |
| 11 | BD-1263 | P2 | `tools/phone_capture.py`: adb burst, tap and sheet with the Roblox-in-front and lock-screen guard |
| 12 | BD-1264 | P3 | Loading screen polish (logo letter, plate gap, number on the bar) |

## 4. Rules learned for phone captures

- Capture only when `mCurrentFocus` is `com.roblox.client` **and** no keyguard is showing. One capture caught the lock screen before the second check existed. It was deleted and never shared.
- When the owner is on the phone at the same time, wait. A two-device join causes Error 273 (`Same account launched experience from different device`).
- Never press a button that buys, claims, rebirths or accepts terms in someone else's game.
