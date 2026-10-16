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
- **PvP is optional.** The core loop is food, eggs, growing. Hunting other players happens, but a Peaceful choice must be easy to find (audit: BD-421).
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
Grass #84AA54 (132,170,84); LeafyGrass #3E7C4E (62,124,78); Mud #5C4C37 (92,76,55); Ground #706442 (112,100,66); Sand #D6BE88 (214,190,136); Sandstone #BA7A50 (186,122,80); Slate #5C666C (92,102,108); Basalt #322F37 (50,47,55); Rock #728589 (114,133,137). Biomes: meadow, fern, conifer, marsh, badlands, volcanic (`BiomeMap.Rock`).
### 5.9 Weather looks (`WeatherLooks.luau`, tint / fog)
Rain #96B6E8 / #78869C; Thunder #A0AEDE / #586084 (violet glow #A08CFF); Blizzard #D6E8FF / #E2EAF6; Volcano #FFE4CD / #96543B (glow #FF8C46); Aurora #B0FFE6 / #28C8AA (glow #3CFFAA); Quake #E8C89C / #C6B092; Blood Moon #FF8C96 / #420E18 (glow #FF2846). Far fog is colour, not a wall ([87](87-vision-and-feel-guide.md)).
### 5.10 Cave (`CaveLightingRules.luau`)
Warm cream shafts #FFECBE (255,236,190); fill lamp #FFD6AA (255,214,170); lava #FF8C46 (255,140,70) (sheet layers #FF7828, #FFB45A, #FFCE6E); crystal light #FFC450 (255,196,80) amber (BD-401; was lavender #C4AAFF); forge #FFBE5A (255,190,90); gate glow #FFD6A0; look: ambient (70,62,60), fog colour (72,56,46), grade tint (255,226,196). Walls: Limestone (196,172,150) and a cool grey-lilac cave-only Cobblestone/Limestone (BD-384); the floor must not be hot orange (BD-384).
### 5.11 Classes and HP bar
HP bar fill green above 50%, yellow 25-50%, soft orange below 25%, plus a heart icon (full/half/small) so colour is never the only signal ([101](101-hp-combat-classes-animations.md) line 85). **No per-class colour table exists in code or docs** (classes Ground, Fly, Water, Armored): conflict C-18, BD-406.
### 5.12 Lighting-colour rule
The palette sits under the place's lighting; a shared grade tames pastel props because `MeshPart.Color` is ignored on textured meshes (BD-399). Dino and food stay readable in every place and weather.

## 6. Lighting rules per place
| Place | Rule | Source / code |
|---|---|---|
| Island (default) | bright daylight: ClockTime 14, Brightness 2, Ambient (130,143,148); soft distance fog, no pop-in | `Bootstrap.server.luau` 22-24, BD-213 |
| Cave hub (Sanctuary) | **DIM, lamp-lit**: warm lamps and ceiling light shafts are the main lights; ambient (70,62,60), Brightness 1.3, exposure -0.25; at most 16 lights, shadows on the 4 strongest; **weather never affects the inside**; assets must look real and grounded in this light | OWNER 2026-10-16; `CaveLightingRules.Look`; BD-398, BD-399 |
| Weather events | per-event grade, haze, soft fog; everything fades to neutral with `1 - Cave.amount()` inside the hall | [84](84-weather-events-v2.md), BD-383, BD-398 |
| Volcanic biome | orange glare, heavy bloom, ash and embers, but soft visibility (no flat red wall) | [84](84-weather-events-v2.md), BD-213 |
| Eggs and dinos in UI | lit warmly on a stage/tile floor, never cubes | [87](87-vision-and-feel-guide.md) |
Open: per-biome daylight rules beyond the island base are not documented (conflict C-9).

### 6.1 Brightness bands and cave stone palette (owner 2026-10-16, confirmed)
- Automatic luminance bands (mean screen luminance 0 = black, 1 = white): **cave 0.15-0.35, island 0.35-0.75**. The quality gates (docs/117, tools/qa/luminance.py) fail outside these bands.
- Cool blue-grey stone is ACCEPTED as cave decoration (depth and contrast); warmth comes from lamps, shafts, amber crystals and warm props. Currency and shop crystals stay amber/yellow (decision 2026-10-16). BD-414/415 are resolved as "accepted, no recolour".

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
1. Generated mesh (Roblox generate_mesh or the approved pipeline), never code-built ([AGENTS.md](../AGENTS.md); BD-206).
2. Low-poly flat facets, chunky/rounded, matte; shared eye style (4.2).
3. **Scale ladder**: a grown dino still feels small next to big trees ([87](87-vision-and-feel-guide.md)). No numeric scale table exists yet (BD-407).
4. **Grounded**: the bottom touches the floor at all slopes (raycast per prop); nothing sunk or floating (OWNER 2026-10-16: trees were sunk, BD-395).
5. **No overlap** with other solid props, paths, pads or the lava basin (`tools/verify_cave_overlap.py`; OWNER 2026-10-16).
6. Looks real under its place's lighting (section 6): judge a screenshot in that lighting, not the Studio edit light.
7. Palette fit (section 5); amber for currency crystals.
8. Budget ([107](107-offline-mobile-budget.md)): phone about 3,000 parts and 250 k tris in range, hub 410 parts / 730 k tris, 16 lights, about 300 live particles, 12 players + 5 NPCs.
9. Pivot at the bottom centre; collision is a separate invisible part (colliders are never culled).
10. Registry line in [77](77-asset-registry.md); no invented asset IDs.
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
| Nests | 5 slots, 3 h each, 6-12 eggs (avg 9), up to 3 per run (+1 per 30 eggs after the first, [119](119-catch-rate-15-per-run.md)), drop gate 120 s + 1 catch | [90](90-fusion-ladder-v2.md) s5 |
| Hatch pace | `HatchRevealSeconds` 1 s per egg, ascending rarity, skippable | [09](09-reward-economy.md), BD-044 |
| Colour / pattern | colour tiers Common..Mythic (5.4), colour growth bonus +1% per tier; 8 patterns equally likely | `ProgressionConfig`, BD-172, [88](88-exponential-rarity.md) |
| Prices | trails 0/100/280/390/780/1100/2200/3100/6100/17000; auras 60/470/3700 | `ProgressionConfig` |
| Potion shop | rotates every 2 minutes, 1-3 limited stock | BD-051 |
| Combat | HP, hearts only, 4 classes (Ground, Fly, Water, Armored), `CombatEnabled=false`, Peaceful option | [101](101-hp-combat-classes-animations.md) |
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

## 12. Process rules
- Art rule: no code or Python-drawn final art; effect textures are Blender renders; icons come from Blender or the owner's ChatGPT; **generated meshes only** for 3D ([AGENTS.md](../AGENTS.md), [87](87-vision-and-feel-guide.md), [72](72-ui-copy-and-asset-standards.md)).
- New features ship flag-off-by-default; do not flip combat, cave or low-poly without owner playtest and phone evidence.
- QA agents never touch `Place1.rbxl` ([AGENTS.md](../AGENTS.md)).
- Keep 3 agents running (lead instruction; kanban log says 3-4, [78](78-lead-handoff.md) says at most 2: C-19). Sonnet by default; Fable for hard tasks (BD-397).
- Do not rewrite history: mark SUPERSEDED, keep rows; never mark Done without evidence; status only in the kanban.
- Say plainly what was not verified (Studio, phone, hearing).

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
