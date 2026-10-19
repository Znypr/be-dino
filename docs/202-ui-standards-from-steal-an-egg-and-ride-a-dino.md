# 202 UI standards from Steal An Egg and Ride a Dino (BD-1115, research only)

Written 2026-10-19. **Status: research done, nothing built.** No game code, no Studio, no profile change; the default build is unchanged. Owner request (2026-10-18): play Steal An Egg and Ride a Dino (the ones with the most players), take pictures of menus, buttons and shops, "because you are making things up that are not standard, and we can get inspiration from them". Then the owner added his own screenshots and eleven categories; this page follows his categories.

Read with [72 UI copy and assets](72-ui-copy-and-asset-standards.md), [103 earlier text-only research](103-ui-research-popular-games.md), [180 shop and NPC prompts](180-shop-and-npc-interaction-design.md), [114 handbook s8.2](114-handbook.md). Labels: **OWNER TARGET**, **CURRENT BUILD**, **RESEARCH** (seen in a picture) or **NOT SEEN**.

## 0. IMPORTANT: third-party pictures are LOCAL ONLY
The repository is PUBLIC. Every picture named here lives on the owner's PC in `C:\Users\znypr\Documents\be-dino-reference-shots\` and **must never be committed, linked as an image or copied into the game**. This page names pictures by local file only. Housekeeping done in the same PR: the Grow a Garden pictures from [180](180-shop-and-npc-interaction-design.md) and the 13 Steal An Egg screenshots committed on 2026-10-04 were removed from the repo (git history still holds them; the old copies are in the local folder). `.gitignore` now blocks the folder name and `Screenshot 20*.png`. Our OWN Studio pictures (`docs/evidence/...`) are fine.

Local folders and short names used below:

| Short name | Folder (inside `be-dino-reference-shots`) | What it is |
| --- | --- | --- |
| **OW-nn** | `owner-shots-by-category\` | The owner's 25 screenshots from 2026-10-18, renamed with a number and his category. Originals are the loose `Screenshot 2026-10-18 17xxxx.png` files. PRIMARY evidence. |
| **SE-nn** | `steal-an-egg\` | 19 frames I took from three YouTube videos of Steal An Egg |
| **OG-nnnnnn** | `steal-an-egg-owner-shots\` | The 13 Steal An Egg screenshots the owner gave on 2026-10-04 (file `reference-NNNNNN`) |
| **RD-nn** | `ride-a-dino\` | 9 frames from a YouTube video of the top Ride a Dino game |
| **RE-nn** | `ride-a-dino-second-game-1.7K-egg-carry\` | 9 frames of a DIFFERENT, smaller game also called Ride a Dino |
| (old) | `grow-a-garden-earlier-study\` | The earlier Grow a Garden pictures (moved out of the repo) |

Contact sheets (with a letter-and-number ruler so the owner can say "D3"): `SHEET-owner-shots-by-category-RULER.png`, `SHEET-steal-an-egg-own-captures-RULER.png`, `SHEET-ride-a-dino-top-game-own-captures-RULER.png`, `SHEET-ride-a-dino-second-game-egg-carry-RULER.png`, `SHEET-steal-an-egg-owner-gallery-4-oct-RULER.png`.

## 1. The two games (facts, read on 2026-10-18 and 19)
| | Steal An Egg | Ride a Dino (the one with the most players) |
| --- | --- | --- |
| Roblox link | roblox.com/games/107778070777162/Steal-An-Egg | roblox.com/games/93523763376122/Ride-a-Dino (title "[meteor] Ride a Dino") |
| Active players (game page) | **924,446** | **21,451** (21,442 from the Roblox data page) |
| Visits / favourites | 8.68 billion / 8,205,332 | 3,851,578 / 100,156 |
| Created / updated | 2026-07-25 / 2026-10-18 | 2026-08-24 / 2026-10-18 |
| Max per server | 7 | 8 |
| Pitch | steal eggs from pets, hatch rare pets, earn money, treadmill speed, Halloween event | ride stampeding dinos, tame 50+ species Common to Divine, pens earn cash, secret dinos |

**How I decided.** Roblox search "steal an egg": the top tile is this game at 923.6K playing; the next real "Steal an egg" game is Break and Steal an Egg at 104.1K, so the choice is clear. (Third-party trackers disagree wildly on its all-time peak, 2.2 M to 14.3 M, so I quote none.) Roblox search "ride a dino": there is **no exact "Ride a Dino" with big numbers**; the best exact-name game is the one above with 21.4K. A bigger neighbour is **Ride A Pet** at 30.8K (not dinosaurs) and I did not use it. **There are TWO games called Ride a Dino:** a smaller one (place 131652231424227, 1,683 playing, group "Dino Riders!", hatch eggs and mutate dinos) shows up in one popular YouTube video (the "JENNY AND CHAN" video: egg carry, Rebirth, wooden menus). Frames from it are kept apart (RE-nn) and flagged. **The owner's blocky voxel screenshots match the top game** (meteor and night timers, Aura names, Fuse Machine), as does the video behind RD-nn.

## 2. What I could and could not see (honest)
- **No game was played.** Everything is a paused frame from YouTube (1080p video, shown at about half size, so the text is small) or one of the owner's own screenshots. I never logged in, never clicked Play, Buy, Follow or Like, downloaded nothing and closed my tab.
- **Not seen:** the hatch reveal of Steal An Egg (I took frames from the 100-eggs video but could not look at them, so none are kept); any phone layout (every picture is a desktop 16:9 frame); animation timing and sound; the Roblox game page pictures (the owner's browser shows his account, Robux and private chats on that page, so I did not keep any); a controller or touch prompt look.
- **Count:** 19 + 9 + 9 own frames, short of the "25 to 40 per game" target (each frame costs a video seek). The 25 owner shots and the 13 older gallery pictures carry most of the evidence. The first caption of every Steal An Egg frame was a guess made before I could see it; all were corrected after looking at the sheet.
- Sizes below are read off pictures (a fraction of the screen width or height), not measured in-game.

## 3. The owner's 25 screenshots, one line each (categories are his)
| Pic | Cat | What it shows |
| --- | --- | --- |
| OW-01 | 2 popups | "IT'S YOURS!" in white-outlined green words on a dark strip with a green border and a dino head icon at the left |
| OW-02 | 2 popups | "2 SECURED" (green, outlined) above two square cards: dino head on a rarity-coloured tile, name under it, a small "HUGE" tag on one |
| OW-03 | 2 popups | "GREAT RUN!" huge orange bubble letters on a dark band with thin gold lines top and bottom |
| OW-04 | 3 timers | two lines: meteor icon "in 5m 29s", moon icon "in 0m 39s" (white italic outlined text, no panel) |
| OW-05 | 4 counters | two pills: bolt icon "5.6K" (white) and cash stack "$963.6K" (green), icon left of a big outlined number |
| OW-06 | 5 server msg | "ALL HERDS RESET!" huge white outlined, then one sentence "An Eternal WarpCarnotaurus spawned in Extinction" with the rarity word in its tier colour, the zone in its zone colour, an emoji at the end |
| OW-07 | 5 server msg | same pattern: "A Secret BIG King Gorilla spawned in Volcano" (Volcano orange) |
| OW-08 | 5 server msg | "METEOR SHOWER!" then three sentences, one per spawn: Rare (blue) MAGMA (orange) Velociraptor in Forest (green); Uncommon (green) MAGMA GIANT Ankylosaurus; Common MAGMA TINY Pachycephalosaur in Plains |
| OW-09 | 6 menus | "Dino Index": blue header, title left, grey CLAIM ALL button, red X; left zone tile (Plains, reward $8.5K and +120), a 3-column grid of dino cards (name small on top, big art), a detail card on the right, a green "COMPLETE! 6/6" bar, a big blue bar "Unlocked: 14/55" with a book icon |
| OW-10 | 6 menus | "AURAS": purple header with a bolt icon, red X; tall cards, each a full tier colour (silver, lime, cyan, cobalt), name small, "Lvl 2 Common" with the rarity word in colour, big picture, "x1.75 Stamina", one green "Equip" button |
| OW-11 | 6 menus | "Fuse Machine": purple header; one instruction line "Bring 3 same Dinos to Fuse", three "Empty" slots with big green "+" buttons, a "?" result box, green "3 Dinos Left"; a small dark OK popup beside it |
| OW-12 | 7 prompts | small dark chip: key square "E" at the left, small grey "Fuse Machine" over white "Fuse Dinos" |
| OW-13 | 7 prompts | a pill "My pen" with a key square "R" and a house icon, dark rounded bar (a HUD button that also has a key) |
| OW-14 | 8 signs | huge green outlined word "SELL DINOS" floating above a Lego-style stall (red/white striped roof), a Roblox avatar in a red shirt behind the counter, a red ring on the ground in front |
| OW-15 | 8 signs | huge green outlined word "AURAS" over a purple/white striped stall, avatar in a purple/blue shirt, a purple ring on the ground |
| OW-16 | 8 signs | black signboard "Upgrade Machine / Raptor / +12 > +30 Stamina/s" with a red price bar "$5M" |
| OW-17 | 9 bundles | round badge "LIMITED TIME!" (curved banner), dino head with cash and bolt, "STARTER PACK!", "ONLY [Robux] 99", red pill with a countdown 23:28:48 |
| OW-18 | 9/1 shop | "Shop" window (blue header, red X), green section word "MONEY", a wide tile "DOUBLE Your MONEY x2 FOREVER!" with chest art and a green Robux price button "199", three tiles under it "+$24K CASH", "+$200K CASH", "+$800K CASH" |
| OW-19 | 9/1 shop | the same window scrolled: "+50M STAMINA", "+500M STAMINA", "+1B STAMINA", each tile has art, one line, a purple icon tag and a wide green Robux price button |
| OW-20 | 10 models | a blocky raptor with the tail striped red, orange, yellow, green, blue, purple (rainbow by segment) |
| OW-21 | 10 models | huge "Magma Colossal T-Rex": dark navy cubes with orange crack lines and yellow glowing slabs, label "EXCLUSIVE" (rainbow word), name in orange/white, "+$840K/s", "SOLD OUT" |
| OW-22 | 10 models | a MAGMA ankylosaurus, red cubes with glowing yellow-orange edges and black windows, rider on top |
| OW-23 | 10 models | normal ankylosaurus: orange voxel body, white spikes, brown straps, grey club tail (the plain look to compare) |
| OW-24 | 10 models | the same normal ankylosaurus, side view, rider, dust puff |
| OW-25 | 11 NPC | an avatar NPC "Marina" in a quiet game: dialogue bar at the bottom, small round portrait, name, one line "Oh, hello!", a small advance arrow |

Category 1 ("how shops should look") is OW-09, OW-10, OW-11, OW-18, OW-19 (windows) and OW-14, OW-15, OW-16 (stalls).

## 4. Standards, category by category
Each rule says where it was seen. "Both" means the owner's game and Steal An Egg agree.

### 4.1 How shops should look (OW-10, OW-18, OW-19, OG-212757, OG-212804, RD-04, RE-03)
1. **One window, centred or beside the stall, world still visible**, dark navy or charcoal panel with a faint stud texture. Header bar in ONE bright colour per shop (blue, purple, green) carrying the title **left-aligned**, white, very thick dark outline, about 8 to 10 percent of the window height.
2. **One red square X at the header's right end**, white X, about as tall as the header minus a margin (a large target). Both games, every window (OW-09, OW-10, OW-11, OW-18; OG-212744, OG-212757, OG-212804, OG-212810). Nothing else is red in the header.
3. **Cards in a row or grid, art first.** The picture is more than half the card. Above it: the name in small white text. Under it: ONE benefit line with the number in green and the unit in white ("x1.75 Stamina"). Under that: ONE wide button the full card width.
4. **Price lives ON the button** ("$5K", a Robux coin and "199"), not on a separate line under it. A card with two ways to pay shows two stacked buttons (cash on top in green, Robux under it in orange or green with a coin icon) (RD-04).
5. **Colour carries the tier.** The whole card background is the tier colour (silver, lime, cyan, cobalt) or the rarity word is coloured; never only a thin border. Rarity words: Common white or grey, Uncommon green, Rare blue, Epic purple, Legendary orange or gold, Mythic and Exclusive rainbow (OW-02, OW-08, OW-10, OW-21, RE-03).
6. **Section words are big and green or white** ("MONEY"), not tiny tabs (OW-18). Sold out is a grey button (RE-03 "Out of stock").
7. **Gear and Gamepass pages are loud**: huge art, a big "x2 FOREVER" tile on top, then a grid of three. This is the style we must NOT copy for paid items (section 4.9).
8. **Text is short.** Titles 1 to 3 words, a card has at most name, benefit, price. No paragraphs inside a shop. Large numbers are shortened (5.6K, $963.6K); we keep plain counts for children ([72](72-ui-copy-and-asset-standards.md)).
9. A second small dark popup (OK button, green) confirms a result next to the big window (OW-11), instead of a full-screen confirm.

### 4.2 Popup notifications (OW-01, OW-02, OW-03, SE-03, SE-06, RD-06, RD-07, RE-03, RE-07)
- **Two styles, both short.** (a) No panel: 2 to 4 words in bright text with a very thick dark outline straight on the world, top centre ("Luck Upgraded 35x > 36x", "Bought a Normal Radar! [x4]"). (b) A dark translucent strip with a coloured border and an icon at the left ("IT'S YOURS!" with a green border, "Rebirth 1! Income x2" in a gold-lined strip).
- Gain words are green, warnings red, big moments orange or gold. Win banners ("GREAT RUN!", "DEVOURED!") use a huge tilted bubble font on a dark band with thin coloured lines; they cover the middle of the screen for about a second or two (timing not measured).
- Results come as **small cards you can read in one look**: dino head, name, rarity-coloured tile, a tag like HUGE (OW-02).
- Repeats stack: "[x4]". One thing at a time at top centre; floating "+9" numbers rise from the object that gave them.

### 4.3 Timers (OW-04, RD-03, RD-09, RE-06, SE-10)
- **Two kinds.** (1) World clocks in the bottom-right corner, stacked: an icon and "in 5m 29s" with no panel or a soft dark pill (meteor, night). (2) A bar timer at top centre for a task in progress: title above ("Egg Will Break"), a wide red bar, the seconds number big inside the bar ("21.3s"), the bar drains from the right (RE-06).
- Egg and pet timers on the object itself: a small label above it with a count (SE-10: "13h 13m").
- The icon says WHAT, the number says WHEN, nothing else. No sentence.
- They show "5m 29s"; our rule ([72](72-ui-copy-and-asset-standards.md)) says "5 min" and drops zeros. That stays; we copy the **place and the icon**, not the format.

### 4.4 Progress counters (OW-05, OW-09, RD-01, RD-03, RE-04, OG-212744)
- **Currency pills** bottom-left (cash, big green number with a cash-stack icon) and a second pill above it (stamina, bolt icon). A small green "+" button at the right end opens the shop. Number outline is thick, size about the same as button text.
- **Collection progress is a wide bar with the count written big on it**: "Unlocked: 14/55" on a blue bar with a book icon (OW-09); per-area "COMPLETE! 6/6" on a green bar with a cash icon, area reward written next to it ("$8.5K, +120"), a green CLAIM ALL button in the header. Claimed becomes a grey "CLAIMED!" button.
- Gains float up from the object as green numbers with a bolt or cash icon (RE-04 "+9", "+$19"), so the player sees WHAT earned it.
- Rates are written on the object's name tag ("$6,620/s", "1 in 40K"), small.

### 4.5 Messages and SERVER messages (OW-06, OW-07, OW-08, SE-19)
- **Two-line pattern, no panel at all**: a huge white title with a thick black outline ("ALL HERDS RESET!", "METEOR SHOWER!"), then one sentence in white with **coloured words**: rarity word in the rarity colour, mutation word in its colour (MAGMA orange), size word (GIANT, TINY) in the mutation colour, the place in the place colour, one emoji at the end.
- Several spawns at once become several sentences under one title (OW-08, three lines).
- Sentence shape: "A/An [Rarity] [Mutation] [Size] [Species] spawned in [Place]!" Always starts "A" or "An", always ends with "!". About 45 to 60 characters.
- Top centre of the screen, over the world, fading after a few seconds (not measured). The event story is in the title; the find is in the sentence.
- Steal An Egg uses the same idea at smaller size for its event notes (SE-19, an "x2 egg size" note), and an event countdown can take the whole screen (SE-17), which we should not do.

### 4.6 Menus and shops (see also 4.1)
- **Left rail, two or three big buttons with a word and an icon**: Shop (red), Index (blue) with a red "!" dot when something is new (RD-01 to RD-03; the owner's game); a small tag on the button says "ONLY R$ 3" for an offer. **Right rail**: one button (Pets/Dinos, orange). In the second game (RE-02) the rail is: left Shop, Index, Rebirth; right Eggs, Dinos; each button is an icon with its word under it, about 65 px on a 1080p screen. Steal An Egg keeps the words small (SE-01: "Shop", "Index") but still has words.
- **Never more than five buttons on the HUD.** Anything else is inside the shop or the Index (tabs, sections).
- Index: zone tile on the left with area art, 3-column grid, a detail card on the right with the rarity word and its income, a Variants counter "1/30", a Rewards box with a CLAIMED button (OW-09; OG-212744 does the same in a smaller game).
- Fuse screen: ONE instruction line, big empty slots with a "+" button each, the result as a "?" box, a green button that counts what is left (OW-11). No percent tables on the screen.
- The Roblox pay dialog is the plain Roblox one (SE-08); nothing custom is drawn for the real Buy.

### 4.7 Interaction prompts (OW-12, OW-13, RD-02, RD-08, RD-09, SE-07, SE-14)
- **Four kinds, all small:** (1) the chip: a key square with the letter, two lines (object grey, action white), dark rounded, near the object (OW-12, RD-09). (2) A wide centre-bottom button with a word ("RIDE PET", orange border, RE-01). (3) A hold ring round the key square that fills while you hold (RD-09). (4) A speech list for people (4.11).
- A display dino shows TWO chips stacked: "Ride 8s / Try it" and "Buy for [Robux] 400" (RD-08): one key each (R and E).
- The chip is about 5 to 7 percent of the screen width: **much smaller than our stall bubble** (232 x 112 px). It works because the key letter is the same everywhere (E) and because the object itself is huge.
- Keys: E to use or buy, R for a second action, Q for the inventory.

### 4.8 Signs (OW-14, OW-15, OW-16, SE-16, RE-05)
- **A giant 3D-looking word floats above the stall**: "SELL DINOS", "AURAS", "Food", "Gears", "Track". Thick green or white outline, about as wide as the stall roof, readable from the far side of the map.
- **Colour code**: the roof stripes, the ground ring and the keeper's shirt match each other (red/white for selling, purple/white for auras, blue/white for food).
- **A coloured ring on the ground** tells you where to stand (OW-14, OW-15).
- Info signs are black boards with a white title, a green or yellow detail line and a red price bar (OW-16 "Upgrade Machine / $5M").
- Names on objects are big enough to read from where you ride: rarity word coloured above, name white, rate in green.

### 4.9 Prompts to buy bundles (OW-17, OW-18, OW-19, RD-03, RD-04)
- A **round badge at the top right** under the Roblox bar: curved ribbon "LIMITED TIME!", art, a name, the price with a Robux icon, and a red pill with a ticking countdown. A small "ONLY R$ 3" tag sits on the left Shop rail button.
- Inside the shop the bundle is the **top, widest tile**, then packs with bigger and bigger amounts.
- **These games use pressure** (limited time, countdown, "ONLY"). [103](103-ui-research-popular-games.md) already says not to copy that. **Design note only: our crystal packs are OFF and stay off.** If they are ever built: no countdown, no "limited", one calm tile on the Shop page, odds and price in plain words, behind `PolicyService`.

### 4.10 Other games' dino models and MUTATION looks (OW-20 to OW-24, RD-01, RD-07)
- **Style:** blocky voxel dinos built of cubes (Lego-like), big simple shapes, flat colours, short thick legs, very large heads. Rider sits on a saddle. Normal look = one or two natural colours plus a contrast (white spikes, brown straps) (OW-23).
- **Mutation = a different whole-body material, not a tint:**
  - **Magma:** dark or red cubes with glowing orange crack lines and bright yellow glowing slabs and edges; a flame glow around it (OW-21, OW-22).
  - **Rainbow:** one hue per body segment along the tail, strong saturated stripes (OW-20).
  - Names carry the look: the mutation word is coloured the same as the effect (MAGMA orange), size words TINY, GIANT, BIG, COLOSSAL, HUGE are part of the name, "EXCLUSIVE" is a rainbow word.
- The mutated dino is readable from **far away** because it glows and has high contrast, and because a label floats above it.
- **Our look** ([114 s5.6](114-handbook.md), `MutationLook.luau`): a gentle tint pulled at most 35 percent, soft rim, matte, calm. That keeps our vibe, but next to these it will be very hard to see at riding distance.

### 4.11 Roblox avatars (NPCs) beside shops that you can talk to (RE-05, SE-18, OW-14, OW-15, OW-25)
- **A plain Roblox avatar stands behind the counter**, dressed in the stall's colour (red shirt at the sell stall, purple at the aura stall). It does not move much. The stall name is the giant sign above, not a name tag.
- **Talking:** walk up, the keeper shows a **speech line and 2 to 3 numbered choices** floating above the stall: "Hungry dinos? I have snacks!", "1. Show me your food!", "2. When's the restock?", "3. Bye!" (RE-05, the highlighted option is orange; this frame is from the smaller second game). Steal An Egg: "Anything else, starlight?" then "View Stars", "Star Drop Event?", "Bye!" (SE-18). The last choice is always "Bye!".
- For story NPCs: a dark rounded bar at the bottom, round portrait, name, one short line, an advance arrow (OW-25).
- No hold, no long text, no sound seen.

## 5. Our screens against the standard
Our pictures (all in `docs/evidence/review-2026-10-17/`, taken in Studio at about 516 x 481): HUD 381, shop landing 386, shop Auras 363, Potion shop 403, toast covering the rail 361, Eggs screen 396, hatching 397, reveal 398, Dino Index 382, Run Complete 395, weather toast 394, stall prompt 266 (older G button). Catalogue pages: `docs/catalog/Shop-items.md`, `Mutations-and-fusion.md`.

| Screen / part | What we have today (CURRENT BUILD, from the pictures) | The standard | Why it may hurt children | Recommendation | Pri / effort |
| --- | --- | --- | --- | --- | --- |
| HUD rail | A grid of six small square icon buttons top left (no words), a Crystals pill top right, a purple Admin button, EGGS counter | 2 to 3 big buttons with icon AND word, red Shop and blue Index, 1 or 2 on the right, never more than 5 | Icons alone are guessed; small tiles are hard to hit with a thumb; the rail covers the top of open menus (BD-1101, BD-1102) | **R1:** icon + word on every rail button, at least 56 px, at most 5 visible, the rest inside the Index or Shop; colour per button | **P1 / M** |
| Window title and X | Title about 14 to 18 px left, red X small in the right corner | Title 8 to 10 percent of window height, thick outline, X a large red square | The X is the child's way out; small = trapped feeling | **R2:** title at least 22 px with outline; X at least 48 px red square, same spot on every window | **P1 / S** |
| Shop cards (Auras, Trails, Eggs, Potions) | Many tiny text lines per card (name, tier, "Growth +35%", price line under BUY), small dark cards, price separate from the button | Art over half the card, name, ONE benefit line, ONE wide button with the price written on it | Four lines of 10 to 12 px text cannot be read by a 7-year-old on a phone; BD-1103 already found clipping | **R3:** card = art, name, one line, one button "35 Crystals" (price on the button). Details behind a small "Info" word button (needed anyway for odds) | **P1 / M** |
| Text style everywhere | Thin text, small, little outline on cards and toasts | Bold rounded font, white, very thick dark outline, 18 to 28 px | Low contrast and small size hurt young readers and phones | **R4:** one `TextStyle` "outlined": 2 px dark outline, floor 16 px in cards, 22 px titles (the floor in [72](72-ui-copy-and-asset-standards.md) is 14 px, this lifts it for headings and prices) | **P1 / S** |
| Rarity | Mostly a small coloured chip ("Common", "Rare" on a pill), tier shown by a thin border | The rarity WORD in its colour, or the whole card in the tier colour | Colour plus word is learned in one look; a thin border is missed | **R5:** rarity word coloured on every card, toast, reveal and announcement; card background by tier on shop cards | **P1 / S** |
| Rare-find announcement ("Name hatched a Legendary Compy!") | `RareHatchClient`: one dark purple strip, one gold text colour, 22 to 30 px, name plus species | Two lines, no panel: huge white outlined title, then a sentence with coloured words (rarity, mutation, place) | A flat strip is easy to ignore; coloured words make a rare moment feel big and teach the colours | **R6:** restyle: title ("A rare find!"), sentence with the rarity and mutation words coloured, no panel, 4 s. Keep names filtered and cut at 20 characters as now; keep the Secret rule (no species name) | **P1 / S** |
| Toasts | Dark card with coloured side bar and icon plate, small text, cover the rail and the top of menus (361, 405, 406) | Short (2 to 4 words) outlined text at top centre, one at a time; or a slim dark strip with a coloured border | Covering buttons steals taps; long lines are skipped | R7: toasts only in the top-centre band, never over the rail or a window header (BD-1102); plain outlined text for small news; card only for big moments | P2 / S |
| Stall prompt bubble (BD-1017, flag on) | Cream bubble above the stall: name, one warm line, big key button (232 x 112) | Small dark chip (key square + object + action); a NPC with numbered choices where there is more than one choice | Ours is bigger and friendlier (good for phones). It lacks a keeper and a big sign, so the player does not know WHO is talking | R8: keep the bubble; add the key square look (letter in a square) and show it from a little farther; then staging in R9 | P3 / S |
| Stall sign and keeper | Stone sign with a small lamp-lit word, no keeper, no ground ring | Giant outlined word above the stall in the stall colour, ring on the ground, an avatar-like keeper in the same colour | A new player cannot see which stall is which from across the cave | **R9:** big coloured word (14 characters max kept), ground ring in the stall colour, a keeper figure behind the counter (our own dino or a simple cave person; art task) | P2 / L |
| NPC talk | Not built (design B in [180](180-shop-and-npc-interaction-design.md)) | Speech line plus up to 3 numbered options, last is "Bye!" | More than one choice is clear to a child when it is a short list | **R10:** only if a stall gets a second real choice; keep three options and "Bye!" | P3 / M |
| Timers | Weather and potion timers as small cards ("Weather in 4 min"); Potion shop restock "New offers in 25 s" in small text | Icon plus time, stacked bottom right, no panel; bar timers with the number inside | A plain icon and a number is read faster than a sentence | **R11:** timers become icon + number chips bottom right; growth and potion timers get a drain bar with the time in it | P2 / M |
| Progress counters | Index shows "Collected 1 of 22 (4%)" in tiny text; Crystals in a small pill | A big bar with the count written on it, per-area complete bars and a reward | A child sees the bar fill; a percent in small text is invisible | **R12:** big count bar "Found 1/22" with a book icon; area bars with a small reward; floating "+N" with an icon | P2 / M |
| Hatch screens | Chips, "Tap for next egg (3 left)", Skip the rest, many small chips that overlap at 498 px (416) | (not seen in these games; the hatch frames could not be read) | n/a | none from this study; keep BD-1088/1101 fixes | n/a |
| Mutation looks | Gentle tint at most 35 percent, matte, soft rim | Whole-body material change with glow, strong contrast, mutation word coloured in the name | At riding distance the mutated dino looks like a slightly odd colour | **R13:** add readable cues inside our calm style: a bold named pattern or glow crack layer, a bigger rim, mutation word in colour on the name tag. Needs a Blender material study first | P2 / L |
| Bundles | Crystal packs OFF; Crystals page "coming soon" | Round badge, countdown, "ONLY", huge tile on top | Pressure and urgency hurt children ([103](103-ui-research-popular-games.md)) | **R14:** notes only (section 4.9); never enable | P3 / S |
| Phone layouts | Checked by us at 516 and 498 px | **Not seen** in any reference picture | unknown | **R15:** someone with the games on a phone captures the HUD and one shop | P3 / S |

## 6. Top recommendations
P1 (rows added to the board): R1 rail with words and bigger buttons; R2 window title and X sizes; R3 shop card with the price on the button; R4 one outlined text style; R5 coloured rarity words; R6 two-line rare-find announcement with coloured words. P2: R7 toast zone, R9 stall signs with ground ring and keeper, R11 timers, R12 progress bars, R13 mutation readability. P3: R8, R10, R14, R15.

**Server messages for kids (owner asked):** we already have one (BD-428, `RareHatch.luau`): the server decides a rare hatch (Legendary, Shiny, mutation, Secret), picks only the best of a burst, limits each player to one per 45 s and the whole server to 4 per 10 s, and Roblox display names are cut to 20 characters. That is safe as it stands. The restyle (R6) keeps all limits. A **zone or event message** like "METEOR SHOWER!" would need no player name at all ("A Rare Magma Raptor appeared in the Forest!"): the safest kind, and a good use of our weather events. Do not add a free-text message anywhere.

## 7. Follow-ups and board rows
Parent row BD-1115 (P2) and the rows it lists are in the board. Items that need a person: phone pictures of both games (R15); a real look at the Steal An Egg hatch reveal (not captured here); a Blender study of mutation materials (R13).

**Update 2026-10-19 (BD-1116):** R1 is built behind `HudRailWordsEnabled`: five word buttons at home, Settings as a gear, words 16 px (desktop) or 14 px (phone), see [212](212-hud-rail-with-words.md). Offline evidence only; the Studio look is BD-1143.
