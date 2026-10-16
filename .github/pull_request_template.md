## What and why

## Evidence (tests run, Studio/phone checks, or "not verified")

## Handbook check (docs/114)
- [ ] Vision/feel: calm, bubbly, friendly; checked against docs/87 on a screenshot or marked "not verified"
- [ ] Design language: low-poly facets, no ellipses/primitive code art, matte (gloss only fused tiers), eyes glossy black + white dot
- [ ] Palette: colours from handbook section 5; currency crystals amber/yellow
- [ ] Lighting: right for its place (island bright; cave DIM lamp-lit; weather never inside the cave)
- [ ] Sound: soft, quiet, short, max 2 cues, priorities kept; marked "unheard" if not owner-judged
- [ ] Asset quality bar (8.1): grounded, no overlap, scale, budget, pivot, collision, registry line
- [ ] UI bar (8.2): text >= 14 px, targets >= 44 px, contrast >= 4.5:1, kid words (docs/72), phone + desktop
- [ ] FX bar (8.3): calm, budget stated, Reduce Motion version
- [ ] Economy numbers match handbook section 9 (or doc and code updated together)
- [ ] Art rule: no code-drawn final art, generated meshes only, flags off by default, Place1.rbxl untouched

## Quality gates (docs/117 section 4; world, cave, assets, lighting or palette changes)
- [ ] `python tools/verify_world_overlap.py` and `tools/verify_cave_overlap.py` pass
- [ ] `python tools/qa/palette_report.py` passes (no NEW offenders; fixed ones removed from KNOWN)
- [ ] Grounding, palette and budget probes re-run in my own Studio copy and `tools/qa/ground_report.py` / `budget_report.py` pass with `--input`, or marked "not verified"
- [ ] Screenshots per place checked with `tools/qa/luminance.py` (island, cave heart, cave station), or marked "not verified"
