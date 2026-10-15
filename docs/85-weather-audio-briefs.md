# 85 Weather audio: layer and sound briefs (owner feedback 2026-10-15)

Owner: "Weather events are silent" and "the weather start sound is super loud and annoying".

## What is built
- `src/shared/WeatherSounds.luau`: table of 11 sounds, one bed (loop) per event plus a few one-shot accents. **Every id is empty** (PROVISIONAL, do not invent ids);
  empty or malformed ids are skipped silently, like `Sfx.luau`. Volumes are final in-game values: beds 0.16-0.26 (cap 0.3), accents at most 0.5.
- `src/client/WeatherAudio.client.luau`: fades the active event's bed in and out over 2.2 s with the weather, honours SOUND ON/OFF (`Theme.HatchSoundEnabled`),
  and plays accents when `WeatherVisuals` fires a cue (`strike`, `eruption`, `quake`) through the cue bus in `WeatherSounds`.
- `weather_start` in `Sfx.luau` (the title-card sting) is now volume 0.2 (was 0.6; the global `Sfx.Master` 0.5 still applies). The current uploaded cue has a sharp
  transient: please replace it with the softer sound below (brief 12).
- `tools/verify_weather.py` checks the table (ids empty or valid, bed cap, one looping bed per event, rate-limited fades) and `tests/test_weather.py` checks the docs and the volume.

## Sound briefs (to generate and upload, then paste the id into `WeatherSounds.Sounds`)
All mono or stereo, 44.1 kHz, no clipping, peak below -6 dB, soft attack (no click at the loop point, loops are seamless), kid-friendly (nothing harsh or scary).

| # | Name | Length | Character |
|---|---|---|---|
| 1 | rain_bed | 20-30 s loop | steady soft rain on leaves and grass, no thunder, warm, low-mid heavy |
| 2 | thunder_bed | 20-30 s loop | heavier rain with a low wind, distant faint rumble underneath, no sharp cracks |
| 3 | thunder_roll | 3-5 s | low rolling thunder tail, slow attack and long decay |
| 4 | thunder_strike | 1-2 s | soft deep "thump" with a short crackle on top, rounded (no sharp transient), bass heavy |
| 5 | blizzard_bed | 20-30 s loop | whistling cold wind with gusts and fine snow hiss, gentle, no howl screams |
| 6 | volcano_bed | 20-30 s loop | deep low rumble and slow crackling embers, warm, tension but not scary |
| 7 | volcano_boom | 1.5-3 s | far eruption boom, low and round, with a short rock rumble tail |
| 8 | quake_bed | 20-30 s loop | low ground rumble with faint rattling pebbles |
| 9 | quake_burst | 1-2 s | dull earth thud with cracking stone and a short dust sigh |
| 10 | bloodmoon_bed | 20-30 s loop | low eerie drone, slow pulse, a few soft distant whispers, spooky but gentle |
| 11 | aurora_bed | 20-30 s loop | soft shimmering pads and airy choir, slowly rising and falling, magical |
| 12 | weather_start (replacement) | 0.8-1.2 s | soft rising chime or air swell, gentle attack, no sharp transient |

## Cue map
| Event | Bed | Accents |
|---|---|---|
| rain | rain_bed | none |
| thunder | thunder_bed | each lightning strike: thunder_strike now, thunder_roll 0.7 s later |
| blizzard | blizzard_bed | none |
| volcano | volcano_bed | lava bomb impact within 160 studs: volcano_boom |
| quake | quake_bed | each quake burst: quake_burst |
| bloodmoon | bloodmoon_bed | none |
| aurora | aurora_bed | none |
