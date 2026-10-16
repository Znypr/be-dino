# 114 Hatch redesign: paint-bucket egg reveal v2 (BD-397, 2026-10-16)

**Status: Phase 1 (this design) and Phase 2 (code behind `Config.HatchV2 = false`) delivered on branch `claude/hatch-redesign`; Review / test.** The shipped v1 sequence ([docs/86](86-hatch-sequence.md)) is unchanged while the flag is off. Owner brief: BD-397 in [the Kanban](07-kanban.md). Feel rules: [docs/87](87-vision-and-feel-guide.md). Art rules: [AGENTS.md](../AGENTS.md), [docs/72](72-ui-copy-and-asset-standards.md), prompt style [docs/109](109-owner-art-prompt-pack.md). Image budget: [docs/105](105-lowpoly-patterns-and-tiers.md) s3 (80 MiB per client, bytes not count). Studio evidence: [evidence/2026-10-16-hatch-v2/](evidence/2026-10-16-hatch-v2/README.md).

## 1. What the owner saw and what changes

Today (v1, Build 020 + BD-171): a flat Blender egg picture with crack strips, a UI-shape grey bucket, a stroke ring and a few dots as the "splash", the colour applied as an `ImageColor3` tint. It reads as code-drawn.

v2 (this document): a real **3D egg mesh in a ViewportFrame**, two **3D buckets** that fly in, tip and pour a **thick liquid arc**, a **splash crown** and **drip streaks**, and the paint **landing on the egg's own texture**: the base colour floods the egg from the impact points with drips running down; the accent colour then lands **only on the gene pattern** (spots, stripes, scales), so the player watches the pattern being painted; wet gloss dries to the matte final look; then the condition overlay (cracks, dirt, stars) fades in, the egg rattles, cracks and bursts, and the v1 reveal (dino, name, odds, chips, ribbons) follows unchanged. No ellipses, no primitives, no code-drawn final art: the egg and bucket are generated meshes, the splash sprites are the existing white-on-alpha fx3 sheets tinted at runtime, the paint coats are baked texture pixels.

## 2. Beat sheet (full motion, seconds from Open; `HatchV2Plan.luau`)

| Beat | From | To | What happens | Sound (existing cues only) |
|---|---|---|---|---|
| Settle | 0.00 | 0.40 | Plain cream 3D egg on the stage, slow sway (`Plan.sway`), condition chip already shown (BD-223). While the server answer is pending the clock holds here and the egg keeps swaying (BD-170). | - |
| Bucket 1 arrives | 0.40 | 0.85 | Left bucket flies in from off-screen left with a soft back-out overshoot (`Plan.bucketPose`), hovers 265 px left of the egg over its chip. | `pickup_lo` (swoosh) at 0.40 |
| Bucket 1 tips | 0.90 | 1.20 | Tilts 72 deg toward the egg about its lip; the liquid arc grows from the lip (`Plan.stream`, `Plan.streamBlobs`: quadratic arc that sags with gravity, 12 blobs on desktop). | - |
| **Impact 1** | 1.20 | | Chip 1 pops (colour name + rarity badge, e.g. "Blue - COMMON"). Splash crown (`Plan.crown`: 14 droplets up and out, gravity, never below 140 px), a soft puddle bloom at the impact, egg squash 1.11 / 0.89 settling in ~0.5 s (`Plan.squash`), wet gloss rises to 0.28 (`Plan.gloss`). | `pickup` |
| Coat 1 floods | 1.20 | 2.20 | Base colour spreads over the egg texture from 3 splat points on the left flank (`Plan.splats`, `Plan.revealTime`: growing circles in model space, 2 drip streaks per splat that run ahead of the flood), thin bright wet edge on the front, 100 % coverage at 2.20. 2D drip streaks hang under the splash from 1.50 to 2.60 (`Plan.dripStreak`). | - |
| Bucket 1 leaves | 1.55 | 2.10 | Tips back, slides out left, fades. Gloss dries over 1.6 s. | - |
| Bucket 2 arrives / tips | 2.50 | 3.30 | Right bucket, same choreography mirrored, accent colour (or a clear pale varnish for a Plain egg). | `pickup_lo` at 2.50 |
| **Impact 2** | 3.30 | | Chip 2 pops (accent colour + rarity, e.g. "Black - MYTHIC"). Crown, puddle, squash, gloss as above. | `pickup_hi` |
| Coat 2 paints the pattern | 3.30 | 4.30 | Accent colour spreads from 3 right-flank splats but lands **only where the pattern mask is** (`HatchPaintBake.composite`: alpha2 = reveal x mask), so spots/stripes/scales appear and fill in, drips included. | - |
| Pattern chip | 4.30 | 4.70 | "Round Spots" / "No pattern" chip under the egg (v1 chip, same copy). | - |
| Condition | 5.10 | 5.50 | The condition overlay decal (Cracked fractures, Dirty smudges, Rainbow stars, Astra streaks; the same Blender layers as the Eggs screen) fades in on the egg; its material reflectance follows. | - |
| Rattle and cracks | 5.50 | 6.70 | v1 rattle curves on the 3D egg (rotation, offset, push-in zoom), glow rings, rattle cues. | `hatch_rattle` x7, `hatch_crack_stage` x3 |
| Burst | 6.70 | | 3D egg leaves, v1 flash, shell fragments, sparkles; then the v1 dino reveal, chips, ribbons, tap / buttons. | `hatch_burst`, reveal sting |

Total build-up 6.7 s (v1 3.6 s), then burst 0.6 s + settle 0.8 s (Legendary +0.5 s) as before: about 8.1 s per egg before the tap. One tap after the first 0.5 s fast-forwards to the burst (unchanged rule); "Skip all" unchanged. The timings are PROVISIONAL (`Plan.Build`, `Plan.Bucket`, `Plan.Left/Right`, `Plan.Coat`, `Plan.Drips`, `Plan.Condition`) and verified to keep their order and at least 1.2 s of rattle before the burst.

**Reduce Motion:** no buckets, arc, crown, drips, squash or gloss; the 3D egg is shown finished (both coats, pattern, condition) the moment the answer arrives and the v1 Reduced flow (short fade, same tap flow) runs. Chips are not animated (parity with v1 Reduced).

**Failed (Cracked) egg:** the same paint beats, then the v1 splat (shell halves, yolk, puddle) with its funny copy.

## 3. Camera and layers

- Panel space is the 824 x 402 virtual px body of the hatch modal (as HatchFxPlan). The **ViewportFrame covers the whole body** (ZIndex 23, between the v1 back FX layer rings/bloom and the front FX layer), so 3D points project straight to panel px (`Plan.project`, pure) and the 2D sprites line up with the 3D lip and impact points.
- Camera: FOV 30, 7.8 studs from the egg along (0.32, 0.22, 1), offset so the egg centre projects to HatchFxPlan.Center.egg (412, 130) (`Plan.eggCameraSpace`, verified). 96 px per stud: the 2.4-stud egg is about 230 px tall, the buckets hover 2.75 studs = 265 px from the egg, right above their chips (HatchTimeline.BucketX).
- Light: warm key from the camera side, high ambient (no black half), SmoothPlastic matte egg; reflectance only while the paint is wet and for Rainbow / Astra conditions.
- Layers front to back: chips / tap hint / ribbons (v1, Z 27+) > crown droplets (26) > liquid arc, puddle, drip streaks (25) > v1 front sparkles (24) > **viewport: buckets, egg** (23) > v1 bloom / rings / motes (22-23) > backdrop.
- The hidden v1 2D egg stays in the tree: at the burst it returns for its shell fragments (tinted with the gene colours), so the burst, splat and reveal code is untouched.

## 4. Asset list and ready prompts (owner / lead work)

Rule: every id goes into [docs/77](77-asset-registry.md); never invent ids. The style block of [docs/109](109-owner-art-prompt-pack.md) s0 is prepended to every ChatGPT prompt.

### A. Egg mesh: REUSE `80664439797104` (decision)
The generated egg `world_gen_food_egg` (docs/77) was evaluated in Studio: a plump low-poly egg with its own baked texture and a usable UV layout for an EditableImage bake; `CreateEditableMeshAsync` opens it in the owner's Studio, so the 3D position map (pattern that flows across facets) works. Decision: **reuse it**; no new egg prompt is needed for the playtest. Optional later prompt if the owner wants a cuter silhouette: generate_mesh "a plump cute low-poly dinosaur egg, slightly pointed top, smooth rounded facets, plain cream matte shell with no pattern or decoration, single mesh, clean UV layout with large islands" (height 2.4 studs; replace the id in `HatchV2Assets.egg`).

### B. Paint bucket mesh (needed; PLACEHOLDER barrel today)
- generate_mesh prompt (Roblox Studio, owner account): "a chunky cute cartoon paint bucket, slightly wider at the top, thick rolled rim, a round wire handle standing straight up, simple matte painted-metal look with one wooden band, open top, the inside filled with a flat smooth paint surface in pure white, soft rounded low-poly shapes, no text, no logo".
- Parts the animation wants (if generated as one mesh the whole bucket tilts, which is acceptable): body, handle, paint surface. The paint surface is tinted at runtime by vertex colour / `Color` where possible; with one textured mesh the surface stays white (still reads).
- Size: about 1.35 studs tall (`Plan.BucketHeight`). Replace `HatchV2Assets.bucket.assetId`, clear `Placeholder.bucket`, flip the docs/77 row `hatch_v2_bucket_placeholder`.

### C. Paint FX sheets (ChatGPT, white on alpha, docs/109 FX block, 4 x 4 cells of 256 px = 1024 px, 15 % cell margin, under 400 KB)
1. `fx-v3/paint-splash-crown.png`: "a 4 x 4 grid sheet (16 equal cells) of a thick liquid paint splash animation seen from the front: a fat drop hits and spreads into a round crown with rounded blobby tips, the crown opens, droplets fly off, then it settles into a flat puddle; thick glossy liquid, anime cel style, pure white shapes on a transparent background." Key `paintCrown`, OneShot.
2. `fx-v3/paint-drips.png`: "a 4 x 4 grid sheet of a paint drip animation: three rounded drips starting as a bulge at the top and running down with round swelling ends, growing longer frame by frame, thick glossy liquid, white on transparent." Key `paintDrips`, OneShot.
3. `fx-v3/paint-droplets.png`: "a 4 x 4 grid sheet of single round paint droplets of different sizes with a small bright highlight, white on transparent." Key `paintDroplet`, Random.
4. `fx-v3/paint-sheet-gloss.png` (single 1024 x 1024 decal): "a soft glossy wet-paint sheen: a wide diagonal bright highlight band with feathered edges and two small round specular dots, white on transparent." Used as a Decal over the egg while the gloss is wet (replaces plain reflectance).
Binding: `EffectAssets.Requested.<key>.id` (TABLE), then `HatchEggV2` picks them over the smoke sheet (keys are already read through `Fx.resolveUi`; add the keys with `fallback = "smoke"`).

### D. Crack lines decal (needed for the crack stages on the 3D egg)
- ChatGPT, 1024 x 1024 white on alpha: "three stages of thin jagged egg-shell crack lines, growing from a small star crack at the top into a long branching crack down the side, white lines with soft edges on transparent, no shading". Exported as three images (stage 1, 2, 3). Decal on the egg front face, faded in at the v1 crack beats. Until then the 3D egg rattles and glows but shows no crack lines (the Cracked condition art does show its fractures).

### E. Sounds (existing cues reused; no new sound)
`pickup_lo` swoosh at each arrival, `pickup` / `pickup_hi` at the two impacts, `hatch_rattle`, `hatch_crack_stage`, `hatch_burst`, the reveal stings. A wet "splat" and a "drip" cue would fit (brief: soft, round, about -12 dBFS, 150-300 ms); not made, not required.

## 5. Technical design: paint on the egg

**Why texture pixels.** A per-pixel reveal (flood from impact points, drips, pattern-only accent) is impossible with uniform `Color` / `Transparency`; ViewportFrames do not draw ParticleEmitters, Beams or Highlights. So the egg's texture is **one `EditableImage`** per hatch panel (desktop / tablet 256 px = 256 KiB, phone 128 px = 64 KiB, `Plan.Budget`), rewritten a few times per second while a coat runs from a pure composite.

**Source, once per session** (`HatchEggV2.readSource`, same approach as `LowPolyTexture`): the egg's colour map (SurfaceAppearance ColorMap or TextureID) read with `CreateEditableImageAsync` and downsampled (4 MiB transient, destroyed at once) into a shading array (`Bake.shade`: luminance over the mean, clamped 0.55..1.25, so the facets stay visible under the paint); the mesh read with `CreateEditableMeshAsync` (transient) and rasterised into a **position map** (`LowPolyPattern.rasterize`: every texel knows its model-space position, longest side = 1).

**Per egg** (`HatchEggV2.setGenes`, async, started the moment the answer arrives; the clock already holds 0.8 s before the first impact):
1. **Pattern mask** = `LowPolyPattern.compute(patternId, seed, weights = 1, blend / 100, sameFamily, posmap, size)`: the same 3D masks as the low-poly dinos (spots are spheres, stripes planes, scales a staggered lattice) so the pattern flows across facets; UV-space masks when the position map is unavailable; nil for `01_blank`.
2. **Reveal maps** = `Bake.revealMap(size, posmap, seed, side, coat)`: for each texel, the second (after that coat's impact) its paint arrives: the first of 3 growing splats (`Plan.splats`, jittered by the egg id seed) or a drip streak (2 per splat, running down at 2.6 x the flood speed, tapering), clamped so the whole egg is wet by `Plan.Coat.span - soft` (verified: coverage monotonic to 100 %).
3. **Composite** (`Bake.composite`, pure, deterministic bytes): per texel `cream -> base by alpha1 -> accent by alpha2 x mask`, times the shading, plus a thin bright **wet edge** on each advancing front (`Plan.wetEdge`). Written with `WritePixelsBuffer` at most `Plan.Budget.writes` times per second (15 desktop, 8 phone), rows yielded so no frame stalls; the last write (fast-forward, Reduce Motion) uses t = 99 = finished.
4. Gloss while wet: `MeshPart.Reflectance` (0.28 peak, dries in 1.6 s); the condition overlay (`ConditionOverlays.apply`, the Eggs-screen Blender layers as a Decal on the egg's -Z face, which the scene yaws toward the camera) fades in at the condition beat.

**Cache key** `Bake.key(seed, size, patternId, blend, primary, secondary, hasPos)` identifies a bake; the current build keeps one image and rewrites it (a per-key image cache like `PatternAtlasCache` is not needed: one egg is on screen at a time).

**Budget (docs/105 s3):** one 256 KiB image per hatch panel + transient reads (4 MiB image, egg mesh about 1 KiB per face) once per session, under 5 MiB in flight; the low-poly caches stay under half the 80 MiB budget, so this fits. Per-frame CPU: a composite is 65k texels on desktop (about 3-6 ms, spread over yields), 16k on phones. Sprites: 12 arc blobs + 2 x 14 crown + 2 x 6 drips + 2 puddles = 54 pooled ImageLabels / Frames on desktop, 34 on phones (`Plan.sprites`), created once per panel.

**Fallback chain (never blank, never a cube; `tools/verify_hatch_v2.py` checks the wiring, Studio checks the looks):**
1. `Config.HatchV2 = false` (shipped): v1 sequence, nothing loads.
2. Flag on but `ReplicatedStorage.HatchV2Models.egg` missing (server `loadHatchV2` failed: ownership, offline): `HatchEggV2.create` returns nil, **v1 sequence runs for that egg**.
3. Bucket mesh missing: no bucket; the arc still flows from the hover point, the splash plays.
4. Texture unreadable: flat shading bake (paint still floods and drips). Mesh unreadable: UV-space pattern (jigsaw at facet edges, like docs/105 evidence 08).
5. No `EditableImage` (budget, "Allow Mesh & Image APIs" off on a published place): the egg is **tinted** by `MeshPart.Color` with the same timing (cream -> base -> half accent), buckets / arc / crown / drips unchanged.
6. The bake is not ready at an impact (slow read): the egg stays cream until it is; the composite then jumps to the current coat time (no stall); fast-forward writes the finished look when the bake completes.

**Published-server needs** (same as docs/105 s7): the experience must be published under the owner account that generated the egg and bucket, with "Allow Mesh & Image APIs" on; otherwise chain step 5 shows the tint fallback and the log says why.

## 6. Code map

| File | Role | Tests |
|---|---|---|
| `src/shared/HatchV2Plan.luau` | PURE beat sheet, bucket / stream / crown / drip / squash / gloss curves, splats, reveal time field, projection, device budget | `tools/verify_hatch_v2.py` |
| `src/shared/HatchPaintBake.luau` | PURE shading, reveal maps, composite, coverage, cache key | `tools/verify_hatch_v2.py` |
| `src/shared/HatchV2Assets.luau` | Mesh ids (egg reused, bucket PLACEHOLDER barrel) | `tools/verify_hatch_v2.py` (ids in docs/77) |
| `src/shared/HatchTimeline.luau` | `T.useV2(state, true)`: the v2 build-up and paint plan in the same state machine (pending hold, tap gate, skip, Reduced, failed egg unchanged) | `tools/verify_hatch_sequence.py` (v1 unchanged), `verify_hatch_v2.py` |
| `src/server/ImportedResources.luau` `loadHatchV2`, `Bootstrap.server.luau` | Loads the two meshes into `ReplicatedStorage.HatchV2Models` only while the flag is on | wiring |
| `src/client/HatchEggV2.luau` | ViewportFrame scene, source reads, bake writer, buckets, arc, crown, drips, gloss, condition, fallbacks | Studio only |
| `src/client/HatchSequence.luau` | Creates the v2 egg behind the flag, hands it genes / condition / rattle, keeps chips, burst, reveal | wiring |
| `src/client/Bootstrap.client.luau` | One new argument `eggId` (no new locals: 193 / 200) | wiring |

## 7. Studio evidence and honest rating

See [evidence/2026-10-16-hatch-v2/README.md](evidence/2026-10-16-hatch-v2/README.md) (own temp copy of the playtest build with `HatchV2 = true` patched into the copy only; captures by `PrintWindow` of my own Studio window). The README lists every still per beat, the numbers (bake time, image bytes, frame cost) and the rating against docs/87. Not verified: phone hardware, published place, multiplayer, sound (agents cannot listen).

## 8. What still needs owner-made assets

1. Bucket mesh (s4 B): the barrel placeholder reads as a barrel, not a paint bucket.
2. Paint FX sheets (s4 C): today the arc, crown and puddle use the fx3 smoke cells tinted with the paint colour (soft blobs, acceptable but not "thick glossy paint").
3. Crack lines decal (s4 D): no crack lines on the 3D egg during the rattle beat.
4. Optional cuter egg (s4 A) and the wet-sheen decal (s4 C4).
5. Owner eye check of the timings (6.7 s build-up) and of the bright wet edge strength; both are single constants.

## 9. Owner guide: bind the assets and see the new hatch (one page)

**Preview now, with placeholders (Studio only).** Open `src/shared/Config.luau`, set `HatchV2Preview = true`, run the playtest in Studio, open an egg. The new sequence plays with the stand-ins: the egg mesh is real, the bucket is the barrel, the splash and droplets use the soft smoke sheet, no crack lines. It only works in an unpublished Studio place (`HatchV2Assets.enabled`); a published server ignores it. Set it back to `false` before committing: `HatchV2` and `HatchV2Preview` are pinned off in the default AND playtest profiles (`verify_release`).

**What each asset should look like.** Style block of [109](109-owner-art-prompt-pack.md) s0; friendly, vibrant, chunky ([114](114-handbook.md): kids' words, saturated colours, no grey or muddy tones). Blender or the owner's ChatGPT, never code-drawn (art rule). Ready prompts are in section 4.

| Slot name (paste this) | What | Size / frames | Colours | Plays as |
| --- | --- | --- | --- | --- |
| `hatch_bucket` | chunky cartoon paint bucket, rim, wire handle, open top with flat white paint | mesh, about 1.35 studs tall, one MeshPart | warm neutral metal with one wood band; paint surface pure white (tinted by code) | tips over each egg side |
| `paintCrown` | thick glossy paint splash: drop, crown, flying droplets, settled puddle | PNG 1024 x 1024, 4 x 4 cells of 256 px, 16 frames in reading order, 15 % cell margin, under 400 KB | white on transparent (code tints it with the egg colours, 114 s5.4) | OneShot, last cell is the puddle |
| `paintDroplet` | single round droplets of different sizes with a small highlight | same sheet format | white on transparent | Random cell per drop |
| `paintDrips` | three drips that grow longer | same sheet format | white on transparent | not read yet (drips are code-built gradient streaks); slot is ready |
| `paintGloss` | wet sheen: diagonal highlight band + two dots | single 1024 x 1024 | white on transparent | not read yet; optional |

Crack lines (section 4 D) have no slot yet: ask the lead to add one when you have the art.

**How to send them.** Upload as in [120](120-pending-owner-uploads-checklist.md) (images as Image not Decal, mesh from `generate_mesh`), then just paste lines like `paintCrown=rbxassetid://123456789` into chat to the lead. The lead runs `python tools/bind_assets.py ids.txt`; nothing is invented, bad ids are refused. After a bucket bind also flip `hatch_v2_bucket_placeholder` in docs/77.

**What to check after (Studio, preview on).** (1) The bucket looks like a paint bucket, not a barrel. (2) The splash reads as thick paint, not smoke, with no square edges (margin too small). (3) Droplets look like round drops. (4) Nothing is blank or a grey square (a wrong or Decal id shows as one: tell the lead to clear the slot and the stand-in returns). (5) Reduce Motion still shows a finished egg at once. (6) Then ask the lead to move the flag to the playtest profile.

Checks: `tools/verify_hatch_v2.py` (slot reads, fallbacks, toggle guard), `tools/verify_asset_slots.py`, `tools/verify_release.py` (flags pinned off).
