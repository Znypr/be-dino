# 73 Copy pass and Condition Shop (BD-100, BD-103)

## Copy pass
`src/shared/UIFormat.luau` is the only time/boost formatter (tests: `tools/verify_ui_format.py`, in CI).
- Time: `40 s`, `5 min`, `2 h`, `2 h 10 min`, `Ready in 3 h`; minutes are floored, never `5m 0s`.
- Boosts are percent (`Speed +20%`, `Growth +25%`); neutral ones are hidden, so the HUD shows nothing when no boost is active.
- Applied to: potion cards and confirms, active-buff HUD, nest countdowns and toast, weather timer, shop restock ("New offers in 2 min"), leap cooldown, egg timers, mutation/event/trail perks.

## Condition Shop
Crystal Shops > CONDITIONS shows, per condition, its name, a plain egg on a floor swatch and its chance (percent). No "x stats" text, no VIEW ODDS button; footer is "Unlocks at level N". Upgrade button unchanged.
Eggs come from the game renderer with `EggGenetics.neutral(id)` (cream/cream, `01_blank`).
`ShopOdds.lines` / `ShopOdds.conditionPercents` stay callable but no condition screen opens them. The condition odds screen MUST return before Robux crystal packs are ever enabled (the random-egg VIEW ODDS stays).

## Art gap (BD-103)
`EggAppearance`/`EggGenetics.tint` never read `conditionId`, so all five (Cracked, Dirty, Normal, Rainbow, Astra) render as the same plain egg; the name and chance label are the only difference. Cracked only differs in the hatch cutscene. All five need real art; no hand-drawn substitutes. A test pins this so it fails (prompting the art update) once the renderer distinguishes them.
