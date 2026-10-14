# 70 - Aura and trail concepts (BD-086 draft art)

Owner feedback 2026-10-14: auras and trails look like thin minimal strips; redesign them, animated, with more visual complexity, in the game's design language. This doc proposes **three style directions** with 2D draft boards. No gameplay code. Nothing here is uploaded or shipped: every sprite/texture below is a Proposal until the owner uploads art (IDs come only from owner upload).

Boards (1600x1100, real Compy render on game-like grass, regenerate with `tools/design/aura_trail_concepts.py`) in `docs/evidence/2026-10-14-aura-trail-concepts/`: `board-candy.png`, `board-mythic.png`, `board-ink.png`, `comparison-sheet.png`.
Each board has: hero composite, 6 auras, the 10-trail rarity ladder, a 320 px phone panel, and 5-frame loop strips for one trail and one aura (t = 0.0 to 0.8; the loop is 1.0 s and seamless). Concept caveat: the Compy cut-out is auto-masked from the render, so thin parts (front leg, jaw) show small gaps; the effects are the point, not the cut-out.

## a. What exists today (Seen: `src/shared/CosmeticEffects.luau`, `TrailArtwork.luau`, `ProgressionConfig.luau`)

- **Aura** = 2 rings x 4 `Attachment`s orbiting the root, joined by 8 `Beam`s (width 0.1 x scale, Transparency 0.22 / 0.65, LightEmission 1, FaceCamera) plus one `ParticleEmitter` (8 or 12 per second) using the stock `sparkles_main.dds`. Three auras: Meadow Glow (x1.15), Tidal Halo (x1.35), Royal Nova (x1.7), differing only in color.
- **Trail** = 2 `Trail` objects (left/right of the tail, height = catalog `width` 0.35-0.85 studs, lifetime 0.6-1.3 s, WidthScale 1 to 0) plus a walking-only glitter emitter (3-14 per second, same stock sprite). The ten trails differ only in color, width, lifetime and glitter rate. `TrailArtwork` (shop preview) draws two flat 28-segment lines.
- **Why they read as thin strips:** every shape is a 0.1-stud line or a flat-color 0.3-0.8-stud ribbon with no texture; one stock sprite for everything; no outline, no shape language, no per-trail motif; the only motion is rotation; the rings sit at ankle height and vanish at game camera distance; rarity is invisible (a Common and a Legendary trail have the same geometry).

## b. Three style directions

| | **Candy Pop** | **Mythic Glow** | **Storybook Ink** |
|---|---|---|---|
| Identity | Bubbly, chunky, glossy sticker ribbons and soft pops | Layered energy ribbons, runes and light; rare = rich | Ink-outlined paper cut-outs, leaves and confetti |
| Palette | Catalog colors at full saturation + white gloss + navy `#142035` outline; rainbow only for the top class | Catalog colors as light (screen blend), white-hot cores, dark-navy under-shadow for legibility | Flat catalog colors, cream paper `#FFF8E2`, navy ink outline, gold stars for top class |
| Shape language | Thick rounded ribbons (about 0.3 x dino height at the head), polka dots then motif stamps, glossy bubbles, candy-striped rings | Thin braided strands that separate and recombine, comet arcs, sigil rings with 8-12 runes, light pillars, halo | Banded paper strips with dashed stitch, outlined leaf/drop/flame/star cut-outs, paper puffs, sunburst, wind curls |
| Motion | Wobble + stripes sliding along the ribbon, bubbles rise and sway, stars pop | Strands phase-shift, comets orbit, runes spin and fade, pillar pulses | Confetti flutters down, orbit pieces spin, bands scroll, puffs rise |
| Fit with UI/dino | Closest to the v2 UI (chunky, bright, outlined, rounded); reads best on saturated grass and at phone size | Premium feel for top tiers, but light washes out on bright grass without the dark under-layer; least like the flat UI | Matches the low-poly flat dino and outlined icons; calm, never noisy; lower "wow" at the top end |

How rarity scales in every style: class 0-1 plain ribbon + dots/confetti; class 2 adds motif stamps or a second strand; class 3 adds bands/second layer; class 4 adds sparkle pops and head glow; class 5 (Mythic) adds rainbow gradient and a signature head effect.

## c. Roblox feasibility

| Needed | Candy Pop | Mythic Glow | Storybook Ink |
|---|---|---|---|
| `Trail` with texture | 2 per side, opaque, LightEmission 0.2, `Texture` 256x64 (plain/dots/stripe/rainbow), outline baked into the texture | 2-3, additive (LightEmission 1), gradient texture, braid via `Trail`s with different attachment offsets | 1-2, opaque banded texture with ink edge, LightEmission 0 |
| `Beam` | orbit ribbon loop (tier 2+), 4 segments, textured | comet arcs (4, tier 2+), thin, additive | wind curl (1-2, tier 2+), textured |
| `ParticleEmitter` | bubbles, motifs, star pops (3 emitters, flipbook sheets) | motes, glyphs, sparks (3 emitters) | leaves/confetti, puffs (3 emitters, flipbooks) |
| Ground disc | thin `Part` + `Decal` ring (rotated per frame via one CFrame write) | same disc; sigil also tried as one big ParticleEmitter particle (spike in BD-089) | same disc with paper/dashed ring decal |
| Billboard sprites | star crown, tier 3 (5 `BillboardGui`s or 1 emitter) | halo ring above head (1) | sunburst behind dino, tier 3 (1) |
| `SurfaceGui` | not needed | not needed | not needed |
| Lights | none | none (existing mutation `PointLight` stays) | none |

**Sprite/texture list (Proposal; all need owner upload before any ID exists):**
- Candy Pop (7): ring stripe 512x512; motif atlas 1024x1024 (4x4 = 16 glossy shapes); bubble pop flipbook 512x512 (2x2 = 4 frames); star pop flipbook 512x512 (2x2); ribbon strips 256x64 x4 (plain, dots, stamps, rainbow); crown star 128x128; glow dot 128x128.
- Mythic Glow (9): sigil rings 512x512 x2; rune atlas 512x512 (4x4 = 16 glyphs); glow dot 128x128; ribbon gradients 512x64 x3 (plain, plasma, lightning); light pillar 128x512; halo ring 256x256; twinkle flipbook 512x512 (4x4 = 16 frames).
- Storybook Ink (9): paper ring + disc 512x512 x2; motif atlas 1024x1024 (4x4 = 16 outlined cut-outs); confetti sheet 256x256 (4x4); ribbon strips 256x64 x3 (stripe, dots, band); puff flipbook 512x512 (2x2); sunburst 512x512; swirl 256x64.
- All PNG with alpha, power-of-two, under about 3 MB total per style; tint with `Color3` so one sheet serves all ten colors.

**Effect budget (12 players, phones).** Full quality (aura + trail): at most 4 emitters (<= 45 particles/s, lifetime <= 1.5 s, so <= 70 live), 4 beams, 2 trails, 1 ground-disc `Part`, 0 new lights. 12 full players would be 48 emitters, too heavy, so use distance LOD: **full** for the local player and the 2 nearest within 25 studs; **lite** for the rest within 80 studs (1 trail, 1 emitter <= 10/s, ground disc, no beams); **none** beyond 80 studs. Worst case: 3 full + 9 lite = about 21 emitters, about 225 particles/s, 12 beams, 15 trails, at most 10 distinct textures loaded. Shiny sparkles (8/s) and the mutation glow stay on top of this budget.

**Reduced-effects fallback:** local setting Effects Full / Lite / Off (auto-Lite on low graphics level or sustained frame-time spikes; `Theme.MotionEnabled` false also forces Lite with no orbit/spin). Lite = single textured trail + static ground disc, no beams, no emitters. Off = no world effects, equipped item still shown in UI. Gameplay (speed, growth) never depends on the visuals.

## d. Ten trails in six rarity classes, and the auras

The ten trails keep ids, levels, prices and speed multipliers (`ProgressionConfig`). The six classes are the provisional taxonomy from doc 45 (needs owner review); renaming a class never changes speed.

| Class | Trails (catalog rarity today) | Motif | Complexity rule |
|---|---|---|---|
| Common | Normal White (Common), Fern Drift (Common) | puff, leaf | one ribbon, dots / few motifs |
| Uncommon | Tidal Wake (Common), Ember Trail (Rare) | drop, flame | more motifs, gentle wobble |
| Rare | Violet Pulse (Rare), Electric Arc (Rare) | pulse ring, bolt | motif stamps / second strand, jitter for Electric |
| Epic | Frost Comet (Rare), Solar Flare (Legendary) | snowflake, sun | banded layer, sparkle pops |
| Legendary | Nova Ribbon (Legendary) | gold star | head glow, braided second ribbon |
| Mythic | Astra (Legendary) | prism | rainbow gradient + signature head effect |

**Auras (6 per style).** Meadow Glow, Tidal Halo and Royal Nova exist (Seen); Honey Spark, Ember Crown and Prism Dream are proposed names. **Growth-tier idea, no new data:** derive the aura tier from the existing growth multiplier: tier 1 below x1.3, tier 2 from x1.3 to below x1.6, tier 3 from x1.6 (thresholds provisional). Meadow x1.15 and Honey x1.25 are tier 1; Tidal x1.35 and Ember x1.5 tier 2; Royal x1.7 and Prism x1.9 tier 3 (the three new multipliers are Proposals).

| Tier | Candy Pop | Mythic Glow | Storybook Ink |
|---|---|---|---|
| 1 | candy-striped ground ring + disc, bubbles, motif floaters, pops | glowing ground sigil with runes, comets, motes | paper ground disc with dashed ring, orbiting cut-outs, puffs, confetti |
| 2 | + inner ring, orbiting chunky ribbon loop | + inner sigil ring, light pillar, floating glyphs | + wind-swirl ribbon, more cut-outs |
| 3 | + candy rainbow arcs, floating star crown | + outer ring, twin side pillars, halo ring with runes over the head | + sunburst behind the dino, second swirl, gold star crown |

## e. Intake answers (doc 64; Seen = verified in repo, Proposal = new)

1. **Intention:** progress and surprise (a visible reward for levels, Crystals and growth); collection mastery. Moments: run, shop preview, equip.
2. **Extension:** extends `CosmeticEffects`, `TrailArtwork` and the existing AURAS/TRAILS shop tabs (Seen). No new system.
3. **Logical fit:** no loop change. Touches shared config (additive trail class field, aura tier derived), client effects, shop previews. If off, visuals fall back to today's strips; speed and growth are unaffected.
4. **Graphical fit:** world-space effects around the dino, no HUD space. Check overlap with mutation glow, shiny sparkles and the hatch reveal (hide aura/trail during modals and hatch). The phone panel on each board shows legibility at 320 px.
5. **UI visuals:** reuse v2 card frames; six rarity badge colors (Common gray-blue, Uncommon green, Rare blue, Epic purple, Legendary gold, Mythic pink) as used on the boards.
6. **UI icons:** 10 trail icons + 6 aura icons (16) for shop cards, plus 6 rarity badges; flat 2-3 tone, outlined, transparent 1:1, readable at 32 px. IDs only from owner upload (`UIIconAssets`).
7. **Animations:** trail wobble/scroll, aura orbit/pulse/rise (loops of 1.0-2.0 s), equip pop (0.25 s scale + sparkle burst on the dino). Motion-off: no tween, static ground disc + plain trail (Lite).
8. **Audio:** reuse the 17-sound pack (`assets/audio/sfx`): a subtle shimmer on equip, suggested `pickup_hi.wav` at low volume (`shop_buy.wav` stays on purchase); no looping effect audio. `Sfx.play` is a no-op while ids are empty.
9. **Copy:** names unchanged; new ones "Honey Spark", "Ember Crown", "Prism Dream" (sentence-case descriptions, under 40 characters).
10. **Data/server:** none. Effects are client-local cosmetics selected by the existing equipment state; class and aura tier are config/derived values, no profile field, no remote. Unknown id = no effect (fail closed).
11. **Performance:** budget and LOD in section c; effects pooled per player, one `update` tick as today.
12. **Metrics:** more AURAS/TRAILS shop visits and equips; playtest question "which look do you want to earn?"; attribute counter for equipped class.
13. **Acceptance:** owner picks one style (or a hybrid); Studio check of 1 trail + 1 aura per class with 12 simulated players; Android phone-landscape FPS check; motion-off and Effects Off check; sound-off check. Evidence goes to the Kanban.
14. **Tasks:** section f.
15. **Open questions (recommended answer):** (1) Which style? Candy Pop as the base, with Mythic accents for the top two trail classes. (2) Approve the six class names and the aura tier thresholds? Yes, provisional. (3) Approve three new auras and their prices? Yes, prices decided in BD-098.

## f. Task breakdown (Backlog, IDs from BD-086)

| ID | Role | Size | Task |
|---|---|---|---|
| BD-086 | design | S | Owner picks style/hybrid; freeze the per-class spec sheet from the boards |
| BD-087 | art | L | Sprite sheets and textures for the chosen style (list in section c) |
| BD-088 | art | M | Ribbon textures for the ten colors and ground-disc decals |
| BD-089 | tech art | M | Studio spike: one trail + one aura per tier, ground-sigil technique, additive vs opaque on grass |
| BD-110 | client | L | `CosmeticEffects` v2: aura tiers, textured ribbons, orbit beams, pooled emitters |
| BD-111 | client | L | Trail v2: textured trails, motif emitters, six-class complexity |
| BD-112 | design/shared | M | Config: class per trail, aura tier from growth, three new auras (ids, prices TBD) |
| BD-113 | UI art | M | 16 shop icons + 6 rarity badges |
| BD-114 | UI | M | Shop previews use real sprites/loops instead of `TrailArtwork` flat lines |
| BD-095 | client | M | Effects Full/Lite/Off setting, distance LOD, motion-off behavior |
| BD-096 | audio | S | Equip shimmer wiring from the existing pack |
| BD-097 | QA | M | 12-player phone performance and Studio/Android acceptance |
| BD-098 | design | S | Prices and level gates for the three new auras (owner approval) |

Regenerate boards: `PYTHONPATH=<Pillow+numpy site-packages> python tools/design/aura_trail_concepts.py [--styles candy mythic ink] [--no-sheet] [--out DIR]` (deterministic, no clock or network).
