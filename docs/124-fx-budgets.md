# 124 FX budgets and the offline audit (BD-429, code side, 2026-10-16)

Status: PROVISIONAL budgets, CURRENT tool. Companion of [123 anime FX plan](123-anime-3d-fx-research-and-plan.md) (PR #252, phase 0). Labels: **CURRENT** = in code today, **PROVISIONAL** = a guess until a real phone is measured.

## What the tool does
`python tools/fx_budget_report.py --runner <luau>` (CI step "FX budget") does two things.

1. **Static inventory** of the client FX code (HatchSequence, MutationReveal, RareHatchClient when present, CosmeticVisuals, WeatherVisuals, CaveAtmosphere, FxRig, HatchFx, HatchEggV2, FxUi, FxRecipes, CosmeticEffects, MutationEffects, ShinyEffects, EffectsLod): `Instance.new` and pooled `acquire` counts per class (ParticleEmitter, Beam, Trail, lights, Highlight), highest literal `Rate`, number of `Emit` calls. Files missing in a build are listed, not fatal.
2. **Worst concurrent moment per device class**, computed from the real recipe modules (not copied numbers): the largest aura, the largest trail and a mutation on each of 12 players (full look for the nearest `fullDinos`, lite look for the rest, per `EffectsLod`), plus the heaviest weather event (phone density x0.5), plus the hatch UI frames (one egg at a time: Legendary Shiny, every cap at max) and the mutation panel. Three moments: the 15-egg reveal, the open world crowd, an aura party under a clear sky.

It exits non-zero when any moment exceeds a budget, so a new effect that pushes a moment over fails CI until it is trimmed or the budget is changed here with evidence.

## Budgets (PROVISIONAL, per whole scene)
| Counter | Phone | Tablet | Desktop | Meaning |
|---|---:|---:|---:|---|
| live3d | 3300 | 5600 | 7600 | particles alive at once, all emitters |
| big | 120 | 220 | 520 | alive sprites with peak size >= 6 studs (overdraw) |
| beams | 48 | 72 | 160 | enabled Beams |
| trails | 14 | 20 | 40 | enabled Trails |
| lights | 24 | 24 | 24 | enabled lights (2 per dino: aura glow + mutation glow) |
| ui | 130 | 160 | 220 | visible UI FX frames (hatch + mutation panel) |

The first numbers are set just above today's worst case (a ratchet): they stop growth, they do not claim today's rig is comfortable. Today: phone worst moment is about 2700 live3d (blizzard dominates, 2/3 of it weather), 39 beams, 13 trails, 24 lights, 108 UI frames. OWNER QUESTION / open risk: 24 `PointLight`s on a low-end phone (no shadows, range 6-10) is unmeasured; if the probe shows a frame-time cliff, lower the lights budget and drop the lite glow light first.

Nothing visual was changed: no moment is over its budget at the CURRENT code.

## Studio measurement (the truth)
`tools/qa/fx_probe.client.luau` follows the probe conventions of [117](117-asset-quality-audit.md), but it is a CLIENT script (cosmetic, weather and mutation FX are built client-side).

1. Own temp Studio copy, Play mode, device emulator set to a phone profile for phone numbers.
2. Trigger the moment (hatch a Legendary, force a weather event, equip auras with friends or bots).
3. Run `tools/qa/fx_probe.client.luau` in the client datamodel after setting `DEVICE` and `MOMENT`. It samples 6 s and prints one `MOMENT` TSV row with peak live3d (estimated from Rate x mean Lifetime), big, beams, trails, lights, UI frames, one-shot emitter count, and real avg fps / worst frame ms.
4. Save rows to `fx.tsv`, then `python tools/fx_budget_report.py --runner <luau> --input fx.tsv` checks them against the same budgets. Record the numbers in the 123 cost table; replace PROVISIONAL guesses with them.

Not verified here: no Studio or phone run was made for this change.
