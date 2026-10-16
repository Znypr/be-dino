# 111 Multiplayer audit and offline 12-player simulation (2026-10-16, BD-360 to BD-364; prepares BD-019, BD-097, BD-316, BD-319)

Label: **CODE-LEVEL AUDIT plus OFFLINE SIMULATION, NOT a multiplayer test.** No Roblox server, Studio multi-client session or phone was used. The simulation runs the real Luau modules against mocks (virtual clock, mocked DataStore with latency, transient failures and the per-server request budget). It proves ordering, transaction and invariant behaviour. It cannot prove replication, networking, physics, real DataStore latency, BindToClose timing or memory. Section 5 is the owner's step list for the real test. Sources read: AGENTS.md, docs/00, 87, 106, 107, `src/server/*`, `tools/verify_load.py`.

## 1. Result in one paragraph
The repository layer (ProfileRepository, RunLifecycle) is sound for the main flow: every settlement and egg claim is an atomic, lease-checked, idempotent UpdateAsync keyed by run or egg id, so a run settles at most once even when death, Home, being eaten and a disconnect race. The bugs were at the edges: leaving, rejoining, failing and shutting down. Ten are fixed here (seven of them session bugs), the ones in the repository layer with a test that fails on the old code (BD-360). Four real design risks are left as kanban rows (BD-361 to BD-363).

## 2. Findings, ranked (file:line are on this branch after the fixes)

Severity: H = loses rewards, strands a player, or lets one player hurt the others. M = cost or exposure that grows with players. L = small.

### Fixed in this PR (BD-360), all with offline tests
| # | Sev | Finding | Where | Evidence |
| --- | --- | --- | --- | --- |
| F1 | H | **Same-user rejoin lost its lease.** All players of one server share one `leaseId`. A player who left and came back at once (new Player object, same UserId) loaded while the old release was still in flight; the old release then ran `session = nil` on the NEW session, so the next write or renew said `LeaseLost` and the run's rewards were refused. | `ProfileRepository.release` (1817) and `load` (750); fix: `releasing[userId]`, load waits for it | Old code: 3 of 12 rejoined players lost the lease, 9/12 held it |
| F2 | H | **Leaving mid-load kept the lease and cached the profile.** `load` assigned `profiles[player]` after its yield without checking the player. The lease stayed for `ProfileLeaseSeconds` (90 s, so a quick rejoin saw SessionBusy) and the Player plus its profile stayed in memory for the life of the server. | `ProfileRepository.load` (750) | Old code: 12 of 12 leased and cached |
| F3 | H (leak) | **A transaction that finished after the player left put the profile back.** `if not profiles[player] or ... then profiles[player] = updated` ran at 13 sites after a yield, so an in-flight claim, equip or purchase re-created the entry that `release` had just cleared. `isLoaded(oldPlayer)` was true forever; the Player and up to a few MB of profile leaked per such leave. New helper `adopt` only updates a live entry. | `ProfileRepository` `adopt` (about 105) | Old code: 5 of 12 resurrected in the rejoin test; static check keeps exactly 1 unguarded site (load) |
| F4 | H | **`SaveFailed` was a dead end.** Any one failed write (an equip, a potion, a throttle drop) set `ProfileState = "SaveFailed"`. Nothing ever set it back: runs, claims, equips refused, `renew` refused, and the run settlement of a leaving player was refused (`profile_not_loaded`), forfeiting the whole run. Now `renew` accepts `SaveFailed`, and a success proves the store is consistent (every write is one atomic, lease-checked UpdateAsync) and restores `Loaded`. `commitRunSettlement` is attempted in that state too. | `ProfileRepository.renew` (1785), `commitRunSettlement` (about 855) | Old code: renew refused, settlement left 0 eggs |
| F5 | H | **A failed settlement of a departed player never released the lease** (the Bootstrap callback returned before the release), so a rejoin saw SessionBusy for up to 90 s and the profile leaked. | `Bootstrap.server.luau` settlement callback | LeaveCoordinator test |
| F6 | H | **BindToClose walked players one after another and ignored players whose leave was already running ("busy").** 12 players x (settlement + release + 3 leaderboard writes), each up to 3 attempts with back-off, can pass the 30 s limit, and the PlayerRemoving threads were never awaited. New `LeaveCoordinator` registers every leave before it yields, runs them in parallel, and `BindToClose` waits (25 s cap) for all of them. | `src/server/LeaveCoordinator.luau`, `Bootstrap.server.luau` (PlayerRemoving, BindToClose) | Sim: 12 players with a 20% failing store take 3.0 s in parallel vs 8.4 s one by one. It also caught a bug in the first version of the coordinator (the wait returned at once because the leave was not registered yet) |
| F7 | H | **SessionBusy and LoadFailed had no retry.** `spawnLoadedPlayer` only warned, so a player teleporting between servers or rejoining within 90 s of a crash had no character and no message. Now it retries every 5 s for `ProfileLeaseSeconds + 10`. | `Bootstrap.server.luau` `spawnLoadedPlayer` | Sim join storm uses the same loop |
| F8 | M | **`ProgressionAction` busy flag could stick.** `repository.progressionAction` was not protected; a thrown error left `busy = true` and every later request answered "busy". | `ProgressionService.luau` remote handler | static check |
| F9 | M | **Bite spam cost.** `CombatBite` built the O(players) candidate list (a `GetExtentsSize` per model) before the cooldown check, so one client could make the server do that scan per request. Now the cooldown is read first (no state change). | `CombatService.luau` bite handler (160 to 170) | static check; flag is off |
| F10 | M | **FoodService hot loop.** The pickup test ran `GetAttribute("VisualScale")`, a radius calculation and a `Vector3.new` per food per player, 12.5 times a second. Per-player values are now computed once per tick and the test is a squared-distance compare. Same result, same tie-break. | `FoodService.luau` (216 to 232) | not measured in Studio |

### Open (kanban rows)
| # | Sev | Finding | Where | Row |
| --- | --- | --- | --- | --- |
| H8 | H | **No shared per-player write budget.** Each remote has its own cooldown (`ChestService` claim 0.35 s, nest 0.5 s, settings 0.5 s, `CollectionService` equip 0.5 s, `MutationService` 0.4 s, `ProgressionService` 0.4 s, `FusionService` window) but all of them end in an UpdateAsync on the same key. A client firing every remote at its limit can issue about 10 writes/s. A server gets 60 + 10 x players requests per minute (about 3/s at 12 players) and a 30-request queue; beyond that `UpdateAsync` errors and the victim's settlement fails. The per-key rule (writes to one key within 6 s are throttled) is also not enforced anywhere. | `ChestService.luau` 26 to 110, `CollectionService.luau` 22 to 83, `MutationService.luau`, `ProgressionService.luau` 170 to 178 | BD-361 | **2026-10-16 (offline) FIXED in code, BD-358:** `ProfileRepository.admit` is one token bucket per player (`Config.WriteBurst` 6, refill `WriteRefillPerSecond` 1/s) plus a global gate (routine writes only while the last 60 s hold fewer than 60% of 60 + 10 x players requests, `WriteBudgetReserve` 0.4 keeps the rest for priority writes). Settlement, lease renew/release, load and purchases never use it. Over budget a routine write answers `rate_limited` (already handled by every client); settings and reveal-skip are coalesced (latest value wins, written when a token is free or merged into the lease release). Only paths that really write are charged (buffered egg reveals and cached duplicates are free). A stale preference write can no longer overwrite a newer one. Not proven on a real server.
| M1 | M | **Settlement has 3 attempts.** `retry` waits 0.5 s then 1 s. A longer hiccup or a throttle wait forfeits the run's eggs; nothing keeps the snapshot. | `ProfileRepository.retry` (320), `RunLifecycle.respawnAfterSettlement` (101 to 112) | BD-362 | **2026-10-16 (offline) FIXED in code, BD-359:** `retrySettlement`: up to 6 attempts, back-off 0.6/1.2/2.4/4.8/9.6 s with 10% jitter, never past 26 s (about 19 s nominal). If the window is exhausted the run stays `SaveFailed` with an in-memory pending record (run id, catches, egg tags, run seconds, weather) and the lease renew tick commits it (2 attempts per tick, exactly once by run id), then respawns the player. `Bootstrap` BindToClose now waits 27 s. Still lost: a settlement whose window runs out while the player is leaving (the pending record dies with the session; the lease expires after 90 s); a store that is down longer than about 26 s at server shutdown.
| M2 | M | **Private data replicates to everyone.** `syncAttributes` sets about 35 Player attributes (`CollectionJson`, `ProgressionJson`, `ChestQueueJson`, `NestsJson`, `SettingsJson`, `EquippedGenesJson`). Attributes go to every client. Sim: 2.5 KB fresh, 9.8 KB after 10 runs of 40 eggs (`CollectionJson` 6.9 KB, `ChestQueueJson` 1.2 KB); a full resync of 12 such players is about 1.3 MB across clients, and every change to a big string resends it to all 11 others. Any player can read any other player's inventory. | `ProfileRepository.syncAttributes` (336 to 395) | BD-363 |
| H8 | H | **No shared per-player write budget.** Each remote has its own cooldown (`ChestService` claim 0.35 s, nest 0.5 s, settings 0.5 s, `CollectionService` equip 0.5 s, `MutationService` 0.4 s, `ProgressionService` 0.4 s, `FusionService` window) but all of them end in an UpdateAsync on the same key. A client firing every remote at its limit can issue about 10 writes/s. A server gets 60 + 10 x players requests per minute (about 3/s at 12 players) and a 30-request queue; beyond that `UpdateAsync` errors and the victim's settlement fails. The per-key rule (writes to one key within 6 s are throttled) is also not enforced anywhere. | `ChestService.luau` 26 to 110, `CollectionService.luau` 22 to 83, `MutationService.luau`, `ProgressionService.luau` 170 to 178 | BD-361 |
| M1 | M | **Settlement has 3 attempts.** `retry` waits 0.5 s then 1 s. A longer hiccup or a throttle wait forfeits the run's eggs; nothing keeps the snapshot. | `ProfileRepository.retry` (320), `RunLifecycle.respawnAfterSettlement` (101 to 112) | BD-362 |
| M2 | M | **Private data replicates to everyone.** `syncAttributes` sets about 35 Player attributes (`CollectionJson`, `ProgressionJson`, `ChestQueueJson`, `NestsJson`, `SettingsJson`, `EquippedGenesJson`). Attributes go to every client. Sim: 2.5 KB fresh, 9.8 KB after 10 runs of 40 eggs (`CollectionJson` 6.9 KB, `ChestQueueJson` 1.2 KB); a full resync of 12 such players is about 1.3 MB across clients, and every change to a big string resends it to all 11 others. Any player can read any other player's inventory. | `ProfileRepository.syncAttributes` (336 to 395) | BD-363; **fixed for the big values by BD-360, see docs/112** |
| M3 | M | **Loops that grow with players x things** (table below). | see below | BD-364 |
| M4 | M | **Leaderboards.** `publish` is 3 sequential OrderedDataStore UpdateAsync per leave and per player per 60 s; `refresh` does 3 `GetSortedAsync` and a `GetNameFromUserIdAsync` per unseen name. At 12 players that is 36 writes per minute plus the leave writes, on a budget that is not modelled here. | `Leaderboards.luau` 18 to 36 and 105 to 115 | BD-362 |
| L1 | L | `runStartedAt[runId]` is only cleared by a settlement snapshot, so a run that never settles (character swapped while Active) leaves one entry | `RunLifecycle.luau` 14, 49 | BD-363 |
| L2 | L | `world.defeats` (friend shield) is keyed by userId and never pruned | `CombatRules.luau` 45 to 62 | BD-363 |
| L3 | L | Every per-player cooldown table is keyed by the Player object and cleaned on PlayerRemoving (checked in all 14 services), so a rejoin resets the cooldowns; `ProfileRepository` bounds the damage | all services | BD-363 (2026-10-16: Chest, Collection, Mutation and Leap cooldowns now keyed by UserId via `CooldownMemory`; other services and cross-server hops still open) |
| L4 | L | `LeaseLost` (renew failed, another server took over) is silent: the player keeps running and the settlement is refused | `ProfileRepository.renew` | BD-363 (2026-10-16: `handleLeaseLost` logs, sets `LeaseLost`, kicks after 6 s; sim-tested) |

### Server loops that scale with players (the O(n squared) list you asked for)
| Loop | Rate | Cost with 12 players | Note |
| --- | --- | --- | --- |
| `FoodService` pickup, `FoodService.luau` 216 to 232 | every 0.08 s | foods x players = 2,400 x 12 = 28,800 checks per tick, 360k/s (F10 made each check cheap) | the only loop that is clearly hot; spatial grid per sector is the fix (BD-364) |
| `ProgressionService` crystals, 128 to 150 | every 0.25 s | crystals x players, plus `Players:GetPlayers()` allocated per crystal and `FindFirstChild` x2 per pair | hoist the eligible list (BD-364) |
| `PredationService`, 92 to 99 | every 0.1 s | players squared = 132 pair checks, a raycast only for in-range pairs | runs only while `CombatEnabled` is false; cheap |
| `CombatService` bite, 160 to 190 | per bite request | players + NPCs, a `GetExtentsSize` each | gated by F9; flag off |
| `CombatService` Heartbeat, 205 to 215 | 10 Hz | O(players), HP byte attribute only on change at 5 Hz | trivial |
| `NpcPredatorService.playerSnapshot` (167) and bite loop | 10 Hz | O(players) with `GetExtentsSize`; NPCs (at most 5) x players in `Rules.step`; an inner loop over players per bite event | flag off |
| `RunLifecycle.predatorNearby` | per Home click, 0.75 s cooldown | O(players) | fine |
| `MovementGuard`, `FallRecovery`, `ProgressionService` weather loop | 10 Hz, 5 Hz, 1 Hz | O(players), JSON decode per player per second in `colourGrowth` | fine |
| `HubGateService` | per player per tick, `GetDescendants` once a second per character | flag off | check when the cave hub is on |

### Things checked and found fine
- **Exactly-once settlement.** `tryEnd` flips `Active` to `Ending` before any yield; `endForDisconnect` and `tryEnd` share the same flip; `commitRunSettlement` is idempotent by `run:<runId>` and `recordSettledRun`. Death plus leave, Eaten plus leave, double end and Home plus death all settled once in the sim (13 runs, 4 orderings).
- **Egg claims.** Three concurrent claims of one egg gave one `claimed` and two `duplicate`; a claim in flight at leave neither duplicates an egg nor keeps the lease.
- **Per-player state.** Eggs, crystals, XP and operations of each user matched only that user's runs in every ordering; the nest queue is a pure per-list function.
- **Lease design.** `leaseId` per server, 90 s lease, renew every 30 s, `ownSession` checked inside every transaction: a server that loses the lease cannot overwrite the new owner (writes are refused, F4 aside).
- **Join storm.** 12 loads at the same tick finished by 2.4 virtual seconds with no throttle; 12 staggered joins with a 5% failing store all loaded.
- **PlayerAdded/Removing ordering.** Bootstrap connects `PlayerAdded` and walks `GetPlayers()` (the usual idiom); `PlayerRemoving` is connected before the food and combat services start, and `spawnLoadedPlayer` returns if the player left while waiting for the world.

## 3. What was NOT possible offline
Replication cost and attribute sizes on the wire, `BindToClose` real timing (the sim uses a virtual clock), real DataStore latency and the real OrderedDataStore budget, instance and connection leaks (the mocks have no instances), Humanoid and physics behaviour, `Players.PlayerRemoving` firing order against `BindToClose` on a real server, weather sync, and any frame-time or phone number (docs/107 is an estimate).

## 4. The offline test
`python tools/verify_multiplayer_sim.py --runner <luau>` (CI runs it after `verify_load.py`). `tools/multiplayer_sim.luau` is appended to the verify_load.py scheduler, DataStore mock and module loader, so it runs the real ProfileRepository, RunLifecycle, LeaveCoordinator, RewardMath, CombatRules and NestQueue unmodified.

| Scenario | What it asserts |
| --- | --- |
| join-storm (12 at the same tick; 12 one second apart with a 5% failing store) | all 12 Loaded, ready within 60 virtual s, no throttle drop, 12 distinct leased keys |
| settlement-races x3 orders | 12 users, 7 modes (manual end, death, leave while Active, eaten then leave, death and leave in the same tick, double end then leave, end, rejoin, run again): each run settled at most once; eggs in profile equal eggs of committed runs; no duplicate egg id; every operation belongs to its own user; leases released; no loaded profile for a departed player |
| determinism-under-reordering | the per-user result (eggs, crystals, XP) is identical in three different join and leave orders |
| settlement-races-flaky-25pct | the same under a 25% failing store: at most once, no duplicates, no crash |
| rejoin-race | 12 users with an equip in flight leave and return one tick later: new session holds and renews the lease, old Player is not cached |
| leave-during-load | no lease kept, nothing cached |
| save-failed-recovery | `SaveFailed` after a failed write, renew recovers, settlement still committed |
| egg-claims | three concurrent claims give one `claimed`; a mid-claim leave leaves no cached profile and no lease |
| shutdown-parallel-12 | BindToClose path with 12 active runs and a 20% failing store finishes in 3.0 s (old behaviour 8.4 s); 11 of 12 runs settled (the 12th shows F-M1) |
| budget-spammer-12 (+ flaky 30%, + budget-off contrast) | BD-358: one client fires settings, reveal-skip and nest-claim remotes at 10 Hz each for 60 s while 11 others end runs: all 11 settlements committed, no throttle-queue drop, the spammer's own key takes at most burst + 1 write/s (about 90 writes; 257 without the budget), its latest settings are saved (or it was told), any 60 s window stays under 60 + 10 x 12 = 180 requests (peak about 100) |
| hiccup-15s-present-12, hiccup-60s-present-12, hiccup-15s-leaving-12 | BD-359: 12 runs end while the store fails completely for 15 s: all 12 committed inside the retry window (no recovery needed); for 60 s: windows fail, SaveFailed pendings are committed by the renew tick, nothing doubled, players back; 12 players leaving over a 15 s outage settle and release inside 27 s; peak request rate stays under the budget |
| flaky-store-20pct-12, flaky-store-40pct-12 | BD-359: every run credited exactly once, no duplicate egg id or operation, nothing lost, also when half the players leave under the failures |
| attribute-volume (report only plus a 64 KB cap) | prints the replicated bytes quoted in M2 |
| attribute-volume | BD-360: prints public (replicated to all) and private (owner-only) bytes; fails above 2 KB public per player and when a private name is set as a Player attribute (public 453 B vs 8,279 B before) |
| combat-12-players | 900 fuzzed bites: defeat and settle fire once per (userId, run), HP stays in range, same defeated set for two join orders, a defeated dino cannot bite, a rejoin gets a fresh run key |
| nest-queue-12-users | no shared state; many small advances equal one direct advance |

Proof that the test bites: with the old `ProfileRepository.luau` it fails 12 checks (F1 to F4, plus the static check). Run it again when the repository changes.

Seeded (`math.randomseed`) for the retry jitter; Luau table order still varies run to run, so the sim was run 8 times in a row to check stability. Limits of the new scenarios: the mock DataStore queue and 60 + 10 x players rate are the model of the real budget, nothing here measures real DataStore latency, the OrderedDataStore budget or BindToClose timing.

## 5. Manual Studio multi-client test (owner, about 45 minutes)
Do this in your own copy, never on `Place1.rbxl`. Use the playtest profile (`python tools/build.py --profile playtest`) so there are no Robux products. Flags: leave `CombatEnabled`, `CaveHub`, `LowPolyDinos` off for 5.1 and 5.2, turn `CombatEnabled` on only for 5.3.

### 5.1 Setup
1. Open the place. Test tab > Clients and Servers > set Players to 4 > **Start** (Local Server). You get one server window and four client windows.
2. Open **View > Output** in the server window (the Server tab of the Output) and keep it visible. Search for `[Be Dino]`, `SaveFailed`, `LeaseLost`, `settlement failed`, `warn`.
3. In each client open the Developer Console (F9) > Log for client errors.
4. In the server window open **Explorer > Players**, click a player, and read its Attributes in Properties.

### 5.2 Core flow (no combat)
| Step | Do | Expect |
| --- | --- | --- |
| 1 | Wait for all 4 clients to show the hub | Each Player has `ProfileState = Loaded`. Output shows no `SessionBusy` or `LoadFailed`. Time from start to controllable: note it |
| 2 | In every client press Play and walk 60 s, eating food | Each client's EGGS counter grows by its own catches only. In Explorer each Player's `LastRunId` differs |
| 3 | Client 1 presses Home (confirm). Client 2 stands still until eaten or dies. Client 3 closes its window mid-run (stop that client). Client 4 keeps running | Client 1 and 2: run summary shows. In Output exactly one settlement per run: `LastSettledRunId` is now owner-only (BD-360): read it on that client with `require(PlayerScripts.Client.PrivateState).get("LastSettledRunId")` and compare it with the `LastRunId` attribute. Client 3's `LastSettledRunId` is not visible after it left, but Output must show no `settlement failed` |
| 4 | Client 3 re-joins at once (the Clients tab in the Test toolbar adds a player) | It loads (`ProfileState = Loaded`), its eggs from the run it left are in the queue (EGGS page). No `LeaseLost` or `SessionBusy` |
| 5 | Clients 1, 2 and 4 open the Eggs page and reveal at the same time | One egg at a time, no stalls; no `save_failed`; `LastChestClaimStatus` is `claimed` then `duplicate` only if you double-clicked |
| 6 | All clients open Settings, Shop and the Odds page while one is hatching | No client sees another's inventory in its UI. In Explorer note the size of `CollectionJson` on a Player (a long string): record its length |
| 7 | In the Test tab stop the server (Stop) with 2 runs active | Output shows all four players settled and released, in under 30 s, with `leaving` finishing; look for `shutdown: some players were not released in time` (must NOT appear) |

### 5.3 Two-player combat checks (BD-316), `CombatEnabled = true`
Run in the same Local Server with 2 clients (and a 3rd for assists). Read `LastBiteStatus` and `HpByte` in Explorer. Note: a synthetic key press did not trigger a bite in the single-player MCP test; here use a real keyboard or mouse in each client window.
1. **Bite works.** Client A faces client B and bites (default F). Expect `LastBiteStatus = ok`, B's `HpByte` drops, A's `BiteSeq` and B's `HitSeq` change, B's HP bar updates on B's screen and on A's.
2. **Cooldown and rate limit.** A bites 5 times in one second. Expect `cooldown` or `rate` for the extra ones and no extra damage.
3. **Defeat settles once.** A defeats B. B's run ends once (`LastRunEndReason = Defeated`, one `LastSettledRunId`), B keeps its eggs; A gets no eggs from B.
4. **Friend shield.** B respawns and starts again; B is protected for the shield time; A's bites during it return `no_target`.
5. **Team-up assist.** A, C bite B together; both get the small growth bonus once, capped.
6. **Peaceful mode.** Turn Peaceful on in B's Settings: A cannot bite B (`no_target`), and B cannot bite.
7. **Leave mid-fight.** B closes its window while being bitten: one settlement, no error in Output, A's `HpByte`/target logic keeps working.
8. **Bandwidth.** In A's F9 > Network, note Data Receive KB/s while 4 players fight: write it down (the docs/107 estimate is 2 KB/s).

### 5.4 What to paste back
Copy these into BD-364 / BD-319: the Output lines containing `[Be Dino]` and any `Warning` from the server for the whole run; the time to controllable for each client (step 1); `CollectionJson` length (step 6); the F9 Network KB/s (5.3 step 8); one line per step: pass or fail. For performance (BD-097): in the server window Stats (Shift+F3) Heartbeat and "Instances" with 4 players, and the MicroProfiler (Ctrl+F6) top 3 server scopes with 4 clients.

### 5.5 Then the published private place
Repeat 5.2 steps 1 to 6 with friends or alts (2, then 4, then 8 players), as in docs/55 section 5 and docs/106 section 4. Watch for `SessionBusy` when someone leaves and rejoins fast, and for any `save_failed` on a player who did not do anything unusual (that would be H8).

## 6. Honest status
Offline only. Nothing here was run on a real server, so BD-019, BD-097, BD-316 and BD-319 stay open; they now have a script (section 5) and BD-364 to record the result.

**BD-363 remainder (bite, predation repeat-victim, MovementGuard reject clock):** now keyed by UserId through `CooldownMemory` (memory only, never the profile), so a rejoin on the same server no longer resets them. `PredationService.previous` and `MovementGuard.states` stay per Player on purpose: they are character-bound position baselines, not cooldowns.
