# 226 Hatch pacing: fast Common and Uncommon eggs, full show for Rare and up (BD-1164), 2026-11-12

Status: **Review / test**. Code and offline tests are done. **Not seen in Studio, not seen on a phone, nobody has watched or heard it.**
Why: OWNER decision 2026-11-10 ([115](115-decisions-log.md)): in a batch the eggs stay one at a time in rising rarity; Common and Uncommon flash by in about 1 s each; Rare and up keep the full slow build-up and reveal. LEAD decision 2026-11-12: the first 3 eggs a brand-new save is shown always get the full show (first impression, ties in with the starter run, [225](225-starter-run-spec.md)).

Labels: section 1 is **CURRENT BUILD BEHAVIOR** (default profile, measured from the code). Sections 2 to 4 are **CURRENT BUILD BEHAVIOR of the playtest profile only** (flag `HatchFastCommonsEnabled`). The default build is unchanged (flag off). Every timing is **PROVISIONAL**. Presentation only: no server, odds, save or economy change.

## 1. Step 1: what one egg really takes today (measured from the code)

Source: `HatchTimeline.durations` and `HatchSequence.luau`. Full motion, v1 hatch. "Tap" is how long the player takes to tap after the hint appears; the table assumes 0.7 s (an assumption of this measurement, not a rule). The server answer arrives while the egg already wobbles (it holds at 0.35 s), so it adds nothing unless it takes longer than that.

| Egg | Build-up (2 paint buckets, rattle, 3 cracks) | Burst | Reveal settle | Reveal lag | To the tap hint | With the tap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Common, Uncommon | 3.60 | 0.60 | 0.80 | 0.10 | **5.10 s** | 5.80 s |
| Rare (+0.15 rattle) | 3.75 | 0.60 | 0.80 | 0.10 | **5.25 s** | 5.95 s |
| Epic (+0.30 rattle) | 3.90 | 0.60 | 0.80 | 0.10 | **5.40 s** | 6.10 s |
| Legendary (+0.50 rattle, +0.50 hold) | 4.10 | 0.60 | 1.30 | 0.10 | **6.10 s** | 6.80 s |
| Cracked (splat) | 3.60 | 0.70 | 1.00 | 0.10 | **5.40 s** | 6.10 s |

- There is **no auto-advance**: every egg waits for a tap (or Space, Enter, gamepad A).
- A tap during the build-up (allowed from 0.5 s) jumps to the burst: the shortest possible egg today is 0.5 + 0.6 + 0.8 + 0.1 = **2.0 s plus the tap, with two taps per egg**.
- **Mismatch found:** `Config.HatchRevealSeconds = 1` ("1 s per egg" in docs/09, docs/114 s11, the catalogue and the 2026-11-11 correction in docs/115) is **not read by any client or server code**. Only `tools/session1_smoke.luau`, `tools/verify_load.py` and the catalogue text use it. The real reveal is the 5 to 6 s above. Logged as C-56 in [116](116-handbook-conflicts.md).

Typical batches (rarity mix from the AGENTS.md examples; 2 of every 5 eggs Cracked-and-failed, which is the tier 0 config: 50% Cracked x 80% fail; every 5th hatching egg "notable", from the Studio count in BD-1056):

| Batch | Watching every egg | Tapping every build-up away |
| --- | ---: | ---: |
| 15 eggs (11 Common, 3 Uncommon, 1 Rare; 6 cracked, 1 notable) | **1:29** (89 s), 15 taps | 0:42 (42 s), 30 taps |
| 120 eggs (86 Common, 29 Uncommon, 4 Rare, 1 Epic; 48 cracked, 14 notable) | **11:51** (711 s), 120 taps | 5:38 (338 s), 240 taps |

Reproduce: `python tools/verify_hatch_pacing.py --runner <luau.exe> --report`.

## 2. Step 2: what the player sees with the flag on

- Still **one egg at a time**, in the order the server gives them (rising rarity). Nothing is merged or hidden.
- **Fast egg** (Common, Uncommon, and every cracked egg): a short wobble (0.30 s), the burst (0.15 s), the dinosaur pops in with its **name, rarity chip and the colour and pattern line** (0.50 s), then the next egg comes **by itself, no tap**. About **1.0 s** per egg (cracked: 1.15 s, the same splat, short). The egg shows its **real colours and pattern at once** (no paint buckets). Two sound cues at most (burst and the rarity's reveal cue).
- **Full show, exactly as today:** Rare, Epic, Legendary; every Shiny, BIG, event mutation, Rainbow, Astra and secret find (the same rule as "Skip the rest": `RevealSkip.isNotable`); an egg whose rarity cannot be read; **the first 3 eggs of a brand-new save**.
- **"Something special is coming":** when a Rare or better egg follows 2 or more fast eggs, the egg first holds still for 0.7 s, the glow rings swell once in the rarity colour, a soft screen flash, the line **"Ooh! Something special!"** and the existing soft `level_up` chime. Then its normal full build-up starts. Existing effects and an existing sound only: no new art, no new sound id.
- **The last egg of the party never moves on by itself:** DONE (and TRY AGAIN after a splat) stay the player's buttons.
- **Skip the rest** works as before (button on every card; on a fast egg it jumps to the burst or moves on). A tap on a fast egg cannot break it. X, Escape and a tap outside close as before.
- **Reduce Motion:** a fast egg is a 0.9 s fade, then the next; no lead-in.

## 3. Rules (pure, tested)

`src/shared/HatchPacing.luau` (`plan`): flag off -> always the full show, nothing touched. Otherwise, in this order:

1. brand-new save and one of the first 3 eggs shown -> full ("first");
2. cracked -> fast;
3. notable -> full;
4. rarity above Uncommon or unreadable -> full ("rare");
5. else fast.

`auto` = fast and more eggs are waiting. `special` = rule 4 and 2 or more fast eggs right before it.
`src/shared/HatchTimeline.luau`: `Fast`, `FastSplat`, `FastReduced`, `durations(..., fast)`, `readyAction` (wait / advance / hint), the lead-in clock (`supply(..., fast, lead)`, `leadGlow`). The party facts (`shown`, `fastRun`, `fresh`) live on the "Egg 3 of 15" party table and end with the party.

**"Brand-new save" on the client:** the save holds only the starter Compy when the party's first egg is put on screen (`FtueRules.collectionCopies`, read before the egg's dinosaur is added). The client has no lifetime hatch counter and this task may not change the server, so the rule is "the first 3 eggs of the first hatch party of a save that has never hatched a dinosaur". Limits: if that party is closed after 1 egg, the next party is not brand-new any more; a save whose first eggs all cracked stays brand-new until one hatches. An exact lifetime count needs one owner-only number from the server (follow-up, not built).

## 4. Step 3: after (same batches, flag on)

| Batch | Before (watching) | After | After, brand-new save | Taps before -> after |
| --- | ---: | ---: | ---: | ---: |
| 15 eggs | 1:29 (89 s) | **0:26** (26 s), 13 fast eggs, 1 lead-in | 0:41 (41 s) | 15 -> 2 |
| 120 eggs | 11:51 (711 s) | **3:25** (205 s), 104 fast eggs | 3:39 (219 s) | 120 -> 16 |

Per egg: Common / Uncommon 5.10 s + tap -> **1.00 s, no tap**; Cracked 5.40 s + tap -> **1.15 s, no tap**; Rare 5.25, Epic 5.40, Legendary 6.10 s + tap: **unchanged** (+0.7 s lead-in once after a fast run).
The 16 remaining taps of the 120-egg batch are the 14 notable eggs (Shiny, BIG, Rainbow, Astra), the Rare and Epic eggs that hatched, and DONE. BD-1056 (should notable eggs stop "Skip the rest"?) is the same open owner question; this change does not decide it.

## 5. Flag and files

- `HatchFastCommonsEnabled`: false in `Config.luau` and the default profile, true in the playtest profile ([157](157-playtest-profile-newest-features.md)), in the rehearsal list.
- `src/shared/HatchPacing.luau` (new), `src/shared/HatchTimeline.luau`, `src/client/HatchSequence.luau`. `Bootstrap.client.luau` and every server file are untouched.
- Check: `tools/verify_hatch_pacing.py` (rules, ordering, first-3, timeline, flag off = unchanged, the real `HatchSequence` in the engine mock with the flag off and on, measurement, wiring, 66 mutants), in the CI workflow.
- The close-path and small-window smokes (`verify_close_paths.py`, `verify_small_window.py`, `verify_hatch_polish.py`) check the full show: their copy of the Config keeps this one flag off, also under the all-on rehearsal ([152](152-switch-on-rehearsal.md)); the fast path runs in the same mock in `verify_hatch_pacing.py`.

## 6. Not verified

- **Not seen:** no Studio run, no phone, no child. Whether 0.5 s is enough to read a name, whether a 100-egg cascade feels calm or hectic (docs/87), and whether the lead-in reads as "special" are judgement calls for the owner.
- **Not heard:** the reveal cue once per second for a long batch, and the `level_up` chime as the lead-in cue.
- **Not run in the real engine:** the drawing code (`HatchSequence`) ran only in the offline engine mock (flag off and on: a fast egg moves on in about 1 s with no hint and no button, the lead-in line and cue appear and go, the last egg waits, X stops the party). The mock draws nothing: how it looks is unknown. The v2 hatch (`HatchV2`) with the fast path is untested.
- Real network delay: an answer slower than 0.35 s adds to every egg, before and after alike.
