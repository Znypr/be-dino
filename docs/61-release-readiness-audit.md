# 61 Release-readiness audit (private playtest)

**2026-10-14, read-only audit of main @ bbfd2a5.** No gameplay code changed. No Studio, device or Blender checks were run here. "Fact" = seen in the repo. "Guess" = inference to verify live. Owner guidance: a cohesive, polished game beats exact numbers.

## (a) One-page summary

| # | Question | Verdict | Reason |
|---|---|---|---|
| 1 | Design language fits? | Yellow | Fact: one v2 kit (buttons, headers, cards, tiles, 4 weather icons, 9 uploaded nav icons) is coherent, but newer features have no art. |
| 2 | 3D sufficient? | Yellow | Fact: 17 authored creature files plus egg are in game; BD-061 Gold/Emerald/Diamond finishes exist only in Blender/docs; in game, tiers use plain Metal/Glass material swaps. |
| 3 | Sounds? | Red | Fact: only 2 hatch sound IDs and a SOUND ON/OFF toggle; nothing else makes noise. |
| 4 | Minimal enhancements? | Yellow | A 12-15 sound pack plus about 8 cheap juice items (section b) give the most feel for the least effort; all are S/M. |
| 5 | Game makes sense? | Yellow | Fact: a one-time "Welcome" tutorial exists. Guess: no persistent goal line, so minutes 10 and 60 lack direction. |
| 6 | Looks good? | Yellow | Guess: dinos and UI look decent. Fact: world is Legacy primitive props (BiomeKit off); no icons for potions/nests/skip/tiers. |
| 7 | Feels good / not laggy? | Yellow | Unmeasured. Fact: no phone frame-time evidence exists (doc 55 says so). Known heavy spots in c5. |
| 8 | Someone truly engaged? | Yellow | Many hooks (hatch, Shiny, fusion, weather) but weak goal visibility, no collection-completion or daily pull. |

Nothing is Green because nothing is measured on a phone. Audio is Red because the game is silent.

## (b) Ranked top-15 polish tasks

| Rank | Task | Owner | Size | Blocks playtest? |
|---|---|---|---|---|
| 1 | Phone measurement pass (checklist in d); fix the worst offender | code | M | Y |
| 2 | Safe `Sfx` helper: no-op on empty IDs, pcall, one table of all sounds, honors the SOUND toggle | code | S | Y |
| 3 | Generate and upload the 12-15 SFX pack (c3); fill IDs | audio | M | N (game stays silent) |
| 4 | Persistent "next goal" HUD line (e.g. "Gold: 31/50 Base", level XP) | code+UI | M | Y |
| 5 | Hatch juice: flash on crack, rarity-colored burst, Shiny/BIG banner, tiny capped shake | code | S | N |
| 6 | Progress bars for Gold/Emerald/Diamond on Dinos and Fusion screens (`progress-track` art exists) | UI+code | M | N |
| 7 | Make Gold/Emerald/Diamond look distinct in game (wire BD-061 or a cheap sheen/neon approximation) | 3D | L | N |
| 8 | Icons in v2 style: potions, nest, skip-reveal, tier badges, crystal, level | UI | M | N |
| 9 | World: enable BiomeKit only with uploaded MeshParts; else keep Legacy and add 2-3 landmarks | 3D | L | N |
| 10 | Food pickup: number pop, pickup sound, small scale pulse | code | S | N |
| 11 | Button press feedback (scale 0.96 + click sound) in the shared `button()` helper | code | S | N |
| 12 | Leap: FOV kick +6 deg for 0.2 s; run start/end stinger | code | S | N |
| 13 | Toast polish: icon by type, stack max 3; weather-start banner with weather icon | code+UI | S | N |
| 14 | Collection completion line ("x/y species") and "NEW" badge on first-time dinos | code | S | N |
| 15 | Audit that new shake/FOV/flash obey `Theme.MotionEnabled` | code | S | N |

Optional later: daily streak, event countdown calendar.

## (c) Per-role details

### c1 UI art director
Fact, existing art:
- `resources/ui/v2/components`: 37 files (blue/dark/gold/green/purple/red buttons and headers, common/rare/legendary cards, popup body, progress-track, reward-burst, close). `resources/ui/v2/scalable`: 43 files. `resources/ui/icons`: 14 SVG+PNG pairs (amber, bolt, close, dinos, egg, gift, home, leaf, lock, play, settings, shop, snow, trophy).
- `src/shared/UIIconAssets.luau`: 8-9 uploaded IDs (trophy, dinos, egg, home, fusion, shield, amber, leap). Also `IconVectors`, `EventIconVectors`, `IconTiles`, `NavigationArtwork`, `TrailArtwork`, `ArtworkAssets` (3 aura rings, 2 potion bases, gold and diamond mutation badges, catches mark).
- v2 icons: weather clear/rain/thunder/blizzard, leap, premium egg (normal, cracks), egg-green, egg-nest.
- Language: Fact, a consistent card/header/button vocabulary with colored headers. Guess: vector icons and raster PNG icons may differ in stroke weight; compare them side by side.

Gaps (no matching art found):
- Emerald tile/badge (only a green color constant in `FusionWidgets.luau:94`).
- Potion item art beyond two bases.
- Nest HUD icon (sprite exists, not in `UIIconAssets`).
- Skip-reveal setting, crystal currency icon, level badge.
- Volcano/quake weather icons (`WeatherVisuals.client.luau:45` lists them; only 4 icon files exist).
- Shiny/BIG banners and event-mutation icons.
- Check all 10 trails have `TrailArtwork` entries.

### c2 3D/tech artist
Fact, in game:
- 17 authored creature files in `src/shared/CreatureData` plus the egg.
- Metal/Glass material swap for gold/diamond (`DinosaurVisual.luau:109,141`).
- Shiny glints, mutation smoke texture, auras (`CosmeticEffects.luau`), trails.

Fact, count mismatch: the brief says 22 species; only 17 creature data files exist. Owner to confirm (could include legacy primitive models such as `resources/models/ankylosaurus.obj`).

Fact, Blender/docs only:
- BD-061 finishes: `assets/blender/fusion` (8 files), doc 48.
- BD-049/050 world kit: `resources/models/world` (82 files), `assets/blender/world/fbx` (41 FBX).
- `Config.WorldArtMode="Legacy"` and `FoodArtMode="Legacy"`, so the kit is off. The native kit fallback is about 18k anchored parts. Uploaded MeshParts (owner task) are the phone path.

Missing for a convincing first impression: visibly distinct tier finishes, a landmark at spawn, event-mutation looks readable at distance. Guess: authored creatures and primitive world props may clash; check in a screenshot.

### c3 Audio
Fact: the only sound code is `HatchPresentation.luau:13-14,65-70` (two stock IDs: crunch and chime). A `HatchSoundEnabled` toggle exists (`Bootstrap.client.luau:700`). No ambient, music or UI sounds.

Minimal pack (13, up to 15):
1. ui_click, 2. ui_open, 3. pickup_food, 4. pickup_egg, 5. hatch_crack (reuse with 3 pitches), 6. reveal_common, 7. stinger_rare_legendary, 8. stinger_shiny_big, 9. run_start, 10. run_end, 11. shop_buy, 12. shop_refresh, 13. weather_start. Optional: 14. level_up, 15. fusion_reveal.

How to get them (feasibility is a Guess until tried):
- A, preferred: original synthesis. A Python script (numpy plus stdlib `wave`) writes sine/triangle blips with an ADSR envelope, noise bursts for cracks, short arpeggios for stingers. Keep each under 1.5 s, 44.1 kHz mono 16-bit WAV. Works offline, no license risk. The owner uploads each file in Creator Hub (moderation delay applies). Script would go in `tools/` (not written here).
- B: Creator Store free audio. Fast, but license and availability vary per asset; check each one. Do not invent IDs.
- Safe fallback code: `Sfx.play(name)` silently returns when the ID is `""`, wraps in pcall, honors the toggle. Ship this first so empty IDs never error.

### c4 UX / game design
Fact: tutorial modal once per join (`Bootstrap.client.luau:721,995`), HOW TO PLAY in settings, HUD, DINOS, CHESTS, nests (BD-044), Fusion Menu (BD-065), shops.
- Minute 1 (Guess): tutorial, run for food, catch an egg, hatch. Verify the first egg arrives within about 60 s.
- Minute 10 (Guess): first weather and restock happen but no stated goal.
- Minute 60 (Guess): Gold needs 50 Base with no visible progress (task 6).
- Possible dead ends to confirm live: Fusion Menu with too few duplicates; shop with 0 crystals and no hint where crystals come from; unexplained skip settings.
- Hooks present: Shiny/BIG, mutations, weather, leaderboards, levels, trails. Missing: goal line, collection completion, NEW badges, daily streak (optional).
- Event cadence is fine (reveals seconds, runs minutes, shop 2 min, weather 10 min). Surface it with small countdowns for the next restock and weather.

### c5 Performance / feel
Fact = file exists; impact is a Guess until measured.
- World art: Legacy props and the BiomeKit native fallback are both about 18k anchored noncolliding parts (doc 56). Mitigate: MeshParts, StreamingEnabled, lower `WorldArtDensity`.
- Per-frame scripts: `Bootstrap.client.luau:955`, `CosmeticVisuals.client.luau:18` (all players' aura/trail/mutation), `ResourceVisuals.client.luau:142`, `WeatherVisuals.client.luau:38`, `MutationEffects.luau:80` (already 30 Hz), `DinosaurPreview.luau:75`, `PreviewCamera.luau:44` (RenderStepped). Mitigate: distance-cull cosmetics, throttle to 15-30 Hz, pause hidden previews.
- ViewportFrame previews: doc 38 cut collection descendants 3752 to 1974. Cap visible previews, lazy-load.
- 400-egg reveals: `HatchPresentation.luau` fragments plus flight Heartbeat; `RevealSkip.luau` exists. Cap simultaneous particles; make bulk reveals skip-by-default.
- Remote spam: validation exists (docs 14, 22). Confirm rate limits on catch, claim, leap.
- Cheap mitigations: lower particle rates on mobile, low-end default `MotionEnabled=false`, fewer lights.

Targets: 60 fps desktop; 30+ fps (under 33 ms frames) on a mid Android with 8-12 players; no spike over 100 ms during hatch; memory under about 1 GB on mobile.

### c6 Juice quick wins
1. Sfx on buttons and pickups (tasks 2, 10, 11). 2. Hatch flash plus rarity burst (5). 3. Number pops. 4. Rarity glow on dino cards (`card-rare/legendary` art exists). 5. Leap FOV +6 deg. 6. Shake capped at 4 px / 0.15 s, only for legendary/Shiny/BIG, never in bulk reveals. 7. Toast with icon and stacking. 8. Route everything through `Theme.MotionEnabled` (reduced-motion option already exists).

## (d) Live Studio checklist (screenshots)
1. Spawn view on desktop and phone-landscape emulator (HUD fits, world reads).
2. Tutorial modal, then HUD after closing: is a goal visible?
3. First food pickup and first egg catch.
4. Hatch reveal: crack frames, 1 s reveal, Shiny and BIG.
5. Dinos collection with 20+ entries (preview load, scroll fps).
6. Fusion Menu: Base to Gold, Emerald, Diamond, plus result screen.
7. Shop tabs: auras, trails, potions (restock timer, empty states, missing icons).
8. Nest claim and skip settings.
9. Weather start (volcano/quake icons, visuals).
10. Gold/Emerald/Diamond dinos side by side in the world.
11. Confirm species count (22 vs 17).
12. 400-egg reveal; an 8-12 player scene.
13. Perf: Developer Console (F9) memory/network; MicroProfiler (Ctrl+F6) during hatch, weather, run start; Stats frame time. Android: 5-minute recording, note fps drops and heat.
14. Output window clean with empty sound IDs.
