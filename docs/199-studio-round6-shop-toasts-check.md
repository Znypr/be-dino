# 199 Studio round 6: shop, potion shop and toasts after the Bootstrap move (BD-1089)

Label: **STUDIO EVIDENCE**, 2026-10-18, by the Studio QA helper. Build screen label **BUILD redesign-020 66d71f3e** (playtest profile, main after #530, `playtest_freshness` said up to date). Window 500 x 465 (the only size; no tool can resize it). In-game crystals only, nothing published, no flag or chance forced, crystal packs untouched. Pictures 360 to 379 in `docs/evidence/review-2026-10-17/`, list and verdicts in [evidence/2026-10-18-studio-r6/README.md](evidence/2026-10-18-studio-r6/README.md). The owner asked to wrap up, so this round is short.

| Item | Verdict |
| --- | --- |
| A Shop landing and tabs (Auras, Trails, Eggs, Crystals) | PASS (the build has 4 tabs, no Conditions tab) |
| A Odds pages (Chances, More details) | PASS |
| A Buy aura and Cancel on the confirm page | PASS (cancel changed nothing; buy gave EQUIP) |
| A Potion Shop buy and use | PASS; replace and restock notice not reached |
| A Toast shows, tap dismisses | PASS; Calm motion and the Crystals plate check not reached |
| A Fusion menu, Dino Index open | PASS |
| A Console | no error or nil index from ShopScreens or Toasts; only Roblox UIBlox warnings and the tool's camera notice |
| B Small windows (BD-1085, BD-1067) | NOT DONE: only 500 x 465; the Eggs screen was not reached |
| C BD-1083, BD-1095, BD-1096, BD-1099 | not in this build (PRs not merged into 66d71f3e) |

Defects: BD-1101 (P1, Shop tabs under the HUD rail: a tap on the EGGS tab closed the shop and pressed the rail EGGS button, same cause as BD-1083, pictures 367 and 369), BD-1102 (P2, toasts cover the rail and menu tops, 361, 366, 376), BD-1103 (P3, small layout slips, 363 to 379). Left to re-check: BD-1104.

How to open the shops in Studio without walking: move the character to within 10 studs of the prompt in `workspace.HubWalkUpPrompts`, then click the rail button. The mouse tool takes GUI coordinates (AbsolutePosition), not screenshot pixels (screenshot y is about 57 more).
