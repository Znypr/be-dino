# 84 Weather events v2 (owner feedback 2026-10-14)

Owner, after checking the weather events in Studio: "pretty weak, minimal, boring. Stronger, more colourful, more aggressive."
Evidence: a thin 36-part rain pool, a pink tint and a toast; volcano and earthquake showed nothing.

## Roles
- **Designer:** each event gets its own mood, colour and one signature moment (bolt, lava bomb, quake burst, aurora curtains, blood pulse).
- **Engineer:** client-local only (no gameplay or server change). Lighting grade, Atmosphere haze, Bloom and SunRays per event, blended in and out
  over about 2 s; particle rigs that follow the player; one-shot effects (bolts, lava bombs, shock rings); camera shake bound after the camera script.
- **Art:** phase 1 uses built-in Roblox particle textures. Phase 2 replaces them with Blender-rendered flipbooks (smoke puff, branching bolt,
  rain streak, snowflake, ember, dust, shock ring, aurora curtain, lava glob) like the Mythic Glow set.
- **Audio:** thunder, rumble, wind, lava impact. Needs the sfx upload (docs/83 section 4).
- **QA:** Studio screenshot per event, phone density (half rates), Reduce Motion (docs/72: grade at half strength, no particles, no shake).

## Per event
| Event | Mood | Signature moments |
|---|---|---|
| Rain | grey-blue, haze, dark | streak rain, ground splashes, low mist |
| Thunderstorm | darker, violet, heavy haze | forked bolts every 4-9 s, white flash and bloom, shake |
| Blizzard | whiteout fog, blue-white | 1100 snow flakes, side gust streaks, drift clouds, sun rays |
| Volcanic Bloom | orange sky, glare, heavy bloom | far eruption column, ash fall, rising embers, lava bombs with trails, impact bursts and shock rings, rumble |
| Northern Lights | teal, bloom | 4 animated colour curtains in the sky, glowing motes |
| Earthquake | dusty tan | shake bursts with shock rings, dust clouds, falling rubble |
| Blood Moon | crimson fog, dark | giant pulsing moon with halos, red motes, red ground fog, red pulses |

Every event also shows a title card ("VOLCANIC BLOOM!") with a scale-in, so the start is felt.
Phase 2 and 3 are tracked as BD-131 and BD-132.

# Weather v3 (owner feedback 2026-10-15)
Owner, after playing v2: "Weather events should be even stronger, especially the Northern Lights were quite boring: more hue effects, a fully
colored sky. Overall more usage of smoke and mist in the distance as well, limiting the view distance."

Data and math moved to `src/shared/WeatherLooks.luau` (pure, no Roblox types); `src/client/WeatherVisuals.client.luau` draws it.
`tools/verify_weather.py` (in the workflow) checks look completeness, particle budgets, the aurora palette, fog and blend math, and that
nothing creates Instances inside the per-frame loop.

## View distance (Lighting.FogStart / FogEnd / FogColor + fog banks)
Studio test: `Atmosphere.Density` alone showed no fog in the playtest place, classic `Lighting.FogStart/FogEnd/FogColor` did. v3 therefore drives
classic fog per event (FogEnd blended in 1/distance so the view closes in smoothly) and keeps Atmosphere density, haze and decay as an extra layer.
On top, four large soft smoke volumes in a ring (125 studs out) for every event, with the centre empty, so far scenery fades into colour.
The near area stays readable: fog starts at 25+ studs (blizzard 12), plus a neutral near-lamp (PointLight, range 32) and an event glow light.

| Event | Fog start - end (studs) | Distance layers |
|---|---|---|
| Rain | 40 - 220 | grey-blue fog banks, four rain curtains 130-140 studs out, ground mist |
| Thunderstorm | 30 - 170 | dark violet banks, curtains, forked bolts and sheet flashes |
| Blizzard | 12 - 50 (whiteout) | white wind-driven banks, drift clouds, side gust and flurry streaks |
| Volcanic Bloom | 40 - 180 | three eruption columns 250-400 studs out with ash plumes, an ash ceiling 150 studs up, red-black banks |
| Northern Lights | 140 - 520 | low teal mist; the sky itself is the effect (below) |
| Earthquake | 25 - 110 | dust haze banks, ground dust, rubble |
| Blood Moon | 100 - 300 | crimson fog walls, ground fog, moon 230 studs out (inside the fog end so it stays visible) |

Every event also gets a horizon DepthOfField (far blur, off on phones), a sky colour shift and darker exposure where it fits, and bloom.

## Northern Lights
A fully coloured sky from any camera angle: a "sky shell" of 33 sheer neon slabs (3x3 ceiling, four walls of 3 segments x 2 bands) follows the player,
each slab with its own hue; 28 vertical rays in four parallax layers converge overhead; five rippling arcs at different heights and speeds; a ground ring;
motes, twinkling sky sparkles and a glow light that tints the ground and the dino. All colours come from one palette (green, teal, violet, magenta,
blue-violet, teal) that cycles in 26 s with slow noise and a per-object hue offset. Lighting.ColorShift_Top/Bottom, fog colour, ambient, Atmosphere
colour/decay, bloom, exposure and star count follow the same cycle. Reduce Motion: static grade only, no shell, rays or particles.

## Weather v3.1 fixes (owner playtest 2026-10-15)
- Fog culls everything beyond FogEnd; that cut was the hard red/teal silhouette against the sky. A box of five fog-coloured slabs sits just inside FogEnd, so the
  sky and the faded world are one colour (smooth, no edge). It also hides the default sun, moon and stars, so the blood moon shows exactly one moon. The default
  Sky's celestial bodies are switched off during events too.
- Readability: at 30 studs fog covers at most 10% (fog starts at 25-100 studs), blizzard view 110 (was 50), quake 220, volcano 320 with a brown-orange haze,
  lighter fog-bank particles (transparency 0.82-0.9), no colour-shift tint. Enforced by `tools/verify_weather.py`. The tables above show the v3.0 numbers; the
  current ones are in `WeatherLooks.luau`.
- Earthquake: anchored on the terrain under the root (the ray ignores the dino), three flat segmented shock rings with thinning width, 12 radiating cracks, dust burst,
  rock chips, camera shake and a quake cue for the sound layer.
- Northern Lights: the ground ring, the SurfaceGui shell and the near rays are gone. The sky is the fog-coloured box (hue cycling) plus three high curtain arcs of 14
  ribbons each, 230-300 studs out, with sparkles.
- Audio: see docs/85. `weather_start` volume 0.2.

## Intensity and budgets
Rain 1400 streaks/s (thunder 2000) with more splash and a darker grade; bolts every 2.2-5 s with two forks, 35% double strikes, sheet flashes every 1.2-3 s;
blizzard 1300 flakes/s; volcano a lava bomb every 0.45-1.1 s and three eruption columns; quake shake 0.3 constant and 0.95 on bursts with much more dust.
Caps (desktop, phone halves every rate): at most 6000 concurrent particles and 500 concurrent big (30+ stud) sprites per event, 4 bolt slots,
6 lava bomb slots, 6 impact bursts, 6 shock rings, 140 beams. Lightning, bombs, bursts, rings and aurora parts are created once at start and reused
(no per-frame Instance creation, no Debris). Reduce Motion: grade at half strength, no particles, no shake, no bolts or bombs.
