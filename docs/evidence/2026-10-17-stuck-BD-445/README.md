# BD-445 / BD-372 first Shop visit with 0 crystals (2026-10-17, round 2)

Build: `python tools/build.py --profile playtest` to an own file, new Studio window, Play, single player, 1140x785. Scratch-copy config edits only (never committed): `StudioTestCrystals = 0` (the Studio test wallet normally gives 1,000,000), `NestIncubationSeconds = 20`. Input: real mouse clicks on the rail and Shop buttons. Nothing was written by hand.

| Step | Result | Image |
| --- | --- | --- |
| Shop landing at 0 crystals: 4 tiles (Auras, Trails, Eggs, Crystals), "You have 0" and the one-line hint "Play a run to earn crystals!" | PASS | 01 |
| CONDITIONS tab is hidden at account level 1 and 2 (tabs are AURAS / TRAILS / EGGS / CRYSTALS) | PASS | 02, 06 |
| Hint line on the Eggs tab | PASS | 02 |
| Hint line on the Auras / Trails page | FAIL then fixed: the hint was drawn on top of the footer line "Level 1 - 0 Crystals" and the two texts overlapped (BD-529) | 05 (before), 06 (after) |
| BUY EGG with 0 crystals | FAIL then fixed: opened the "Buy Egg?" confirm with a negative balance, and the confirm only answered "Not available yet" (BD-530) | 03, 04 (before), 07 (after: grey "NEED 150 CRYSTALS" button and toast) |
| CONDITIONS tab appearing at level 3, grey "Need N Crystals" button on it (BD-372) | NOT SEEN (only levels 1 and 2 were in the shop; the tab has to be opened at level 3+ with fewer crystals than the price) | - |

Fixes (small, in `src/client/Bootstrap.client.luau`, shop menu): the aura/trail pages now show the hint in the footer line instead of over it; BUY EGG is a grey "NEED 150 CRYSTALS" button with a toast when the balance is below `RandomEggPrice`, so no confirm opens.

Left for BD-445 / BD-372: open the Shop at level 3+ with fewer crystals than the cheapest condition upgrade (Studio: `StudioTestCrystals = 0`, play until `AccountLevel` is 3) and look at the CONDITIONS tab. Both rows stay Review / test until then.
