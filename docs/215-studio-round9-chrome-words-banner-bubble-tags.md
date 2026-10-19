# 215 Studio round 9: window chrome, coloured rarity words, rare-find banner, stall bubble, hatch tags (BD-1133, 1135, 1114, 1111, 1134)

Label: **STUDIO EVIDENCE**, written 2026-10-19 by the Studio QA helper. Playtest build of `origin/main` `71fec69f` (screen label **BUILD redesign-020 71fec69f**, `playtest_freshness.py`: up to date). In-game crystals only (one 20 crystal potion), nothing published, no chances forced, keyboard and mouse only. Pictures 457 to 517 in `docs/evidence/review-2026-10-17/`; list and verdicts in [evidence/2026-10-19-studio-r9/README.md](evidence/2026-10-19-studio-r9/README.md).

## 1. Window sizes

First 1156 x 793 (window on a 1080p screen), then 296 x 304 by itself, then **516 x 481** after `monitor4.py place --maximize`. Most checks were done at 516 x 481, the small-window layout.

## 2. Pass or fail

| Item | Verdict |
| --- | --- |
| 1 Window chrome (BD-1117, BD-1119) | **PASS with one exception.** Title in the outlined style and a red square X (48 x 48 measured at 516) in Tutorial, Index, Eggs, every shop page, Potions, Settings (all tabs), Go home, Run Complete, Auto-opened summary, Food guide (pictures 457 to 483, 494, 503 to 511). Closes by X, tap outside, C twice, E at the stall, B twice. **Escape does not work through the key tool** (cannot judge). **Exception: the Fusion menu X is 60 x 44 / 62 x 45, not a 48 square** (BD-1146). Card text readable, nothing cut except Fusion (BD-1146). |
| 2 Coloured rarity words (BD-1120) | **MOSTLY PASS.** Coloured: Eggs auto-open line, Index Patterns and Colours labels, potion names, banner. Filled chips keep a white word (aura and trail chips, Common chip darker grey, whole). **Still white:** the Auto-opened summary line and the Auto toggles in their AUTO state; the Common grey is faint on dark cards (BD-1147). |
| 3 Rare-find banner (BD-1121) | **PASS.** No natural rare hatch came in 48 eggs: **not seen naturally.** Shown by a TEST CALL: in the throwaway Studio the server datamodel fired the real `BeDinoRemotes.RareHatch` remote at me with the same payload shape `RareHatchService` sends other players (legendary, epic shiny mutant, secret). Look: huge outlined RARE FIND!, one sentence with a coloured rarity word, no panel, no name, secret never names the species, gone after about 4 s (pictures 513 to 516). At 516 it lies over the rail icons while it shows (BD-1148). Reduce Motion not tried. |
| 4 Stall bubble (BD-1128, 1130, 1133) | **PASS.** Nests, Potions, Fuse, Shop, Dinos, Heart: visible, clear of rail, weather, Home, Explore, Tell us!, Admin at 516 and 1156. Tell us! and Admin hide while Fusion is open. Heart says "Show off". AUTO opens Settings on Help. Settings Look and Controls rows spaced. "You have 1" on the Trails tile. Not seen: the weather line at the start of a weather (faded before the picture); a sold-out potion card. Small defect: the Potions bubble covers the left text of an open Goals sheet. |
| 5 Hatch tags (BD-1107, 1114) | **FAIL.** Natural Rainbow and BIG and Blood Moon eggs came. Tags are drawn with **TextSize 100** in boxes about 106 x 15 px, so they show as huge overlapping letters cut to "B...", "Sk...", "N..." (pictures 488 to 493); the colour chip word "Cream" is cut by the COMMON chip (489). Likely the real engine text measure gives 0 and the fit falls back to the 100 maximum; the offline mock cannot see that (BD-1145, P1). Better than round 8: the Rainbow title "Rainbow egg! Always shown" sits whole in the header; the class badge sits left of the name. Goals sheet opens under the rail (BD-1108 PASS). Fusion tab names whole (BD-1103 PASS). |
| 6 BD-1111 moved screens | **PASS for what was reached**, no console error from game scripts: Dino Index (cards, arrows, Collected bar, FUSION button, Patterns and Colours tabs back to Dinos), details, Sort and filter, Back, Settings (4 tabs), Go home, Run Complete, Auto-opened summary, Food guide, Tutorial, Eggs. No rename control found. Not reached: Escape, gamepad, phone, secret cards. |
| 7 BD-1134 | **Still there:** bottom third of the Index panel empty in all three tabs, class badge icon only, Species and Boost lines of My dinos hidden under EQUIP and BACK; new: BLOOD M chips cut on grid cards, Sort and filter DONE cut at the top. DEWDROP chip and the left-cut tab not seen (no Dewdrop egg). |

## 3. New defects

| # | Defect | Picture | Severity | Row | Suggested fix |
| --- | --- | --- | --- | --- | --- |
| 1 | Hatch tags TextSize 100, cut to B..., Sk..., N...; "Cream" chip cut | 488 to 493, 489 | P1 | BD-1145 | clamp the fitted size, re-measure after the font loads |
| 2 | Fusion X 62 x 45; "Pu t"; odds line cut | 500, 463 | P3 | BD-1146 | use the shared X size and floors |
| 3 | Summary line and AUTO toggles white; Common grey faint | 484, 494, 471 | P3 | BD-1147 | colour the words, lighten Common on dark |
| 4 | Own-hatch banner covers title and X; egg touches header; banner and Potions bubble over HUD | 487, 490, 513, 512 | P3 | BD-1148 | place banners clear of the header and rail |
| 5 | Left over checks | 517 | P2 | BD-1149 | next round |

## 4. Not verified

Weather title at weather start, 848 x 423, 667 x 339, phone, gamepad, Escape, the G key, a natural Rare+ hatch, Dewdrop reveal, Reduce Motion, a banner from a real second player. Looks judged against docs/114 section 4 and docs/72: calm and clear except the hatch tags, which are ugly.

Tool notes: a single mouse click often did nothing; a move to a nearby point, a wait, a move onto the button, a wait, then down, wait, up worked every time. The stall prompts need the character inside 10 studs but some stalls push it back: stand 4 studs from the point. The Studio window changed size by itself once (296 x 304).
