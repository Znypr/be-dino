# Water dash delivery, before and after (BD-572, 2026-10-17)

**CURRENT BUILD BEHAVIOR measurement**, desktop Studio, one window of my own, Play, memory-only profile, one player. Two playtest builds (`python tools/build.py --profile playtest`, ClassMovement on) of branch `claude/water-dash-hold` merged with main; they differ only in `src/client/ClassDash.client.luau`: BEFORE = main's single velocity write, AFTER = the per-frame hold.

Set-up honesty: the player's `EquippedSpeciesId` was forced to `mosasaurus` from a server script (re-applied every 0.1 s, because the profile put `compy` back after a few seconds), so the class logic is Water (WalkSpeed 18.7, JumpPower 0, server answers the dash). The visible model is still the Compy. The dash was requested by firing the `ClassDash` remote the way the client script's `JumpRequest` handler does (the Studio keyboard tool does not reach the game). Position is the root's horizontal displacement, sampled every Heartbeat from the moment the request is sent. Nominal dash: 48 studs/s x 0.35 s = 16.8 studs.

## Displacement (studs, horizontal)

| Build | Ground | Result at 0.35 s / final (1.5 s) |
|---|---|---|
| BEFORE (main) | flat, (0, 30) facing -Z, trial 1 | 1.1 / **1.1** |
| BEFORE (main) | same spot, trial 2 | 1.1 / **1.1** |
| AFTER | flat, (0, 30) facing -Z, trial 1 | 11.5 / **15.2** |
| AFTER | flat, (0, 30) -Z, second run | 11.3 / **14.2** |
| AFTER | flat, (0, 15) +X | 10.9 / **13.9** |
| AFTER | flat, (0, 15) -X | 11.1 / **14.2** |
| AFTER | gentle slope 12 deg uphill | 11.3 / **14.3** (rose 2.8) |
| AFTER | slope 18 deg uphill | 11.3 / **14.2** (rose 4.4) |
| AFTER | slope 25 deg uphill | 11.1 / **14.6** (rose 6.9) |
| AFTER | slope 12 deg, but a conifer trunk collider 1.5 studs ahead of the dino's start | answered, stopped at **3.8** (the wall stop; later checks with the same Blockcast show a vertical Part ahead, Normal.Y 0) |

So the suspected bug is real: on main the dash moves the dino about 1 stud (peak planar speed 32 studs/s in one frame, then the Humanoid ground controller takes it). With the hold it travels about 14 to 15 studs, 85 to 90% of the nominal 16.8 (the rest: the hold starts when the answer arrives, and each Heartbeat write is partly damped by the physics step before it moves the dino). No speed number was changed.

## Wall cast: no false stops

Flat ground (3 headings) and slopes of 12, 18 and 25 degrees all gave the same 14 to 15 studs, so the per-frame Blockcast does not stop the dash on ground (surfaces flatter than `MaxSlopeAngle` are ignored) and does stop it at a real obstacle. MovementGuard: `MovementSecurityStatus` stayed `OK` in every dash.

## Image

`01-after-dash-top-view.jpg`: top view after a dash on flat ground. The green bar is the start, short ticks every stud, long ticks every 5 studs; the dino ended at about 14 studs. (Compy model, Water class logic, see above.)

## Not covered

Phone input (Space and the jump button), a second client, latency above localhost, real Mosasaurus visual and its surge animation (BD-556), the 3 s cooldown timing in Studio.
