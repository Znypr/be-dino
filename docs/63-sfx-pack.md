# 63 - Original SFX pack

All sounds are synthesized by `tools/generate_sfx.py` (numpy: envelopes, filtered noise, FM/additive tones, small reverb tails). No samples or third-party audio are used, so the pack is original work. Output: 17 mono 16-bit 44.1 kHz WAVs (~1.5 MB total, each 0.05-2.5 s, peak about -3 dBFS, faded edges) plus `assets/audio/sfx/manifest.json` (duration, peak, suggested volume, suggested rate jitter, trigger). Overview image: `docs/evidence/2026-10-14-sfx-pack/sfx-overview.png`.

Regenerate: `python tools/generate_sfx.py` (seeded, `--seed N` to vary). Verify: `python tools/generate_sfx.py --check` (CI) and `tests/test_sfx_pack.py`.

## Sounds

| Name | Length | Use |
|---|---|---|
| hatch_crack | 0.45 s | egg cracking |
| hatch_common | 0.75 s | common reveal, soft chirp |
| hatch_rare | 1.45 s | rare reveal, bell arpeggio |
| hatch_legendary | 2.45 s | rising stinger, use sparingly |
| shiny_bang | 1.7 s | shiny shimmer |
| big_thud | 0.6 s | heavy landing / stomp |
| pickup, pickup_hi, pickup_lo | 0.14 s | item pickup, pitch variants |
| run_start / run_end | 0.5 / 1.1 s | round start / end |
| shop_buy | 0.8 s | coin-like purchase |
| shop_refresh | 1.4 s | soft chime |
| weather_start | 1.8 s | wind swell |
| level_up | 1.4 s | short arpeggio |
| fusion_reveal | 2.4 s | build-up then payoff |
| ui_click | 0.05 s | button tick |

Fatigue guidance: the common hatch and pickups are short and quiet; apply the manifest `suggestedRateJitter` (random playback speed +/-) on each play, and rotate the three pickup variants. Reserve legendary/fusion for rare moments.

## Owner upload steps

Roblox audio must be uploaded by the account (or group) that owns the experience, otherwise other players may be unable to hear it. The uploader must be the owner; Claude/agents do not upload.

1. Creator Hub > Creations > (the experience's owner: your account or group) > Asset Manager > Audio > Import, then select the WAV files (bulk import works).
2. Wait for moderation; audio is reviewed automatically and can take minutes to longer, and can be rejected. Rename if needed, but keep the sound names.
3. Copy each asset's numeric ID.
4. Paste the IDs into the Sfx table in `src/shared/Sfx.luau` (entries are keyed by the sound names above; placeholders are empty until then), e.g. `hatch_common = "rbxassetid://<id>"`. Never guess IDs.

Uncertain, verify on the Creator Hub before relying on it: upload fees and free monthly quotas have changed over time (historically a per-upload Robux fee for longer clips, with free allowances varying by ID verification status; age-based rules for under-13 accounts may also apply). Short clips under about 10 seconds have generally been free; check the current rules at upload time. Also confirm whether the audio privacy/permission setting must grant the experience access.

## Silent-safe until then

Until real IDs are pasted in, the Sfx module treats empty/placeholder entries as "no sound": nothing is played, nothing errors, and gameplay is unaffected.
