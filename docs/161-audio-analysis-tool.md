# 161 - Audio analysis tool (BD-637)

Status 2026-10-18: tool, tests and a first report on the real SFX pack are done (Review / test). **Follow-up the same day (BD-166 / BD-637 / BD-997):** the safe suggestions of the report were applied as numbers in `src/shared/Sfx.luau` (no file, no asset id changed), soft re-renders of the two worst files were made locally with ffmpeg (not uploaded), and a test now keeps the cue volumes quiet. See section "Fixes applied" below. Read with [87](87-vision-and-feel-guide.md) (calm sounds), [110](110-sound-audit.md) (cue table) and [63](63-sfx-pack.md) (the pack).

## Why

An agent cannot listen. Until now every sound row said "nobody listened, the owner judges by ear" (BD-166, BD-081, BD-258). That stays true for taste, but several complaints are about things a computer CAN measure: one sound is louder than the rest, one is shrill, one clips, one has a long silent lead. `tools/audio_report.py` measures those and draws a picture so a person can look at the sound.

## How to use it

```
python tools/audio_report.py assets/audio/sfx                          # one table, one line per file
python tools/audio_report.py assets/audio/sfx --compare                # + loudness outliers versus the rest of the pack
python tools/audio_report.py assets/audio/sfx --game src/shared/Sfx.luau --compare --out build/audio-images --md build/audio.md
python tools/audio_report.py new_sound.ogg --out build/audio-images    # a single WAV / OGG / MP3
```

Needs Python 3 and numpy. ffmpeg and ffprobe (default `C:/ffmpeg/bin`, or `FFMPEG=`/`FFPROBE=`) are needed for OGG/MP3, for the pictures and for a loudness cross-check; plain 16-bit WAV needs neither. No network.

## What it measures, in simple words

| Number | Meaning |
|---|---|
| peak dBFS, true peak | How close the loudest instant is to the digital ceiling (0). True peak also looks between the samples. |
| clip runs | Flat tops at the ceiling. Any run means the sound is distorted. |
| LUFS-M max | How loud the loudest 0.4 s feels (K-weighted, the broadcast standard, ITU-R BS.1770). This is the number used to compare sounds. Sounds under 0.4 s are padded with silence, so a tiny tick counts as quieter, as the ear hears it. |
| LUFS-I | Whole-sound loudness. The tool computes it itself; the ffmpeg value is printed next to it as a check (they agree within 0.1 LU on the pack). |
| lead / tail s | Silence before the sound starts (feels laggy) and after it (wasted time). Gate: -60 dBFS. |
| attack ms | Time from the first sound to 90% of the peak. Under 5 ms is a snap or click. |
| decay ms | Time from the peak until the sound has fallen 20 dB for good. |
| crest dB | Peak minus average level. A smooth tone is about 3, a click is 25 or more. |
| main Hz, centroid Hz | The strongest pitch, and the "centre of mass" of the sound (higher = brighter). |
| energy per band | Share of the sound in sub (20-100 Hz), low (100-400), mid (400-2k), presence (2-5k), high (5-8k), air (above 8k). Presence plus high plus air is "above 2 kHz". |
| harsh (0-100) | 60% from how much of the sound is above 2 kHz (the ear is most sensitive 2-5 kHz) plus 40% from a sharp transient (very fast attack AND a spiky shape). 55 or more = harsh. |
| verdict | calm, ok, loud, harsh, too quiet, clipped or silent, for a children's game. Worst problem first; every problem is listed in the report. |

`--game src/shared/Sfx.luau` adds the level the PLAYER gets: file loudness plus 20 x log10(cue volume), before the Master (0.5) and Settings sliders (0.8 x 0.7). A cue that carries another file's asset id (run_end plays the run_start chime since BD-166) is measured with the file that owns the id. Cue rate (pitch) is not applied to the loudness.

`--compare` lists the files side by side and flags any whose loudness is 4 LU or more from the pack median (3 LU is the usual tolerance), and any whose harshness is 20 points above the median.

The pictures (one PNG per file): waveform on top, spectrogram below (low pitch at the bottom, 20 Hz to 20 kHz, log scale). Guide lines: white at 100 Hz, 1 kHz and 10 kHz, **red at 2 kHz** (harshness starts), **orange at 8 kHz** (docs/110 says no energy above it). Bright blobs above the red line = bright sound.

## What it cannot tell you

- Whether a sound is **nice**, fits the game, or is bubbly. Taste cannot be measured.
- Whether a sound is **annoying when repeated** 100 times (repetition, pitch jitter, overlap with other cues).
- How it **mixes** with music, other cues and the phone speaker. Cues play together; the tool reads one file at a time.
- What was **really played** in a session: it does not read the game. It uses the cue volumes in `Sfx.luau` and ignores rate, jitter, ducking, sliders and EQ effects.
- Whether harsh is wrong: a 2 kHz bell may be exactly what the owner wants. The score says "this sits in the range the ear finds sharp", not "this is bad".

So the tool can flag **loud, harsh, clipped, inconsistent and silent**. Anything it calls ok or calm still needs the owner's ears (BD-081 stays open).

## Thresholds

All numbers that turn a measurement into a verdict live in ONE table, `THRESHOLDS` at the top of `tools/audio_report.py`, each with its reasoning in a comment (EBU R128 / BS.1770 references, mobile loudness targets, ISO 226 ear sensitivity). They are engineering starting points for a calm children's game, **not** owner-approved. If the owner's ears disagree, change the table there and record it here. Reference values were quoted from memory of the standards (no network); check them before relying on them for anything but ranking.

## Verification

`tests/test_audio_report.py` generates its own sounds (sine, clipped sine, silence, click, padded, shrill, loud, whisper, stereo, a shaped envelope) and checks peak, crest factor, loudness (against the BS.1770 value for a sine and against ffmpeg's ebur128), dominant frequency, band shares, clipping, silence, attack, decay, verdict words, outlier detection, the cue-to-file mapping and the picture output. First real run: [evidence/2026-10-18-audio-report/report.md](evidence/2026-10-18-audio-report/report.md) (17 files, pictures, culprit analysis for BD-166).

## Fixes applied (2026-10-18, BD-166 / BD-637 follow-up)

Numbers only, from the report's own suggestions. **Nobody listened; the owner must.** Full before/after table, pictures and the owner's upload steps: [evidence/2026-10-18-audio-fix](evidence/2026-10-18-audio-fix/README.md).

| Change | Where | Result by the numbers |
|---|---|---|
| `level_up` volume .4 to .3 | `Sfx.luau` | about 2.5 LU quieter, now at the pack median (-23.9 LUFS player level) |
| `shop_buy` rate 1 to .75 | `Sfx.luau` | lower and slower; harshness stays 60 until the new file is uploaded (rate alone does not fix it) |
| `shiny_bang` volume .8 to .5 | `Sfx.luau` | about 4 LU quieter; still scored harsh (98) until the new file is uploaded |
| `hatch_legendary` volume .85 to .7 | `Sfx.luau` | the optional quieting of a legendary payoff; the BD-437 reveal ladder is unchanged |
| `shop_buy_soft.wav` (rate .75, low-pass 4 kHz, 10 ms fade-in) | evidence folder, NOT uploaded | harshness 60 to 27 (ok); above 8 kHz 34% to 0% |
| `shiny_bang_soft.wav` (rate .70, 2x low-pass 3.5 kHz, 10 ms fade-in) | evidence folder, NOT uploaded | harshness 98 to 31 (calm); above 8 kHz 34% to 0% |

The Sfx module has no fade-in or EQ, so those parts live only in the new files. Re-render with `python tools/render_soft_sfx.py [--out DIR] [--check]` (needs ffmpeg; prints a note and exits 0 without it). When the owner uploads the new files, set the `shop_buy` rate back to 1 (the new file is already slowed) and register the ids in [77](77-asset-registry.md).

**Level checks** (`tests/test_sfx_levels.py`, part of `python -m unittest discover -s tests`, so CI runs it; it reads only the committed WAVs and `Sfx.luau`, and needs no ffmpeg except one re-render test that is skipped when ffmpeg is missing): every cue volume is in 0..0.9 and every everyday cue is at most .6; `level_up` at most .3, `run_end` at most .25; no cue is more than 4 LU above the median player level, except the rare payoff cues, which have their own caps (they step up on purpose, see [87](87-vision-and-feel-guide.md); holding them to 4 LU would flatten the reveal ladder; today they sit +5.5 to +7.8 LU over the median); only `shop_buy` and `shiny_bang` may still score harsh, and only while their asset id is the old one; the soft candidates must measure ok or calm. `tools/verify_audio.py` also checks the new volume numbers in the cue table.

## Suggested next steps (not done)

- Owner listens to the two soft candidates and uploads them if they are good (kanban BD-997); then the lead swaps the ids and sets `shop_buy` rate back to 1.
- Add `audio_report.py --check` to CI only after the owner approves thresholds (today it would fail on the existing pack by design: it reports problems).
