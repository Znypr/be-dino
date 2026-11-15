# Player simulation: PLAY AGAIN what-if (BD-1199, docs/239), 2026-11-15

Tool: `python tools/simulate_players.py --players 300` (seed 1200, 30 days, the game's real egg numbers, PROVISIONAL personas; a design tool, not a retention forecast, docs/235).

Files: `base.txt` (identical to the 2026-11-14 base), `with-play-again.txt` (`--play-again`), `with-play-again-first-only.txt` (`--play-again --streak-first-only`).

What the what-if assumes (PROVISIONAL, written in the tool): the button adds **one run to every session** (`runs_per_session` +1); a **run streak 3 or 5** in a session is a small "new" moment (the soft toast and its crystals). Two readings of "new":
- **every session** (`--play-again`): each session that reaches streak 3 / 5 counts as new. This is an upper bound and an artifact: every persona has 3+ runs now, so every session has "something new" and nobody quits (D30 100 percent). **Do not read it as a result.**
- **first time only** (`--streak-first-only`): only the first time a kid ever reaches streak 3 and 5 counts. The cautious reading, used below.

| persona | still D7 base | D7 what-if | still D30 base | D30 what-if | species D7/D30 base | species D7/D30 what-if |
| --- | --- | --- | --- | --- | --- | --- |
| Noah | 91% | 85% | 2% | 1% | 7/9 | 8/10 |
| Mia | 92% | 89% | 1% | 1% | 10/11 | 10/11 |
| Ava | 94% | 92% | 1% | 1% | 11/12 | 11/13 |
| Sam | 91% | 89% | 1% | 1% | 10/11 | 11/12 |
| Leo | 56% | 57% | 0% | 0% | 14/14.5 | 15/15 |

Reading (300 players a persona, so differences of about 3 points are noise; the what-if changes how many random numbers a session uses, which also moves the draws):
1. **The button does not move the week-2 cliff by itself.** D7 and D30 stay about where they were; a streak moment is not new content, and the quit rule is "nothing new for N sessions".
2. **It does speed up collecting**: about one more species by day 30 for Noah, Ava, Sam, Leo, and the first Epic / Legendary come earlier (Leo first Epic day 3 instead of 4, Noah first Legendary day 5.5 instead of 13, small samples).
3. So the value of BD-1199 in this model is **more runs per visit (the 6-minute rule of docs/235)**, not retention. Retention still needs new things to find after week 1 (the rest of the BD-1197 / BD-1198 backlog). Real players decide; the playtest watch sheet (docs/222) should record runs per visit with the flag on.
