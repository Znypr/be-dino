# Playtest report

Overall: **YELLOW**. 5 visits, 4 runs, 2 servers.
1 of 5 visits have no leave line (the server closed first or the log was copied too early): their run and time numbers are missing.

| Light | Check | Number | In plain words |
| --- | --- | --- | --- |
| YELLOW | Runs per visit | 1 | A visit has 1 runs on average (we want 2 or more). Players leave after too few runs. |
| YELLOW | Left before a first run | 1 of 4 | 1 of 4 visits ended without one finished run. Check the start: it may be confusing or too slow. |
| YELLOW | Set back by the anti-cheat | 6 (1.2 per visit) | 6 set-backs in 5 visits. Players hit this often. |
| YELLOW | Told "too fast" | 9 (1.8 per visit) | 9 "too fast" answers in 5 visits. Players hit this often. Most: Chest 6, Gift 3. |
| YELLOW | Errors and crashes | 2 errors, 0 crashes | 2 script errors and 0 crashes were reported. Open the error list and fix them. Crashes are not counted by the game: look at the Creator Hub list. |
| GREEN | Eggs in a 5-minute run | 15 (goal 15) | Players earn about 15 eggs in 5 minutes. The goal is about 15. |
| GREEN | Eggs for 500 food | 11.95 (setting 12) | 500 food gave 11.95 eggs; the game setting gives 12 before weather bonuses. |
| GREEN | Run length | 5.0 min | The middle run lasts 5.0 minutes (we want about 5). |
| GREEN | Quit in the middle of a run | 0 of 4 | 0 of 4 runs ended because the player left the game. |
| GREEN | Time in the cave | 37% | Players spend 37% of the time in the cave and the rest in runs. |
| GREEN | Shop use | 2 (0.4 per visit) | 2 things bought. Most: buyPotion 2. |
| GREEN | Hatching | 11 (2.2 per visit) | 11 times. Most: Egg 11. |
| GREEN | Fusion | 1 | 1 made in the test. |
| GREEN | Time to first food | 50 s | The middle player needs 50 seconds to eat the first food (3 visits). |
| GREEN | Time to first run | 30 s | The middle player needs 30 seconds to start the first run (3 visits). |
| GREEN | Players: fun | 2.67 of 3 | Players say it is fun. |
| GREEN | Players: looks | 2.67 of 3 | Players like how it looks. |
| GREEN | Players: difficulty | 2 of 3 | The difficulty feels just right. |

## Where players drop off

    Came into the game              4   100%  ########################
    Started a run                   3    75%  ##################......
    Ate food                        3    75%  ##################......
    Finished 1 run                  3    75%  ##################......
    Earned an egg                   3    75%  ##################......
    Hatched an egg                  1    25%  ######..................
    Finished 2 runs                 1    25%  ######..................
    Finished 3 runs                 0     0%  ........................

Biggest loss: 100% of players are gone between "Finished 2 runs" and "Finished 3 runs".

## How fast players got there (median, from joining)

    Started a run            30 s   (3 visits)
    Ate food                 50 s   (3 visits)
    Earned an egg           345 s   (3 visits)
    Hatched an egg          355 s   (1 visit)
    Bought in a shop        500 s   (1 visit)

## Problems in plain words

- YELLOW: Runs per visit. A visit has 1 runs on average (we want 2 or more). Players leave after too few runs.
- YELLOW: Left before a first run. 1 of 4 visits ended without one finished run. Check the start: it may be confusing or too slow.
- YELLOW: Set back by the anti-cheat. 6 set-backs in 5 visits. Players hit this often.
- YELLOW: Told "too fast". 9 "too fast" answers in 5 visits. Players hit this often. Most: Chest 6, Gift 3.
- YELLOW: Errors and crashes. 2 script errors and 0 crashes were reported. Open the error list and fix them. Crashes are not counted by the game: look at the Creator Hub list.

## What players wrote

3 feedback entries.
- [Run, compy] The eggs are fun

## Script errors seen (scrubbed text, one line per kind)

- ChestService: ServerScriptService.ChestService:88: attempt to index nil with <p>
- Other: attempt to compare nil with number

## The game does not record these yet

- Crashes (players kicked or the app closed): read the Creator Hub list (BD-651). Fill in by hand: a `count` line or a CSV row.
- Shop opened (no server event exists; purchases are counted instead) (BD-652). Fill in by hand: a `count` line or a CSV row.

---
Target: about 15 eggs in a 5-minute run. Egg setting: FoodCatchRate 12/500 (docs/119, current; 40/500, 15/150 and 4/500 are historical). Limits are provisional (docs/167 section 9).
