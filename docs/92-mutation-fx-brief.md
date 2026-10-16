# 92 Mutation FX brief and Blender sub-task list (BD-161 / BD-162 prep)

Status: PREP. The brief for the lead to render the mutation effect art later. **2026-10-16: batch 1 (BD-186) and batch 3 (BD-188) are rendered** (`resources/effects/fx-v2/`, [docs/77](77-asset-registry.md) `fx_glowPlate*`, `fx_ring*`; source `tools/blender/fx_glow_rings_v3.blend`, script `tools/blender/build_fx_glow_rings.py`); upload and binding pending ([docs/120](120-pending-owner-uploads-checklist.md)). Other batches are not rendered and no asset IDs exist yet.
Feel rules come from [docs/87](87-vision-and-feel-guide.md): **anime-inspired but gentle** (layered smoke, rim light, soft rings and sparkles with real depth and bright colour, soft edges, slow rhythm, "magical sparkle" not "explosion"), always readable, budgeted, with a Reduce Motion version. Task status lives only in [the Kanban](07-kanban.md) (BD-186 to BD-190). Art rule ([docs/83](83-playtest-asset-list.md)): textures are **Blender renders**, never code-drawn.

## What exists today (BD-155 / BD-156, this branch)
- One shared look table, `src/shared/MutationLook.luau` (per mutation: soft tint colour, tint pull `amount` at most 0.35, rim colour, glow strength, matte material, mist and spark colours, badge colour, mood). The world dino, the previews (Dino Index, My dinos, dino details, hatch dino), egg-card colour hint and `MutationEffects` mist all read it.
- The mist still uses one soft smoke texture (`rbxassetid://105629313112163`) tinted per mutation. Everything below replaces or adds to it as Blender renders.
- Dinos stay matte (no Neon, Metal, Glass, reflectance). Conditions never appear on dinos.

## The seven mutations (one per weather event)
Hex values are the current `MutationLook` colours (tint / rim / mist / spark). Render art **white or neutral grey** where possible so the runtime tints it from the table; only the multi-hue ones (Aurora) need coloured renders.

| Mutation id | Name | Weather | Tint | Rim / spark | Mist | Mood | Signature motif |
|---|---|---|---|---|---|---|---|
| `dewdrop` | Dewdrop | Rain | #78E2BE | #70F4BF | #2B9A6F | fresh, dewy, playful | tiny round droplets, shiny bubbles, gentle drip sparkle |
| `charged` | Charged | Thunderstorm | #FFE278 | #FFCF48 | #384257 | zippy, bright, tingly | small soft zigzag sparks, rounded static puffs (never harsh flashes) |
| `frost` | Frost | Blizzard | #A0E8FF | #AFEBFF | #70B8D3 | crisp, sparkly, cool | six-point snow crystals, frosty breath puffs, glitter |
| `seismic` | Seismic | Earthquake | #E2BE82 | #D2AD71 | #85613E | warm, sturdy, rumbly | round pebbles, dust puffs, a soft ground ring |
| `ember` | Ember | Volcanic Bloom | #FF8C5A | #FF9033 | #633622 | cozy campfire glow | rising warm embers, soft flame wisps, glowing sparks |
| `aurora` | Aurora | Northern Lights | #8CFADC | #51E9BB | #6D4196 | dreamy, shimmering, magical | flowing ribbons that drift green, blue, violet, magenta (see aurora cycle in docs/84) |
| `bloodmoon` | Blood Moon | Blood Moon | #FF7896 | #FA4366 | #7A1A2E | moody but cozy | a soft crescent glow, round crimson motes, slow pulse |

Weather (not the mutation art) keeps its own look in [docs/84](84-weather-events-v2.md). Mutation art is a small aura on one dino or egg, never a screen effect.

## Where each asset is used
| Place | What shows | Notes |
|---|---|---|
| World dino (equipped) | soft body tint (done), mist, 4 beams, up to 4 floating details, rim point light | at most 8 dinos with effects, nearest first (existing cap) |
| Dino Index hero, My dinos cards, dino details | tint (done), badge dot (done), later a looping glow plate behind the dino | one animated plate per viewport, off-screen viewports unload |
| Eggs screen cards, hatch egg | colour hint (done) now; later a soft surrounding smoke ring around the egg (docs/39: never paint the shell) | shell keeps gene colours and condition look separate |
| Hatch reveal (BD-162) | one-time burst: ring + sparkle sheet + smoke puffs, then a calm loop | skippable, soft sound only |

## Budgets (apply to every asset below)
- Textures: 256 x 256 for single glows, rings and icons, 512 x 512 for flipbooks (4 x 4 or 8 x 8 cells), PNG with alpha, no pre-multiplied fringes, under 400 KB each. One shared sheet per effect type, tinted at runtime, rather than 7 coloured copies (Aurora is the exception).
- Particles per dino: at most 24 alive at a time on desktop, 12 on phone (half rate); at most 4 emitters per dino. Existing mist rate is 4 per second per emitter and must not grow.
- Parts per dino effect: at most 6 (anchor, up to 4 floating details, 1 light). No Neon on dino bodies; glow comes from Beams/ParticleEmitters/lights.
- Lights: one PointLight per dino, range at most 8 studs, brightness at most 0.8 (use `MutationLook.glow`).
- Reduce Motion: static tint and badge only; no particles, no beams, no looping plates (already enforced for the mist).
- Frame times: updates at 30 Hz or less, no per-frame Instance creation, pool and reuse.
- Readability: effects stay transparent enough that the dino outline, food and controls are clear (about 30% to 60% transparency on large soft sprites).
- Every file gets a line in [docs/77-asset-registry.md](77-asset-registry.md) when added, with the Blender source (.blend) path and render settings.

## Blender sub-task list (for the lead to render later)
Role for all: VFX artist (Claude, Blender via Blender MCP on the owner's PC). Each batch ends with a Studio upload, an asset-registry line and a screenshot on a dino at phone scale.

1. **BD-186 Soft glow plates.** One neutral radial glow (256 px, soft falloff, faint rim light) used behind dinos/eggs and as the badge halo; plus 3 shape variants: round, droplet-shaped (Dewdrop), crescent (Blood Moon). Tinted at runtime.
2. **BD-187 Smoke puff flipbook.** A layered soft smoke puff flipbook (512 px sheet, 4 x 4, 16 frames, white on alpha, gentle swirl, no hard edges) to replace the single mist texture; a second denser variant for ember/seismic dust; a wispy "breath" variant for Frost.
3. **BD-188 Rings.** A soft rim ring (256 px) and a thin "shock" ring for the hatch burst, with a faint inner gradient and slight bevel highlight; one thicker, rounder variant for Seismic.
4. **BD-189 Sparkle and motif sheets.** One 512 px 4 x 4 sheet per motif: droplets (Dewdrop), soft zigzag sparks (Charged), snow crystals (Frost), pebbles and dust (Seismic), embers and flame wisps (Ember), ribbon wisps in the aurora colours (Aurora, coloured), crimson motes and crescent shimmer (Blood Moon). Each has 8 to 16 frames or variants of one rounded shape.
5. **BD-190 Mutation badge icons.** Seven 128 px icons (drop, bolt, snowflake, pebble, flame, ribbon wave, moon), friendly low-poly look, readable at 64 px, for the Eggs, My dinos and hatch badges (replaces the plain colour dot used now).
6. Follow-up (engineering, after the renders): wire the assets into `MutationEffects`, previews and the hatch reveal; add a verifier that checks the texture IDs, sizes and particle caps (extend `tools/verify_mutation_look.py`). Not a separate Blender task.

## Open questions for the owner
- Should the mutation badge show the name as well as the colour on small cards, or colour/icon only? (children: short text)
- Aurora and Blood Moon are the top-rarity events; should they get a richer hatch burst than Dewdrop (docs/88: rarity expressed by more sparkle, not loudness)?
- Sounds for mutation reveals are a separate brief (docs/62, docs/63); nothing here is audio.
