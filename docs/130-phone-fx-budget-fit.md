# 130 Phone FX budget fit (BD-438)

CURRENT BUILD BEHAVIOR (this change, flags unchanged). Budgets: `tools/qa/phone_budgets.json` (PROVISIONAL, 16 lights, 24 beams). Model: `tools/fx_budget_report.py`.

Before: phone worst case was 24 lights and 39 beams (15-egg reveal + rare hatch + mutation + blizzard + 12 players with aura, trail and mutation).

Change, only in `FxRecipes.resolve` for device `phone` and detail `lite` (the other players; the local dino is always `full`):
- Lite auras drop the PointLight glow and the beam rings (the smoke and sparkles stay).
- The lite mutation ring uses 1 beam (a wider soft arc) instead of 3. The mutation glow light stays, so a mutation is still readable.
- Weather has no lights, so weather is unchanged.

After: phone 13 lights and 17 beams worst case. Tablet and desktop numbers are unchanged. Effects Full/Lite/Off, Reduce Motion, the rare-hatch and the mutation reveal are untouched.

Not verified: no Studio or phone run was made. Real numbers need `tools/qa/fx_probe.client.luau` on a phone (BD-085).
