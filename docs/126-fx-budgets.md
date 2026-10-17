# 126 FX budgets and the offline audit (BD-429, code side, 2026-10-16)

Status: PROVISIONAL budgets, CURRENT tool. Companion of [123 anime FX plan](123-anime-3d-fx-research-and-plan.md) (PR #252, phase 0). Labels: **CURRENT** = in code today, **PROVISIONAL** = a guess until a real phone is measured.

## What the tool does
`python tools/fx_budget_report.py --runner <luau>` (CI step "FX budget") does two things.

1. **Static inventory** of the client FX code (HatchSequence, MutationReveal, RareHatchClient when present, CosmeticVisuals, WeatherVisuals, CaveAtmosphere, FxRig, HatchFx, HatchEggV2, FxUi, FxRecipes, CosmeticEffects, MutationEffects, ShinyEffects, EffectsLod): `Instance.new` and pooled `acquire` counts per class (ParticleEmitter, Beam, Trail, lights, Highlight), highest literal `Rate`, number of `Emit` calls. Files missing in a build are listed, not fatal.
2. **Worst concurrent moment per device class**, computed from the real recipe modules (not copied numbers): the largest aura, the largest trail and a mutation on each of 12 players (full look for the nearest `fullDinos`, lite look for the rest, per `EffectsLod`), plus the heaviest weather event (phone density x0.5), plus the hatch UI frames (one egg at a time: Legendary Shiny, every cap at max) and the mutation panel. Three moments: the 15-egg reveal, the open world crowd, an aura party under a clear sky.

It exits non-zero when any moment exceeds a budget, so a new effect that pushes a moment over fails CI until it is trimmed or the budget is changed here with evidence.

## Budgets (PROVISIONAL, per whole scene)
| Counter | Phone | Tablet | Desktop | Meaning |
|---|---:|---:|---:|---|
| live3d | 3300 | 5600 | 7600 | particles alive at once in the whole scene, all emitters incl. weather (Rate x mean Lifetime). Not the "about 300" of docs/107, which is the cosmetic-only figure (auras, trails, mutations; model 168): [115](115-decisions-log.md) PB1 |
| big | 120 | 220 | 520 | alive sprites with peak size >= 6 studs (overdraw) |
| beams | 24 | 72 | 160 | enabled Beams |
| trails | 14 | 20 | 40 | enabled Trails |
| lights | 16 | 24 | 24 | enabled lights (2 per dino: aura glow + mutation glow) |
| ui | 130 | 160 | 220 | visible UI FX frames (hatch + mutation panel) |

**Phone beams and lights are read from [tools/qa/phone_budgets.json](../tools/qa/phone_budgets.json), the single source of truth shared with the BD-085 QA kit (docs/127, PR #257); the stricter value was chosen (beams 24, lights 16), with a one-line rationale per metric in the file. All PROVISIONAL until measured.** Today's phone worst case (39 beams, 24 lights) is therefore over these two budgets: a finding, not a build failure.

The first numbers are set just above today's worst case (a ratchet): they stop growth, they do not claim today's rig is comfortable. Today: phone worst moment is about 2700 live3d (blizzard dominates, 2/3 of it weather), 39 beams, 13 trails, 24 lights, 108 UI frames. OWNER QUESTION / open risk: 24 `PointLight`s on a low-end phone (no shadows, range 6-10) is unmeasured; if the probe shows a frame-time cliff, lower the lights budget and drop the lite glow light first.

Nothing visual was changed: no moment is over its budget at the CURRENT code.

## Global live-FX budget (BD-432, CURRENT code, PROVISIONAL numbers)
`EffectsLod.Live` caps the enabled beams, trails, lights and aura shells of the WHOLE scene (phone 24 / 14 / 16 / 1, tablet 72 / 20 / 24 / 2, desktop 160 / 40 / 24 / 3; phone beams and lights equal `tools/qa/phone_budgets.json`, `verify_fx` checks it). `CosmeticVisuals` asks `Lod.fit` before each rig: a look that does not fit steps down from full to lite, then is dropped. The local dino and the event-mutation cue never vanish (lite floor); the local dino is not counted against others' use. The aura shell (Epic+, full look, no Reduce Motion) is built only when `AssetSlots.Meshes.aura_shell_mesh` holds a real upload; the slot is empty today, so nothing is drawn. One `ribbonTexture()` helper gives every trail ribbon and orbit beam the shared `ribbonSoft` render (empty slot: plain coloured ribbon). The smoke layers already play the fx3 `smokeSheet` flipbook.

## Moment FX caps (BD-433, CURRENT code, PROVISIONAL numbers)
Three one-shot moments sit outside the live-FX budget above and have their own small caps in `EffectsLod`. The own-dino rim (`client/MomentRim`) is ONE extra `Highlight` for 1.5 s: `EffectsLod.rimFits(mode, live)` refuses it at Effects Off and when 30 Highlights are already alive (`RimHighlightHardCap` 31 minus one), a fused-tier rim is brightened instead of adding a second one, and a repeat inside 1.5 s is ignored. The shock dome (`FxRig`, mesh slot `shock_dome_mesh`) is limited by `EffectsLod.Domes` (phone 1, tablet 1, desktop 2) with `FxRecipes.DomeGap` 2 s between two. The rare-banner sweep is one UI image on the own banner only. `tools/verify_fx_moments.py` checks all of it offline; no phone measurement yet (BD-085).

## Studio measurement (the truth)
`tools/qa/fx_probe.client.luau` follows the probe conventions of [117](117-asset-quality-audit.md), but it is a CLIENT script (cosmetic, weather and mutation FX are built client-side).

1. Own temp Studio copy, Play mode, device emulator set to a phone profile for phone numbers.
2. Trigger the moment (hatch a Legendary, force a weather event, equip auras with friends or bots).
3. Run `tools/qa/fx_probe.client.luau` in the client datamodel after setting `DEVICE` and `MOMENT`. It samples 6 s and prints one `MOMENT` TSV row with peak live3d (estimated from Rate x mean Lifetime), big, beams, trails, lights, UI frames, one-shot emitter count, and real avg fps / worst frame ms.
4. Save rows to `fx.tsv`, then `python tools/fx_budget_report.py --runner <luau> --input fx.tsv` checks them against the same budgets. Record the numbers in the 123 cost table; replace PROVISIONAL guesses with them.

Not verified here: no Studio or phone run was made for this change.
