# Build 005: PvP, spawn safety and run ending

## Implemented prototype behavior
- Every spawn starts a new temporary run with `GrowthScore = 0`, `CatchScore = 0` and a server-generated run ID.
- Spawn protection lasts 5 seconds. Protected players can neither eat nor be eaten.
- Predation is server-authoritative and runs in one bounded 0.1-second loop.
- An attacker must have strictly more growth and at least 110% of the victim's growth score.
- Bite range starts at 5.5 studs and grows modestly with visual scale, capped at 9 studs. Arena geometry blocks bites through rocks/walls.
- Sampled displacement rejection excludes implausible movement from predation checks. This is not complete anti-cheat.
- A successful eat ends the victim once, adds 1 temporary catch to the attacker and gives the attacker 25 temporary growth points.
- The HUD shows growth, catches, size, spawn-protection countdown and an `END RUN` button.
- `END RUN` has no client payload. The server rate-limits it, channels for 3 seconds and cancels if the player moves more than 2 studs.
- Predation, manual exit and natural death all use the same one-way terminal guard. The first terminal event wins.
- No progression is saved yet. Build 005 is still a disposable gameplay test.

The 10% margin, 5-second protection, 25-point PvP growth and 3-second exit channel are reversible test defaults, not final balance.

## Tester checklist
Use the new `build/BeDino-Prototype.rbxlx`. First press F5 for the single-player checks, then F7 with 2 clients for multiplayer.

| # | Test | Expected |
|---|---|---|
| 1 | Spawn | HUD shows `SAFE` counting down from about 5 seconds; movement/food still work |
| 2 | Manual exit while standing still | Click `END RUN`; button counts down about 3 seconds; character dies/respawns; new run starts at 0 growth/0 catches |
| 3 | Cancel manual exit | Click `END RUN`, then walk more than about 2 studs before it finishes | Countdown cancels; character remains alive |
| 4 | Equal-size contact | After protection ends, put both 0-growth players together | Neither player can eat the other |
| 5 | Bigger eats smaller | Player A eats at least one berry; Player B stays at 0; after protection, walk A into B | B is eaten once and respawns; A gets +1 catch and +25 growth |
| 6 | Protection blocks PvP | Immediately after B respawns, A stays on top of B | B survives until protection expires |
| 7 | Remote result replication | Watch both clients during an eat | Victim death/respawn and attacker's catch/growth update are visible correctly |
| 8 | Exit-vs-predation race | Smaller player starts `END RUN`; bigger player eats them before 3 seconds | `Eaten` wins; no second death or duplicate catch occurs |
| 9 | Reset character | Use Roblox Reset Character | One normal respawn; new run returns to 0 growth/0 catches and systems still work |

Optional stronger concurrency check: run 3 clients, make two attackers eligible for the same victim and approach together. Exactly one attacker should receive the catch/growth award.

## Report back
For each failed row, send the test number, what happened, and any red Output error. If all 1-9 pass, BD-009 can move from `Review / test` to `Done` for desktop multiplayer; touch/device acceptance remains tracked separately.
