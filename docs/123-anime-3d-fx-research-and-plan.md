# 123 Anime-style 3D FX: technique catalogue and phased plan (BD-161, 2026-10-16)

Status: RESEARCH + PLAN, docs only. Builds on [93 anime FX direction](93-anime-fx-direction.md) (what anime does and the layer recipes, already implemented) and adds what 93 lacks: a Roblox technique catalogue with phone cost, a technique-per-effect mapping, a prioritised asset list and phases. Labels: **CURRENT** (in code today), **PROPOSED**, **PROVISIONAL** (numbers need a real-phone check). Honest scope: the costs below are craft knowledge of the Roblox engine, not measurements; the first task (BD-429) measures them.

Guard rails: vibe words polished, satisfying, calm, bubbly, friendly, vibrant ([114](114-handbook.md) s0); low-poly matte dinos (glow lives in particles, beams and lights, never on the dino); kids' audience; every effect has Full / Lite / Off (`EffectsLod`: Full range 25 studs, cull 180/80/60, max dinos 12/6/4; Off keeps only the mutation cue) and a Reduce Motion variant; **no code-drawn final art**: textures are Blender renders or owner ChatGPT images ([AGENTS.md](../AGENTS.md), [83](83-playtest-asset-list.md)).

## 1. Technique catalogue

Cost scale on a mid phone (about a 2019 Android): **XS** negligible, **S** fine in dozens, **M** budget a few at a time, **L** one or two only.

| # | Technique | Good for | Phone cost | Notes and limits | Lite / Off |
|---|---|---|---|---|---|
| T1 | **ParticleEmitter, plain sprite** (soft dot, spark) | motes, sparkles, droplets | XS-S (about 10-30 live particles) | Cheapest FX; cost is overdraw from big soft sprites, not count. Keep sprites small, `LightEmission` low. | rate x0.6 / mutation cue only |
| T2 | **Flipbook ParticleEmitter** (`FlipbookLayout` Grid4x4 or 8x8, Loop / OneShot / PingPong / Random) | smoke puffs, paint splash, shell burst, flame tongues | S-M | One texture (<= 1024 px, 4x4 of 256) animates by frame, so detail costs memory not CPU. Big translucent overlapping cards are the overdraw hot spot: cap size and peak opacity (93 s3: smoke <= 50%). | fewer particles, smaller / skip |
| T3 | **Beam** (curved, texture scroll via `TextureSpeed`, `Segments`) | aura ribbons, orbit rings, rising spirals, lava crust flow | S per beam (Segments 6-10) | Needs two Attachments; curve with `CurveSize0/1`; `FaceCamera` for flat ribbons. Cost rises with Segments and screen area; 3-4 beams per dino is the practical cap. | 1-2 beams / none |
| T4 | **Trail** (Attachment pair, `Lifetime`, `WidthScale`, `Transparency` sequence) | speed trails behind running dinos | S | Texture along length (`TextureMode`); long lifetimes plus several per dino add up. | 1 ribbon / none |
| T5 | **Mesh FX with scrolling texture** (cone, ring, shell, dome mesh + `TextureOffset` / `Transparency` tween) | shock dome, light shaft, aura shell | M | A real 3D mesh gives the anime "volume" and depth from any angle. Cost = triangles (keep < 200) + translucent overdraw; tween from one shared client loop, never per-frame Instance creation. Needs Blender-modelled meshes (not code-drawn). | static or drop |
| T6 | **Highlight** (`FillColor`, `OutlineColor`, DepthMode) | rim light, egg / pickup emphasis | M-L (engine cap 31 active per place; each adds a pass) | Best "anime rim" per cost but capped. Use on the local dino and the hatch egg only, never on every player. | off for others |
| T7 | **PointLight / SurfaceLight** | breathing glow, lamp pools | S, L on many | Keep `Shadows` false, Range <= 10, one per effect (93 s1). | brightness only / none |
| T8 | **UI gradient and image FX** (`UIGradient` with animated `Offset` / `Rotation`, `UIStroke`, ImageLabel sheets, ring / ray images) | hatch screen glow, rarity banners, counters | XS-S | Cheapest place to be fancy; the hatch already lives here. Use stroke + gradient on few elements. | static |
| T9 | **Emissive surface** (Neon / emissive `SurfaceAppearance`, Decal) | lava crust, crystals, mutation sheen on eggs | XS-S | Nearly free; use instead of a light for static glow. | same |
| T10 | **Post effects** (ColorCorrection, Bloom, Atmosphere; DepthOfField) | weather grade, rare-hatch "moment" | M-L (full screen) | Tween the existing grade, add no passes; small Bloom radius; skip DepthOfField on phones. Never a white flash (calm rule). | half strength / off |
| T11 | **Tween-driven scale / squash / rotate of 3D parts** | egg squash, aura breathing, orbit | XS | CPU only; one shared Heartbeat loop. | static |

Cross-cutting rules: (1) one driver loop per system, not one per effect; (2) pool and reuse emitters (toggle `Enabled` / `Emit`) instead of create and destroy; (3) add global live-FX ceilings to `EffectsLod` (beams, flipbook particles, meshes, Highlights); (4) every texture is white on alpha and tinted at runtime from `FxRecipes` / `MutationLook`, so one render serves every colour; (5) prefer flipbooks over more emitters; (6) a row only moves to Review / test with a phone-viewport Studio check.

## 2. Which technique for which effect

| Effect | CURRENT | PROPOSED upgrade (technique) | Full / Lite / Off |
|---|---|---|---|
| **Hatch v1/v2 build-up and burst** ([118](118-hatch-redesign.md)) | UI image tween, emitters, sounds | T8 gradient sheen on the egg and a rarity ring; T2 flipbooks for paint crown / drips / shell burst (118 C1-C4); T5 one soft **light shaft cone** behind the egg for Epic and up; T11 squash | Full all; Lite no shaft, fewer particles; Off plays the egg without particles |
| **Mutation reveal burst and calm loop** (BD-162) | emitters, motif sheets, orbit ring | motif flipbooks per mutation (T2, BD-189); T5 aura **shell** at the reveal; T6 rim Highlight on the revealed dino for 1.5 s only | mutation cue always kept in Off |
| **Rare / Legendary hatch and server announce** (BD-428) | banner, sound | T8 gradient banner sweep, T2 star-pop flipbook, T10 gentle grade nudge (no flash) | Lite: banner only |
| **Auras** | rim PointLight, motes, smoke, 3 orbit beams, ripple | keep T3 beams (rising spirals); swap the smoke emitter for a T2 flipbook; optional T5 shell (Epic+); T6 only on own dino | layer counts per 93 s2 (Lite 2 layers) |
| **Trails** | ribbon Trail, sparkles, speed-line ribbons | T4 with the shared `ribbon-soft` render (BD-178), T2 star pop at start; at most 2 trails per dino at Full | Lite 1 ribbon; Off none |
| **Weather** ([84](84-weather-events-v2.md)) | grade, fog, particle fields, soft beds | keep T1 fields; T2 flipbooks for lightning glow and aurora (BD-189 ribbons); T10 grade only; T5 sky dome for Aurora; none of it inside the cave | half-strength grade, no particles under Reduce Motion |
| **Cave lava** ([104](104-cave-hub-design.md)) | falls sheet layers, forge pulse | T3 / T9 **scrolling lava crust texture** on the existing mesh (BD-385 asset), emissive crust, T1 rare embers; scenic only, no light cost | Lite static texture; Reduce Motion stops the scroll |
| **Pickups, crystals, shop sparkle** | emitters | T9 emissive + T1 twinkle, amber only ([114](114-handbook.md) 5.3) | Off: no twinkle |
| **UI reveal banners, fusion wheel** | UI tweens | T8 only | static |

## 3. Prioritised asset list (Blender renders or models, white on alpha, tinted at runtime)

Most flat textures are already tracked as BD-186..190 (glow plates, smoke, rings, motifs, badges) and partly exist in fx-v2 / fx-v3; they are not duplicated here. The list below is what this plan adds, by payoff per effort. Every row is also in [120](120-pending-owner-uploads-checklist.md) section 2; each finished asset gets a [77](77-asset-registry.md) line. Maker: Claude via Blender MCP unless noted; the owner may swap in ChatGPT sheets for textures.

| P | Asset | Used by (technique) | Spec |
|---|---|---|---|
| P0 | **Soft flame-tongue flipbook** (aura base, calm, no flicker) | auras (T2) | 4x4 of 256 = 1024, under 400 KB |
| P0 | **Star pop flipbook** (4-point twinkle, 8 frames) | rare hatch, trail start, equip pop (T2) | 4x4 of 256 |
| P0 | **Soft shock dome mesh + gradient texture** (low-poly half sphere, about 120 tris) | equip pop, landing, rare hatch (T5) | FBX + 512 px white on alpha; uploaded in Studio, bound by the lead |
| P1 | **Light shaft cone mesh + vertical gradient** | hatch Epic+ reveal, cave shafts (T5) | about 80 tris, 256x512 gradient |
| P1 | **Aura shell mesh** (slightly inflated low-poly shell, soft edge texture) | Epic+ auras, mutation reveal (T5) | about 150 tris, 512 px |
| P1 | **Lava crust tile** (existing 120 BD-385 row, no duplicate) | cave lava (T3 / T9) | 1024 tileable |
| P1 | **Speed-line streak sheet** (4 soft streaks) | trails Epic+ (T4 / T3) | 512x512 |
| P2 | **Rainbow-shift gradient strip** (grey ramp so runtime hue works) | Legendary / Mythic trails, banners (T4 / T8) | 1024x64 |
| P2 | **Soft vignette rim ring (UI)** | hatch and banner glow (T8) | 1024 ring |

**Status 2026-10-17 (BD-430, BD-431):** the P0 and P1 assets are rendered (Review / test, not uploaded): `flameTongue`, `starPop` (512 px, 4x4 of 128, not the 1024 / 256 sizes planned above), `domeGradient` (512), `shaftGradient` (256x512), `shellEdge` (512), `speedStreaks` (512), and the three meshes `shock-dome` (112 tris), `shaft-cone` (80), `aura-shell` (144) in `assets/blender/fx/`; see docs/77 `fx_*` and `fx_mesh_*` lines and the contact sheet in `docs/evidence/2026-10-17-vfx/`. Readers wired behind empty slots (empty id = today's exact look): hatch light shaft (2D gradient, `HatchFx`), star pop on the own rare banner (`RareHatchClient`), aura and mutation shell (`FxRig`). Not read yet: `flameTongue` (BD-432), `domeGradient` + `shock_dome_mesh` (BD-433 equip pop), `speedStreaks` (BD-432), `shaft_cone_mesh` (BD-434 cave shafts). The hatch panel is 2D, so the hatch shaft uses the gradient texture, not the cone mesh; the banner sweep is not built.

## 4. Phased plan

| Phase | Goal | Content | Exit evidence |
|---|---|---|---|
| 0 Measure | know real costs | BD-429: Studio test place with a stress rig per technique T1-T6 on desktop and a phone profile; particles, draw calls, frame time; fill the cost column with numbers; set `EffectsLod` ceilings | numbers table here, desktop + phone screenshots |
| 1 Assets | unblock the rest | BD-430 P0 renders, BD-431 P1 renders, plus the already planned BD-186..190 | docs/77 lines, uploaded ids, owner picks |
| 2 Aura and trail v4 | anime depth on cosmetics | BD-432: flipbook smoke, optional shell, shared ribbon, global FX budget, `verify_fx` update | Studio desktop + phone; Lite / Off / Reduce Motion checked |
| 3 Moments | hatch, mutation, rare reveal | BD-433: hatch shaft and star pop, mutation shell + rim Highlight, rare banner sweep | hatch flow video, no frame drop on phone |
| 4 World | weather and cave | BD-434: lava crust scroll, aurora dome, amber emissive crystals, weather flipbooks | cave + weather checks (`verify_cave_weather`) |
| 5 Polish | consistency and safety | BD-435: calm audit (no strobing, readability 25-30 studs), photosensitivity check, cross-links to 93 / 114 | owner review |

Phases 0 and 1 run in parallel; 2-4 each ship behind the existing Effects setting and do not change shipped defaults until the owner approves. Nothing here touches economy, saves or Robux.

## 5. Open owner questions
1. OWNER QUESTION: are FX meshes (shock dome, shaft cone, shell) welcome, since they are models rather than flat textures? Proposed yes: modelled in Blender, within the art rule.
2. OWNER QUESTION: may the local dino get one Highlight rim during reveals (engine cap 31)? Proposed yes.
3. OWNER QUESTION: what is the lowest phone to support? Until answered BD-429 uses a mid Android profile.

## Handbook check
- 114 s0: all proposals read as polished, satisfying, calm, bubbly, friendly, vibrant; no flashes, strobing or screen shake.
- 114 s4.1 and AGENTS.md art rule: every new texture and mesh is a Blender render or model or an owner ChatGPT image, never code-drawn; rows added to 120, registry lines required on delivery.
- 114 s4.5 and 87: every effect keeps a Reduce Motion variant and Full / Lite / Off.
- 114 s5.3: crystals stay amber; cave lava is scenic only; weather never inside the cave.
- Consistent with 93 (layer recipes kept) and 118 (hatch v2 assets); BD-186..190 referenced, not duplicated.
