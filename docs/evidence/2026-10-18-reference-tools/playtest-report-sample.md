# Playtest report: Build 021 playtest (2026-10-19)

Overall: **YELLOW**. 6 visits, 10 runs, 6 testers.

| Light | Check | Number | In plain words |
| --- | --- | --- | --- |
| YELLOW | Runs per visit | 1.67 | A visit has 1.67 runs on average (we want 2 or more). Players leave after too few runs. |
| YELLOW | Left before a first run | 2 of 6 | 2 of 6 visits ended without one finished run. Check the start: it may be confusing or too slow. |
| YELLOW | Set back by the anti-cheat | 9 (1.5 per visit) | 9 set-backs in 6 visits. Players hit this often. |
| YELLOW | Errors and crashes | 1 errors, 0 crashes | 1 script errors and 0 crashes were reported. Open the error list and fix them. |
| GREEN | Eggs in a 5-minute run | 14.55 (goal 15) | Players earn about 14.55 eggs in 5 minutes. The goal is about 15. |
| GREEN | Eggs for 500 food | 11.83 (setting 12) | 500 food gave 11.83 eggs; the game setting gives 12 before weather bonuses. |
| GREEN | Run length | 4.9 min | The middle run lasts 4.9 minutes (we want about 5). |
| GREEN | Quit in the middle of a run | 1 of 10 | 1 of 10 runs ended because the player left the game. |
| GREEN | Time in the cave | 37% | Players spend 37% of the time in the cave and the rest in runs. |
| GREEN | Told "too fast" | 2 (0.3 per visit) | 2 "too fast" answers in 6 visits. |
| GREEN | Shop use | 7 (1.2 per visit) | 7 times. |
| GREEN | Hatching | 31 (5.2 per visit) | 31 times. |
| GREEN | Players: fun | 2.75 of 3 | Players say it is fun. |
| GREEN | Players: looks | 2.75 of 3 | Players like how it looks. |
| GREEN | Players: difficulty | 2.25 of 3 | The difficulty feels just right. |

## Where players drop off

    Came into the game              6   100%  ########################
    Finished 1 run                  4    67%  ################........
    Finished 2 runs                 3    50%  ############............
    Finished 3 runs                 2    33%  ########................

Biggest loss: 33% of players are gone between "Came into the game" and "Finished 1 run".

## Problems in plain words

- YELLOW: Runs per visit. A visit has 1.67 runs on average (we want 2 or more). Players leave after too few runs.
- YELLOW: Left before a first run. 2 of 6 visits ended without one finished run. Check the start: it may be confusing or too slow.
- YELLOW: Set back by the anti-cheat. 9 set-backs in 6 visits. Players hit this often.
- YELLOW: Errors and crashes. 1 script errors and 0 crashes were reported. Open the error list and fix them.

## What players wrote

4 feedback entries.
- [Run, compy] I like the eggs!
- [Hub, compy] The shop door is hard to find
- [Run, compy] The big dino ate me too fast

## The game does not record these yet

- Shop things bought (BD-652). Fill in by hand: a `count` line or a CSV row.
- Steps before the first run (first food, first egg, first hatch) (BD-653). Fill in by hand: a `count` line or a CSV row.

---
Target: about 15 eggs in a 5-minute run. Egg setting: FoodCatchRate 12/500 (docs/119, current; 40/500, 15/150 and 4/500 are historical). Limits are provisional (docs/167 section 9).
1 lines looked like data but could not be read.
1 lines had an event this report does not know; they were skipped.
