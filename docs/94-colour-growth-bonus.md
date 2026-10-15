# 94 Colour growth bonus (BD-172)

Status: **PROVISIONAL numbers**, code in review. Owner example: black = 5%, double black = 10%.

## Rule
- Every egg colour has a rarity tier from the shared ladder (`RarityCurve`, docs/88): Common 0, Uncommon 1, Rare 2, Epic 3, Legendary 4, Mythic 5.
- Colour bonus (percent) = tier of the primary colour + tier of the secondary colour, **capped at 10**. One tier = 1 percent point, so a one-colour dino counts the same colour twice (double).
- It multiplies **growth gained** (never score, eggs, crystals or speed): `gainedGrowth = food * GrowthPerFood * GrowthMultiplier`, where `GrowthMultiplier = min(GrowthCap, weather * potions * aura * mutation * ...) * (1 + bonus/100)`. The bonus sits after the existing cap, so potions and fusion are not clipped by it and the colour bonus is never more than +10%.
- Conditions are not involved (they never appear on dinos).

| Colours | Bonus |
| --- | ---: |
| Cream, Blue (Common) | +0% |
| Green (Uncommon) | +1% (+2% for two greens) |
| Teal, Pink (Rare) | +2% each |
| Amber (Epic) | +3% |
| Purple (Legendary) | +4% |
| Red, Black (Mythic) | +5% each |
| Black + Black | +10% (cap) |
| Red + Black | +10% (cap) |

## Where
- `src/shared/ColourBonus.luau` pure math (`percent`, `multiplier`, `text`).
- `src/server/ProgressionService.luau`: reads the server-held `EquippedGenesJson` once a second, applies the multiplier, publishes `ColourGrowthPercent` (display only).
- Dino Details and the Index "My dinos" panel: "Colour bonus +N% growth" trait row (`FusionSelection.details`, hook `catalog.colourBonus`).
- Hatch paint-bucket chip: second line under the colour name.
- Dino Index species card: replaces "Special variant" for gene dinos.
- Test: `tools/verify_colour_bonus.py` (tiers, double, cap, unknown/junk input, max multiplier 1.10).

## Open
- Stacking with fusion tier stat boosts is plain multiplication; owner to confirm.
- 1 percent per tier and the 10 cap are tuning knobs (`ColourBonus.PercentPerTier`, `MaxPercent`).
