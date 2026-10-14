# 81 Mythic Glow aura and trail v2 (BD-086 to 088, 110 to 112, 095), 2026-10-14

**Owner pick (2026-10-14): Mythic Glow** (docs/70, board `docs/evidence/2026-10-14-aura-trail-concepts/board-mythic.png`).
Status: the effect code is built and **inactive until the textures are uploaded**. The 10 textures in this PR are
**Python-drawn PLACEHOLDERS and not acceptable as final art** (owner, 2026-10-14). They only fix the file names, sizes
and layout. Final textures are Blender renders: spec and session plan in [docs/83](83-playtest-asset-list.md).
Studio spike (BD-089) and phone check (BD-097) are pending.

## Frozen spec
Light ribbons, runes and glow, tinted per aura/trail colour. Each layer is white light tinted at
runtime, so one texture set serves every colour. A navy under-layer keeps the light readable on
bright grass (the risk named in docs/70).

**Trails: six classes** (speed, price and level unchanged):
| Class | Trails | Layers |
| --- | --- | --- |
| 1 Common | Normal White, Fern Drift | navy under-layer + main glow ribbon |
| 2 Uncommon | Tidal Wake, Ember Trail | + glow motes while walking |
| 3 Rare | Violet Pulse, Electric Arc | + wobbling plasma strand (Electric: lightning strand) |
| 4 Epic | Frost Comet, Solar Flare | + sparkle pops |
| 5 Legendary | Nova Ribbon | + braided third ribbon |
| 6 Mythic | Astra | rainbow main ribbon |

**Auras: three tiers from the existing growth multiplier** (below x1.3: 1, below x1.6: 2, else 3):
Meadow Glow tier 1, Tidal Halo tier 2, Royal Nova tier 3.
- Tier 1: rotating rune sigil on the ground with a navy under-glow, rising rune glyphs and motes, 2 orbiting comets.
- Tier 2: adds a counter-rotating inner sigil, a pulsing light pillar and a 3rd comet.
- Tier 3: adds a 4th comet and a rune halo over the head.
The 3 extra auras from docs/70 (Honey Spark, Ember Crown, Prism Dream) are **not added**: their prices need BD-098.

## Textures (10, `resources/effects/mythic-glow/`, 343 KB total)
sigil-outer, sigil-inner (512), runes (512, flipbook 4x4), glow-dot (128), ribbon-plain, ribbon-plasma,
ribbon-lightning (512x64, tile along the trail), light-pillar (512x128, along the beam), halo-ring (256),
twinkle (512, 16-frame flipbook). They are generated deterministically by
`tools/design/mythic_glow_textures.py`, and `--check` runs in CI. Review sheet:
`docs/evidence/2026-10-14-mythic-glow-v2/texture-sheet.png` (raw, tinted on navy, tinted on grass).

## Code
- `src/shared/AuraTrailStyle.luau` is pure. It holds the trail class and aura tier mapping, `plan(aura, trail, quality)`
  (a layer list), `quality(...)` (LOD), `ready(assets)` and the budget checks.
- `src/shared/EffectAssets.luau` holds the 10 texture IDs, all empty until upload. While any ID is empty or malformed, the game
  keeps the **v1 strip effects unchanged**, so merging this changes nothing in play until the upload.
- `src/shared/CosmeticEffects.luau`: `createV2` builds discs (anchored, non-colliding client-only Part +
  Decal in `workspace.LocalCosmetics`), ParticleEmitters (flipbooks), comet Beams, a pillar Beam, a halo
  BillboardGui and textured Trails. v1 remains the fallback.
- `src/client/CosmeticVisuals.client.luau`: LOD. Your own dino and the 2 nearest within 25 studs get full,
  others within 80 studs get lite (sigil + one trail), and anything further gets none. Motion off caps at lite. The cap of 8
  players with effects stays.
- Per-player budget at full: 4 emitters, 5 beams, 4 trails, 2 discs, 1 billboard (checked for every
  catalog combination). Worst case with 12 players is 3 full + 9 lite, which is about 12 emitters and 15 beams.

## To make it live (playtest steps)
1. Render the 10 textures in Blender (docs/83 section 5) over the placeholder files, same names and sizes.
2. Upload the 10 PNGs (owner account, or the lead through Studio), then put the IDs into `EffectAssets.luau`
   and docs/77. v2 switches on automatically when all 10 are bound.
3. BD-089 Studio spike: one trail and one aura per class/tier on grass. Check additive brightness, sigil
   height on slopes, comet curvature, halo height on large dinos, and LOD switching churn at the 25-stud edge.
4. BD-097: phone frame time with 12 players.

## Not done / risks
- Nothing is visually verified: no Studio access from this session. Sizes and offsets are first guesses.
- The sigil disc is anchored and placed every tick (30 Hz) at a fixed offset under the root, so it can float or
  clip on slopes.
- The Effects Full/Lite/Off setting toggle (BD-095), shop previews with real sprites (BD-114) and shop
  icons (BD-113) are not built.
