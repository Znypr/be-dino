# Kid-text report, 2026-10-18 (BD-655, fixes BD-998)

Two runs of `python tools/lint_kid_text.py --report --top 20 --markdown` on the real tree (`src/client` and `src/shared`).
How the tool works: [162](../../162-kid-text-lint-and-screenshot-diff.md).

How to read it: LONG_TEXT = too many words or letters for the place it sits (limits are in one table in the tool).
SHOUTING = ALL CAPITALS beyond a short word. TECH_PUNCT = marks like `;` `[ ]` `->`. JARGON = words a child should not need
(server, profile, cooldown, request...).

## Before and after (BD-998)

| | First run (list only, no text changed) | After the rewrite |
| --- | ---: | ---: |
| Problems | **94** | **5** |
| Files with a problem | 15 | 5 |
| LONG_TEXT | 39 | 5 |
| SHOUTING | 26 | 0 |
| TECH_PUNCT | 15 | 0 |
| JARGON | 12 | 0 |
| MULTIPLIER (1.2x) | 1 | 0 |
| DECIMAL | 1 | 0 |

Only wording changed. No layout, flag, remote or config code was touched, and no number in any odds text changed.
Offline evidence only: the new texts have NOT been looked at in Studio at real sizes or on a phone yet.

### Eight example rewrites

| Where | Before | After |
| --- | --- | --- |
| Home card button | `EXPLORE ISLAND` | `Explore` |
| Egg shop, odds button | `ODDS / DETAILS` | `Chances` (the panel is now titled "Egg Chances") |
| Egg chances panel | `BACK TO SHOP` | `Back` |
| Fusion error | `Your profile session moved. Rejoin, then reopen Fusion to see the result.` | `Rejoin the game, then open Fusion to see the result.` |
| Fusion error | `Saving failed. Nothing is lost; retrying with the same request.` | `Could not save, but nothing was lost. Trying again.` |
| Odds line (BIG size) | `Normal size: 97%; BIG (Rare): 3% (size only, 1.2x)` | `Normal size: 97%, BIG (Rare): 3%. Size only, 20% bigger.` |
| Potion replace button | `REPLACE & USE` | `Replace` |
| Index detail button | `BACK TO INDEX` | `Back` (the old Dinosaur Fusion pages were removed on main, so their rewrites are gone with them) |

More: `SORT / FILTER (2)` -> `Sort/filter (2)`; `Request token invalid. Please confirm again.` -> `That did not work. Please confirm again.`;
`Crystals • already banked` -> `Crystals, already saved`; `HOW TO PLAY` -> `How to play`; `LEAP [E] • READY` -> `LEAP [E] ready`;
`TAP TO GO!` -> `Tap to go!`; `BACK TO SANCTUARY` -> `Back home`; tutorial step `JUMP & EXPLORE` -> `JUMP & LEAP`;
mini-goal names `Add a dino toward a fusion step` -> `Add a fusion dino`, `Hatch a Rare or better` -> `Hatch Rare or better`.

Odds disclosure: every percentage is unchanged. The two longest ShopOdds lines were split into shorter lines so nothing was
dropped: Shiny in Volcano, Northern Lights, Earthquake and Blood Moon, 0% in other weather, BIG rolled separately, only Cracked
can fail, totals are rounded, filters keep the original chances. One small reassurance was dropped on purpose: the Settings help
page no longer adds "Auto-opened eggs are still saved!" (the auto-open summary screen already says "All saved in your collection!").

### What is left (5 problems, kept on purpose, all in the baseline file)

| Text | Why it stays |
| --- | --- |
| `Eat 500 food for %d eggs. Weather can add more!` (Food guide) | Two short friendly sentences in a wide box. The tool's "label" limit is for small labels; cutting the weather hint would lose a useful tip. |
| `Your last fusion did not finish. Check result is safe: it never fuses twice.` (Fusion, after a lost answer) | The reassurance that a retry never fuses twice is the point of this screen. It fills a big status box. |
| `Oops! Splat!` (failed Cracked egg title) | A cheerful two-word cry on purpose (calm, bubbly tone, [114](../../114-handbook.md)). A test pins the wording. |
| `A tiny chance of a secret dino in free eggs` (Egg Chances, free eggs) | The owner reviewed this exact sentence (a test pins it): it says free eggs only and a tiny chance, so it is not changed. 43 letters against a 40 limit. |
| `Secret find! You hatched a ...!` (secret dino hatch) | A celebration line; two short sentences read as one cheer. A test pins the wording. |

Two more texts are allowed in `tools/lint_kid_text_allow.json`, each with a reason (not counted above): `LEAP [E] ready` (the
bracket letter is the key picture, same as the existing `LEAP [E]` entry) and `You got a gift from` (only the first half of a
title; the sender's name follows, so the whole title is short).

---

# First run (before any text was changed)

This was a LIST ONLY. It shows where player text was longest, loudest or most technical. Good news at that time: no "5m 0s"
style times were found, and only one "1.2x" and one decimal.

Kid-text report: 94 problems in 15 of 387 files scanned.

## By rule
- LONG_TEXT: 39
- SHOUTING: 26
- TECH_PUNCT: 15
- JARGON: 12
- MULTIPLIER: 1
- DECIMAL: 1

## Top 20 files
| # | File | Problems | Mix |
| ---: | --- | ---: | --- |
| 1 | `src/client/Bootstrap.client.luau` | 30 | SHOUTING 15, LONG_TEXT 11, TECH_PUNCT 3, JARGON 1 |
| 2 | `src/shared/FusionSelection.luau` | 21 | JARGON 10, LONG_TEXT 6, TECH_PUNCT 3, SHOUTING 2 |
| 3 | `src/shared/ShopOdds.luau` | 12 | TECH_PUNCT 6, LONG_TEXT 2, SHOUTING 1, MULTIPLIER 1, DECIMAL 1, JARGON 1 |
| 4 | `src/client/FusionMenu.luau` | 8 | LONG_TEXT 7, SHOUTING 1 |
| 5 | `src/client/DinoIndexPanels.luau` | 5 | SHOUTING 3, LONG_TEXT 2 |
| 6 | `src/shared/EggOutcomeView.luau` | 3 | TECH_PUNCT 3 |
| 7 | `src/shared/FtueCopy.luau` | 3 | LONG_TEXT 2, SHOUTING 1 |
| 8 | `src/shared/ObjectiveConfig.luau` | 3 | LONG_TEXT 3 |
| 9 | `src/shared/FtueP1.luau` | 2 | LONG_TEXT 1, SHOUTING 1 |
| 10 | `src/shared/OddsCopy.luau` | 2 | LONG_TEXT 2 |
| 11 | `src/client/RunComplete.luau` | 1 | SHOUTING 1 |
| 12 | `src/shared/FtueRules.luau` | 1 | SHOUTING 1 |
| 13 | `src/shared/GiftUiModel.luau` | 1 | LONG_TEXT 1 |
| 14 | `src/shared/HatchTimeline.luau` | 1 | LONG_TEXT 1 |
| 15 | `src/shared/RareHatch.luau` | 1 | LONG_TEXT 1 |

## Top 20 worst single texts (most rules broken at once)
- `src/client/Bootstrap.client.luau:998` "PATTERN FUSION: 6 -> NEW GOLD" - LONG_TEXT, SHOUTING, TECH_PUNCT
- `src/shared/FusionSelection.luau:565` "Saving failed. Nothing is lost; retrying with the same request." - JARGON, LONG_TEXT, TECH_PUNCT
- `src/shared/ShopOdds.luau:36` "Normal size: %g%%; BIG (Rare): %g%% (size only, 1.2x)" - DECIMAL, MULTIPLIER, TECH_PUNCT
- `src/client/Bootstrap.client.luau:726` "FINAL OUTCOME DETAILS" - LONG_TEXT, SHOUTING
- `src/client/Bootstrap.client.luau:967` "Cosmetic fusion: 6 Base → Gold; 3 Gold → Emerald; 2 Emerald → Diamond. Highest o" - LONG_TEXT, TECH_PUNCT
- `src/client/Bootstrap.client.luau:1380` "LEAP [E] • READY" - SHOUTING, TECH_PUNCT
- `src/client/DinoIndexPanels.luau:447` "SORT / FILTER (" - LONG_TEXT, SHOUTING
- `src/client/FusionMenu.luau:970` "Your last fusion did not get an answer. CHECK RESULT asks again for the SAME fus" - LONG_TEXT, SHOUTING
- `src/shared/FusionSelection.luau:556` "Your dinos changed. Odds were refreshed; please review and confirm again." - LONG_TEXT, TECH_PUNCT
- `src/shared/FusionSelection.luau:566` "Your profile session moved. Rejoin, then reopen Fusion to see the result." - JARGON, LONG_TEXT
- `src/shared/ShopOdds.luau:38` "Earned eggs: Shiny (Epic) %g%% during Volcano, Northern Lights, Earthquake or Bl" - LONG_TEXT, TECH_PUNCT
- `src/shared/ShopOdds.luau:39` "Each combined outcome multiplies its independent probabilities; only Cracked can" - JARGON, TECH_PUNCT
- `src/shared/ShopOdds.luau:40` "Displayed percentages are rounded; their total may differ from 100%. Filters ret" - LONG_TEXT, TECH_PUNCT
- `src/client/Bootstrap.client.luau:502` "EXPLORE ISLAND" - SHOUTING
- `src/client/Bootstrap.client.luau:543` "ODDS / DETAILS" - SHOUTING
- `src/client/Bootstrap.client.luau:727` "BACK TO SHOP" - SHOUTING
- `src/client/Bootstrap.client.luau:753` "ODDS / DETAILS" - SHOUTING
- `src/client/Bootstrap.client.luau:820` "Rarer potions appear less often. Six of twelve are offered each restock." - LONG_TEXT
- `src/client/Bootstrap.client.luau:841` "No potions yet. Buy from this restock's offers above." - LONG_TEXT
- `src/client/Bootstrap.client.luau:849` "potion ends immediately. Its remaining time is lost. Consume 1 potion for a fres" - LONG_TEXT
