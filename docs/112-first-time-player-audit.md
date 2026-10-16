# 112 First-time player audit: the first 10 minutes (2026-10-16)

Label: **CURRENT BUILD BEHAVIOR** (main at 92cf941, `redesign-020`, playtest profile, low-poly dinos on). Method: own temp Studio copy of `python tools/build.py --profile playtest`, Play mode, one player, no seed, the Admin panel never opened. Played only with what the screens say. Screenshots: [evidence/2026-10-16-ftue/](evidence/2026-10-16-ftue/) (01 to 19, 765 x 784 viewport). Per [87](87-vision-and-feel-guide.md) (calm, bubbly, kind) and [72](72-ui-copy-and-asset-standards.md) (short words for children).

## Honest limits
- Studio is not a real child. A bot (`Humanoid:MoveTo` the nearest food) walked, because injected keys do not move the character (docs/108). It eats the nearest thing, which is what a child does too, but it never gets lost, so real times are longer.
- Studio gives the test wallet (1,000,000 Crystals), a "STUDIO PREVIEW" line, a BUILD line, an Admin button and a "FOOD: 2375" debug line. None of those exist on a published server (`HudRules.showFoodDebug`). The wallet means I could not see the poor-child shop state.
- Phone, sound and a live second player were not tested. I could not hear anything: "loud or sharp" moments are judged from visuals only.
- Fresh profile: no seed, but Studio local profiles start with one Compy, so "Collected 1 of 22" in the Index is the starter.

## The journey, step by step
Rating = would a 7 to 10 year old understand and want to go on (1 lost, 10 effortless).

| # | Step (screenshot) | What happens | Where a child gets confused or bored | Rating |
| --- | --- | --- | --- | --- |
| 1 | Loading (01) | "BE DINO! Loading your collection..." and a green bar. | Fine, short. | 9 |
| 2 | Welcome modal (02) | Three cards: EAT & GROW "Find small food clusters across the island.", JUMP & EXPLORE "Space to jump, E to leap. Buttons on mobile.", BANK & HATCH "Return to sanctuary to bank catches and eggs." Big LET'S PLAY. | "clusters", "mobile", "sanctuary", "bank", "catches" are all adult words. Nothing says how to walk (W A S D / stick) or that eating makes eggs. Cards are a wall of 22 px text for a child who wants to play. **Fixed in this PR** (new copy below). | 5 (was 4) |
| 3 | Lobby (03) | Dino seen from behind in a small stone area. Left column: DINOS, EGGS, FUSION, SHOP, POTIONS, SETTINGS. Right: LEAP [E] READY, Weather in 4 min. Bottom: EGGS 0, EXPLORE ISLAND. Top: Crystals, "Goal Level 1: 0/100 XP". | **Nine controls at once** and no arrow to the one that matters (EXPLORE ISLAND is lower-middle and dark green on dark green). FUSION is open on minute zero but needs 6 of one dino. "Goal Level 1: 0/100 XP" says nothing about what the goal is. Nobody says "walk out and eat". | 5 |
| 4 | Eggs, empty (04) | "Nests 0/5 ... Nest eggs are lucky!", "Eggs waiting: 0", "No eggs yet", big "NO EGGS", AUTO, "Auto-open: off". | Empty screen with no next step ("Eat food on the island to find eggs"). "Nests" and "Auto-open" are unexplained. Five empty nests read as a chore list. | 4 |
| 5 | Shop (05, 06) | Tabs AURAS, TRAILS, EGGS, CONDITIONS, CRYSTALS. Cards "Meadow Glow, Common, Tier 1, Growth +15%, 60 Crystals, BUY". Conditions tab: "Condition level 0", five eggs with 50%, 30%, 15%, 4.5%, 0.5%, a green "UPGRADE: 100 CRYSTALS" button and under it "Reach level 3 to buy this." | "Aura", "Tier", "Condition", "Crystals" never explained. The Conditions tab tells a child that half of their eggs are **Cracked** and the green button is not buyable (the line under it contradicts it). A new player has 0 crystals, so on day one every BUY is a dead end. | 3 |
| 6 | Settings (07, 08) | Sound sliders, LOOK, CONTROLS (Camera RESET, Jump button size), HELP (HOW TO PLAY, FOOD GUIDE, Auto-open eggs). | Calm and clear. **CONTROLS lists no keys** (no W A S D, Space, E, mouse drag), so a keyboard child cannot look them up. "Auto-open eggs: Common SHOW" is a hard sentence for a child. HOW TO PLAY reopens the same 3 cards. | 6 |
| 7 | Start the run (09) | Press EXPLORE ISLAND. The button turns red HOME. The camera stays behind the dino. | **No goal on screen.** Food is small coloured bits in grass, the SIZE bar has no explanation, there is no arrow and no "eat this" prompt. The six menu buttons stay on the left and cover a fifth of the view while running. Calm, pretty world though (low-poly dino reads well). | 4 |
| 8 | Eating (10, 11) | Walking into food raises Growth and fills SIZE a little. Berry = 1 point, fruit 4, egg 15, amber 50. | **A berry is worth 1 and the first egg needs about 110 to 125 points** (`FoodCatchRate = 4/500` with carry), so the first egg took **about 4 min 10 s** with a bot that never wanders and never stops, and 2 min 20 s in run two (bigger food, +20% weather). No bar or counter says "next egg in X". Nothing happens when an egg is found except the number "EGGS 1" changing in a corner: no pop, no sound cue seen, no toast. A child will not notice they earned something. | 3 |
| 9 | Weather (11) | "Volcanic Bloom 1 min", "Growth +20% • Loot +65%" under it. | Nice surprise, but the buff line is about 11 px and "Loot" is jargon. | 6 |
| 10 | HOME (12) | Confirm "Return to Sanctuary? Your current run will end and rewards will be banked. Banking 1 catches • 65 growth", RETURN / CANCEL. | Three different names for one thing (HOME button, Sanctuary, "banked"). "1 catches" is a grammar error. **Fixed in this PR** ("You found 1 egg  •  Growth 65"). | 5 |
| 11 | Run Complete (13) | Trophy, "Growth 68", "Catches 1", "1 run egg \| 1 egg nest", "+7 Crystals • Level 1", BACK TO SANCTUARY / OPEN EGGS. | "Catches", "run egg", "egg nest" are three words for eggs. Both big buttons are clear (OPEN EGGS is a good next step). **"Catches" fixed to "Eggs found".** Server text "run egg / egg nest" is filed (BD-373). | 6 |
| 12 | Eggs, ready (14) | Egg card with "Common" and "Cracked" tags, "Eggs waiting: 0", READY!, big green OPEN, a nest with "2 h 59 min". | "Eggs waiting: 0" next to a READY egg reads as a bug. "Cracked" has no warning that it can fail. A 3 hour timer is a wall for a child, nothing says "it opens by itself later" or "come back". | 5 |
| 13 | Hatch (15, 16) | "An egg is hatching..." with a cracked egg, "Cracked • hatches 1 in 5", then "Oops! Splat! This cracked egg did not hatch. Cracked eggs hatch 1 time in 5", then a plain "Done". | **The first reward of the whole game was a fail, after 4 minutes.** Both of my first two eggs were Cracked and both splatted (an egg is Cracked 50% of the time and a Cracked egg fails 80% of the time: 40% of children get nothing from their first egg, see section 3). The splat art is gentle and the words are kind, but there is no consolation (no crystal, no "try again, nests are luckier"). "Done" is grey text, not a button. | 2 |
| 14 | After the splat (17) | Back to the empty Eggs screen: "NO EGGS", nest 2 h 57 min. | **Dead end.** No hint to run again. | 3 |
| 15 | Dino Index (18) | Compy found, 21 black silhouettes, "Collected 1 of 22 (4%)", FUSION button. | The nicest screen: silhouettes make a child want to find more. "1 Base • 0 Gold • 0 Diamond" is about 10 px. "Common • 26% of eggs" is a number a child does not need. | 7 |
| 16 | First crystal | Gold gems lie in the grass. | I only saw "+7 Crystals" in the Run Complete toast; nothing says what crystals buy, and the nearest use (SHOP) shows prices a new player cannot pay. | 4 |

Time measurements (Studio, bot, run one / run two): start to first egg found **about 4 min 10 s / 2 min 20 s**; end of run to the hatch screen **about 25 s** (HOME, RETURN, OPEN EGGS, OPEN, 5 s hatch); start to the **first hatch result about 5 min**, and that result was a splat twice. First successfully hatched dino: **not reached in 10 minutes of play** (0 of 2). A child that gets lost will be slower: expect 6 to 8 minutes to the first egg, which is longer than the attention span of the audience.

## 2. Readability scan (by eye from the 765 x 784 screenshots; not measured with a tool)
| Item | Approx. size | Verdict |
| --- | --- | --- |
| Welcome card body | 22 px, white on dark grey | Readable; too much text per card for the target age |
| Menu buttons (DINOS...) | about 22 px bold, white on bright fill | Good |
| Egg tags "Common / Cracked" | about 15 px | OK; "Cracked" purple on purple fill is low contrast |
| Weather buff line "Growth +20% • Loot +65%" | about 11 px, grey-gold on dark | Too small and low contrast |
| "Weather in 4 min" | about 15 px, white-grey | OK |
| Index counts "1 Base • 0 Gold • 0 Diamond" | about 10 px | Too small |
| "Done" on the splat screen | about 30 px but dark grey (#555 on #222, roughly 2:1) | Fails contrast, and it is not styled as a button |
| "Reach level 3 to buy this." | about 17 px gold | Readable but contradicts the button above it |
| BUILD / STUDIO PREVIEW lines | about 14 px | Studio only |

## 3. Egg odds a first-time child meets (from `ProgressionConfig` and `HatchTimeline`)
Cracked eggs are 50% of eggs at Condition level 0 and hatch only 1 in 5. P(first egg splats) = 0.5 x 0.8 = 40%; P(both of the first two splat) = 16%. This run hit it. This is the single worst moment in the first ten minutes.

## 4. Ranked fix list
### P0 (a child quits or feels cheated)
1. **First egg must not splat.** Make the first N (suggest 3) run eggs of a new profile never Cracked (or give Cracked eggs a consolation: a few crystals and "Cracked eggs are tricky. Nest eggs are luckier!"). Owner decision on odds (docs/09 ties the 50% to the target), filed as BD-365.
2. **Give the run a goal and a feedback loop.** A first-run hint chip after LET'S PLAY ("Eat food to find eggs!", gone after the first egg), an egg progress ring or bar ("Next egg"), and a gentle pop plus soft sound when an egg is found ("You found an egg!"). Starter area with fruit and amber so the first egg takes under 60 s. BD-366 and BD-367.
3. **Do not show nine controls on minute zero.** Hide SHOP, POTIONS and FUSION until the first hatch (or dim with a small "Later" lock) and point at EXPLORE ISLAND with a bouncing arrow. BD-368.

### P1 (confusing words and dead ends)
4. Fixed in this PR (small copy): welcome cards, HOME confirm, "Catches" label (`src/shared/FtueCopy.luau`, `tools/verify_ftue_copy.py`).
5. Eggs screen: "Eggs waiting: 0" next to READY (hide it at 0 or say "More eggs: 0"); empty state "No eggs yet. Eat food on the island!"; a short note under the nest timer ("Opens by itself. Come back later!"); add a one-line "Cracked eggs may not hatch" under the tags before OPEN. BD-369.
6. After a splat, show "Run again" next to Done and style Done as a real button. BD-371.
7. Shop on day one: hide the Conditions tab until level 3, reword jargon ("Aura" is fine with a one-line hint "Glow that helps you grow", drop "Tier 1/2/3", "Crystals" shown as the gem icon), and replace the contradicting line "Reach level 3 to buy this." by a locked button. BD-372.
8. Server reward line "1 run egg | 1 egg nest" to "1 egg + 1 nest egg" or an icon row (touches `verify_nests`/`verify_progression` strings). BD-373.

### P2 (polish)
9. Controls tab: add the key list (W A S D move, Space jump, E leap, drag to look; phone: stick and buttons). BD-374.
10. Rename "Return to Sanctuary?" to "Go home?" to match the HOME button and the "Returning to Sanctuary..." toast. BD-375.
11. Raise the weather buff line and Index counts to at least 14 px; make "Loot" "Gems" or drop the number. BD-376.
12. Add a first-time "arrow to the nearest food" fade-in after 20 s without eating (never a loud effect).

### Concrete copy (docs/72 style)
| Where | Now | New (shipped here unless noted) |
| --- | --- | --- |
| Welcome 1 | Find small food clusters across the island. | Walk into food to eat it. Eat lots to find eggs! |
| Welcome 3 | BANK & HATCH: Return to sanctuary to bank catches and eggs. | SAVE & HATCH: Tap HOME to save your eggs. Then open them! |
| Welcome 2 | Buttons on mobile. | Buttons on phone. |
| HOME confirm | Your current run will end and rewards will be banked. Banking 1 catches  •  65 growth | Your run ends and your eggs are saved. You found 1 egg  •  Growth 65 |
| Run Complete | Catches 1 | Eggs found 1 |
| Hint chip (BD-366) | none | Eat food to find eggs! |
| Eggs empty (BD-369) | NO EGGS | No eggs yet. Eat food on the island! |
| Splat (BD-365/371) | Done | Run again / Close |

## 5. Top 10 problems
1. The first egg is Cracked half of the time and splats 80% of those (P0, BD-365).
2. No goal or hint once the run starts (P0, BD-366).
3. No visible or audible "you found an egg" moment (P0, BD-367).
4. First egg takes about 4 minutes on berries worth 1 point (P0, BD-366).
5. Nine buttons on the first screen, none pointed at (P0, BD-368).
6. Jargon: catches, banked, sanctuary, run egg, egg nest, condition, tier, loot (P1, fixed in part).
7. Eggs screen: "Eggs waiting: 0" beside READY, 3 hour timer, empty dead end (P1, BD-369).
8. Dead end after a splat, "Done" is not a button (P1, BD-371).
9. Shop: Conditions tab and a contradicting locked button, nothing affordable (P1, BD-372).
10. Controls tab has no keys; small 10 to 11 px text (P2, BD-374, BD-376).

## 6. What I changed
`src/shared/FtueCopy.luau` (new, pure strings), `src/client/Bootstrap.client.luau` (4 lines swapped to use it, no new top-level locals), `tools/verify_ftue_copy.py` (new). Rows BD-365 to BD-376 in the [kanban](07-kanban.md). Nothing else is changed; Build 020 behaviour and flags are untouched. Not re-screenshotted after the copy change (the screenshots show the old text on purpose); the new text needs one Studio look.
