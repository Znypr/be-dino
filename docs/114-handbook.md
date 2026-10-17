# 114 Be Dino! Handbook (single fact-check reference)

Written 2026-10-16 (branch claude/handbook). **Purpose:** one place the lead and every subagent check a PR against, so the owner only steers. It does not replace the specs; each line cites its source. Where sources disagree see [116 conflicts](116-handbook-conflicts.md); dated owner decisions are in [115 decisions log](115-decisions-log.md). Labels: **OWNER** (owner said it), **LEAD** (lead decision, owner may overrule), **CODE** (what the source does today), **PROVISIONAL** (number not final). The newest owner decision wins; code that contradicts the handbook is a bug (kanban BD-401..BD-408).

## 0. The vibe words (owner 2026-10-16): how to read them
The owner's guiding adjectives are **polished, satisfying, calm, bubbly, friendly, vibrant** (calm, bubbly, friendly, a little magical in [87](87-vision-and-feel-guide.md); polished, satisfying and vibrant added 2026-10-16). They describe the OVERALL VIBE of every facet: visual design, sound, animation, looks, feel, transitions, copy. They are NOT literal per-place rules: "bright" or "calm" must never be read as "the cave must be bright" or "weather must be quiet everywhere". Each facet interprets them in its own way, and a decision is judged by whether it would feel at home with these words, not by matching one word literally:
- **Polished**: nothing looks code-generated or unfinished: no primitive/elliptical placeholder shapes, no clipped text, no overlap, no floating or sunk assets, consistent materials and lighting, tidy edges, nothing flickers or pops.
- **Satisfying**: every action has clear, quick, juicy feedback and a payoff: soft sounds, squash/stretch, small particle bursts, counters that pop, rewards that land with a moment, smooth easing, no dead ends.
- **Calm**: no stress, no harsh or sharp sounds, no strobing or violent shake, readable at a glance, gentle failure; calm is about how it feels, not about being dim or empty (a dramatic weather event can still feel calm when it is soft and readable).
- **Bubbly**: round, chunky, soft shapes, bouncy motion, playful rhythm, cute faces; sparkles and bubbles, never aggressive or edgy.
- **Friendly**: welcoming copy in kid words, warm colours and light, nothing scary or gory, helpful hints, no pressure timers.
- **Vibrant**: rich, saturated, harmonious colours that pop within a palette; even a dim lamp-lit cave stays colourful (warm lamps, glowing crystals, coloured props), never grey or muddy.
**Use:** cross-reference new tasks and decisions vaguely against these words and against the relevant handbook section (palette, lighting, sound, asset bar); read only what the task touches, not the whole stack. The lead uses the handbook for quality and vision assessment of every merge and updates it when the owner adds or changes something; open questions to narrow it down are collected in docs/116 as OWNER QUESTIONs and asked over time.

## 1. Vision and pillars
- Roblox dinosaur survival, growth, collection and hatching game: eat, grow, avoid/fight predators, settle the run, then watch the run's eggs hatch one at a time ([AGENTS.md](../AGENTS.md) Game vision; [09](09-reward-economy.md)).
- Feeling in one line: **calm, bubbly, friendly, a little magical** ([87](87-vision-and-feel-guide.md), owner 2026-10-15).
- Five pillars ([87](87-vision-and-feel-guide.md)): cozy before flashy; bubbly and playful; readable at a glance; rewarding never harsh; handmade and consistent.
- Keep distinct: food/growth points, catches (= run eggs), hatched dinosaurs, account XP, crystals, bonus nests ([AGENTS.md](../AGENTS.md)).

### 1.1 Vision answers (OWNER 2026-10-16, see [115](115-decisions-log.md))
- **Hunting is each player's own choice, food alone must be enough.** The core loop is food, eggs, growing. Fighting or hunting other players stays ON for everyone; there is NO Peaceful opt-out (the 2026-10-16 "Peaceful must be easy to find" reading was a misread, ~~BD-421~~ SUPERSEDED, docs/115 OWNER CORRECTION). Instead, a player who only eats food must get enough growth, eggs and crystals, so nobody has to rely on eating others (balance audit and proposal: [131](131-food-only-progression-audit.md), BD-439).

### 1.1 Food-only progression (owner correction 2026-10-16)
See [131](131-food-only-progression-audit.md): finding today is that eating a player pays +1 run egg plus growth, about 42 food-equivalents of egg value per kill, which is outsized next to food. OWNER decision 2026-10-16 (option B): a player kill now gives 0.25 run egg, at most 3 per run; growth and NPC kills unchanged (BD-439, in Review / test).
- **Session shape:** short runs of about 5 minutes, a hatch party after each, several runs per session (BD-426).
- **Long-term goal:** an equal mix of completing the collection, perfecting one favourite dino to Diamond, and playing new dinos with a different class feel (BD-427).
- **Robux line:** looks plus convenience (skins, cosmetics, potions, extra nest spots), never exclusive power; flags off until policy is tested (BD-425).
- **Run end:** eggs caught are ALWAYS kept, also when eaten; being eaten only ends the run early (code already matches, BD-422).
- **Cave hub mood:** cosy home base: warm, safe, lamp-lit den to relax, shop and show off dinos (matches section 3 and 6).
- **Play as ANY owned dino**, each with its own class feel (BD-423).
- **Rare hatch** (Legendary, Shiny, event mutation): huge celebration with screen-wide fanfare, confetti, special sound and a server announcement (BD-424; none of the announcement exists today).

## 2. Audience and tone
- Audience: **children (target ages 7-10, LEAD reading of "children are the audience, parents nearby")** ([87](87-vision-and-feel-guide.md) UI and copy; [72](72-ui-copy-and-asset-standards.md); [86](86-monetization-ideas.md)). The exact age band 7-10 is not written in any doc (conflict C-20).
- Tone: short warm plain words, one fact per line, no jargon, no fear copy, no countdown panic, errors say what to do next ([72](72-ui-copy-and-asset-standards.md), [87](87-vision-and-feel-guide.md)).
- Copy rules: "5 min", "2 h", "Back in 40 s"; never "5m 0s"; "Speed +20%" never "1.2x"; "1 left", "Sold out"; hidden thresholds stay hidden ([72](72-ui-copy-and-asset-standards.md)). Menu names say what the player gets ("Shop") ([87](87-vision-and-feel-guide.md)).

## 3. Feelings per moment
| Moment | Target feeling | Rules | Source |
|---|---|---|---|
| Run | in control, curious, never pressured | responsive but grounded movement; smooth camera; no panic copy; first egg quickly (about 60 s target) | [87](87-vision-and-feel-guide.md), kanban BD-366 |
| Hatch | a moment of discovery, warm | one egg at a time, rarity shown by richer harmony not loudness, always skippable, Cracked failure funny/gentle | [87](87-vision-and-feel-guide.md), [86](86-hatch-sequence.md), BD-397 |
| Shop | toy-like, clear, never pushed | tiles/cards not lists, plain words, odds shown for random items | [87](87-vision-and-feel-guide.md), [43](43-player-access-and-paid-random-policy.md) |
| Cave (hub) | cosy, lamp-lit, safe | DIM warm cave lit by lamps and light shafts, readable dino, weather never inside, lava scenic only | OWNER 2026-10-16 ([115](115-decisions-log.md)), [104](104-cave-hub-design.md) |
| Weather | dramatic to look at, calm to be inside | strong colour, big sky, soft audio beds, about 25-30 studs readable around the dino | [87](87-vision-and-feel-guide.md), [84](84-weather-events-v2.md) |
| Defeat | gentle, funny | short (about 1.5 s) soft animation, no gore, keeps everything earned, simple fade under Reduce Motion | [87](87-vision-and-feel-guide.md), [97](97-dino-skins.md), [101](101-hp-combat-classes-animations.md) s16 |
| Fusion | earned, ceremonial but calm | precommitted server result, staged wheel reveal, itemised irreversible-loss warning first | [46](46-pattern-fusion-dino-identity-and-cosmetic-progression.md), [96](96-fusion-menu-v2.md) |

## 4. Design language
### 4.1 Shapes
Friendly **low-poly** with soft rounded forms: chunky, few large flat facets, flat-shaded, clean colour ([87](87-vision-and-feel-guide.md), [97](97-dino-skins.md), [100](100-species-visual-reference.md) prompts). **No ellipses, primitive stacks or code-drawn "art" as final** ([98](98-no-more-cubes.md), AGENTS.md art rule, BD-206, BD-397). Dinos are split into body parts for animation ([97](97-dino-skins.md)).
### 4.2 Eyes
Solid glossy black with a white highlight dot, not hollow, on every dino ([100](100-species-visual-reference.md) prompts). Eye and claw parts are untextured and never get a tier gloss ([105](105-lowpoly-patterns-and-tiers.md) line 37). See conflict C-13.
### 4.3 Materials
Dinos are **matte** (Plastic, reflectance 0, no Neon/Metal/Glass). Gloss/metal only on fused tiers: Gold = Metal 0.14, Emerald = Glass 0.10, Diamond = Glass 0.22, cap 0.3 ([87](87-vision-and-feel-guide.md), [105](105-lowpoly-patterns-and-tiers.md), `LowPolyTier`). Mutation tints never exceed pull 0.35 and never touch fused tiers (`MutationLook.luau`). Conditions are egg-only; dinos never show one ([87](87-vision-and-feel-guide.md), BD-181).
### 4.4 Text and outline
Light fill + dark stroke 2-3 px on the world/HUD; dark fill with no stroke on light panels; contrast fill vs stroke >= 4.5:1 (`TextStyle`, BD-390, [72](72-ui-copy-and-asset-standards.md)). Buttons use FredokaOne (`UITheme.decorate`). **Minimum text 14 px on screen, minimum button/target 44 px** (`PhoneScale.MinText = 14`, `MinButton`; BD-333, BD-376). Icons readable at 64 px ([87](87-vision-and-feel-guide.md)). UI icons: chunky outline, saturated palette, rounded forms, same light direction ([72](72-ui-copy-and-asset-standards.md)).
### 4.5 Motion language
Ease in/out, slight squash and stretch, soft overshoot, nothing snaps; reveals take their time but are skippable; gentle camera zoom/shake scaled by intent ([87](87-vision-and-feel-guide.md)). UI tween default Quad Out (`UITheme.animate`); button hover 1.035, press 0.96. **Reduce Motion:** `Theme.MotionEnabled=false` applies goals instantly; weather grade at half strength, no particles or shake ([84](84-weather-events-v2.md)); cave dust motes off, lava scroll stops, forge pulse static ([104](104-cave-hub-design.md)); defeat = simple fade ([97](97-dino-skins.md)); glow guide static (BD-396). Every effect needs a Reduce Motion variant ([87](87-vision-and-feel-guide.md), [93](93-anime-fx-direction.md)).

## 5. Colour palette (hex; where it lives)
Rules: saturated but harmonious, no muddy greys, no single-colour walls ([87](87-vision-and-feel-guide.md)). A new colour family needs a registry line ([77](77-asset-registry.md)).
### 5.1 UI (`src/shared/UITheme.luau` `Theme.Colors`)
panel #2A2835 (42,40,53); card #3D3A49 (61,58,73); outline/dark text #0D0F14 (13,15,20); text #FFFFFF; accent green #5DED1F (93,237,31); **gold/amber #FFD22B (255,210,43)**; blue #2ECEFF (46,206,255); purple #C256FF (194,86,255); red #F73930 (247,57,48).
### 5.2 Rarity (one colour everywhere: species, potions, trails, auras; `Theme.RarityColors`)
Common #808E9E (128,142,158) grey; Uncommon #5DED1F green; Rare #2ECEFF blue; Epic #C256FF purple; Legendary #FFD22B gold; Mythic #F73930 red. Tier chances 80/16/3.2/0.64/0.128/0.0256% ([88](88-exponential-rarity.md), `RarityCurve.luau`).
### 5.3 Currency: crystals = AMBER / YELLOW everywhere (OWNER 2026-10-16)
Crystal currency art, icons, packs and **shop crystal meshes** are amber/yellow (gold #FFD22B family; Amber egg colour #F1A024 (241,160,36)). Blue-purple crystals (cave `CrystalColor` (196,170,255), lavender/teal inner light) are **decoration only inside the cave, never in a shop or currency context**. Code that violates this: BD-400, BD-401.
### 5.4 Egg colours (`ProgressionConfig.EggColors`)
Cream #F7EAC4 (247,234,196) Common; Blue #2484D3 (36,132,211) Common; Green #1DAF4B (29,175,75) Uncommon; Teal #16AA97 (22,170,151) Rare; Pink #D74893 (215,72,147) Rare; Amber #F1A024 Epic; Purple #9E50CB (158,80,203) Legendary; Red #ED2C21 (237,44,33) Mythic; Black #1D2229 (29,34,41) Mythic.
### 5.5 Conditions (egg only)
Cracked, Dirty, Normal, Rainbow, Astra; stats 0.8 / 0.8 / 1 / 1.2 / 1.8 (`ProgressionConfig.Conditions`). Overlay art is textures with no tint hex in code (`ConditionOverlays.luau`); no condition colour table exists (conflict C-17, BD-406).
### 5.6 Event mutations (`MutationLook.luau`; tint / rim / badge)
Dewdrop #78E2BE / #70F4BF / #55D8B0; Charged #FFE278 / #FFCF48 / #FFDA58; Frost #A0E8FF / #AFEBFF / #87E9FF; Seismic #E2BE82 / #D2AD71 / #DCB473; Ember #FF8C5A / #FF9033 / #FF743E; Aurora #8CFADC / #51E9BB / #70FFCD; Blood Moon #FF7896 / #FA4366 / #FF5580. Mist colours in [92](92-mutation-fx-brief.md).
### 5.7 Auras and trails (`ProgressionConfig`)
Auras: Meadow #62EC70 (98,236,112), Tidal #50D6FF (80,214,255), Royal #B46AFF (180,106,255). Trails: White #F5F7FF, Fern #62EC70, Tidal #50D6FF, Ember #FF743E, Violet #B46AFF, Electric #50F3FF, Frost #87E9FF, Solar #FFD55E, Nova #B46AFF, Astra #70FFCD. FX shadow colour = primary mixed 45% toward navy (28,36,92) ([93](93-anime-fx-direction.md) s3).
### 5.8 Biomes (terrain, `BiomeMap.Colors`)
Grass #84A644 (132,166,68; was #84AA54; BD-460 candidate C, owner pick, for the built-in Grass, see 138); LeafyGrass #58843E (88,132,62; was #3E7C4E, BD-460 no dark teal patches); Mud #5C4C37 (92,76,55); Ground #706442 (112,100,66); Sand #D6BE88 (214,190,136); Sandstone #BA7A50 (186,122,80); Slate #5C666C (92,102,108); Basalt #322F37 (50,47,55); Rock #728589 (114,133,137). Biomes: meadow, fern, conifer, marsh, badlands, volcanic (`BiomeMap.Rock`).
### 5.9 Weather looks (`WeatherLooks.luau`, tint / fog)
Rain #96B6E8 / #78869C; Thunder #A0AEDE / #586084 (violet glow #A08CFF); Blizzard #D6E8FF / #E2EAF6; Volcano #FFE4CD / #965438 (glow #FF8C46); Aurora #B0FFE6 / #28C8AA (glow #3CFFAA); Quake #E8C89C / #C6B092; Blood Moon #FF8C96 / #420E18 (glow #FF2846). Far fog is colour, not a wall ([87](87-vision-and-feel-guide.md)).
### 5.10 Cave (`CaveLightingRules.luau`)
Warm cream shafts #FFECBE (255,236,190); fill lamp #FFD6AA (255,214,170); lava #FF8C46 (255,140,70) (glow layers #FF7828, #FF963C, #FFBE64; the old sheet layers were dropped by #277); crystal light #FFC450 (255,196,80) amber (BD-401; was lavender #C4AAFF); forge #FFBE5A (255,190,90); gate glow #FFD6A0; look: ambient (62,52,44; was (70,62,60) before the BD-296 dim pass #323, owner 'too bright', D25), fog colour (72,56,46), grade tint (255,226,196). Walls: matte Concrete (124,104,86; was (186,170,150) before the BD-296 dim pass #323; Limestone was dropped for its horizontal strata stripes) with cave-only Cobblestone (110,92,76; was (158,142,126)) on the floor (BD-384); the floor must not be hot orange (BD-384).
### 5.11 Classes and HP bar
HP bar fill green above 50%, yellow 25-50%, soft orange below 25%, plus a heart icon (full/half/small) so colour is never the only signal ([101](101-hp-combat-classes-animations.md) line 85). Per-class colours are decided (owner 2026-10-16, 'Nature set'; C-18 / Q2 resolved). One source: `ClassInfo.Colors` (`src/shared/ClassInfo.luau`), used by `ClassBadge` and the class picker line. Hex values are the darkened, white-text-safe versions of the C-18 proposal (white label/icon contrast about 3.7:1 or better, fine for the big bold 1-letter badge; colour is never the only signal, the label and letter always show).

| Class | Name | Hex | RGB |
| --- | --- | --- | --- |
| Ground | green | #2F9E44 | 47,158,68 |
| Fly | sky blue | #1E88E5 | 30,136,229 |
| Water | teal | #0F8F80 | 15,143,128 |
| Armored | amber-brown | #A8643A | 168,100,58 |

Class icon art (docs/120) is drawn on these colours.
### 5.12 Lighting-colour rule
The palette sits under the place's lighting; a shared grade tames pastel props because `MeshPart.Color` is ignored on textured meshes (BD-399). Dino and food stay readable in every place and weather.

## 6. Lighting rules per place
| Place | Rule | Source / code |
|---|---|---|
| Island (default) | bright daylight: ClockTime 14, Brightness 1.8, Ambient (146,155,158), OutdoorAmbient (140,150,153) (`Config.IslandLight`, BD-460: softer contrast, was Brightness 2 / Ambient 130,143,148); **no haze in clear daylight** (owner 2026-10-16: no screenshot may look milky): Atmosphere density .1, haze .3, glare 0, no far blur, no bloom, saturation +0.04, contrast 0 (BD-460: was +0.08 / +0.04), fog colour = sky-horizon blue; desktop fog 400 to 1400, tablet 250 to 700, phone tight (capped by its cull radius 190); the old 374-stud desktop cap was removed (it milked the mid-distance); UI blur only while a modal is open, reset to 0 otherwise; DepthOfField stays at zero intensity | `Bootstrap.server.luau` 22-24, BD-213 |
| Cave hub (Sanctuary) | **DIM, lamp-lit**: warm lamps and ceiling light shafts are the main lights; ambient (62,52,44), Brightness 1.3, exposure -0.6 (BD-296 dim pass #323: measured luminance 0.57 to 0.30, inside the 0.15-0.35 band of 6.1); at most 16 lights, shadows on the 4 strongest; **weather never affects the inside**; assets must look real and grounded in this light | OWNER 2026-10-16; `CaveLightingRules.Look`; BD-398, BD-399 |
| Weather events | per-event grade, haze, soft fog; everything fades to neutral with `1 - Cave.amount()` inside the hall | [84](84-weather-events-v2.md), BD-383, BD-398 |
| Volcanic biome | orange glare, heavy bloom, ash and embers, but soft visibility (no flat red wall) | [84](84-weather-events-v2.md), BD-213 |
| Eggs and dinos in UI | lit warmly on a stage/tile floor, never cubes | [87](87-vision-and-feel-guide.md) |
Open: per-biome daylight rules beyond the island base are not documented (conflict C-9).

### 6.1 Brightness bands and cave stone palette (owner 2026-10-16, confirmed)
- Automatic luminance bands (mean screen luminance 0 = black, 1 = white): **cave 0.15-0.35, island 0.35-0.75**. The quality gates (docs/117, tools/qa/luminance.py) fail outside these bands.
- Cool blue-grey stone is ACCEPTED as cave decoration (depth and contrast); warmth comes from lamps, shafts, amber crystals and warm props. Currency and shop crystals stay amber/yellow (decision 2026-10-16). BD-414/415 are resolved as "accepted, no recolour".

### 6.1b Cave shape and stone (OWNER 2026-10-16, Studio feedback)
The cave must read as a natural cave, not a cube: a central chamber plus 3-5 short winding tunnels and side caves (alcoves) where the stations sit; organic irregular walls and ceiling; gently rolling floor with slight hills and a few steps; stations carved into the rock (counters and shelves are rock ledges in the same stone palette); little decor, growing out of the walls. Stone must look like the cave itself (seamless, same style). The s6.1 brightness band, amber crystals and weather rule stay. Design and numbers: docs/104 s17.

### 6.2 Cave stations: prompt-only opening and every-side signs (OWNER 2026-10-16)
- A shop or station NEVER opens because the player walked near it. Each menu station has a `ProximityPrompt` (big round "Open" button, >= 96 px tap, keyboard **G**, gamepad L1) that appears within 10 studs and opens it only when pressed. G was chosen because E is LEAP, F is BITE, C and B open Collection and Eggs. The pad dwell rule (0.5 s) was removed from `HubWalkUpRules`; `tools/verify_cave_gate.py` asserts no auto-open API remains.
- Fast travel (Crystal Shop perk, docs/104 s7) still opens the shop on arrival, because the player chose it by pressing the rail button; `walkUp.note()` debounces a prompt press in the same instant.
- Station signs read from every side: SurfaceGui on the Front and Back faces plus a small lamp-lit BillboardGui word above the sign (max distance 90 studs, not always on top, self-lit). Positions come from `CaveHubLayout`, copy from `HubSignCopy`.

## 7. Sound rules
Source: [87](87-vision-and-feel-guide.md), [110](110-sound-audit.md), [62](62-polish-sfx-goal-juice.md), [63](63-sfx-pack.md). Agents cannot hear: never call a sound "fine"; say "unheard".
- Soft, round, bubbly (marimba, kalimba, glass bubbles, soft pops); no saw/square buzz, clipping, harsh highs (above about 8 kHz), noise bursts, sirens.
- Fade-in >= 10 ms; short tails. UI ticks 50-150 ms, rewards 0.5-1.5 s, rare moments up to 2.5 s.
- Volume: cues 0.15-0.35 normally, hard clamp `Sfx.MaxCueVolume` 0.9, prefer <= 0.7; final = cue x `Sfx.Master` 0.5 x slider; nothing bypasses `Sfx.Master`. Beds 0.15-0.3, fade in and out.
- **Max 2 simultaneous cues**; one reward-style cue at a time (`Sfx.playCue`); chain by timing, not volume.
- Priority high to low: reveal rarity sting, fusion_reveal, level_up, run_end, shop_buy, weather accent, pickup, ui_click; a higher cue ducks lower ones by 40%; pickups and clicks are dropped, not queued (BD-339).
- Pickups at most 1 per 0.15 s; pitch +/-5%; rarity = richer harmony, not louder.
- Every new sound: brief, [77](77-asset-registry.md) line, owner listens before it ships.
Known violations: [110](110-sound-audit.md) flags legendary .43, fusion .375, hatch sting plus chime doubling; weather beds are silent (ids empty).

## 8. World and asset quality bar (acceptance checklists)
### 8.1 Any 3D asset or prop
1. Generated mesh (Roblox generate_mesh or the approved pipeline), never code-built ([AGENTS.md](../AGENTS.md); BD-206). The only exception is the scoped owner-approved V3 trees; Blender is also allowed for world and colossal-tree art (8.4.2).
2. Low-poly flat facets, chunky/rounded, matte; shared eye style (4.2).
3. **Scale ladder**: a normal-run dino (size up to about 2) still feels small next to big trees ([87](87-vision-and-feel-guide.md)); only a long-run giant (size 3 or more) outgrows ordinary trees, and colossal ancient trees stay taller (LEAD decision 2026-10-16, docs/139 Q3). The numeric table is section 8.1.1 (`src/shared/ScaleLadder.luau`, BD-407), checked by `tools/verify_scale_ladder.py`; every new prop's size must fit it.
4. **Grounded**: the bottom touches the floor at all slopes (raycast per prop); nothing sunk or floating (OWNER 2026-10-16: trees were sunk, BD-395).
5. **No overlap** with other solid props, paths, pads or the lava basin (`tools/verify_cave_overlap.py`; OWNER 2026-10-16).
6. Looks real under its place's lighting (section 6): judge a screenshot in that lighting, not the Studio edit light.
7. Palette fit (section 5); amber for currency crystals.
8. Budget ([107](107-offline-mobile-budget.md)): phone about 3,000 parts and 250 k tris in range, hub 410 parts / 730 k tris, 16 lights, about 300 live COSMETIC particles (auras, trails, mutations) and 3,300 live particles in the whole scene including weather (two measures, not one budget: [115](115-decisions-log.md) PB1), 12 players + 5 NPCs. Phone guards (BD-495..497, [146](146-phone-forecast-2026-10-17.md) s10): the 12 nearest cave lights and 4 shaft beams, no cosmetic glow light in the hub, weather density 0.25.
9. Pivot at the bottom centre; collision is a separate invisible part (colliders are never culled; on a PHONE the far ones are culled with the props beyond the cull radius, BD-496).
10. Registry line in [77](77-asset-registry.md); no invented asset IDs.
### 8.1.1 Scale ladder table (BD-407, CODE numbers)
Source of truth: `src/shared/ScaleLadder.luau`. The block below is generated from it and checked in CI by `tools/verify_scale_ladder.py` (code drift, ladder order, this table). **Not Studio evidence:** 19 of 22 species heights are ESTIMATES until the Studio bounding-box measurement in BD-471 replaces them. A new prop or species adds a row to the Lua table, then `python tools/verify_scale_ladder.py --runner luau.exe --write-doc`.
<!-- scale-ladder:begin -->
All sizes in studs. Generated from `src/shared/ScaleLadder.luau` by `tools/verify_scale_ladder.py --write-doc`; CI fails when this block, the Lua table or the code that builds the things drift apart. **WIRED** = the game code reads the table; **MIRRORED** = the owner module stays the source and the verifier recomputes the value from it.

**Dinosaurs (MIRRORED scale; height at scale 1 is MEASURED in Studio for 22 of 22 species, BD-471, 2026-10-17).** Drawn height = height at 1 x the growth scale. In the cave hub every dinosaur is exactly 1x (docs/115).

| Species | Model scale | Height at 1 | Source | run x1.52 | mid x2 | long x3 | max x4 | bigMax x4.8 |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| compy | 2.2 | 6.60 | MEASURED | 10.0 | 13.2 | 19.8 | 26.4 | 31.7 |
| triceratops | 3 | 8.39 | MEASURED | 12.8 | 16.8 | 25.2 | 33.6 | 40.3 |
| tyrannosaurus | 3.66 | 10.20 | MEASURED | 15.5 | 20.4 | 30.6 | 40.8 | 49.0 |
| raptor | 2.1 | 8.40 | MEASURED | 12.8 | 16.8 | 25.2 | 33.6 | 40.3 |
| stegosaurus | 2.64 | 4.91 | MEASURED | 7.5 | 9.8 | 14.7 | 19.6 | 23.6 |
| ankylosaurus | 2.66 | 6.49 | MEASURED | 9.9 | 13.0 | 19.5 | 26.0 | 31.2 |
| archaeopteryx | 1.76 | 5.28 | MEASURED | 8.0 | 10.6 | 15.8 | 21.1 | 25.3 |
| baryonyx | 2.42 | 6.22 | MEASURED | 9.5 | 12.4 | 18.7 | 24.9 | 29.9 |
| brachiosaurus | 3.87 | 10.63 | MEASURED | 16.2 | 21.3 | 31.9 | 42.5 | 51.0 |
| dimorphodon | 1.9 | 5.70 | MEASURED | 8.7 | 11.4 | 17.1 | 22.8 | 27.4 |
| elasmosaurus | 2.66 | 6.52 | MEASURED | 9.9 | 13.0 | 19.6 | 26.1 | 31.3 |
| gallimimus | 2.9 | 4.92 | MEASURED | 7.5 | 9.8 | 14.8 | 19.7 | 23.6 |
| ichthyosaurus | 2.3 | 3.45 | MEASURED | 5.2 | 6.9 | 10.4 | 13.8 | 16.6 |
| microraptor | 1.7 | 5.10 | MEASURED | 7.8 | 10.2 | 15.3 | 20.4 | 24.5 |
| mosasaurus | 3.22 | 3.29 | MEASURED | 5.0 | 6.6 | 9.9 | 13.2 | 15.8 |
| pachycephalosaurus | 1.98 | 5.11 | MEASURED | 7.8 | 10.2 | 15.3 | 20.4 | 24.5 |
| parasaurolophus | 2.31 | 5.54 | MEASURED | 8.4 | 11.1 | 16.6 | 22.2 | 26.6 |
| plesiosaurus | 2.42 | 6.73 | MEASURED | 10.2 | 13.5 | 20.2 | 26.9 | 32.3 |
| pteranodon | 2.31 | 6.93 | MEASURED | 10.5 | 13.9 | 20.8 | 27.7 | 33.3 |
| quetzalcoatlus | 2.8 | 8.40 | MEASURED | 12.8 | 16.8 | 25.2 | 33.6 | 40.3 |
| spinosaurus | 3.51 | 8.43 | MEASURED | 12.8 | 16.9 | 25.3 | 33.7 | 40.5 |
| therizinosaurus | 3.19 | 10.93 | MEASURED | 16.6 | 21.9 | 32.8 | 43.7 | 52.5 |

Growth stages (growth = food x 0.1, `s = min(4, sqrt(1 + growth / 50))`): spawn x1 (growth 0), run x1.52 (growth 65), mid x2 (growth 150), long x3 (growth 400), max x4 (growth 750), bigMax x4.8 (growth 750, BIG). Hub scale 1. BIG multiplier 1.2. Torso collider 2.6 wide x 3.2 long, top 2.6 x scale above the floor. Estimate rule: model scale x 2.84.

**World, food and hub (height in studs unless stated).**

| Rung | Size | Where it comes from |
| --- | --- | --- |
| Food berry / fruit / egg / amber (largest side) | 0.7 / 1 / 1.3 / 1.5, drawn x0.86 to x1.16 | WIRED: `FoodService.TYPES` |
| Golden Drumstick (flag off) | 1.9; the drumstick mesh is drawn x1.45, so up to 3.2 | WIRED: `SpecialFoods`, `FoodService` |
| Food pickup reach | 2.25 | MIRRORED: `Config.FoodPickupRadius` |
| Egg Nest pad (w x h x d) | 5 x 1 x 5 | WIRED: Arena legacy hub; MIRRORED: `CaveHubLayout.Kinds.nest` |
| Nest ledge behind the station (w x h x d) | 12 x 12 x 6.4 | MIRRORED: `CaveHubLayout.Kinds.hub_nest_ledge` |
| Ground cover (grass, flowers) | 1.9 to 4.8 | MIRRORED: kit extent x `BiomePlacement.Scales.groundcover` |
| Small band plants (ferns, bushes, mushrooms) | 4.2 to 12 | MIRRORED: `BiomePlacement.SmallBand` |
| Rocks (boulders to 10.6, spires and ledges to the top) | 1.7 to 25.6 | MIRRORED: kit extent x `BiomePlacement.Scales.rock` (0.85 to 1.8) |
| Ground rocks, Blender (small / medium / mossy; ids empty) | 1.2 / 2.3 / 3.2 | MIRRORED: `WorldGeneratedMeshes.Props` |
| Landmarks (statue, fossil, arch, altar) | 9.4 to 25.8 | MIRRORED: kit extent x `BiomePlacement.LandmarkScale` 1.4 |
| Normal trees | 4.7 to 42 | MIRRORED: kit extent 5.24 to 26.22 x `Scales.tree` 0.9 to 1.6 |
| V3 Blender trees (broadleaf, conifer, palm) | 4.7 to 42 | fitted inside the same kit box (`Arena.generatedProp`), so the same range |
| Colossal ancient trees | 80 to 140, crown at most 100; ancient mesh 117.59 / 117.29 / 105.03 | MIRRORED: `BiomePlacement.Colossal`, `WorldGeneratedMeshes.Colossal` |
| Dino door: gate mouth (w x h) | 30 x 20; frame mesh 39.79 x 25.79 x 9.77 | MIRRORED: `CaveHubLayout.get().gate`, `CaveTerrainRules.GateHeight`, `Kinds.cave_gate_frame` |
| Hub tunnel (width, ceiling, path) | 22, 30, 8 | MIRRORED: `CaveHubLayout.TunnelRadius`, tunnel height, `PathHalf` |
| Station pad radius | fame 12, fusion 20, gate 15, heart 18, index 20, nests 17, potions 15, settings 10, style 18 | MIRRORED: `CaveHubLayout` stations |
| Signs (w x h x d): stone / arrow / legacy board | 5.5 x 5.5 x 2 / 5 x 5 x 0.8 / 30 x 7 x 1 | MIRRORED: `CaveHubLayout.Kinds`; the legacy board is WIRED in `Arena` |
| Station props (w x h x d) | Potion stall 14 x 10 x 7; Forge altar 8 x 5 x 5; Shop counter 8.8 x 7 x 4.5; Lectern 3 x 4 x 3; Wall frame 3.8 x 4.5 x 0.7 | MIRRORED: `CaveHubLayout.Kinds` |
<!-- scale-ladder:end -->
Code against docs, found while building the table (the code value is in the table; none of this changes the game):
- Tree height: docs/139 s3.3 lists 5.0 to 41.9 (seed 1404 placements, truncated); the rule bounds are kit extent x scale, 5.235 x 0.9 = 4.7 and 26.222 x 1.6 = 41.96 (table 4.7 to 42).
- Rocks: docs/139 s3.3 lists a 20.8 maximum (seed 1404 placements); the rule bound is the spire 14.228 x 1.8 = 25.6. Ground cover: docs/139 lists 1.3 to 4.8; the code gives 1.184 x 1.6 = 1.9 to 4.8.
- docs/139 s3.3 shrubs 1.1 to 10.2 and giants 33.5 to 99 are the pre-BD-473 layout; the code is the Small band 4.2 to 12 and the colossal band 80 to 140 (docs/139 s17 already says so).
- Hub dino size: docs/139 s3.1 calls 1x a side effect of the GrowthScore reset; docs/115 (BD-480) makes it a guaranteed rule, which is what the table uses.
- Dino door: `CaveHubLayout.Kinds.hub_gate_arch` is 24 x 24 x 8.7 and `CaveHubProps` records a final size of 16 x 15.9 x 5.8, but no station places that prop any more; the door is the terrain mouth 30 x 20 (`CaveTerrainRules.GateHeight`) with the `cave_gate_frame` mesh 39.79 x 25.79 x 9.77 (docs/140 gives the opening as 29.2 x 19.6).
- Only Compy, Gallimimus and Tyrannosaurus heights are Studio-measured (the `LowPolyDinoAssets` comment still mentions the old 1.2 x 3.4 x 4.0 Gallimimus at scale 2.0). The other 19 are ESTIMATES until BD-471.
### 8.2 Any UI screen
Text >= 14 px; targets >= 44 px; contrast >= 4.5:1; kid words per [72](72-ui-copy-and-asset-standards.md); checked on phone landscape (844x390) and desktop; one idea per screen; final art is an asset task, not code drawing; shared `TextStyle`; lead screenshots it before merge.
### 8.3 Any FX
Calm and soft (no flicker, no full-screen flash); never hides dino, food or controls; particle/part budget stated; phone rate about half; Reduce Motion variant; colours from the palette; at most 8 dinos with FX, nearest first ([93](93-anime-fx-direction.md), [92](92-mutation-fx-brief.md)).


#### 8.3.1 Royal Nova aura appearance benchmark (OWNER, 2026-10-16)
Source: owner review of the Royal Nova image draft in ChatGPT on 2026-10-16: "i would expect slightly more smoke, and more floor rings. but overall pretty good", followed by approval to update this handbook.

- **OWNER TARGET:** colourful, dimensional anime magic with a calm, bubbly feel. Auras need clearly visible volume and layered depth. Calm describes their motion and feel; it does not mean faint, sparse or minimal.
- Royal Nova's accepted overall draft direction: purple-and-gold flowing energy ribbons passing behind and in front of the dino, rounded lavender smoke curls near the feet/lower body, sparse gold stars, a soft vertical glow and ground swirls. Keep the dino matte and its face, silhouette and body markings readable.
- **Owner-requested refinement:** slightly more smoke presence and more floor rings than the initial draft. Build a fuller, softly curling smoke base with gaps around the feet; use multiple distinct floor rings with visible spacing and differing radii rather than one thin wire or a solid luminous floor disc.
- **PROVISIONAL next-draft interpretation:** 2-3 floor rings, with gentle counter-rotation or expanding ripples in an eventual animation. The owner approved the direction, not an exact ring count, particle count, opacity or timing.
- Soft, curling flame-like energy shapes are allowed. Avoid aggressive jagged spikes, harsh flashes and flicker. This owner clarification supersedes the blanket "no flame shapes" wording in [93](93-anime-fx-direction.md) for aura appearance; retain its calm-motion and readability principles.
- The draft is an **aura appearance benchmark only**. Its dinosaur model and environment are not approved production assets; a still image does not establish animation quality, implementation, Studio acceptance or phone performance. The revised draft remains subject to owner feedback.
- Preserve device budgets and Reduce Motion support. Achieve richness through authored shapes, composition and depth; verify readability in daylight, the cave and stacked mutation/aura/trail combinations. This direction does not authorize raising budgets or changing runtime code by itself.

## 8.4 Visual environment polish (owner discussion 2026-10-16; DESIGN TARGET, fact-checked 2026-10-16)

The owner requested these visual guidelines and four illustrated reference pages be recorded in the handbook. **The illustrations are generated concept art, not screenshots of verified Roblox output.** The 4-page PDF and original illustrations are saved in the owner's ChatGPT Library folder `/be dino/handbook visual references/`: `01 Environment Polish.png`, `02 Asset Quality.png`, `03 Growth and Vegetation.png`, `04 Special Skin Finishes.png`, and `Be Dino Visual Handbook Illustrated Supplement.pdf`. These are not GitHub-hosted image assets and were not available to the fact-check; do not fabricate accessible image URLs. Where this section and a dated owner decision disagree, the decision wins ([115](115-decisions-log.md)). The concrete numbers and the Studio evidence live in [138](138-env-visual-polish.md), [139](139-giant-dino-vegetation-scale.md) and [140](140-tree-quality-test.md), not here. Items marked **PROPOSAL / not owner-approved** are listed in [116](116-handbook-conflicts.md) section G.

### 8.4.1 Six high-value visual fixes
Status of each fix against the code (BD-460, [138](138-env-visual-polish.md)); the Studio check is still pending, so none of these is accepted yet:
1. **Grass first: DIAGNOSED AND DECIDED.** The dark repeating waves came from the `BeDino_Meadow` colour map itself (Studio control, 138 s1), not from normals or shadows. **OWNER 2026-10-16: use Roblox's built-in Grass now**, terrain colour 132,166,68 (candidate C, BD-460); `BeDino_Meadow` stays packaged but unbound. A new matte Blender grass texture is the follow-up BD-461 and is bound only if it beats the built-in grass side by side at gameplay distance.
2. **Green saturation:** keep the hierarchy goal (mint treetops, terrain and the green player must not blend) and keep the cheerful colour. CODE (BD-460): per-asset foliage tone, clear-weather grade saturation +0.04 and contrast 0; no blanket desaturation. Collectibles stay vivid.
3. **Player grounding:** CODE (BD-460): a soft contact shadow under each dino (3 stacked flat discs, grows with the dino). Extra dimensional shading on the body and neck is the PR author's **PROPOSAL / not owner-approved** (docs/116 C-28). Do not make the dino glow.
4. **Distance depth: NO HAZE (OWNER 2026-10-16, "no screenshots should have this hazy effect").** The PR's "lower distant contrast and slightly lighter distant hills/trees" is withdrawn because it is a milky-haze look. Clear island daylight keeps Atmosphere density .1 / haze .3 / glare 0, no far blur, no bloom (section 6); weather events add their own soft atmosphere and ramp back to clear. Depth must come from scale, layering and silhouette, never from lightening or fogging the distance.
5. **Reduce clutter:** clear traversal paths and small-dino lines of sight; group plants and flowers in intentional clusters; replace rather than add. CODE (BD-460): wider main routes and a larger spawn keep-out. Clearings and band-based planting are the PROPOSAL in [139](139-giant-dino-vegetation-scale.md) s6 (BD-473, P2).
6. **Lighting:** CODE (BD-460): island Brightness 1.8 with a higher ambient floor so crowns do not clip and the ground is not near black. Keep the dino and food the visual priority. Re-measure with the luminance gate (section 6.1) after the grass colour change.

### 8.4.2 Procedural placement does not excuse poor asset shapes
- **Round trees, conifers and palms: DECIDED.** Repeated sphere-clusters, identical stacked pine layers and straight palm poles read as automatic primitives. **OWNER 2026-10-16: use the Blender V3 trees (broadleaf, conifer, palm)**, with asymmetric clumps, tapered trunks, roots and branches, drooping skirts and curved palm trunks ([140](140-tree-quality-test.md), BD-462, Review / test). This is a **scoped exception** to the no-code-built-models rule (D8/D15 in [115](115-decisions-log.md)): it covers ONLY `world_tree_broad_v3`, `world_tree_pine_v3` and `world_tree_palm_v3`. The meshes are not uploaded yet, so the game still shows the current generated trees.
- **Blender is allowed for world and colossal-tree art** (OWNER 2026-10-16, docs/139 Q5). Every other model (dinos, props, plants) still needs a generation or hand-modelling pipeline: generated mesh, then cleanup and optimisation, then Roblox import. Code-built stacks stay placeholders.
- **Grass, ferns and small plants:** broader, slightly bent leaf blades, layered clusters, a few recognisable families, no thin crossed triangles. Spec only, not built (BD-463, P2).
- **Ground props:** sculpted stones, short logs, roots, stumps, bushes and mushrooms around major tree bases, replacing other clutter so part count and visibility do not regress. Spec only, not built (BD-464, P2). Grounding and overlap follow section 8.1.
- **Player dinosaur:** preserve the recognisable chunky silhouette and face; only minor refinement at neck, hip, mouth and limb intersections. The base look is the faceted low-poly dino (D14); this refinement is the PR author's **PROPOSAL / not owner-approved** (docs/116 C-28).
- Compare old and new variants at normal gameplay camera distance, with mobile performance evidence ([107](107-offline-mobile-budget.md)). Follow section 8.1, docs/87 and AGENTS.md.

## 8.5 Scaling: jungle at tiny, medium and colossal sizes (DESIGN TARGET; the numbers are in docs/139)

**Intended emotional curve:** newly spawned dinosaurs feel tiny in dense, towering vegetation; growing dinosaurs outgrow small plants; giant dinosaurs visibly dominate small players without the *whole* jungle looking miniature. The height hierarchy (Small / Medium / Colossal bands, the 42-80 stud gap, placement rules, camera curve, collision and budgets) is specified once, in [139](139-giant-dino-vegetation-scale.md) s5-s9, and is not repeated here. **All of it is a PROPOSAL.** **LEAD decisions (owner delegated 2026-10-16, [115](115-decisions-log.md); the owner may overrule):** Q3 ordinary trees ARE outgrown, but only by a long-run giant (size 3 or more), colossal ancient trees stay taller; Q4 the mix is counted over trees plus giants of 12 studs and up, starting 68 / 27 / 5; Q6 trample plus soft rustle only if a giant actually wedges; Q7 camera distance, aim and FOV first; Q8 the dino fills 38% growing to 55% of the screen; Q9 fog measured from the dino when the camera is pulled out; Q10 scale table folded into BD-471; Q11 hills stay (giants are bigger than hills); Q12 larger colossal cull radius only if the phone numbers pass. Most of the build rows (BD-472, 474-478) are P3 after the pacing answer; only BD-471 and BD-473 are P2 (BD-470 is Done).

- **Vegetation mix:** the "60-70% small/medium, 20-30% larger, 5-10% colossal" split came from an outside design review and is **not approved**. [139](139-giant-dino-vegetation-scale.md) s5 reads it as 65 / 27 / 8 of the tree-plus-giant placements of 12 studs and up (Q4). Use grouped placement and clearings, not an evenly scattered forest of giants; test biome by biome.
- **Camera:** the principle is not to zoom linearly up and out with size, because top-down framing makes the map look like miniatures: keep trunks and the horizon visible, small players visible beside giants, and test occlusion and control at each size. Today the camera IS exactly proportional (minimum zoom 12 x size). The sub-linear camera curve is the PROPOSAL in [139](139-giant-dino-vegetation-scale.md) s7 (BD-472, P3, flag off; Q7/Q8 decided by the LEAD 2026-10-16).
- **Gameplay risks:** max-size dinos must traverse terrain, avoid tree and cave geometry and reach food and eggs without broken animation, physics or camera clipping; audit combat, predation and NPC encounters; record mobile performance. Tracked as BD-476 / BD-477 (P3).
- **Intimidation is awe only (OWNER Q2 2026-10-16):** size, footsteps, shadow and camera framing. No fear mechanics and no small-dino reactions (BD-478). Read "dominate small players" in that way.

**Growth pacing is DECIDED and unchanged (OWNER Q1 2026-10-16).** `GrowthPerFood` stays 0.1 and the cap stays 4 (BIG x1.2 reaches 4.8). A normal 5-minute run ends at about size 1.5, the cap takes about an hour, and gigantic is a rare long-run reward ([139](139-giant-dino-vegetation-scale.md) s1.1 and s3.1, [115](115-decisions-log.md)). ~~Possible playtest targets of about 2.5-3x after a good five-minute run and a 6x long-run maximum~~ (NOT ADOPTED: the owner kept the pacing; history kept, do not implement). What every run still sees is the START: a new dino should feel small in a tall world (Small band, skyline, clearings). That is BD-473 work, not a growth change.

## 8.6 Fused-tier surface finish benchmark (DESIGN TARGET, not implementation proof; Gold is in progress and not final)

Four identical poses are compared in concept art: **top left Original, top right Gold, bottom left Emerald, bottom right Diamond.** The same red-and-purple stripe pattern, base dinosaur proportions, cream belly, black eye and claws remain in all panels.

**OWNER 2026-10-16 (the rule this benchmark is judged by):** a fused tier keeps the dino's **same colours and pattern**, seen **under a tinted crystal / metal coat with an outline**. The tier is told apart through that coat and outline, primarily through the surface itself rather than particle emitters.

| Variant | Target surface (coat over the unchanged colours and pattern) | Outline |
| --- | --- | --- |
| Original | Original matte base; clear saturated red-purple pattern | none |
| Gold | Bright polished golden metal coat, original stripes legible; not matte orange | Clean strong golden edge |
| Emerald | Glossy translucent emerald gem coat, original stripes perceptible | Mint/emerald edge |
| Diamond | Icy pale blue-white, polished crystalline coat, underlying stripes perceptible | Crisp blue-white edge |

**Roblox findings (Studio, 2026-10-16) that shape the build:**
- A `SurfaceAppearance` created at runtime does **not render**. One **authored in Edit mode and cloned at runtime** does. Keep the template in the place and clone it per dino.
- The stripes are **runtime-baked textures**, so the PBR maps go on a **separate alpha-mapped shell over them**, not into the pattern texture. The PR's remark that a duplicated transparent shell looked plasticky is a finding about that test shell, not a reason to drop the shell; its "single-mesh texture plus PBR maps instead of extra shells" suggestion is withdrawn.
- At **graphics quality 1 reflections are off**. The tier must still read with reflections off through the tint and the outline; a phone fallback is required (phone budget, section 8.1 item 8).
- **Gold is in progress and not final.** The look and numbers for Gold, and so Emerald and Diamond, are open until the owner accepts a Studio screenshot. The open tier work is PR #291 (`tier-shiny`); the numbers in section 4.3 describe the code on main today and may be reworked by it.
- Do not assume the Glass or Metal material setting alone produces concept-art reflections. Eye and claw parts stay exceptions as in section 4.3; keep the current caps there.
- **PROPOSAL / not owner-approved:** the PR author's view that Emerald and Diamond need material-specific art, not just a recoloured Gold (docs/116 C-30).

**Review standard:** four same-pose Studio screenshots in bright daytime, another lighting or weather check, original beside variant, at the actual game-camera distance, with no particles or trails; repeat at graphics quality 1 (reflections off) and at a normal quality; note engine limits and mobile cost. Do not let a bright outline hide an unconvincing coat. The generated illustration is a **visual reference**, never an engine performance claim.

## 9. Game rules cheat sheet (numbers true today; CODE unless noted)
| Rule | Value | Source |
|---|---|---|
| Eggs per catch | one run egg per catch, one dinosaur per successful egg | [09](09-reward-economy.md), [AGENTS.md](../AGENTS.md) |
| Catch rate | `FoodCatchRate = 12/500` (500 food = 12 eggs, 5,000 = 120; a normal 5-minute run is about 15 eggs); per-run cap 150 (PROVISIONAL, needs Studio measurement); 4/500 and 40/500 are HISTORICAL | [119](119-catch-rate-15-per-run.md) (owner 2026-10-16) |
| Growth | `GrowthPerFood = 0.1`, predation 2.5; scale = min(4, sqrt(1+growth/50)); eggs use raw food | [90](90-fusion-ladder-v2.md) s6, BD-386 |
| Fusion ladder | Gold = 6 Base (same species, any pattern, plurality pattern kept), Emerald = 3 Gold, Diamond = 2 Emerald (same species + pattern); donors consumed, new instance, guaranteed stage, fresh traits | [90](90-fusion-ladder-v2.md), BD-335 |
| Species tiers | base Common 72 / Uncommon 24 / Rare 3.2 / Epic 0.7 / Legendary 0.1; run boost {1,1,1.1,1.1,1.1}, full at 120 eggs | [82](82-species-rarity-tiers.md), [89](89-catch-rate-4.md) |
| Rarity curve | r = 1/5, six-tier ladder 80/16/3.2/0.64/0.128/0.0256; price factor x2.8 | [88](88-exponential-rarity.md) |
| Conditions, tier 0 | Cracked 50 / Dirty 30 / Normal 15 / Rainbow 4.5 / Astra 0.5; Cracked hatch success 20% | `ProgressionConfig`, [09](09-reward-economy.md) |
| First eggs safe | `SafeEggs = 2`: the first 2 eggs are never Cracked; Cracked 50% from the third egg (OWNER 2026-10-16: keep) | `ProgressionConfig.SafeEggs`, BD-365 |
| Run crystals | `min(300, floor((250*min(n,12)+176*max(0,n-12))/100))`: 12 eggs -> 30, 120 -> 220 (PROVISIONAL) | [09](09-reward-economy.md) |
| Nests | 5 slots, 3 h each, 6-12 eggs (avg 9), unlimited per run (owner 2026-10-16; only 5 spots, each extra nest becomes crystals, PROVISIONAL 50; +1 per 30 eggs after the first, [119](119-catch-rate-15-per-run.md)), drop gate 120 s + 1 catch | [90](90-fusion-ladder-v2.md) s5 |
| Hatch pace | `HatchRevealSeconds` 1 s per egg, ascending rarity, skippable | [09](09-reward-economy.md), BD-044 |
| Colour / pattern | colour tiers Common..Mythic (5.4), colour growth bonus +1% per tier; 8 patterns equally likely | `ProgressionConfig`, BD-172, [88](88-exponential-rarity.md) |
| Prices | trails 0/100/280/390/780/1100/2200/3100/6100/17000; auras 60/470/3700 | `ProgressionConfig` |
| Potion shop | rotates every 2 minutes, 1-3 limited stock | BD-051 |
| Combat | HP, hearts only, 4 classes (Ground, Fly, Water, Armored), `CombatEnabled=false`, no Peaceful opt-out (superseded 2026-10-16) | [101](101-hp-combat-classes-animations.md) |
| Flags | `CombatEnabled`, `CaveHub` false; `LowPolyDinos` false default, true in playtest profile | [AGENTS.md](../AGENTS.md), [108](108-lowpoly-playtest-profile.md) |
| Fast travel | Crystal Shop perk bought with crystals; walking is default; additive profile field default off; Settings toggle only after purchase; glow guide stays free; price PROVISIONAL (OWNER 2026-10-16) | [115](115-decisions-log.md), BD-391 |

## 10. Roadmap and priorities (derived from kanban, 2026-10-16)
- **P0:** BD-397 hatching redesign (Fable); BD-398/399 cave lighting and weather gate (Review, need owner eyes); BD-386..389 owner playtest fixes (Review); BD-365/366 first-time-player fixes; BD-019/BD-085 phone and 12-player evidence; BD-225 low-poly playtest profile.
- **P1:** BD-391 fast-travel perk; BD-392/393/394 egg view, aura-shop copy, conditions-shop render; BD-395 sunk trees; BD-396 glow guide; BD-400/BD-401 amber crystals; BD-182 project name; BD-059/061/062/063 fusion looks and per-dino cosmetics; BD-336 owner art uploads.
- **Later:** skins (Plushy, Clay, Bricks, [97](97-dino-skins.md)); roster 5 Fly + 5 Water + 5 Ground (BD-232); notifications and mini objectives (BD-066..078).
Status lives only in the [kanban](07-kanban.md).

## 11. Monetisation and policy boundaries
- **No Robux yet**: all paid flags off until policy and runtime tests pass ([43](43-player-access-and-paid-random-policy.md), [AGENTS.md](../AGENTS.md)).
- Paid random items: check `PolicyService`, disclose all outcomes and numeric odds, enforce on the server, treat failed checks as ineligible; fusing Robux-linked inputs may count as paid random ([46](46-pattern-fusion-dino-identity-and-cosmetic-progression.md)).
- Sell time, information and looks, never power or randomness ([86](86-monetization-ideas.md)); skins are cosmetic and bought directly ([97](97-dino-skins.md)). Fast travel costs **crystals**, not Robux.
- Never rewrite persistent profiles or enable Robux packs without evidence.

### 11a. The Robux line (OWNER 2026-10-16, BD-425)
Robux buys **looks and convenience**, never exclusive power. Enforced in CI by `tools/verify_robux_line.py` (flags off, crystal-only handlers, PolicyService and odds gates). Convenience multiplier cap: **1.25x**, and never beyond the normal in-game limit.
| Category | Allowed with Robux | Never with Robux |
|---|---|---|
| Looks | skins, auras, trails, hatch styles, titles, home themes | any stat, size or speed change |
| Time-savers | potions or potion bundles (capped, see [86](86-monetization-ideas.md)), Nest Warmer, auto-open | growth multiplier above 1.25x, stacking past the normal limit |
| Capacity | extra nest spots, storage | more luck or bigger rewards per nest |
| Currency | crystal packs (crystals only, flag off) | direct dinos, species or rarity |
| Random items | only behind `Config.PaidRandomItemsEnabled`, a passed `PolicyService` check and shown numeric odds | hidden or changed odds, extra fusion success |
| Power | nothing | combat or predation advantage, exclusive species |

## 12. Process rules
- Art rule: no code or Python-drawn final art; effect textures are Blender renders; icons come from Blender or the owner's ChatGPT; **generated meshes only** for 3D ([AGENTS.md](../AGENTS.md), [87](87-vision-and-feel-guide.md), [72](72-ui-copy-and-asset-standards.md)).
- New features ship flag-off-by-default; do not flip combat, cave or low-poly without owner playtest and phone evidence.
- QA agents never touch `Place1.rbxl` ([AGENTS.md](../AGENTS.md)).
- Keep 3 agents running (lead instruction; kanban log says 3-4, [78](78-lead-handoff.md) says at most 2: C-19). Sonnet by default; Fable for hard tasks (BD-397).
- Do not rewrite history: mark SUPERSEDED, keep rows; never mark Done without evidence; status only in the kanban.
- Say plainly what was not verified (Studio, phone, hearing).
- **Automated handbook check (BD-408, CI):** `python tools/verify_handbook.py` fails on (a) a UI rule constant or literal under the s4.4 floors (text 14 px, tap target 44 px; the known pre-existing offenders are a counted baseline `UI_KNOWN`, docs/116 C-37, and it only shrinks), (b) a cue louder than `Sfx.MaxCueVolume` or a played/listed cue missing from `Sfx.Sounds`, (c) any hex in s5 (and the s6 island/cave colour numbers) that differs from the code table that owns it (`UITheme`, `RarityColors`, `EggColors`, `MutationLook`, `ProgressionConfig` auras/trails, `BiomeMap`, `WeatherLooks`, `CaveLightingRules`, `CaveLavaRules`, `CaveTerrainRules`, `ClassInfo`), (d) a missing PR template. When it reports a palette mismatch, change the side that is older: the doc when the code is the newer owner-approved value (check [115](115-decisions-log.md)), the code when it breaks the handbook.

## 13. Handbook compliance checklist (paste into every PR body)
```
Handbook check (docs/114):
- [ ] Vision/feel: vibe words (polished, satisfying, calm, bubbly, friendly, vibrant: section 0, read as overall vibe not literal rules) cross-referenced; checked on a screenshot or marked "not verified"
- [ ] Design language: low-poly facets, no ellipses/primitive code art, matte (gloss only fused tiers), eyes glossy black + white dot
- [ ] Palette: colours from handbook section 5; currency crystals amber/yellow
- [ ] Lighting: right for its place (island bright; cave DIM lamp-lit; weather never inside the cave)
- [ ] Sound: soft, quiet, short, max 2 cues, priorities kept; marked "unheard" if not owner-judged
- [ ] Asset quality bar (8.1): grounded, no overlap, scale, budget, pivot, collision, registry line
- [ ] UI bar (8.2): text >= 14 px, targets >= 44 px, contrast >= 4.5:1, kid words (docs/72), phone + desktop
- [ ] FX bar (8.3): calm, budget stated, Reduce Motion version
- [ ] Economy numbers match handbook section 9 (or doc and code updated together)
- [ ] Art rule: no code-drawn final art, generated meshes only, flags off by default, Place1.rbxl untouched
```
