# Build 006: persistent run settlement

Build 006 adds the first real DataStore-backed profile and immediate run reward settlement.

## Important setup before testing

Roblox Studio cannot use DataStoreService for an unpublished local file by default. Use a separate private test experience, not a live production experience.

1. Open the newest `build/BeDino-Prototype.rbxlx`.
2. Publish it as a separate private test experience.
3. In Studio open **File > Experience Settings > Security**.
4. Enable **Studio Access to API Services** and save.
5. Keep this test experience/data separate from any future production experience.

The build uses the isolated store name `BeDino_PrivateTest_v1`.

## Implemented behavior

- Character auto-loading is disabled until the server acquires a profile lease.
- New profiles start with 1 base Compy, 0 Triceratops and 0 T-Rex.
- Profile writes use `UpdateAsync`, a server lease, revisions and bounded retries.
- Lease target is 90 seconds with renewal every 30 seconds.
- A load failure, schema error or lost lease fails closed instead of creating writable defaults.
- Every run settlement uses `run:<runId>` as its immutable operation ID.
- Immediate dinosaur rewards are computed server-side from catch score and committed with the profile.
- Earned chests are recorded as `pendingChestGrants`; the actual queue/claim mechanic remains BD-013.
- The most recent 50 operation IDs/outcomes are retained for duplicate protection.
- Build 006 deliberately retries the same settlement once after every successful run. HUD `Idempotency: duplicate-ok` proves the second request returned the stored result without granting again.
- Same attacker/victim pair can add catch score only once per 60 seconds. Predation still works during the cooldown.
- Respawn occurs only after settlement succeeds.
- Disconnect tries to settle an active run before releasing its lease.

## Tester checklist

Use F5 first, then F7 with 2 clients where specified.

| # | Test | Expected |
|---|---|---|
| 1 | Start with API access enabled | Character spawns; HUD shows `Profile: Loaded`; Compy starts at 1 on a new test profile |
| 2 | End a 0-catch run | Respawn after settlement; copies do not increase; HUD shows `Idempotency: duplicate-ok` |
| 3 | Two clients: A eats B once, then A ends run | A has 1 catch before ending; after settlement A gains exactly 1 Compy copy, not 2 |
| 4 | Check duplicate probe after test 3 | HUD still shows only one added copy and `Idempotency: duplicate-ok` |
| 5 | Stop Play, start again with the same account | Previously earned Compy count loads again |
| 6 | Reset Character with a loaded profile | Run settles once, respawns, profile remains Loaded |
| 7 | Repeat victim within 60 seconds | The second predation works, but attacker catch score does not increase again |
| 8 | Wait over 60 seconds, eat same victim again | Catch score can increase again |
| 9 | Disable Studio API access, then start | No playable character should spawn; profile should fail closed with a DataStore error instead of silently using a new blank profile |
| 10 | Re-enable API access and restart | Existing saved profile loads again; no reset to starter defaults |

For test 9, re-enable API access immediately afterward. Do not use this failure test in a production experience.

## Evidence needed for full BD-011 acceptance

Passing tests 1–10 establishes load/save/rejoin and duplicate-settlement behavior. A separate competing-session/stale-lease test is still required before BD-011 can be marked fully Done.
