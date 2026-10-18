# 183 Faster fights (BD-1025)

Written 2026-10-18. Owner request, verbatim: "attacking dinos should be faster, and they should have less health, a fight should take like less time overall."

**CURRENT BUILD after this change. Offline numbers only: no Studio run. Combat is still behind `CombatEnabled` (off for real players).** Every number is PROVISIONAL.

## What changed (2 numbers)
| Number | Before | After | Who it touches |
| --- | --- | --- | --- |
| Bite cooldown (`CombatConfig.BiteCooldownSeconds`) | 0.9 s | **0.6 s** | every bite (players and wild predators; the 2 bites per second rate limit still fits) |
| Wild predator HP (`CombatConfig.WildHpX`, new) | 100% | **40%** of the normal HP for its size | wild predators only (`NpcPredatorRules.joinCombat`) |

Not changed: player HP (full), how hard a bite hits, class table, size curve (T-Rex and big dinos stay the strongest), the wild predator's own bite speed (one bite per 2.5 s, at most 2 per chase) and its damage. So **the damage a player takes per second is the same as before.** Players do not die faster.

## Before and after (`python tools/combat_fight_time.py --runner <luau.exe>`)
Bites = how many bites to win. Seconds = time from the first bite (it lands at once), perfect hits, no regen, so real fights are a little longer. The wild predators are all Ground dinos today, so the table is "each player class bites a wild Ground predator".

**Even fight (player and wild predator the same size):**
| Player class | Wild HP | Bites | Seconds |
| --- | --- | --- | --- |
| Ground | 135 -> 54 | 22 -> **9** | 18.9 -> **4.8** |
| Water | 135 -> 54 | 27 -> 11 | 23.4 -> 6.0 |
| Fly | 135 -> 54 | 17 -> 7 | 14.4 -> 3.6 |
| Armored | 135 -> 54 | 30 -> 12 | 26.1 -> 6.6 |

**Small against big, first try: SUPERSEDED the same day.** The first version only changed the cooldown and wild HP and gave 26 -> 11 bites for a fresh player against the biggest wild predator. Owner (2026-10-18): "no, that should be almost instant". Replaced by the size-difference curve below.

**Player against player (even, size 1; HP not changed, only the cooldown):** Ground 14.4 -> 9.6 s, Fly 8.1 -> 5.4 s, Water 23.4 -> 15.6 s, Armored 27.9 -> 18.6 s. Bites stay 17 / 10 / 27 / 32.

Studio check from round 2 (docs/145): "about 24 bites" for a wild predator. The model says 22 before, so the numbers agree. It should now be about 9 to 11 bites and about 5 to 6 seconds.

## Part 2: the size difference sets the fight (owner 2026-10-18)
Owner, plain words: similar sizes = a longer fight (so dinos do not fight each other and eat to grow instead); a big size difference = exponentially shorter; the biggest difference is a ONE-SHOT; a small one never goes up to a big one and a big one never goes up to a small one; 100-growth vs 800-growth about 5 bites.

**The size number.** Bites depend on z = 1 + growth / 50 (growth = `GrowthScore`, capped at 750), which is the drawn scale squared (`s = sqrt(1 + growth/50)`, cap 4, docs/139). So z runs from 1 to 16. **R = bigger z / smaller z**, so the biggest possible R is 16 (a fresh dino against a capped one; BIG dinos count as 16). 100 vs 800 growth is R 5.3, because 800 is above the 750 cap. Mismatch worth knowing: the old combat scale `Stats.scale(growth)` only reaches 1.7 at growth 750 (it was made for the old food score), so HP and damage hardly differ between a small and a big dino; the new rule uses z, not that scale.

**Bigger hits smaller:** bites = 1 + (B0 - 1) x (1 - x^1.37), x = ln R / ln 16, B0 = 9 (or the even-fight bites if fewer). Gentle at first, steeper at the end, exactly 1 bite at R = 16. A long even fight (two players, 22 bites) eases into the curve over the first part of the range, so there is no step at R = 1. **Smaller hits bigger:** the bite is multiplied by 0.1^(y^1.5), y = ln R / ln 16 (1 at R = 1, 0.1 at R = 16), never below 1 HP. **A wild predator keeps its plain bite on players** (it bites once per 2.5 s, at most twice per chase; players must not die faster).

`python tools/combat_fight_time.py --runner <luau.exe>` prints the table. Ground vs Ground, same combat scale 1.26, only R changes. Bites (seconds):
| R | Bigger hits a wild predator | Bigger hits a player | Smaller hits a wild predator | Smaller hits a player |
| --- | --- | --- | --- | --- |
| 1 | 9 (4.8) | 22 (12.6) | 9 (4.8) | 22 (12.6) |
| 1.5 | 9 (4.8) | 14 (7.8) | 10 (5.4) | 25 (14.4) |
| 2 | 8 (4.2) | 9 (4.8) | 12 (6.6) | 29 (16.8) |
| 3 | 7 (3.6) | 7 (3.6) | 16 (9.0) | 39 (22.8) |
| 5 | 6 (3.0) | 6 (3.0) | 24 (13.8) | 60 (35.4) |
| **8** | **4 (1.8)** | **4 (1.8)** | 39 (22.8) | 97 (57.6) |
| 12 | 3 (1.2) | 3 (1.2) | 55 (32.4) | 136 (81.0) |
| **16 (max)** | **1 (one-shot)** | **1 (one-shot)** | 55 (32.4) | 136 (81.0) |
| 20 | 1 | 1 | 55 | 136 |

The owner example (100 vs 800 growth, R 5.3) is 6 bites, about 3 s. 2 bites come at about R 13.5, not at half the maximum (8): the owner's own example (about 5 bites at R 5 to 8) and "2 bites at half the max" cannot both hold on one smooth curve. A fresh dino against a capped one needs 55 bites (wild, floor of 1 HP per bite) or 136 bites (player): hopeless, never zero.

**Wild predator target rule** (`CombatConfig.WildMaxSizeRatio` = 4, `NpcPredatorRules.sizeOk`, used for picking a target, for the chase and for the bite): a wild predator ignores a player more than 4 times smaller (no reward, hard to see) or 4 times bigger (hopeless). The first suggestion was 6, but wild dinos only reach R 6 against a fresh player (z 6 vs 1), so 6 would never trigger; 4 protects fresh players from the bigger half of the wild dinos. Players can still choose to fight anyone. The server passes each player's growth score to the wild AI (`NpcPredatorService.playerSnapshot`); a player entry with no score is not filtered.

## Test
`tools/verify_combat_stats.py` also tests the curve: falling with R (never longer when R grows, 200 steps, both HP cases), R 1 against a wild predator 6 to 10 bites, R 8 4 to 6 bites, R 16 and above exactly 1 bite, equal size = the plain hit, a wild attacker keeps the plain hit, a smaller dino's bite never reaches 0 and a fresh dino needs 60+ bites on a capped one. `tools/verify_npc_predators.py` tests `sizeOk` and the target pick. `tools/verify_combat_service.py` now uses a size-unit-7 dino instead of a capped one for the "six small beat one big" check (against a capped dino six fresh ones cannot win any more, by design). `tools/verify_combat_stats.py` first fails if an even fight against a wild predator (wild score 60 to 250) takes more than 8 s for any class, or if the Ground fight is not 6 to 10 bites. `tools/verify_npc_predators.py` checks that wild HP = normal HP x `WildHpX` and that players keep full HP. `tools/verify_combat_teamup.py`: the six-small-beat-one-big window moved from 20 to 35 s to 13 to 25 s (now 15.6 s, 5 survivors; the faster cooldown scales every team fight by 2/3).

## LEAD decision (owner delegated 2026-10-16)
- Decision: an even fight takes about 8 s or less and 6 to 10 bites for the Ground dino; faster bites and clearly lower wild HP first, player HP and the damage a player takes stay as they are.
- Options not picked: lower HP for everyone (kids would die faster, the wild bites would take a bigger share of the bar); raise bite damage (the same, and it makes the player take more per wild bite); a bigger cooldown cut to 0.45 s (the 2 per second rate limit and a quick tap rhythm for young players start to matter).
- Known side effect: a wild predator now falls in about a fifth of the time, so the growth reward (BD-313: 5% of own growth, same slot once per 120 s, at most 3 per 300 s) can be earned a bit faster. The limits are on count, not on fight length, so the farm cap holds.
- Not fixed here: Water and Armored players still need 11 to 14 bites by class design; player against player Water and Armored fights are still 15 to 19 s (their HP is not lowered on purpose).
- Part 2 decision: z = 1 + growth/50 is the size number (the drawn scale squared; max R 16); one-shot at R 16; threshold for wild AI 4 (not 6, see above); a wild predator keeps its plain bite on players. Options not picked: R from the old combat scale (only 1.7 at the cap, so no big differences possible); R from raw growth (a fresh dino has growth 0, so the ratio is infinite); a hard "cannot hit" rule for tiny dinos (the owner wants a hit to stay possible, never 0). To overturn: `OneShotRatio`, `BigCurveBites`, `BigHitCurvePower`, `SmallHitFloorX`, `WildMaxSizeRatio` in `CombatConfig`.
- To overturn part 1: set `BiteCooldownSeconds` back to 0.9 and `WildHpX` to 1.0 in `src/shared/CombatConfig.luau` (and the windows in `verify_combat_teamup.py`).
