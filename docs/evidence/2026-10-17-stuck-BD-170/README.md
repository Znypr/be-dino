# BD-170 hatch flow (2026-10-17, Studio, single player)

Seen in the BD-148 run ([../2026-10-17-stuck-BD-148/README.md](../2026-10-17-stuck-BD-148/README.md)), real clicks:
1. OPEN starts the egg opening at once: "An egg is hatching..." with the egg and the two colour tags (10-open-hatch-batch-counter-skip.jpg); no dino cycles through patterns first.
2. The egg is the real egg render, not a cube (same images).
3. Next egg stays inside the sequence ("Egg 1 of 58", "Egg 2 of 58", ...) until the batch ends (12-egg-2-of-58-stays-in-sequence.jpg).

Defect seen once (new row BD-519): at the first OPEN of one session the egg was drawn at the top-left corner over the title (01-egg-drawn-top-left-at-first-open.jpg). It did not repeat in later hatches.
