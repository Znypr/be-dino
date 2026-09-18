# Build 012: security and multiplayer regression test

Build 012 begins BD-018. It keeps the accepted player-facing UI and adds a temporary security harness.

## Hardening change

The old movement plausibility check only ignored the first impossible sample. A teleported location could become trusted on the next tick. Build 012 adds a server movement guard that keeps the last trusted transform, snaps impossible displacement back, clears velocity and records a rejection.

## Security harness

The SECURITY TEST panel has two checks:

- RUN REMOTE ATTACKS sends malformed types, unknown IDs, overlong strings, extra arguments, disabled debug-grant calls and a 60-request equip flood through the real remotes. PASS requires inventory, Gold counts, equipped species, chest queue, profile revision and active run state to remain unchanged.
- RUN TELEPORT CHECK locally jumps the character to a distant food position. PASS requires the server movement guard to reject the jump and restore the prior trusted position.

These controls are test-only and must be removed before release.

## Test objectives

Use the existing private test experience or another private copy with Studio API access.

1. Single client: dismiss tutorial, open SECURITY TEST, run RUN REMOTE ATTACKS. It must report Remote: PASS. Inventory, equipped dinosaur and chest queue must look unchanged.
2. Run RUN TELEPORT CHECK. It must report Movement: PASS and your dinosaur must snap back instead of staying at the distant food location.
3. After both security checks, normal food pickup, DINOS, CHESTS and END RUN must still work.
4. Start a Studio server with 2 players. Both clients must load profiles and move normally.
5. On client A, run RUN REMOTE ATTACKS. A reports PASS and client B's run/inventory remains unchanged.
6. With equal fresh Growth Scores, A and B cannot eat each other after spawn protection ends.
7. Let A collect one food, then eat B. A gains exactly one Catch Score and +25 Growth from predation; B gets one run ending/summary and one respawn.
8. After B's spawn protection ends, have B start END RUN while A tries to eat B during the 3-second channel. Only one terminal outcome may win: B gets one summary and one respawn, with no duplicate reward/settlement. Stop the test and start again once to confirm committed inventory still loads.

If all eight pass, the main BD-018 gameplay/security regression is accepted. BD-019 still requires real-device/load and published-asset validation.
