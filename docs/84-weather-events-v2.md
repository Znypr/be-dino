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
