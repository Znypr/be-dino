# Audio fix candidates, 2026-10-18 (BD-166, BD-637, BD-997)

Made with `python tools/render_soft_sfx.py` (ffmpeg) and measured with `python tools/audio_report.py` ([docs/161](../../161-audio-analysis-tool.md)). **Nobody listened to anything: the owner must listen.** The numbers say "less sharp" and "quieter"; they cannot say "nice", "bubbly" or "still sounds like a coin". Nothing was uploaded to Roblox and no asset id was changed.

Files here: `shop_buy_soft.wav`, `shiny_bang_soft.wav` (the candidates), `report.md` (full numbers, old and new side by side), `pictures/` (waveform on top, spectrogram below; red line = 2 kHz where sharpness starts, orange = 8 kHz; compare `shop_buy.png` with `shop_buy_soft.png`, and `shiny_bang.png` with `shiny_bang_soft.png`: the bright blobs above the red line are gone).

## Before and after, in plain words

| File | Harshness (55 or more is harsh) | Above 2 kHz | Above 8 kHz | Loudest 0.4 s | Verdict |
|---|---:|---:|---:|---:|---|
| shop_buy.wav (in game now) | 60 | 89% | 34% | -12.8 LUFS | harsh |
| **shop_buy_soft.wav** (new) | **27** | 32% | 0% | -15.5 LUFS | **ok** |
| shiny_bang.wav (in game now) | 98 | 100% | 34% | -20.1 LUFS | harsh |
| **shiny_bang_soft.wav** (new) | **31** | 36% | 0% | -26.9 LUFS | **calm** |

How they were made (from the current files, nothing else added):

- `shop_buy_soft.wav`: play 25% slower and lower (about 5 semitones), low-pass at 4 kHz, 10 ms fade-in. A 5 kHz low-pass (the first idea) only got harshness to 38, still "a bit bright", so 4 kHz was used. Length 0.8 s to 1.07 s. Rate alone or a filter alone left harshness at 60 (first report).
- `shiny_bang_soft.wav`: play at 70% speed (about 6 semitones lower), two low-pass stages at 3.5 kHz, 10 ms fade-in. One filter stage left harshness at 80 or more, because the sound is a spike more than it is bright. Length 1.7 s to 2.43 s (it has a 1.5 s silent tail that could be trimmed). It loses its sparkle: this is the file where the owner's ears matter most.
- Both are 16-bit mono WAV, 44.1 kHz, together 0.3 MB (limit 5 MB). Their peaks are lower than the rest of the pack on purpose (-6 and -13 dBFS); the cue volume in `Sfx.luau` is the knob.

## What changed in the game right now (numbers in `src/shared/Sfx.luau`, no new sound file)

| Cue | Before | Now | Effect |
|---|---|---|---|
| level_up | volume .4 | **.3** | about 2.5 LU quieter; it was the loudest cue at run end; now at the pack median |
| shop_buy | rate 1 | **.75** | lower and slower; this alone does NOT fix the sharpness (score stays 60): it needs the new file |
| shiny_bang | volume .8 | **.5** | about 4 LU quieter, a stopgap until the new file; still scored harsh (98) |
| hatch_legendary | volume .85 | **.7** | the optional quieting of a legendary payoff; the five-step reveal ladder (BD-437) is untouched |

Player-level loudness of the pack (median) went from -22.3 to -23.9 LUFS. Not done: a fade-in or an EQ in the game (the Sfx module has neither), which is why the new files exist. Not done: lowering the epic and legendary reveal stings to .7 (they step up on purpose; a test caps them instead).

## Owner steps to put the soft files in (upload route: [docs/63](../../63-sfx-pack.md))

1. **Listen first.** Play `shop_buy_soft.wav` and `shiny_bang_soft.wav` from this folder next to `assets/audio/sfx/shop_buy.wav` and `shiny_bang.wav`. Decide: softer and still fine, or too dull. If too dull, tell the lead which one; the recipe is one line each in `tools/render_soft_sfx.py` and can be tried again with a brighter cut.
2. Creator Hub > Creations > the account or group that owns Be Dino! > Asset Manager > Audio > Import. Select the two WAV files and import. Audio must be uploaded by the experience owner; agents never upload.
3. Wait for moderation (minutes to longer; it can be rejected). Keep the names `shop_buy_soft` and `shiny_bang_soft`.
4. Copy the two numeric asset ids and give them to the lead (kanban BD-997).
5. The lead then: sets the new ids in `src/shared/Sfx.luau`; sets the `shop_buy` rate back to **1** (the new file is already slowed; leaving .75 would slow it twice, a test checks this); sets the `shiny_bang` volume the owner likes (.5 to .8); copies the soft WAVs into `assets/audio/sfx/` and `manifest.json` so the report measures what plays; adds two lines to [docs/77](../../77-asset-registry.md); and re-runs `python tools/audio_report.py assets/audio/sfx --game src/shared/Sfx.luau --compare`.
6. Listen in a real run: tap a nest after a run (shop_buy) and hatch a Shiny (shiny_bang).

## Honest limits

- Taste: nobody listened. The tool measures loudness, brightness and the sharpness of the start of a sound, nothing else.
- The ffmpeg filters are simple (rate change, low-pass, fade). A real re-render by a sound designer (Blender or an audio tool) could do better; these are the cheapest candidates, not final art.
- `level_up` still starts fast (2.8 ms) and `shop_buy` plays on every nest tap. Whether that tires the ear over a long session only listening can tell.
