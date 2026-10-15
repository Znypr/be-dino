# 93 Anime FX direction (BD-161 / BD-162 / BD-163)

Status: DIRECTION + FIRST IMPLEMENTATION (this branch). Owner vision 2026-10-15: auras, trails and mutations should look like anime power-ups (very colourful, with 3D depth) but fitted to the calm, bubbly look of [docs/87](87-vision-and-feel-guide.md). Everything here is **CURRENT BUILD BEHAVIOR on this branch** unless marked TODO. Feel rules (docs/87): gentle, readable, never hides the dino or food, budgeted, always a Reduce Motion version.

Honest scope note: the research below is craft knowledge of how anime and anime-style games build effects, written from experience of the genre, not a literature review with citations. The numbers (budgets, rates, timings) are PROVISIONAL and need the owner's eyes and a real phone.

## 1. How anime renders these effects (and what we keep)

| Anime device | How it is built | Be Dino! adaptation |
|---|---|---|
| **Aura** (power-up) | Flame-like sheets rising off the body in 2-4 overlapping layers; core colour bright, outer edge saturated and darker; edge flicker; ground ring; small floating specks | Soft rising motes + soft smoke base + orbiting ribbon rings + a breathing rim light. No flicker, no flame shapes, slow rise |
| **Layered smoke** | Several translucent puffs, each a different shade (dark rim, bright centre), swelling as they rise | One smoke emitter per aura, gradient deep (cool, dark) -> primary; peak opacity capped at 50% so the dino stays readable |
| **Rim light / glow** | Bright edge light that "wraps" the character | One soft PointLight per effect, 0.4 brightness, pulses at 0.55 Hz (breathing) |
| **Shock rings** | A flat ring expands from the feet and fades, on power-up and landings | Disc emitter (ripple), 1 ring per ~0.9 s, a bigger one-shot ring on equip/start |
| **Speed lines / motion trail** | Thin streaks behind the mover plus a fat soft smear | Main ribbon + wide faint under-ribbon + two thin "speed line" ribbons (Rare and up) |
| **Impact sparkle / star pops** | Four-point twinkles that pop then shrink | Sparkle emitters use a pop curve (0 -> full -> 0) and, at Epic and up, four-point stars |
| **Colour grading** | Shadows shift to a cool hue, highlights to near-white, accent hue appears at the edge | Palette rule below: every effect has a cool-shifted shadow colour and a near-white glint |
| **Transformation burst** | A short white-hot flash, shock ring, sparks | One-shot "pop" (6-14 particles, 0.6 s) on equip / first run step; never a screen flash |

Deliberately NOT adopted: screen shake, full-screen flashes, hard outlines/cel shading on dinos, flicker, speed above 3.5 studs/s, anything that covers more than the dino's silhouette. Dinos stay matte; glow lives only in particles, beams and one light.

## 2. Layer recipe per rarity tier (data: `src/shared/FxRecipes.luau`)

Layers are added in PRIORITY order. A tier shows the first N layers; a device shows layers until the next one would break its budget. More rarity = more layers, more palette colours, 10% more particle rate per tier, 5% bigger sprites per tier. Palette entries come in this order, and a tier may use the first N: **primary, accent, deep, light, hueA (+40 degrees), hueB (+120 degrees)**.

| Tier | Layers | Palette colours | Aura layers (priority order) | Trail layers (priority order) |
|---|---:|---:|---|---|
| Common | 2 | 2 | rim glow, rising motes | main ribbon, shed sparkles |
| Uncommon | 3 | 3 | + soft smoke base | + wide faint under-ribbon |
| Rare | 4 | 3 | + orbit ring (3 beams) | + smoke puffs behind |
| Epic | 5 | 4 | + ground shock ripple | + two thin speed lines |
| Legendary | 6 | 5 | + rising spiral ribbons (2 beams); sparkles cycle the full palette | + four-point stars |
| Mythic | 7 | 6 | + crown ring (hue-shifted, counter-rotating) | + start-of-run star pop |

Current content: auras Meadow Glow (Common), Tidal Halo (Rare), Royal Nova (Legendary); trails White, Fern (Common), Tidal, Ember (Uncommon), Violet, Electric (Rare), Frost, Solar (Epic), Nova (Legendary), Astra (Mythic). Mutations use a fixed "Rare" look (glow, motif particles, smoke, orbit ring, plus an equip pop) with a **motif** per mutation (`FxRecipes.Motifs`): Dewdrop slow round bubbles, Charged fast small stars, Frost crystals drifting down, Seismic pebbles and dust, Ember rising flame wisps, Aurora hue-drifting ribbons, Blood Moon slow round crimson motes.

Mutations and auras/trails can be combined on one dino. The first rig gets the dino's detail level; the second and third rig always use the **lite** layer count (2 layers, rates x0.6), so the combined look stays inside roughly one budget.

## 3. Palette rules
1. **Shadow colour is a cool shift, not black**: `deep = primary mixed 45% toward navy (28,36,92)`. Mutations take their own mist colour from MutationLook.
2. **Glint is near-white**: `light = primary mixed 55% toward white`; used at the bright core of ribbons and stars.
3. Gradients always run **deep -> primary -> accent/light** (dark at the edge, bright at the core), never the other way.
4. Rarity adds hues, it does not add saturation: Legendary/Mythic add the two hue-shifted colours (hueA/hueB, clamped to S 0.45-0.9, V >= 0.85) so they read as rainbow-tinged, not neon.
5. At least 24 (sum of RGB distance) between any two palette colours (verifier), so extra colours are actually visible.
6. Aurora mutation is the only effect that cycles green/blue/violet on purpose.
7. Smoke peak opacity <= 50%, sparkles <= 90%, so food, eggs and the dino outline stay readable. Tint of the dino body is untouched (BD-155 MutationLook, still <= 35% pull).

## 4. Timing curves (calm)
| Item | Value |
|---|---|
| Fade-in on equip/appear | 0.35 s ease-out (cubic) |
| Breathing glow | 0.55 Hz sine (limit 0.8 Hz) |
| Orbit speed | 0.45-0.7 rad/s (limit 1.0) |
| Particle life | 0.9-1.7 s (limit 2.2), speed <= 3.5 studs/s |
| Transparency curve (`fadeInOut`) | 1 -> 0.3 at 18% -> 0.5 at 55% -> 1 (fast soft in, long soft out) |
| Sparkle size (`sizePop`) | 0 -> full at 20% -> 0 |
| Smoke size (`sizeGrow`) | 0.4 -> 1 at 35% -> 1.25 (swells as it rises) |
| Trail width (`taper`) / alpha (`trailAlpha`) | 1 -> 0 / 12% -> 50% -> 100% transparent |
| One-shot pop | 0.6 s, 6-14 particles, only on equip and when a run starts (1.5 s cooldown) |
All values live in `FxRecipes.Timing` and `FxRecipes.Curves`, checked by `tools/verify_fx.py`.

## 5. Particle and part budgets (per dino effect, PROVISIONAL)
| Device class | Emitters | Beams | Trails | Anchor parts | Lights | Particles alive | Rate scale | One-shot burst | Dinos at full detail |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Phone (touch, no mouse, short side < 700 px) | 3 | 3 | 2 | 1 | 1 | 18 | **0.5** | 6 | 1 (own dino) |
| Tablet (touch, short side >= 700 px) | 5 | 5 | 3 | 1 | 1 | 30 | 0.75 | 10 | 2 |
| Desktop | 6 | 8 | 4 | 1 | 1 | 45 | 1.0 | 14 | 3 |
`alive` = rate x lifetime after rate scaling. The existing cap of 8 dinos with effects within 180 studs stays; beyond the "full detail" dinos (and farther than 25 studs) a dino shows the lite look (2 layers, rates x0.6). No per-frame Instance creation: instances are pooled (`FxRig`, 64 per class), updates run at 30 Hz, scale-dependent sizes are only rebuilt when the dino's scale changes by 5% or more. No Neon parts; the single anchor part is invisible and anchored.

Phone example (a Legendary aura): glow + motes + smoke + ring + ripple = 5 layers (the 2-beam spiral does not fit 3 beams), 3 emitters, 3 beams, about 11 particles alive.

## 6. Reduce Motion fallback
- Aura and mutation: **one still soft light**, no particles, no beams, no pulse, no pop. (The MutationLook body tint stays: it is static.)
- Trail: **one short plain ribbon (0.45 s)** that only follows the dino; no particles, no lines, no pop.
- Shop previews: aura shows one still glow disc; trails keep the existing static ribbon art (BD-111 `TrailArtwork`).
- Switching Reduce Motion rebuilds the rigs (same as before).

## 7. How it is built
- `src/shared/FxRecipes.luau`: PURE data and maths. `FxRecipes.resolve(kind, item, {device, reduce, detail})` -> palette + ordered layers + cost, trimmed to the device budget. Verified offline.
- `src/shared/EffectAssets.luau`: semantic texture keys -> uploaded Blender texture if its id is set, else the engine's built-in white sprites. Never invented ids; only the existing BD-155 soft mist id is present.
- `src/client/FxRig.luau`: builds and pools ParticleEmitters, Beams, Trails, Attachments and one anchor part from a recipe for a world dino (`attach`, `update`, `burst`, `destroy`). Used by `CosmeticVisuals.client.luau` for auras, trails and mutations (replacing `CosmeticEffects` and the `MutationEffects` mist, which stay in the repo as history and for the BD-155 scan).
- `src/shared/FxUi.luau`: 2D twin for menus. **ParticleEmitters, Beams and Trails do not render inside ViewportFrames**, so previews on UI play the same recipe layers as pooled sprites: glow discs, an orbit of dots passing in front of and behind the dino for depth, particle sprites, a ribbon history behind a runner orb. One shared 30 Hz loop, at most 8 previews alive, stops when its frame leaves the game. `UITheme.icon` hooks it for `trail_<id>` and `aura_<id>` icons (BD-143 animated previews). `FxUi.mount(parent, "mutation", MutationLook.get(id))` is ready for the Eggs screen, Index and hatch panels (BD-162 menu part, TODO wiring).

## 8. Missing textures: Blender requests for the lead
Everything works with built-in sprites, but it will look better with real art. Render white or neutral grey on alpha (runtime tints them), PNG, under 400 KB, then upload and put the id into `Assets.Requested[key].id`. Add a docs/77 line per asset. These requests extend docs/92 (the mutation brief) and the Mythic Glow v2 set (PR #45, 10 textures, none uploaded yet; those overlap `ringSoft`, `glowPlate`, `starFour`, `ribbonSoft` and can be reused).

| Key | What | Size | Used by |
|---|---|---|---|
| `glowPlate` | soft neutral radial glow (docs/92 batch 1) | 256 | glow layers, Blood Moon motes |
| `ringSoft` | soft rim ring | 256 | aura rings, ripples |
| `ringShock` | thin shock ring | 256 | ground ripple (Disc emitter) |
| `smokeSheet` | layered smoke 4x4 flipbook, 3 densities (docs/92 batch 2) | 512 | aura / trail / mutation smoke |
| `sparkSheet` | soft sparks, bubbles, round motes 4x4 (docs/92 batch 4) | 512 | motes, shed sparkles, Dewdrop |
| `flameSheet` | soft flame wisps and embers 4x4 | 512 | Ember mutation, Solar trail |
| `crystalSheet` | snow crystals, pebbles, droplets 4x4 | 512 | Frost, Seismic |
| `starFour` | four-point twinkle, soft | 128 | stars, Charged |
| `ribbonSoft` | soft tapered ribbon strip, horizontal | 512x64 | Trail / Beam texture (stretch) |
| `speedLine` | thin streak strip | 512x32 | speed lines (not yet bound) |
Flipbooks: the rig sets Grid4x4 + Random automatically once a key has a real id.

## 9. What is verified and what is not
- Verified offline (`python tools/verify_fx.py --runner luau.exe`): every aura, trail and mutation resolves on phone/tablet/desktop within budget; layers, palette colours and cost never shrink as rarity rises; phone particle rates are exactly half of desktop; calm limits (life, speed, spin, opacity, ring radius, size); Reduce Motion layers; curves; texture keys; no invented asset ids; Bootstrap untouched.
- Needs eyes (see the PR for what Studio could show): how it looks, frame time on a real phone, the Disc/Cylinder emitter orientations, whether built-in sparkle DDS sprites render in ImageLabels, the pop timing. The owner judges the look; agents cannot judge taste.
- TODO: wire `FxUi` into Eggs/Index/hatch mutation previews (BD-162), bind real textures, a quality slider in settings, QA overlay listing which keys still use fallbacks, audit of weather overlap (effects near Blood Moon/aurora haze).
