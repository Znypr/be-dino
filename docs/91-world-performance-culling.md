# 89. World performance budget and distance culling (BD-168)

Status: implemented, Studio-measured on a desktop PC; **not verified on a real phone**.

## Measured baseline (playtest build, Studio Play, BeDino-Perf window, desktop)
| Item | Before culling |
| --- | --- |
| BaseParts in workspace | ~7,500 (6,081 MeshParts) |
| Kit placements / native parts / triangles (server attrs) | 3,551 / 2,375 / ~155,000 |
| Parts within 150 studs: hub spawn / map centre | 92 / ~708 |
| Memory (Stats total) | ~3,295 MB (Studio, includes the editor) |
| Server and client heartbeat | 0.17 to 0.23 ms (not the bottleneck) |
Studio frame rate (~15 fps, all windows open) is not meaningful for phones; real fps needs a device.

## What was added
- `src/client/WorldCulling.client.luau` (new script; Bootstrap untouched). Decorative kit props under `BeDinoArena.WorldKit` are tracked by position and parented to nil beyond a radius (hysteresis x1.15, re-evaluated every 0.4 s after the player moves 6 studs). Nearest props are kept first inside a **part budget**.
- Never culled: collision proxies (`*Collider`; **phone class only since BD-496 (2026-10-17): culled by the same radius**, docs/146 s10), terrain, hub, crystals, server food logic. Food pickups are only hidden locally with `LocalTransparencyModifier` (radius x1.25), so server writes still apply.
- `Config.WorldCulling`: `Phone` radius 190 / budget 1,400, `Tablet` 280 / 2,400, `Desktop` 440 / 5,000 (PROVISIONAL, untested on devices). Class = non-touch Desktop, touch with short side >= 600 Tablet, else Phone. Set workspace attribute `PartBudgetOverride` to test another budget live.
- Admin panel (F2): "World parts" readout (class, visible props/total, budget, radius, instance count).

## After (desktop class, same build)
| Place | Props shown | Parts in workspace | Parts within 150 |
| --- | --- | --- | --- |
| Hub spawn | 1,432 / 3,551 | 5,390 | 94 |
| Map centre | 3,146 / 3,551 | 7,104 | 729 |
| South-east far | 1,346 / 3,551 | 5,304 | 652 |
| South-east, phone-like budget 1,400 | 1,400 / 3,551 | 5,358 | 729 |
Parts near the player stay the same (nearest props win); far parts drop by 25 to 30 percent on desktop and much more with the phone radius.

## Limits and honesty
- Memory did not fall: culled props stay in memory (detached, not destroyed), so this reduces render/scene cost, not RAM. True memory savings need StreamingEnabled or lower prop counts.
- Colliders stay (about 1,074 invisible parts); a later step can cull them too.
- Phone numbers (fps, thermals, memory) are unmeasured. Radius and budget values are guesses until tested on a phone.
- A prop destroyed by the server while culled is not noticed (props are static today).
Before adding BD-167 volume, test Phone class on a real device and tune `Config.WorldCulling`.
