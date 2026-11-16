# BD-1218 + BD-1219 audio: Studio load evidence (2026-11-16)

Place: `build/BeDino-audio-playtest.rbxlx` built with `python tools/build.py --profile playtest` from this branch (uncommitted at the
time, Build stamp `a19b2327*`), opened in its own Roblox Studio window (not the owner's Place1) and run with Play (Client datamodel).
**Nobody listened.** These are load / play / routing checks from the Studio MCP, not a listening test. The owner judges by ear (docs/87).

## Runtime checks (Client, flag on)
- `Config.AudioPolishEnabled = true` in the playtest build; `SoundService.AudioPolish` exists.
- Music: `Music_island` playing at 0.220 in `BeDinoMaster.BeDinoMusic` while `Location = Island`; home and hatch beds at 0.
- Crossfade: setting BeDinoUI `Screen = "hatch"`: +1.25 s island 0.110 / hatch 0.070, +2.75 s island 0 / hatch 0.140; back to `""`: +3 s island 0.220 / hatch 0.
- Footsteps: walking on Grass (MoveTo, speed 22) played 5 steps in 1.3 s (`Step1..3` in the Sfx group), alternating 9114165461 / 9114165789, rate 1.02 / 1.08, volume 0.080 (0.16 x Sfx.Master 0.5). The default human `Running` sound in HumanoidRootPart reads volume 0.
- Cues: after `AudioPolish.apply` every one of the 16 filled cues returned `Sfx.play = true`; spot checks `nest_open_cue`, `rare_hatch_fanfare`, `mutation_frost_reveal`, `hatch_burst` read `IsPlaying = true` at 1.1-1.2 s in `SoundService.BeDinoSfx` (volumes 0.20-0.25 after Sfx.Master).
- Console: no error or warning from AudioPolish, Sfx or the mixer. (Pre-existing lines unrelated to audio: an HudCohesion infinite-yield notice and ContentId failures for 6 non-audio ids.)

## Cue -> id table (all `IsLoaded = true` in Studio, creator checked with MarketplaceService:GetProductInfo)
| Cue | Asset id | Title (Creator Store) | Creator | Length |
|---|---|---|---|---|
| music island | 9046598930 | Watching the Garden Grow (a) | APMOfficial | 163.13 s |
| music home | 9046598509 | Tiny Twinkle Toes (a) | APMOfficial | 140.75 s |
| music hatch (softer) | 1842071889 | Whimsical Carousel (a) | APMOfficial | 134.54 s |
| hatch_rattle | 9112752910 | Bubble Wobble Comic Bloops Slight Rhythm 4 | ProSoundEffects | 0.68 s |
| hatch_burst | 9119378289 | Soft Suck Explosion Med Whoosh 8 | ProSoundEffects | 2.26 s |
| rare_hatch_fanfare | 9116395085 | Magic Glows Soft Clusters Of Chiming Hits 5 | ProSoundEffects | 4.46 s |
| mutation_dewdrop_reveal | 9126190364 | Water Drips Into Filled Bowl Cave Water Drop | ProSoundEffects | 1.95 s |
| mutation_charged_reveal | 9126072453 | Synth Sparkle Tone High Pitch Bell Tone Burst | ProSoundEffects | 1.37 s |
| mutation_frost_reveal | 9125644905 | Magic Twirling Small High Pitch Spinning Chime | ProSoundEffects | 3.07 s |
| mutation_seismic_reveal | 9114166629 | Dragon Footsteps 27 (rate 0.8) | ProSoundEffects | 0.52 s |
| mutation_ember_reveal | 9114446852 | Fire Whoosh 15 | ProSoundEffects | 0.83 s |
| mutation_aurora_reveal | 9125635650 | Magical Exit Sparkling Pass Bys Clinking Chime | ProSoundEffects | 3.81 s |
| mutation_bloodmoon_reveal | 9116394756 | Magic Glows Soft Clusters Of Chiming Hits 3 (rate 0.8) | ProSoundEffects | 3.34 s |
| defeat_soft | 9112752818 | Bubble Wobble Comic Bloops Slight Rhythm 3 (rate 0.8) | ProSoundEffects | 0.71 s |
| cracked_fail | 9113959343 | Crack Egg Crunchy 11 | ProSoundEffects | 1.02 s |
| crystal_cue | 9114619221 | Glass Tinks 3 | ProSoundEffects | 2.73 s |
| nest_open_cue | 9120873624 | Wooden Chest Open Close Cedar Box 5 | ProSoundEffects | 2.09 s |
| ui_open / ui_close | 9113537815 | Boink Wet Suction Pop Blip Hollow 3 | ProSoundEffects | 1.01 s |
| steps soft (grass, ground, plastic) | 9114165461, 9114165789 | Dragon Footsteps 5 / 11 | ProSoundEffects | 0.95 / 0.81 s |
| steps sand | 9118685591 | Rocks Dirt Impacts In Ground 12 | ProSoundEffects | 0.58 s |
| steps rock | 9118609285 | Rock Hits Rock On Rock Various Versions 10 | ProSoundEffects | 1.03 s |
| steps wood | 9114166137 | Dragon Footsteps 18 | ProSoundEffects | 0.93 s |
| steps snow / ice | 9126274134 | Wood Paddle Canoe Impacts Into Icy Snow | ProSoundEffects | 0.72 s |
| steps water (swimming) | 9120609652 | Water Wading Walking Through Shallow Pool 2 | ProSoundEffects | 2.37 s |

## Not covered
- Listening (loudness, character, harshness) - owner by ear.
- Phone, and a real run with a hatch, defeat, nest open, crystal pickup or mutation find (the cue wiring is offline-tested by `tools/verify_audio_polish.py`; hatch-side `cracked_fail` / `rare_hatch_fanfare` calls from the hatch code are not wired: PR #599 owns those files).
