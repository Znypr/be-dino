# 86. Hatch sequence (presentation only)

Owner feedback 2026-10-14: the egg hatch was choppy, too fast and low quality. The server-committed outcome (species, genes, odds, saved data) is unchanged; only the client presentation changed.

- `src/shared/HatchTimeline.luau`: pure timing, curves, tap gating, skip rules, rarity escalation, Sfx cue list. Tested by `tools/verify_hatch_sequence.py` (wired into the workflow).
- `src/client/HatchSequence.luau`: draws it. Pooled frames only; one Heartbeat connection per egg.
- `Bootstrap.client.luau`: builds the labels and calls `HatchSequence.play`; tap on the last egg calls `finishBatch`.

Flow per egg (PROVISIONAL timings): about 3.0 s rattle/crack/glow build-up (rotation and position jitter easing in, push-in zoom, three crack stages), 0.6 s burst (flash, shell fragments, rarity-scaled sparkles, Rare+ shockwave, Epic+ energy arcs and stronger shake, Legendary fireworks and camera punch), dinosaur reveal with overshoot and a rarity-coloured light burst, name, rarity pill with base odds ("Rare - 12% of eggs"), Shiny/BIG/mutation ribbons (Shiny rainbow shimmer and gold rain, BIG stamp), then the player taps (or presses Space/Enter/A) for the next egg: "Tap for next egg (N left)", "Done" on the last. A tap during the build-up jumps to the burst once. "Skip all" sends every later non-notable egg down the quick path; chosen skip rarities still work; Shiny, BIG, mutations, Rainbow and Astra are never skipped.

Reduce Motion: no shake, zoom or particles; short fade, same tap flow.

Sfx hooks (silent until ids are bound): `hatch_rattle`, `hatch_crack_stage`, `hatch_burst`, `hatch_reveal_common|uncommon|rare|epic|legendary`.

Not verified: Android/phone hardware (only logic and Studio desktop).

BD-170/171/174 update: Open starts the egg at once (plain Blender egg image, wobbling; the server answer is supplied later via `handle.supply`). Build-up is about 3.6 s: left bucket splashes (whole egg takes the colour, chip with name and tier), right bucket splashes (pattern revealed on the real 3D egg, chip with name and tier), then rattle and crack. Tiers use PROVISIONAL percent cut-offs (HatchTimeline.TierFloors). Next egg stays in the sequence until the batch ends. The egg condition is drawn on egg visuals only, never on dinosaur models or the reveal. Logic tests: tools/verify_hatch_sequence.py.
