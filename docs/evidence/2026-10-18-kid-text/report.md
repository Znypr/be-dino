# Kid-text report, 2026-10-18 (BD-655)

One run of `python tools/lint_kid_text.py --report --top 20 --markdown` on the real tree (`src/client` and `src/shared`).
This is a LIST ONLY. No game text was changed. It shows where player text is longest, loudest or most technical,
so the owner can decide what to rewrite. How the tool works: [162](../../162-kid-text-lint-and-screenshot-diff.md).

How to read it: LONG_TEXT = too many words or letters for the place it sits (limits are in one table in the tool).
SHOUTING = ALL CAPITALS beyond a short word. TECH_PUNCT = marks like `;` `[ ]` `->`. JARGON = words a child should not need
(server, profile, cooldown, request...). Good news: no "5m 0s" style times were found, and only one "1.2x" and one decimal.

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
