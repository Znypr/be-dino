# 192 Studio round 4: close paths, player walkthrough, hatch screen audit (BD-1027, BD-1045, BD-1042)

Label: **STUDIO EVIDENCE** (desktop Studio, one player, unpublished copy, memory profile, test wallet, the player is admin). Written 2026-10-18 by the Studio QA helper. Nothing was published, no flag changed, no chance forced, nothing bought with Robux. Pictures 200 to 271 are in [evidence/2026-10-18-studio-r4/](evidence/2026-10-18-studio-r4/README.md) and in `docs/evidence/review-2026-10-17/` (files `NNN-studio-r4-...`).

## 0. Which build was this (plain answer)

* The screen label read **BUILD redesign-020 ff4116fc**. That is `origin/main` `ff4116fc` (the merge of #506) at the moment I built. `tools/playtest_freshness.py` said "up to date" at build time.
* **It is not the newest any more.** While I tested, four more changes merged: `1da6adf5` (#513 colours on the rarity ladder, BD-1036), `819cd657` (#516 pattern and colour growth boost, BD-1038), `4028a941` (#509) and `84867868` (#514). So the colour tags and colour chips I judged in part C are the **old** colour odds, not the #513 ones. Defects below that do not depend on the colour odds (bucket, chips, egg size, layout, close paths) are unaffected.
* Release flags as built: playtest profile, `HatchV2` off (the "paint bucket" the owner sees is the normal hatch bucket, not the V2 one), `CrystalPacksEnabled` false, `PaidRandomItemsEnabled` false, `QaOverlayEnabled` false, `SecretSpeciesEnabled` true.
* Windows: Studio was started with `tools/monitor4.py launch studio`. It opened on another screen first (the tool skips a window that has focus), later it was on the virtual 1280 x 720 monitor. Viewport was 1156 x 793, then 1488 x 793, and for the last 15 minutes **848 x 481** after the window landed on the virtual monitor. Input kept working. The owner's `Place1.rbxl` window was not running and was never touched. I closed only my own Studio at the end.

## 1. Part A: BD-1027 close paths (build ff4116fc)

| Item | Result | What I saw | Picture |
| --- | --- | --- | --- |
| X while the egg wobbles (350 ms after OPEN EGG) | **PASS** | menu closed, eggs left stay in the queue | (checked by `MenuOpen`), 239 |
| Dark backdrop tap while the egg cracks | **PASS** | nothing happens, the egg goes on | 239 |
| X with the dino shown | **PASS** | closed | 240 |
| Dark backdrop tap after the dino has shown for over half a second | **PASS** | closed, toast "2 dinos hatched / Best: Common Compy" | 217 |
| X on a splat, and backdrop tap on a splat | **PASS** (both) | closed | 242 |
| X and backdrop on the last egg (splat with DONE and TRY AGAIN) | **PASS** | X closes; backdrop closes | 254 |
| TRY AGAIN after the last splat | **PASS** | really starts a run (RunState Active, dino on the island) | 254, 255 |
| Escape | **NOT TESTABLE with these tools** | the tool's Escape key never reaches the game (`UserInputService.InputBegan` sees the C key but never Escape; Studio keeps Escape for itself). So the BD-1027 question "does Roblox mark Escape as already used, so the code ignores it" is **still open**. Source: `Bootstrap.client.luau` line 1738 and `FusionMenu.luau` line 143 only react when `processed` is false; that is exactly the risk. A real keyboard test in a Studio window or a phone with a keyboard is needed | none |
| Fusion menu X and backdrop | **PASS** (both) | closed | 262, 265 |
| "Skip the rest" bottom right and readable | **PASS** | button at the bottom right, text clear, does not cover anything | 247, 248, 252 |
| Run Complete OPEN EGGS opens the Eggs screen from the cave | **PASS** (BD-1055 fixed) | Eggs screen opened, no "Follow the glow" | 211, 212 |
| Skip the rest stops on a Legendary | **Legendary not seen** | 144 eggs hatched, no Legendary came; not forced. It stopped on Rainbow and BIG eggs only (eggs 8, 19, 34, 58, 64, 77, 87, 92 and more) | 248, 249, 251 |
| `tools/qa/regression_walk` (step 7) | **does not run on this setup** | `VirtualInputManager` is blocked ("lacking capability RobloxScript"), as written on 2026-10-17; every tap step would only print NEEDS. I did the same checks by hand with real clicks, which is the stronger proof | none |
| Phone landscape and gamepad | **not tested** | no phone, no gamepad. A small window (848 x 423 usable) showed layout problems (BD-1067) | 269 to 271 |

Headline A: the close-path fix and OPEN EGGS work in Studio. Open: Escape, Legendary stop, phone, gamepad.

## 2. Part B: BD-1045 player walkthrough

Rule from the owner: **"what would a player expect when they click outside?"** A player expects a menu to close when tapping the dark area, and a key that opens a menu to close it again when pressed twice. I judged against that.

Method: real clicks and keys through the Studio tools. I read the Food folder, walked with `character_navigation` and short `MoveTo` loops (every loop waits) to the nearest food I could see. Four runs: 274 s with 7 eggs (telemetry `food_raw` 247, +17 crystals, +1 nest), one with the admin food x10 slider to get 140 eggs, a 4-egg run and a 14-egg run. Only in-game crystals were used. Nothing was bought with Robux.

| Item | Works or broken | Evidence | Note |
| --- | --- | --- | --- |
| Spawn, Welcome card | works | 200, 201 | backdrop tap closes it |
| Tap to go, start a run | works | 202 | |
| Move and eat the food I can see, grow | works | 202, 255 | SIZE bar and EGGS count rise; walkers get stuck on trees, a player would not |
| Wild predator | works | 205 | two big predators; one bit me (HP 255 to 225 in seconds); camera went inside bushes |
| Go home window (HOME) | works | 211 | X closes, backdrop closes (run goes on) |
| Run Complete, OPEN EGGS | works | 211, 212, 231 | |
| Eggs screen (nest station G, rail EGGS) | works, with a catch | 232, 238 | G works only from some sides of the nest (BD-1074) |
| Hatch several eggs, Skip the rest | works | 213 to 254 | see part C for looks |
| Dino Index (key C, rail DINOS) | works | 204, 228, 263 | key C pressed twice stays open (no toggle) |
| My dinos (species page) and BACK | works | 229, 265 | "Compy x 40" list, BACK and X close |
| Equip a dino | works | 230, 237 | Raptor shows in the cave; **a charged (Mutant) Compy showed pure black in the cave** (BD-1066) |
| Potion shop: open, buy, close | works | 206, 207, 208 | confirm: backdrop tap closes everything and buys nothing; "Your potions" row is cut at the bottom and needs a scroll (BD-1074) |
| Crystal Shops: auras (buy, equip) | works | 219, 222, 258, 259 | Equip closes the shop; balance after buying reads 1,000,000 (test wallet floor) while the confirm said 1,000,255 |
| Crystal Shops: eggs tab, crystals tab | works / "Coming soon" | 220, 221, 260 | Robux crystal packs stay hidden as intended |
| Fast travel (500 in-game crystals) | works | 260, 261, 262, 263, 267 | rail buttons then jump to the station; "Back to the middle" button appears |
| Settings (tabs Sound, Look, Controls, Help) | works | 203, 224, 225, 226 | X and backdrop close |
| Fusion menu | opens, closes | 262, 265 | I did not fuse (not asked) |
| Goals panel (objectives) | works but one thing is off | 264 | tapping outside does **not** close it (the title toggles it); the line "Gold ready: fuse Compy" touches the right edge |
| Weather events | seen | 211, 231 | rain, thunder, volcano, earthquake toasts |
| Console | clean | none | no game error; only Roblox UIBlox warnings and two asset errors (BD-1068) |

The "every screen" test, per screen (X / tap outside / Escape / open key twice / second screen on top):

| Screen | X | Tap outside | Escape | Key twice | Second screen on top |
| --- | --- | --- | --- | --- | --- |
| Welcome card | not seen again | closes | not testable | n/a | n/a |
| Settings | closes | closes | not testable | n/a (rail button) | rail button replaces it (223) |
| Potion shop | closes | closes (confirm too) | not testable | n/a | replaced by the next rail screen |
| Crystal Shops | closes | closes | not testable | **G twice stays open** | n/a |
| Dino Index | closes | closes | not testable | **C twice stays open** | species page and BACK work |
| Eggs screen | closes | closes | not testable | **G twice stays open** | OPEN starts the hatch card |
| Hatch card | closes | see part A | not testable | n/a | n/a |
| Fusion menu | closes | closes | not testable | **G twice stays open** | rail click closes it (acts as an outside tap) |
| Goals panel | title toggles | **does not close** | n/a | n/a | n/a |
| Go home window | closes | closes | not testable | n/a | n/a |

What a player expects when pressing the open key twice is that the menu closes. In this build it stays open. That is a small thing for the owner to decide (BD-1074 lists it).

Headline B: nothing broken in the core loop. No blocker. The worst things seen: the black charged dino, the cut-off layout in a small window, the class icons that do not load.

## 3. Part C: BD-1042 hatch screen audit

Order of what the hatch screen shows for one egg (from the layout log with 0.1 s samples, window 1488 x 793, "cracked" eggs): start, the egg picture (`PremiumHatchEgg`, 304 x 260 flat picture) and the condition pill at the bottom; about 1.2 s later the left bucket and its colour chip (210 x 50 round pill); about 0.8 s later the right bucket and chip; about 0.2 s later the pattern pill (220 x 34) and the 3D egg (`NativeHatchEgg`, a 268 x 268 box that grows to 345 x 345 while it wobbles); then crack, dino, and the buttons or "Tap for next egg".

| Piece | Picture | Judged against docs/114 s4, docs/72, docs/87 |
| --- | --- | --- |
| Start: egg picture + condition pill | 213, 243 | egg ok; pill is a thin outline pill with 14 px text, nothing like the chunky buttons |
| Paint bucket | 213, 215, 243, 244 | flat grey rectangles at an angle, only a thin coloured band at the top. Does not read as paint, no splash of the colour. Not low-poly, not chunky, no outline |
| Colour chip (left and right) | 233, 243 to 245, 239 | round pill with a dot swatch, the colour name, a grey or coloured tier badge. The dot is the shell colour after the Dirty tint, not the colour itself |
| Rarity tag in the chip | 239, 245 | "COMMON" grey, "UNCOMMON" green: readable, uses the shared rarity colours; but old colour odds (build is before #513) |
| Pattern chip | 233, 245 | outline pill "Dots" / "No pattern" / "Freckles", dark fill, thin line |
| Condition chip / overlay | 213, 236, 239 | "Cracked / hatches 1 in 5" pill with a yellow outline, "Dirty", "Rainbow": plain pills; dirt and cracks are drawn on the egg |
| Egg scale, ONE colour vs TWO colours | 243 vs 246 | **reproduced**: one colour: flat egg about 188 px wide. When the second colour and pattern arrive, the 3D egg takes over and is about 114 px wide, then grows to about 147 px while it wobbles |
| Rainbow egg | 239, 249, 250 | pale rainbow streaks and small white sparkle crosses over the egg; bursts with confetti. Looks weak next to the rest. **Astra egg: not seen** (rate 0.5 percent; not forced) |
| Dino reveal | 240, 247, 248, 256 | dino shown on a teal card, name, rarity bar, colour and pattern line, "Tap for next egg" |
| Buttons | 242, 254 | NEXT EGG, DONE, TRY AGAIN: bright fill with a dark heavy outline text; readable but heavy; DONE and TRY AGAIN sit 12 px below the "Cracked eggs hatch 1 time in 5" line |
| Skip the rest | 247, 252 | bottom right, good |

### Defect table (new rows, all Backlog)

| # | Defect | Severity | Pictures | Suggested fix | Row |
| --- | --- | --- | --- | --- | --- |
| C1 | **Paint bucket looks cheap and its colour is hard to see.** Flat grey bucket, thin band only. Reproduced | P2 | 213, 215, 243, 244 | draw the bucket as a chunky low-poly / outlined icon (asset task, docs/72: Blender or owner ChatGPT, registry line) and tip it so the colour pours out with a real splash in the colour | BD-1069 |
| C2 | **Chip dot is not the colour named.** Measured: Blue chip dot RGB 141,183,203 (the colour is 36,132,211); Green dot 76,187,101 (the colour is 29,175,75); a second "Cream" chip had a darker dot 160,152,127. A "Cream" chip showed a green dot (243) | P2 | 243, 244, 245 | the dot always uses `EggColors` rgb, never the shell tint | BD-1069 |
| C3 | **Round pill chips match nothing else in the game.** The game uses chunky rounded rectangles with 2 to 3 px outlines; these are fully round | P2 | 233, 243, 245 | one chip style for the whole game (section 4) | BD-1070 |
| C4 | **Egg size jumps when the second colour arrives** (188 px to 114 px to 147 px) because a flat picture is swapped for a 3D viewport | P2 | 243, 246 | draw both with the same size and pivot (or use the 3D egg from the start); never change scale at a stage change | BD-1071 |
| C5 | **Rainbow effect looks pale and old** (thin streaks, white crosses). Astra not seen | P3 | 239, 249 | a Blender-rendered rainbow sheen texture (docs/83); check Astra when one appears | BD-1072 |
| C6 | **Reveal card layout:** "Egg N of M" lies over the dino's head, the head is cut at the card top, "BIG" prints over the plinth, "Skip the rest" stops without saying why (eggs that stop for being Rainbow show no Rainbow tag on the dino card) | P3 | 247, 248, 251, 252 | move the counter to the header, lower the dino, put the stop reason ("Rainbow egg!") on the card | BD-1073 |

Other new rows from the walkthrough (not hatch audit): BD-1066 (black charged dino), BD-1067 (small window layouts), BD-1068 (class icons do not load), BD-1074 (small things: key twice, Goals outside tap, potion row, hub prompt reach, rail "At home" labels).

## 4. One chip style for the whole game (proposal)

**Chunky tag:** a rounded rectangle (corner about 8 to 10 px, not a pill), 3 px dark outline (`Theme.Colors.outline`), flat fill, FredokaOne text with a 2 px dark stroke at least 14 px, minimum height 28 px (44 px if it can be tapped). Colour comes from the shared tables: rarity from `Theme.RarityColors`, colours from `EggColors`, conditions from the condition palette. A colour dot, when needed, is a small rounded square with the same outline and the exact palette colour. Use it for: hatch chips, rarity tags in shops (the Common / Tier 1 chips in the Auras tab, picture 222), Dino Index tags, fusion tags, the condition and pattern lines. LEAD decision under the owner's 2026-10-16 autonomy: this is a proposal; the owner overrules by picking a picture in the dashboard.

## 5. Things not tested

Escape (tool cannot send it), phone, gamepad, two players, published server, sound, Astra egg, Legendary stop, fusing (menu only), trails and conditions tabs, Settings Reduce Motion toggle, `regression_walk` (blocked), secret dinos.

## 6. Working notes (what cost time)

* The first Studio window opened on a real screen because `monitor4` skips a window that has focus; it was on the virtual monitor later by itself.
* Reading the shared GUI with `GetDescendants` and a "visible" walk was fast once I stopped calling `FindFirstAncestorOfClass`; a first helper call timed out after 2 minutes (not a freeze).
* The window size changed twice (1156 to 1488 to 848 wide); every click map had to be re-read from `AbsolutePosition`. Reading positions with a script (`shared.Q`) saved most time.
* Admin F2 key plus clicks started weather by accident (thunder, volcano, rain); I used the same `AdminAction` remote the slider uses for the x10 food value.
