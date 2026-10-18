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

**Small against big (new player, size 1, against the biggest wild predator):**
| Player class | Wild HP | Bites | Seconds |
| --- | --- | --- | --- |
| Ground | 150 -> 60 | 26 -> 11 | 22.5 -> 6.0 |
| Water | 150 -> 60 | 32 -> 13 | 27.9 -> 7.2 |
| Fly | 150 -> 60 | 19 -> 8 | 16.2 -> 4.2 |
| Armored | 150 -> 60 | 35 -> 14 | 30.6 -> 7.8 |

**Player against player (even, size 1; HP not changed, only the cooldown):** Ground 14.4 -> 9.6 s, Fly 8.1 -> 5.4 s, Water 23.4 -> 15.6 s, Armored 27.9 -> 18.6 s. Bites stay 17 / 10 / 27 / 32.

Studio check from round 2 (docs/145): "about 24 bites" for a wild predator. The model says 22 before, so the numbers agree. It should now be about 9 to 11 bites and about 5 to 6 seconds.

## Test
`tools/verify_combat_stats.py` now fails if an even fight against a wild predator (wild score 60 to 250) takes more than 8 s for any class, or if the Ground fight is not 6 to 10 bites. `tools/verify_npc_predators.py` checks that wild HP = normal HP x `WildHpX` and that players keep full HP. `tools/verify_combat_teamup.py`: the six-small-beat-one-big window moved from 20 to 35 s to 13 to 25 s (now 15.6 s, 5 survivors; the faster cooldown scales every team fight by 2/3).

## LEAD decision (owner delegated 2026-10-16)
- Decision: an even fight takes about 8 s or less and 6 to 10 bites for the Ground dino; faster bites and clearly lower wild HP first, player HP and the damage a player takes stay as they are.
- Options not picked: lower HP for everyone (kids would die faster, the wild bites would take a bigger share of the bar); raise bite damage (the same, and it makes the player take more per wild bite); a bigger cooldown cut to 0.45 s (the 2 per second rate limit and a quick tap rhythm for young players start to matter).
- Known side effect: a wild predator now falls in about a fifth of the time, so the growth reward (BD-313: 5% of own growth, same slot once per 120 s, at most 3 per 300 s) can be earned a bit faster. The limits are on count, not on fight length, so the farm cap holds.
- Not fixed here: Water and Armored players still need 11 to 14 bites by class design; player against player Water and Armored fights are still 15 to 19 s (their HP is not lowered on purpose).
- To overturn: set `BiteCooldownSeconds` back to 0.9 and `WildHpX` to 1.0 in `src/shared/CombatConfig.luau` (and the windows in `verify_combat_teamup.py`).
