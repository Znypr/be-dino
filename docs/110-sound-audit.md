# 110 - Sound audit (BD-081, BD-166, BD-258, BD-132)

Status: audit written 2026-10-16 from source only. **Nobody listened to anything**: an agent cannot hear, so no cue below is called "fine". Loudness figures are arithmetic on volumes, not measured LUFS. Read first: [87](87-vision-and-feel-guide.md) (soft sounds), [62](62-polish-sfx-goal-juice.md), [63](63-sfx-pack.md), [80](80-notifications.md).

Final gain rule of thumb: `final = cue volume x Sfx.Master (0.5) x group slider`. Group sliders default master 0.8 x Sounds 0.7 (AudioMixer), so at defaults the in-game factor is `volume x 0.5 x 0.56`; at slider 100% it is `volume x 0.5`. **Flag** = cue volume x Master above 0.35 (cue volume above 0.7). Group = Sounds (Sfx + hatch tap/crunch/chime), Weather (WeatherAudio, group "ambience"), Everything (master).

## 1. Cue table (CURRENT BUILD BEHAVIOR)

| Cue | Asset | Length | Vol | Rate | Played at | Group | Frequency estimate | Flag |
|---|---|---|---:|---:|---|---|---|---|
| hatch_crack | 135613869332284 | ~0.45 s | .6 | 1 | Bootstrap:972 (egg tap) | Sounds | per egg open, 40-400 per run | no, repeat risk |
| hatch_common | 123602379376075 | ~0.75 s | .6 | 1 | only via Sfx.hatchName (legacy) | Sounds | per egg | no |
| hatch_rare | 100769608611671 | ~1.45 s | .7 | 1 | legacy | Sounds | rare eggs | at limit (.35) |
| hatch_legendary | 109331854464968 | ~2.45 s | .85 | 1 | legacy | Sounds | rare | FLAG .43 |
| hatch_rattle | none (silent) | - | .5 | 1 | HatchSequence:874 via timeline | Sounds | 3 per egg | silent |
| hatch_crack_stage | 135613869332284 (same as crack) | ~0.45 s | .6 | 1 | HatchSequence:874 | Sounds | about 3 per egg | no, repeat risk |
| hatch_burst | none (silent) | - | .8 | 1 | HatchSequence:874 | Sounds | per egg | silent; FLAG when bound |
| hatch_reveal_common / uncommon | 123602379376075 | ~0.75 s | .6 / .65 | 1 | HatchSequence:559 | Sounds | most eggs | no |
| hatch_reveal_rare | 100769608611671 | ~1.45 s | .75 | 1 | HatchSequence:559 | Sounds | uncommon | FLAG .375 |
| hatch_reveal_epic | 109331854464968 | ~2.45 s | .85 | 1 | HatchSequence:559 | Sounds | rare | FLAG .43 |
| hatch_reveal_legendary | same | ~2.45 s | .95 (clamped to .9) | 1 | HatchSequence:559 | Sounds | very rare | FLAG .45 |
| shiny_bang | 124365194004947 | ~1.7 s | .8 | 1 | no call site found (never played) | Sounds | - | FLAG .4 once wired |
| big_thud | 88666885925372 | ~0.6 s | .8 | 1 | no call site found | Sounds | - | FLAG .4 once wired |
| pickup | 97315544055472 | ~0.14 s | .35 | 1 | Bootstrap:1415, DinoMotion:277 (both on every food gain) | Sounds | every 0.2-1 s while eating, thousands per run | spam risk |
| pickup_hi | 86225160041514 | ~0.14 s | .35 | 1 | CombatHud:261 | Sounds | per pickup/heads-up | spam risk |
| pickup_lo | 80767583749596 | ~0.14 s | .35 | 1 | CombatHud:200 | Sounds | per pickup | spam risk |
| run_start | 87202810278231 | ~0.5 s | .25 | 1 | Bootstrap:1485 | Sounds | once per run | no |
| run_end | same asset | 0.6 s | .2 | .9 | Bootstrap:1485 via playCue | Sounds | once per run | no |
| shop_buy | 102585210519734 | ~0.8 s | .35 | 1 | Bootstrap:447, :886 (nest open) | Sounds | per purchase | no |
| shop_refresh | 91960074825710 | ~1.4 s | .45 | 1 | Bootstrap:674, HubTravelClient:67 | Sounds | per restock, per travel | reused for travel |
| weather_start | 120619985059497 | ~1.8 s | .2 | 1 | Bootstrap:1273 | Sounds (not Weather) | per event, minutes apart | no |
| level_up | 135894580270926 | 1.5 s | .4 | .95 | Bootstrap:1402, :1574 via playCue | Sounds | per level, plus nest opened | borderline |
| fusion_reveal | 90816090310479 | ~2.4 s | .75 | 1 | FusionMenu:830 | Sounds | per fusion | FLAG .375 |
| ui_click | 77237659470894 | ~0.05 s | .4 | 1 | Bootstrap:119, FusionMenu:296 | Sounds | every button | quiet, but .4 |
| hatch tap / crunch / chime | HatchPresentation crunchId / chimeId | short | .16 / .38 / .24 | 1.5 / 1 / 1 | HatchPresentation:97-99, 151, 170 | Sounds (raw, no gap) | 3 taps + 1 per egg | crunch .38 |
| Weather beds and accents (rain, thunder, blizzard, volcano, quake, bloodmoon, aurora) | none yet (all ids "") | loops | .16-.26 beds, .4-.5 accents | 1 | WeatherAudio.client, WeatherVisuals | Weather | per event | silent now; accent .5 is high, see BD-132 |

Lengths marked `~` come from docs/63 and were not re-measured. Asset ids are unchanged by this audit.

### Overlap moments
- **Run end**: run_end (0.6 s), level_up (1.5 s), nest opened (level_up again) and crystal / nest toasts. BD-258 already serialises these through `Sfx.playCue` (0.6 s stagger, drop after 3 s). The crystal reward has no sound of its own. Open: a level-up plus a nest opening plays the SAME level_up twice in a row.
- **Hatch**: hatch_crack (tap) + three hatch_crack_stage + hatch_reveal_X + the HatchPresentation crunch and chime fire in about the same second; the crack asset is used by two cue names (pooled separately, so their gaps do not coordinate). The reveal sting and the chime are two stings at once. The max-2 rule is not met.
- **Weather start**: weather_start sting plus the bed fade-in plus the toast. Low risk, quiet (.2).
- **Eating**: pickup fires from Bootstrap and DinoMotion for the same food gain (same name, shared 0.06 s gap, so one survives). CombatHud adds pickup_lo / pickup_hi with their OWN gaps, so variants could stack (fixed by the global throttle below).

### Spam and missing throttle
- **Fixed in this PR**: a global Rapid throttle (0.15 s) shared by pickup / pickup_hi / pickup_lo across all call sites.
- Still open: ui_click gap .04 s (fast tapping stacks 3 pooled voices); hatch tap/crunch/chime have no gap or pool; weather accents only have their own gaps.
- Not done: rate jitter (docs/63 suggests +/- jitter) is not applied anywhere; identical pitch repeated is fatiguing at 40-400 eggs.

## 2. Soft-sound style guide (docs/87 rules made checkable)
1. Quiet: cue volume 0.15-0.35 normally; the loudest cues (legendary reveal, fusion) at most **0.9** in the table, which `Sfx.MaxCueVolume` clamps. Prefer 0.7 or less so final gain stays at or under 0.35 at slider 100%.
2. Soft, short, no sharp attack: at least 10 ms fade-in, no hard transient, no energy above roughly 8 kHz, no noise bursts, no sirens. Prefer bubbly, marimba, soft bell. UI ticks 50-150 ms, rewards 0.5-1.5 s, rare moments up to 2.5 s.
3. Max 2 simultaneous cues. Reward cues go through `Sfx.playCue`; a hatch uses one tap/crack OR the stage cue, one reveal sting, never chime plus reveal.
4. Priority (high to low): reveal rarity sting, fusion_reveal, level_up, run_end, shop_buy, weather accent, pickup, ui_click. A higher cue ducks lower ones by 40% for its length (BD-339); pickups and clicks are dropped, never queued.
5. Category budgets per second: pickups about 6 at most (now 1 per 0.15 s), UI 3, reward 1 (serialised), hatch 2, weather accent 1 per 0.6 s, beds one loop at .16-.26.
6. Pitch variation +/- 5% on repeated cues; never the same pickup variant twice in a row.
7. Every new sound: brief, registry line ([77](77-asset-registry.md)), owner listens before it ships. Settings Sound tab (master, Sounds, Weather sliders) stays.

## 3. Sound Lab plan (BD-081)
A Settings or dev "Sound Lab" page lists every row with a Play button, an A/B/C variant picker and a "pick" mark. The owner auditions by ear; an agent then writes the picks into the Sfx table. **Agents cannot audition.**

Candidate sounds (owner picks by ear):

| # | Sound | Variants |
|---|---|---|
| 1 | Egg tap / crack | A soft wood tick, B bubble pop, C ceramic knock |
| 2 | Hatch reveal common | A chirp, B small bell, C bubble |
| 3 | Hatch reveal uncommon | A two-note chirp, B marimba, C bubble pair |
| 4 | Hatch reveal rare | A bell arpeggio, B harp, C glass chime (soft) |
| 5 | Hatch reveal epic | A rising marimba, B pad swell, C music box |
| 6 | Hatch reveal legendary | A warm swell, B harp glissando, C soft horn |
| 7 | Hatch burst (missing) | A soft poof, B puff of air, C bubble burst |
| 8 | Hatch rattle (missing) | A tiny shake, B wobble blip |
| 9 | Shiny sparkle | A glitter, B soft high bell tail, C twinkle |
| 10 | BIG thud | A soft low pad bump, B drum with no click |
| 11 | Fusion build-up and payoff | A swirl plus bell, B hum plus chime, C bubble crescendo |
| 12 | Shop buy | A coin plink, B pop, C soft register |
| 13 | Level up | A three-note arpeggio, B sparkle, C marimba run |
| 14 | Run end chime | A current chime, B softer lower, C two-note fall |
| 15 | Crystal / reward collect (none today) | A glassy plink, B bubble, C soft ding |
| 16 | Nest opened | A wooden pop, B rustle plus chime |
| 17 | Pickup / food bite | A soft munch, B pop, C leaf tick (3 pitches) |
| 18 | UI click | A soft tick, B bubble |
| 19 | Weather start sting | A wind breath, B low pad |
| 20 | Thunder strike / roll | A distant soft rumble, B muffled boom |
| 21 | Volcano boom / quake burst | A low muffled thump, B drum rumble |
| 22 | Weather beds (rain, wind, aurora) | quiet loops |

Sources, all uploaded by the owner (Roblox audio must be uploaded by the creator through Creator Hub / Asset Manager; it is moderated, may have a monthly upload allowance and a review delay, and must be original or properly licensed): (a) the owner's own recordings or synthesis, e.g. `tools/generate_sfx.py` regenerated with softer settings (synthesized sound is fine as audio, unlike textures, but must be judged by ear); (b) Roblox Creator Store free audio, checking the licence and that the id is usable in this experience; (c) royalty-free or AI-generated packs whose licence allows games. Playback stays on the existing `Sound` + Sfx table; moving to the new `AudioPlayer` API is not needed for this pass.

## 4. Fixed in this PR (small and safe)
- `Sfx.MaxCueVolume = 0.9`; `Sfx.play` clamps each cue volume (hatch_reveal_legendary .95 now plays at .9). Asset ids and table values unchanged.
- `Sfx.RapidNames` / `Sfx.RapidGap` and pure `Sfx.rapidThrottled`: pickup, pickup_hi, pickup_lo share one 0.15 s throttle across all call sites.
- `tools/verify_audio.py` checks both. No locals added to `Bootstrap.client.luau`.

## 5. Bigger items (Kanban)
BD-339 priority ducking and max-2 voice limiter; BD-340 shiny_bang and big_thud have no call site; BD-341 hatch sound stack cleanup; BD-342 crystal and nest reward cue plus rate jitter; BD-343 Sound Lab page. BD-132 stays Backlog: no weather asset ids exist.
