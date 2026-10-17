# 153 WeatherVisuals split into focused client modules (BD-627)

Status: **Review / test** (offline proof only; no Studio run, no phone run, no flag or stored-data change). Owner: LEAD (engineering hygiene, owner delegated). Date: 2026-10-18.

## Why

`src/client/WeatherVisuals.client.luau` (1,065 lines) was the client script closest to Luau's 200 local-register limit: `tools/verify_local_budget.py` counted **147** live locals in its main chunk (fail line 185, compiler limit 200), the highest in `src/` after `Bootstrap.client.luau` (144, split in BD-543). Every new weather effect adds top-level locals, so the next few would have broken the whole weather client.

## What changed (pure moves)

The script's setup code moved, **unchanged**, into six sibling `ModuleScript`s. Each is `return function(ctx) ... end`: the script builds them once, in the original order, from one context table (`folder`, `player`, `random`, `phone`, `DENSITY`, `fx`, `Cave`, later `kit` and `curtainEmit`). Function bodies are not re-indented.

| File | What it holds |
| --- | --- |
| `WeatherVisuals.client.luau` | services and requires, post effects (grade, bloom, rays, depth of field), atmosphere, clouds, device class / `DENSITY` / fog cap, the lamp, the main `Heartbeat` loop and the camera-shake render step |
| `WeatherKit` | shared helpers: texture reader `tex` / `rateOf` (BD-131), `volume`, `emitter`, `burstEmitter`, `groundAt`, `worldAttachment`, `rayParams`, `PARKED`, `DUST_FX`, particle texture constants |
| `WeatherRigs` | the rain / thunder / blizzard / volcano / aurora / quake / blood moon particle rigs, the fog banks, the volcano columns, the textured aurora curtain emitter |
| `WeatherSky` | blood moon (core, halos, optional textured disc) and the aurora curtain ribbons, with `updateMoon` and `updateAurora` |
| `WeatherStrikes` | pooled lightning bolts, shock rings, lava impact bursts, lava bombs, `stopOneShots` |
| `WeatherQuake` | pooled ground cracks, rocks, prop wobble, feet dust, crack decal (`pulse`, `update`, `stop`) |
| `WeatherTitle` | the big event title card and the soft cave toast (`show`, `soften`) |

Main chunk locals: **147 to 85**. The largest module is `WeatherRigs` (14.5 KB); the script itself went from 70 KB to 17 KB.

### The only text edits inside moved code

1. `flash`, `shake` and `pulse` were three plain locals shared by the one-shots and the main loop. They are now fields of one table, `fx` (`fx.flash`, `fx.shake`, `fx.pulse`), passed through the context. Values, ramps and order are the same.
2. `updateAurora` takes the ramp `k` as a last parameter (it used to read the main loop's local).
3. The blood moon block of the loop (18 lines) is the body of `WeatherSky.updateMoon(root, now, moonOn, k)`; `nextPulse` and `auroraWasOn` live in `WeatherSky` with the code that uses them. The loop still computes `moonOn` and calls it at the same point (between the quake and the aurora).
4. Locals that exist only to name a helper (`local seq, tex, ... = kit.seq, kit.tex, ...`) and the `Emitter` type alias (structural, repeated per module) were added.

Instance creation order is unchanged (rigs, lamp, moon and curtains, bolts, rings, bursts, bombs, quake, title card), including the `PlayerGui` wait for the title card.

## Proof that nothing changed

* A line-multiset diff of the old file against the seven new ones: every old line appears in the new set except the lines listed above (the `fx.` rewrites, `updateAurora` signature and call, the moon block, the removed state locals) and two section comments. Everything new is a header, a `local x = kit.x` line, a require, `end` or a `return {...}`.
* `luau-analyze` reports no unknown global that the old file did not already report (the Roblox globals), so no name was lost in the move.
* Every static verifier that read the script as one text now reads `tools/weather_sources.py` (`weather_text()` = the script followed by every part, `main_text()` = the script only, for the checks about the per-frame loop): `verify_weather`, `verify_cave_weather`, `verify_cave_lighting`, `verify_phone_guards`, `verify_settings`, `fx_budget_report` (its inventory row is identical: 2 emitters, 4 beams, 1 trail, 4 lights, max rate 70, 6 emits). Their assertions are unchanged except `shake=` becoming `fx.shake=` (three places) and the moon check reading `WeatherSky.updateMoon`. `tools/asset_slots.json` readers name the part that holds each slot.
* `verify_sources`, `verify_local_budget` (and `--selftest`) pass; see the PR for the full verifier list.

## Not verified

No Studio or phone run. The first Studio check should play Rain, Thunder, Volcano, Quake, Aurora and Blood Moon once (title card, particles, bolts, bombs, cracks, camera shake) and enter the cave during one of them; the code path is the same, but nothing here renders it.

## Adding to weather

Put a new rig in `WeatherRigs`, a new one-shot in `WeatherStrikes`, a new sky prop in `WeatherSky`; give the main script only what must run every frame. `tools/weather_sources.py` finds new parts from the `local X=require(script.Parent.WeatherY)` lines of the main script.
