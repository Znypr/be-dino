# 117 Asset quality audit and the automated quality gates

Written 2026-10-16 (branch claude/quality-gates). Purpose: the owner found sunk props, overlaps, too-bright cave lighting, off-palette crystals and low-quality assets BEFORE any machine did. This doc records what the new gates measure, what they found on current main (Build 020 playtest profile, `CaveHub = true` in a temp Studio copy) and the one command list every agent runs. Rules come from [114](114-handbook.md) (section numbers below); open items are kanban BD-409..BD-417. Labels: MEASURED (a tool printed it), LEAD (my choice, owner may overrule), NOT VERIFIED.

## 1. The gates

| Gate | Handbook | What | Where it runs | Command / files |
|---|---|---|---|---|
| Grounding | 8.1 item 4 | raycast every placed generated prop, report below terrain > 0.3 and floating > 0.3 studs (0.5 before BD-417) | Studio (own copy) + offline report | `tools/qa/ground_probe.server.luau`, `tools/qa/ground_report.py` |
| Overlap (island) | 8.1 item 5 | solid kit-collider footprints pairwise (pure Luau placement) | offline, CI | `tools/verify_world_overlap.py` |
| Overlap (cave) | 8.1 item 5 | cave footprints, paths, pads, lava basin | offline, CI | `tools/verify_cave_overlap.py` (existing) |
| Palette | 5, 5.3, 5.10 | dominant hue buckets of each prop texture vs zone rules | Studio probe + offline report | `src/shared/AssetPalette.luau`, `tools/qa/colour_probe.server.luau`, `tools/qa/palette_report.py` |
| Lighting | 6 | mean luminance of screenshots per place | Studio screenshot + offline | `tools/qa/capture_window.ps1`, `tools/qa/luminance.py` |
| Budget | 8.1 item 8, 107 | real parts / lights per place in Studio, offline triangle estimate | Studio probe + offline | `tools/qa/budget_probe.server.luau`, `tools/qa/budget_report.py`, `tools/verify_world_budget.py` |

The `.server.luau` probes are run with the Studio MCP `execute_luau` (datamodel Server, Play mode) and return TSV text; the python reports read it (default input = the committed probe of the current main build in `tools/qa/data/`, so CI can run them without Studio; after a Studio run pass `--input your.tsv`).

## 2. Findings (MEASURED, 2026-10-16)

### 2.1 Grounding, island world kit (3,555 props probed, 55 lying logs not graded)
- **Root cause found (BD-409):** every generated prop was centred on its pivot. `Arena.generatedProp` set `Model.WorldPivot` but a Model with a `PrimaryPart` pivots on that part's `PivotOffset`, so `PivotTo(ground)` put the mesh CENTRE on the ground. First probe: every tree and bush kind below the terrain (canopy_l 58 of 58, worst 39.9 on slopes; conifer_l 92 of 92, worst 50.7) and all 31 small boulders. Studio's earlier 56-of-985 count missed this because it compared against the layout height.
- **Second cause (BD-409):** rocks and landmarks were not raycast-corrected; the voxel surface is about 2.3 studs above the analytic layout height, so boulders (pivot 2.3 below the ground, height 1.5-2.7) were completely inside the terrain.
- **Fix:** `mesh.PivotOffset = CFrame.new(0, -Size.Y/2, 0)` in `Arena.generatedProp`; Terrain raycast with a footprint-wide lowest-sample rule for rocks and a raycast for landmarks.
- **After the first fix (#217):** plants below the terrain 0 (every tree, bush, fern, grass and flower probed); rocks and landmarks 35 of 354 deeper than the RockSink allowance on steep slopes (worst 5.4, four spires; BD-416); landmark stone arch floats 0.71.
- **Still floating 0.5-1.1 studs on slopes: 195 plants** (ferns a/b 40+50, bush_a 35, bush_b 17, conifer_l 17, canopy_l 12, cycad_l 9, standing dead_l 8, others 7): the bottom rests on the highest trunk sample + 0.2 (BD-417). Not visible at a glance, but listed.


### 2.1b Slope grounding fix (BD-416, BD-417; branch claude/grounding-slopes, MEASURED 2026-10-16 in a temp Studio copy)
- **Root causes found:** (a) giant-layer rocks (badlands spires, bare boulders) were never raycast-corrected (Arena only handled the `rock` layer), so they kept the analytic height; (b) the placement footprint came from the kit EXTENT times scale but the generated mesh is fitted INSIDE the extent, so placement and probe sampled different footprints (boulder lowest ray 1.4 studs lower than the probe's); (c) plants rested on the highest sample of a wide trunk footprint + 0.2, above the probe's narrow footprint.
- **Fix (`BiomePlacement.Ground`, Arena):** the model is built and scaled first, so footprint and embed use the REAL mesh size. Policy table `Ground.Policy`: plants HIGHEST of 5 rays at the stem footprint (min(1, 4% of size)) minus `RootSink` 0.15 (roots meet the ground, nothing floats); rocks, spires, ledges, landmarks LOWEST of 5 rays at the whole base (30% of the mesh, max 6) minus the 12% RockSink embed (a pillar never hangs on its downhill side); giant-layer rocks follow the rock rule; spires and ledges are not placed on slopes steeper than `TallMaxSlope` 25 degrees (one spire became a boulder). Offline tests: `verify_owner_feedback_p1.py` (policy, rule per kind), `tests/test_quality_gates.py` (limits).
- **Gate tightened:** island sunk allowance beyond RockSink 6.0 -> 0, plant float 1.2 -> 0.3 (probe FLOAT 0.5 -> 0.3).
- **Result (probe of 3,558 island props, 55 lying logs not graded):**

| | Before | After |
|---|---|---|
| island rocks/landmarks deeper than allowance | 35 (worst 5.44) | **0** |
| island plants floating > 0.3 (before: > 0.5) | 195 listed at > 0.5 (worst 1.13) | **0** |
| landmark stone arch floating | 0.71 | 0 |
| cave sunk/floating | rim pieces 0.50 by design | unchanged, 0 else |

### 2.2 Grounding, cave (215 props probed)
0 floating, 0 sunk except the rim pieces (cave_wall_pillar 10, wall_arch_small 4, wall_boulder_l 2): 0.50 below the floor, which is the design (`CaveProps.place`: rim pieces at floor - 0.5). Stalactites, hanging moss and stepping stones are placed off the floor on purpose and skipped.

### 2.3 Overlap
- Island: 849 solid props (still 849 and 0 overlaps after BD-416/417) (trees, giants, rocks, landmarks), **1 solid/solid overlap before** (ruins altar x a mossy boulder at (-28,-187)); **0 after** (landmarks keep clear by their half DIAGONAL, `BiomePlacement`). Cap 0 in CI.
- Cave: `verify_cave_overlap.py` stays green (0).
- NOT graded: shrub/ground-cover versus solids, canopy-versus-canopy (forest), lying logs.

### 2.4 Palette (56 props: 43 cave, 13 island; 14 offenders after the crystal stopgap)
- **Currency/shop crystals:** `hub_crystal_l` was 0% amber (blue band), `hub_crystal_s` blue/purple. **Stopgap in this PR:** `CaveHubProps.Warm` flat amber (255,190,60); the gate now reads both as amber. A real regenerated amber mesh remains BD-400.
- **13 cave props read cool in a warm cave** (BD-414; limit 35% of coloured pixels in cyan..magenta): counter_stone 100%, lectern_book 100%, stalagmite_l 100%, stalagmite_s 100%, round rock 100%, stalactite 100%, bench_stone 98%, flat rock 85%, lantern_post 76%, cauldron 76%, stalagmite_cluster 76%, mossy boulder 71%, gong 64%. This matches the screenshots (teal and blue-grey rocks among the warm lit props). Caveat: many are low-saturation blue-greys; the 0.2 saturation floor counts them. The threshold is LEAD.
- **Island:** `rock_pillar` 34% blue-violet (limit 20%, BD-415); `rock_mossy_boulder` 20% (borderline, passes). Decoration `rock_crystal` is exempt inside the cave (handbook 5.3).

### 2.5 Lighting (screenshots of own Studio window, HUD hidden, viewport crop)
| Place | Mean luminance | Range | p5 / p95 |
|---|---|---|---|
| cave Heart | 0.293 | 0.15-0.35 | 0.091 / 0.526 |
| cave potions station | 0.270 | 0.15-0.35 | 0.042 / 0.582 |
| cave fusion station | 0.294 | 0.15-0.35 | 0.058 / 0.650 |
| island meadow noon | 0.387 | 0.35-0.75 | 0.198 / 0.722 |
Evidence images: `docs/evidence/2026-10-16-quality-gates/` (viewport crops). **The ranges are not in the handbook as numbers.** The cave band 0.15-0.35 came from the lead brief; the island band 0.35-0.75 is my LEAD choice ("bright daylight"). Confirm both with the owner and then write them into [114](114-handbook.md) section 6 (open question, see section 6 below). The cave Heart sits near the top of its band (0.293), so "too bright" cave reports will show as a FAIL above 0.35. NOT VERIFIED: weather states, other stations, phone brightness.

### 2.6 Budget (Studio parts, MEASURED)
Island world kit 4,625 parts (cap 5,550; unchanged by BD-416/417, re-measured), cave hub 300 parts (cap 410), whole scene at join 8,441 (cap 9,150), enabled scene lights **16 of 16** (at the cap: the next cave light needs a trade), cave particle emitters 10 enabled. Offline estimate (`verify_world_budget.py`): all caps OK; phone parts 3,514 and triangles about 548 k are over the rule of thumb (WARN, docs/107; phone not measured, BD-085).

### 2.7 Re-run after BD-416/417 (2026-10-16, temp Studio copy, CaveHub = true)
Grounding: island and cave green (above). Palette: probe re-run, the 56 props gave the same buckets as the committed file (spot-checked, not diffed line by line), 14 offenders, all KNOWN and now flagged OWNER-DECISION-PENDING. Budget: island 4,625, cave 300, join 8,441, lights 16 of 16 (committed numbers still true; island mesh parts 3,558). Overlap: 0 (island), cave verifier green. **Lighting NOT re-run:** the Studio client viewport reported 1x1 and PrintWindow returned a blank (0.103 flat) image in this session, so no fresh luminance numbers exist; section 2.5 stays the latest measurement and this PR does not touch lighting.

## 3. How to capture the screenshots (agents)
1. Open YOUR OWN temp copy of the build (`python tools/build.py --profile playtest`, copy the rbxlx to your temp folder, `sed -i 's/CaveHub = false/CaveHub = true/'` in the copy, start Studio with that path, find your id with `list_roblox_studios`). Never touch `Place1.rbxl` or other windows.
2. `start_stop_play` true; on the Client datamodel hide every ScreenGui (`PlayerGui` children `Enabled = false`); on the Server `Character:PivotTo(...)` to the Heart (0, 9, 580), a station or the meadow (0, ground + 4, 30), wait 4-6 s.
3. `powershell -File tools/qa/capture_window.ps1 -Title <your rbxlx name> -Out shots/<place>__<name>.png` (PrintWindow of that one window; works while other windows have focus). `mcp__Roblox_Studio__screen_capture` does not render play mode or ViewportFrames, do not use it for these.
4. `python tools/qa/luminance.py --check-dir shots` (place names: `island`, `cave_heart`, `cave_station`). Close and delete your Studio copy at the end.

## 4. THE command list (run before every PR that touches world, cave, assets, lighting or palette)
```
python tools/build.py && python tools/build.py --profile playtest
python tools/verify_world_overlap.py --runner <luau>
python tools/verify_cave_overlap.py --runner <luau>
python tools/verify_world_art.py --runner <luau> && python tools/verify_world_budget.py --runner <luau>
python tools/qa/palette_report.py --runner <luau> [--input colour.tsv]
python tools/qa/ground_report.py [--input ground.tsv]
python tools/qa/budget_report.py [--input budget.tsv]
python tools/qa/luminance.py --check-dir <shots>          # only with fresh screenshots
```
Studio part (own temp copy, Play mode): run `tools/qa/ground_probe.server.luau`, `colour_probe.server.luau`, `budget_probe.server.luau` with `execute_luau` (Server), save each output as TSV and pass it with `--input`; capture screenshots (section 3). CI runs the offline half (overlap, palette, ground, budget reports on the committed probes, luminance unit tests) in `.github/workflows/build-generated-place.yml`; the Studio half cannot run in CI, so a PR that changes placement, pivots, textures or lighting must attach fresh probe output or say "not verified".

## 5. What the gates do NOT prove
Looks-real-in-the-lighting (6) and art quality (low-poly, matte, scale ladder BD-407) are still a human judgement on a screenshot; the palette gate measures hue buckets only; the grounding probe grades the mesh bounding-box bottom, not the visible silhouette; budgets count parts and lights, not GPU time; no phone measurement (BD-085).

## 6. Open questions for the owner
1. Confirm the luminance bands (cave 0.15-0.35 mean, island 0.35-0.75 mean) so they can move into the handbook.
2. (OWNER DECISION PENDING; the 14 offenders are flagged in `palette_report.py` KNOWN, nothing recoloured or regenerated) Are cool blue-grey cave stones acceptable (decoration like the crystals) or must the cave be warm-grey only? (Decides BD-414: regenerate vs accept.)
