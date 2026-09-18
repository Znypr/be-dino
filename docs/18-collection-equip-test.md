# Build 008: collection and equip test

Build 008 validates BD-012 using the current private test experience and DataStore.

## What changed

- Collection panel for Compy, Triceratops and T-Rex.
- Saved owned/locked copy counts.
- Server-validated persistent equip.
- Distinct placeholder dinosaur visuals.
- Locked species equip requests are rejected.
- A private-test-only one-time +1 Triceratops grant lets us test a successful non-Compy equip without farming 25 catches.

## Test objectives

1. Start F5. Profile says Loaded, your saved Compy count is preserved, and Compy shows EQUIPPED.
2. Click locked T-Rex. Equip result must say locked and nothing changes.
3. Click TEST UNLOCK TRICERATOPS. Triceratops becomes exactly 1 copy. Other counts do not change.
4. Click Triceratops. Equip result says equipped and the dinosaur changes to the blue horned placeholder.
5. Reset Character. Triceratops is still equipped after respawn.
6. Stop Play completely and start F5 again. Triceratops is still 1 copy and still equipped.
7. Equip Compy, stop Play, then start again. Compy remains equipped and the Triceratops copy remains saved.
8. Click T-Rex again. It is still rejected as locked.

If all eight pass, BD-012 is Done.
