# Build 013: original visual kit test

Build 013 validates BD-007 and BD-016 using the all-procedural fallback kit.

## Test objectives

1. Start F5. Normal saved dinosaur/profile loads and gameplay still works. SECURITY TEST is gone; ART PREVIEW is visible.
2. Open ART PREVIEW and select COMPY. Confirm a slim green silhouette, long tail, crest/spikes and large readable eyes.
3. Select TRICERATOPS. Confirm a clearly different four-legged blue silhouette with a large frill and three horns.
4. Select T-REX. Confirm a clearly different rust silhouette with oversized head/jaw, tiny arms and heavy rear legs.
5. On any preview, press GOLD CURRENT. The whole dinosaur should use the metallic amber Gold treatment without excessive glow. Press RESTORE SAVED and verify your real equipped dinosaur returns.
6. Walk around the arena, through bushes/trees/decorative rocks and the starter nest. Decorative pieces must not trap or block movement. The original obstacle rocks, slope and outer boundary should still collide.
7. Collect enough food to grow substantially and rotate/zoom the camera around the dinosaur. Visual pieces must remain attached, readable and not alter the fixed movement collider.
8. Start a 2-player Studio test. Preview different species on each client. Each client should see the other player's current preview correctly; movement/PvP state remains independent and no saved collection/equip counts change after restart.

If all eight pass, BD-007 and BD-016 are Done. The ART PREVIEW test panel is removed before the private release build.
