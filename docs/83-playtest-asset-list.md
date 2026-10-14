# 83 Playtest asset list and Blender session plan, 2026-10-14

One list of every texture, icon and 3D asset the private playtest (30 min, owner + friends) still needs.
Owner rule (2026-10-14): **no code-drawn or Python-drawn art as final** ([docs/72](72-ui-copy-and-asset-standards.md)).
Effect textures are **Blender renders**. Icons are made **by Claude in Blender** or **by the owner with ChatGPT**, as marked.
Every finished asset gets a [docs/77](77-asset-registry.md) line with its Roblox ID.

**Maker** column:
- **Blender**: Claude via Blender MCP on the owner's PC.
- **ChatGPT**: the owner generates with ChatGPT image generation, using the prompt template below. The current
  v2 icon kit (trophy, dinos, home, egg nest, weather x4) was made this way, so new icons match it best this way.
- **Upload**: the file already exists; it only needs uploading and binding.

**Priority**: P0 = needed for the playtest. P1 = should have; the game falls back cleanly without it. P2 = after the playtest.

## 1. Mythic Glow aura and trail textures (Blender, P0)

The v2 effect code is in PR #45 and stays off until all 10 IDs are bound. The PNGs in
`resources/effects/mythic-glow/` are **Python placeholders** and will be replaced file for file (same names, sizes and
layout), so no code changes. All of them: **white light on a transparent background**, RGBA PNG, straight alpha, tinted
per aura or trail at runtime, so no colour in the texture. Look: soft glowing light with a bright core and a wide soft
falloff, carved fantasy runes, magical but friendly (Mythic Glow board, `docs/evidence/2026-10-14-aura-trail-concepts/board-mythic.png`).

| # | File | Size | Used as | Blender build |
|---|---|---|---|---|
| 1 | sigil-outer.png | 512x512 | ground disc under the dino (Decal), rotates | Flat orthographic top view. Two concentric rings, 8 to 12 rune glyphs between them, small notches. Emission curves/meshes, bloom. Clear centre. 6% margin. |
| 2 | sigil-inner.png | 512x512 | inner disc, counter-rotates (tier 2+) | Smaller ring and a 6-point star/knot, a different rune set from #1. |
| 3 | runes.png | 512x512, flipbook 4x4 (16 cells of 128) | rising glyph particles | 16 single glowing rune glyphs, one per cell, centred, 15% cell margin. Same rune alphabet as the sigils. |
| 4 | glow-dot.png | 128x128 | motes, comet heads | Round soft orb, hot white core, smooth radial falloff to 0 at the edge. |
| 5 | ribbon-plain.png | 512x64 | main trail ribbon (all trails) | Bright horizontal centre line with a soft vertical falloff and faint lengthwise streaks. **Must tile left to right** (seamless). |
| 6 | ribbon-plasma.png | 512x64 | 2nd strand, Rare trails | Wavy, twisting energy strand, seamless horizontally (use a looping noise: 4D noise on a circle, or a whole number of sine periods). |
| 7 | ribbon-lightning.png | 512x64 | 2nd strand, Electric Arc | Jagged lightning bolt with small forks, seamless horizontally (start and end at the same height). |
| 8 | light-pillar.png | 512x128 | pulsing beam above the aura (tier 2+) | Vertical light shaft laid along X: bright base fading to 0 at the far end, soft side falloff. |
| 9 | halo-ring.png | 256x256 | rune halo over the head (tier 3) | Thin glowing ring with 6 to 8 tiny rune marks, seen from slightly above (a flattened ellipse is fine). |
| 10 | twinkle.png | 512x512, flipbook 4x4 | sparkle pops (Epic+ trails) | 16 frames of a 4-point star flash: grow, peak with a cross flare, shrink to nothing. |

Acceptance (checked on the Blender render and again in Studio, BD-089): readable tinted green, blue and purple on
**bright grass and on the navy under-layer**; no hard square edges in the alpha; the ribbons show no seam when tiled
3 times; each flipbook cell stays inside its cell. The review sheet is regenerated next to the renders.

## 2. Icons (ChatGPT, P0/P1)

All icons: **1024x1024 RGBA PNG** (Roblox scales it down), true transparent background, **12% clean margin** on every
side, single object, readable at **48, 64 and 128 px** (status icons also at **32 px**), thick near-black contour,
soft rounded bevels, broad hand-painted shading, bright top-left light, saturated cheerful palette, **no text, digits,
logos, ground plane or sparkle bursts**. Save the prompt as a `.json` next to the PNG, as `egg-nest-v1.json` does.

| # | Name / file | Priority | Spec notes |
|---|---|---|---|
| 11 | weather-volcano-v1.png (Volcanic Bloom) | P0 | Small friendly volcano with a glowing orange flower-shaped lava burst. Weather icons show in the HUD and in the weather toasts that the admin panel triggers. |
| 12 | weather-aurora-v1.png (Northern Lights) | P0 | Green and teal aurora ribbons over a small dark-blue night hill with 2 stars. |
| 13 | weather-quake-v1.png (Earthquake) | P0 | Chunky cracked rock slab splitting in two, with tan dust puffs and short shake lines. |
| 14 | weather-bloodmoon-v1.png (Blood Moon) | P0 | Large round crimson-pink moon with soft craters and a thin dark cloud across it. Spooky but friendly, no faces. |
| 15 | notify-crystal-v1.png | P1 | Faceted blue gem (the Crystals currency). Readable at 32 px. |
| 16 | notify-level-v1.png | P1 | Rounded gold star with a white up-chevron. |
| 17 | notify-star-v1.png | P1 | Simple chunky 5-point gold star (task done). |
| 18 | notify-mutation-egg-v1.png | P1 | Ivory egg with a swirling coloured flame band. |
| 19 | notify-warning-v1.png | P1 | Rounded orange-red triangle with a white bar and dot. |
| 20 | toast-body-v1.png | P1 | 9-slice plate, **512x128**, white-to-light-grey rounded panel (radius ~40 px) with a darker 6 px rim, tinted at runtime. No icon or text. Slice centre 48 px in from each edge. |
| 21 | potion-{speed,growth,loot}-{rarity}-v1.png (12 potions) | P1 | Speed = tall slim cyan flask, growth = round green flask, loot = wide amber jar. Rarity shown by cork, trim and glow only: Common plain, Uncommon green trim, Rare blue, Epic purple with a soft rim glow, Legendary gold with a stronger glow. Same angle and lighting on all 12. Replaces the code-drawn bottles in `PotionArt.luau`. |
| 22 | potion rarity frames (5) | P2 | Card frames for Common grey, Uncommon green, Rare blue, Epic purple, Legendary gold, 512x512, 9-slice, empty centre. |
| 23 | shop trail icons (10) and aura icons (3) | P2 | One per trail and aura in `ProgressionConfig.luau`, showing the effect as a short glowing swoosh or ring in its colour. Better made **after** item 1, using the Blender renders as reference, so shop and in-game look the same. |
| 24 | rarity badges (6) | P2 | Small gem badges for the six trail classes (Common to Mythic). |

ChatGPT prompt template (fill in the subject line; copy the rest as is):

> Use case: stylized-concept. One reusable transparent UI icon for Be Dino, a friendly Roblox dinosaur survival and
> collection game for younger players. Match the existing illustrated icons (egg nest, trophy, weather): saturated
> dimensional illustrated 3D, thick near-black contour, soft rounded bevels, hand-painted broad shading, controlled
> highlights, cheerful chunky prehistoric fantasy. Subject: **[SUBJECT FROM THE TABLE]**. Composition: single compact
> object, three-quarter front view slightly from above, centred on a square canvas, whole object visible, at least 12%
> clean transparent margin on all edges. Readable at 48/64/128 px; broad simple shapes, no hair-thin detail. Bright
> top-left lighting, contact shadow only within the object. True transparent alpha background. No environment, ground
> plane, sky, UI panel, logo, lettering, digits, labels, arrows, ribbons, sparkle burst or watermark.

Attach `trophy.png`, `egg-nest-v1.png` and `weather-rain-v1.png` from `resources/ui/v2/icons/` as style references.
Drop the PNG and its `.json` into `resources/ui/v2/icons/` (or send them in the thread) and Claude binds them.

## 3. 3D assets

| # | Asset | Maker | Priority | Notes |
|---|---|---|---|---|
| 25 | Berry and fruit food MeshParts (BD-050) | Upload | P0 | Already modelled in `assets/blender/world/BD050_FoodKit.blend`. Needs a MeshPart upload in Studio so the food pickups use the real models. |
| 26 | Mythic Glow 3D pieces | none | none | Not needed: the effects are textures on Decals, Beams, Trails and particles. |
| 27 | 17 species without an uploaded mesh | Blender | P2, owner decision | Only compy, triceratops, tyrannosaurus, raptor, stegosaurus and ankylosaurus have uploaded meshes. The other 17 draw from generated vertex data in `src/shared/CreatureData/`. They work for the playtest; proper Blender models are a larger job for after it. |
| 28 | Fusion finish v2 (Blender study) | Blender | P2 | Study only, no runtime asset yet. |

## 4. Sound (Upload, P1)

The 17 sfx in `assets/audio/sfx/` (docs/77 rows) need uploading and binding in `Sfx.luau`. Without them the game is silent but works.

## 5. Blender session plan (items 1 to 10)

Needs: the owner's PC with Blender open and the Blender MCP connected, and one Roblox Studio instance for the upload
(reuse an open one, close it after).

1. **Scene setup (once).** New file `assets/blender/effects/mythic_glow_v2.blend`. Orthographic camera looking straight
   down, world colour black at strength 0, **Film > Transparent on**, Eevee, view transform **Standard** (not Filmic/AgX,
   so white stays white), output RGBA PNG 8-bit. Bloom through the compositor (Glare node, Fog Glow, threshold 0.8).
   Render each texture at **2x** its final size and downscale, which gives smooth edges.
2. **Alpha from light.** All geometry uses a white Emission shader. In the compositor, alpha = luminance of the bloomed
   image and colour = white, so the PNG is pure white light whose transparency carries the shape. This is what
   runtime tinting needs.
3. **Order** (cheapest check first): glow-dot (4), ribbon-plain (5), then a quick upload of those two to check
   brightness and tint in Studio on grass before doing the rest. Then sigil-outer (1), sigil-inner (2), runes (3),
   halo-ring (9), light-pillar (8), ribbon-plasma (6), ribbon-lightning (7), twinkle (10).
4. **Runes.** Model one rune alphabet of 16 glyphs as bevelled curves, so the sigils, the runes flipbook and the halo
   share it.
5. **Seamless ribbons.** Render the strand along a path whose start and end match (looping noise or whole sine
   periods), and check by tiling 3 copies side by side.
6. **Flipbooks.** Animate 16 frames, render each frame, then pack them into the 4x4 grid in row order (top-left first)
   with a small assembly script. That script only places rendered frames; it draws nothing.
7. **Export** over the placeholder files in `resources/effects/mythic-glow/` with the same names. Retire the Python
   generator's CI `--check` (it would fail on real renders) and keep the script only as a size and layout reference.
   Regenerate the review sheet from the renders.
8. **Upload** the 10 PNGs through Studio (owner account), put the IDs in `src/shared/EffectAssets.luau` and docs/77
   (status: in game). v2 turns on by itself once all 10 are bound.
9. **Studio check (BD-089).** One trail per class and one aura per tier on grass: brightness, sigil height on slopes,
   halo height on big dinos, LOD switching. Screenshots go in `docs/evidence/`. Then a phone check (BD-097).

## 6. Status

| Group | Items | Done |
|---|---|---|
| Mythic Glow textures | 1-10 | Python placeholders only (PR #45, draft) |
| Weather icons | 11-14 | not started (owner, ChatGPT) |
| Notification icons + plate | 15-20 | not started (owner, ChatGPT) |
| Potion icons | 21-22 | code-drawn placeholder in game |
| Shop icons and badges | 23-24 | not started, after item 1 |
| Food MeshParts | 25 | modelled, upload pending |
| Sfx | section 4 | files exist, upload pending |
