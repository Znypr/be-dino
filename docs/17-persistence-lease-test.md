# Build 007: persistence lease verification

Build 007 is a focused runtime verification build for the final BD-011 persistence requirement.

## What it tests

At server startup, the build creates a temporary DataStore probe key that is completely separate from all player profile keys.

The probe uses two synthetic server lease identities and verifies:

1. lease A can acquire an empty record;
2. live lease A blocks lease B;
3. after lease A is expired, lease B can take over;
4. stale lease A can no longer write;
5. current lease B can still write;
6. the final stored probe value is correct;
7. the temporary probe key is removed afterward.

The HUD reports `Lease test: RUNNING`, then either `Lease test: PASS` or `Lease test: FAIL: <reason>`.

This probe never uses `u:<UserId>` profile keys and must not change dinosaur counts, chests, equipped species or any other player progression.

## Setup

Use the same separate private test experience from Build 006.

1. Open the Build 007 `.rbxlx`.
2. Use **File > Publish to Roblox As...** and update/overwrite the existing Be Dino private test place.
3. Confirm **File > Experience Settings > Security > Enable Studio Access to API Services** is still enabled.
4. Start with F5. One player is enough.

The DataStore remains `BeDino_PrivateTest_v1`, so your Build 006 test profile should load unchanged.

## Test objectives

| # | Test | Expected |
|---:|---|---|
| 1 | Start F5 with API access enabled | Character spawns and HUD shows `Profile: Loaded` |
| 2 | Watch `Lease test` on the HUD | It may briefly show `RUNNING`, then changes to `PASS` |
| 3 | Compare your Compy count with the end of Build 006 | Count is unchanged by the lease probe |
| 4 | Stop and start F5 once more | Existing profile still loads and the lease test reaches `PASS` again |

If all four pass, the runtime evidence covers the remaining stale-session/lease-owner protection required for BD-011.

If the HUD shows `FAIL`, report the exact text after `FAIL:` and do not continue progression testing on that server.
