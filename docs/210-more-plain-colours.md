# 210 More plain colours (BD-1037)

Status: **built and offline-verified, not looked at in Studio.** Owner words (2026-10-18, [186](186-pattern-colour-indexes-and-slower-species.md) section 5): "start with normal colours; glowing, chrome and special colours are low priority", and he wants real differences, not big numbers (same spirit as the patterns: "can you even see the difference?"). This page is the number behind the choice. Label of every statement: **CURRENT BUILD** (what the code does after this change), **OWNER TARGET** (what he asked for), **LEAD decision** (what I picked for him, with the way back at the end).

Picture for the owner: `docs/evidence/review-2026-10-17/458-egg-colours-contact-sheet-16.png` (a contact sheet drawn by a script, review only, **not game art**).

## 1. What changed, in plain words
- Before: 9 egg colours. After: **16**. Seven new plain colours: **Stone, Clay** (Common), **Lime, Sky** (Uncommon), **Lilac** (Rare), **Navy** (Epic), **Wine** (Legendary).
- Every tier now has 2 to 4 colours (Common 4, Uncommon 3, Rare 3, Epic 2, Legendary 2, Mythic 2). Mythic stays Red and Black.
- The nine old colours keep their ids, names, tiers and exact colour values. A dino a player already owns keeps its colours. Nothing in any saved profile is rewritten.
- All seven are flat matte colours: no glow, no chrome, no shifting. Those stay later (low priority).
- The chance of each TIER did not move (80 / 16 / 3.2 / 0.64 / 0.128 / 0.0256 percent for one colour slot). What moved is how a tier is shared: Common used to be 2 colours at 40 percent, now 4 colours at 20 percent each. Rarer tiers are harder to complete than before only because they have more colours in them (Legendary: Purple and Wine).
- The Colours tab of the Index now reads "Colours 0 / 16" and scrolls (6 rows of 3 cards).

## 2. How the colours were chosen (by numbers, not by eye)
Tool: `python tools/colour_distinct.py` (tests: `python tools/verify_colour_distinct.py`, run by CI). It reads the real colour table and measures:
1. **CIEDE2000** distance between every pair (about 1 = the smallest change an eye can see, 2 to 10 = noticed if you look, 20 and more = clearly another colour at a glance).
2. The same distance as seen with **colour-blindness** (protanopia and deuteranopia: red and green get confused; tritanopia: blue and yellow), Machado 2009 matrices at full strength.
3. The **middle blend**. A dino has a main and an accent colour and its tint is the two mixed (`EggGenetics.tint`, plain sRGB Lerp, the middle is share 50). A mix can look like a third colour (red and cream look like pink). Every 50 / 50 mix is measured against every single colour that is not one of its two ingredients.
4. Single colour checks: lightness not too dark or too light (Black and Cream are the only exceptions), not neon (chroma at most 80), and distance to the ground colours of the biomes (information only).

| Limit (PROVISIONAL, lead picked them) | Value | Meaning |
|---|---:|---|
| Normal vision, any two colours | at least 18 | a little under "clearly different at a glance", chosen so that 16 colours fit |
| After colour-blindness simulation | at least 10 | lower bar because those players lose information; a big difference in lightness still helps them |
| 50 / 50 mix against a single colour | at least 8 | about 100 mixes exist, a stricter bar cannot hold; 8 means "side by side you can tell them apart" |

How a new colour is found: a grid of matte colours (lightness 26 to 92, chroma up to 60) is searched per family ("a yellow-green", "a deep blue", "a brown" and so on, `BD1037_FAMILIES` in the tool). The search keeps all pairs above the limits and keeps every LIKELY mix (the pair has at least 0.05 percent chance) away from the other colours, then re-picks each colour with the others fixed until nothing improves (`python tools/colour_distinct.py families`). I chose the families (a friendly yellow-green, a pale sky blue, a lilac, a deep navy, a dark wine red, a grey and a brown); the exact value inside each family is the tool's.

Why 16 and not 18: 16 is the most the owner's ladder allows (Common 4 + Uncommon 3 + Rare 3 + Epic 2 + Legendary 2 + Mythic 2). By distance alone a 17th would still fit (a dull dark plum, #5D4662, passes at 1.17), but no tier has room and it would be the third dark colour next to Navy and Wine. An orange, a coral and a magenta do not pass at all when tried (0.6 to 0.7 on the pass mark of 1.0): they fall inside Red, Amber, Pink and Purple, which is the tool saying "you cannot tell it apart" (owner: same spirit as patterns).

## 3. The chosen colours
| Colour | Tier | Hex | RGB | Chance for ONE colour slot | Lightness L* | Chroma | Hue | Closest other colour (distance) |
|---|---|---|---|---:|---:|---:|---:|---|
| Cream | Common | #F7EAC4 | (247,234,196) | 20.001% | 93 | 20 | 94 | 18.2 (Lime) |
| Blue | Common | #2484D3 | (36,132,211) | 20.001% | 54 | 48 | 271 | 21.6 (Navy) |
| **Stone** | Common | #5A6C69 | (90,108,105) | 20.001% | 44 | 7 | 184 | 21.0 (Pink) |
| **Clay** | Common | #926C56 | (146,108,86) | 20.001% | 49 | 22 | 56 | 21.4 (Red) |
| Green | Uncommon | #1DAF4B | (29,175,75) | 5.334% | 63 | 70 | 145 | 18.4 (Teal) |
| **Lime** | Uncommon | #C4F180 | (196,241,128) | 5.334% | 90 | 59 | 123 | 18.2 (Cream) |
| **Sky** | Uncommon | #A2E5EE | (162,229,238) | 5.334% | 87 | 22 | 211 | 22.1 (Teal) |
| Teal | Rare | #16AA97 | (22,170,151) | 1.067% | 63 | 40 | 181 | 18.4 (Green) |
| Pink | Rare | #D74893 | (215,72,147) | 1.067% | 53 | 63 | 350 | 17.7 (Purple) |
| **Lilac** | Rare | #CDA9F9 | (205,169,249) | 1.067% | 75 | 45 | 309 | 24.1 (Purple) |
| Amber | Epic | #F1A024 | (241,160,36) | 0.320% | 72 | 73 | 73 | 24.2 (Cream) |
| **Navy** | Epic | #0F4995 | (15,73,149) | 0.320% | 32 | 48 | 285 | 21.4 (Black) |
| Purple | Legendary | #9E50CB | (158,80,203) | 0.064% | 49 | 74 | 316 | 17.7 (Pink) |
| **Wine** | Legendary | #871D2E | (135,29,46) | 0.064% | 30 | 48 | 21 | 24.0 (Red) |
| Red | Mythic | #ED2C21 | (237,44,33) | 0.0128% | 52 | 88 | 38 | 21.4 (Clay) |
| Black | Mythic | #1D2229 | (29,34,41) | 0.0128% | 13 | 5 | 267 | 21.4 (Navy) |

Bold = new. Names are one short word each (docs/72). An egg rolls two colours, each on its own with the chance above. The dino shows the **rarer of its two colours** (BD-1036), and boost points per tier are Common 0, Uncommon 1, Rare 2, Epic 4, Legendary 6, Mythic 10 (`GeneBoost`, `ColourBonus`): the seven new colours take their tier's points automatically (tests added).

What a dino shows, the chance that the rarer of its two colours is this tier (same as before, the tier chances did not move): Common 64.0%, Uncommon 28.2%, Rare 6.2%, Epic 1.27%, Legendary 0.26%, Mythic 0.051%. The waits (`python tools/simulate_colour_timing.py --runner luau.exe`, 3 eggs a minute, PROVISIONAL): the first dino with a colour of Rare or better after a median of 9 eggs (3 min), Epic 44 eggs (15 min), Legendary 226 eggs (75 min), Mythic 1,354 eggs (7.5 h). Unchanged by this PR, because only the split inside a tier changed.

## 4. Closest pair, before and after
| | Before (9 colours) | After (16 colours) |
|---|---:|---:|
| Closest pair, normal vision | **17.7** (Pink and Purple) | **17.7** (the same old pair; nobody can change an old colour) |
| Closest pair that includes a NEW colour | n/a | **18.2** (Cream and Lime) |
| Worst colour-blind distance, pair with a new colour | n/a | **10.9** (Cream and Lime, deuteranopia) |
| Worst colour-blind distance overall | 1.8 (Blue and Purple, deuteranopia) | 1.8 (the same old pair) |
| Pairs below a limit | 7 of 36 (all old) | 7 of 120 (the same 7 old pairs, **none with a new colour**) |
| Average distance to the nearest other colour | 23.7 | 20.7 (more colours in the same space) |

The seven old weak pairs (listed, never edited because stored dinos keep their colours): Blue and Purple, Teal and Pink, Green and Teal, Green and Amber, Green and Red (all hard for a colour-blind player) and Pink and Purple, Blue and Teal (close for everybody). This is **OWNER QUESTION material, not a decision**: if the owner wants them fixed later, the way is to retire a colour name for new eggs only (a new id and a new look, the old id stays valid forever); it is not part of this PR.

## 5. The 50 / 50 mixes (what a dino with two colours can look like)
Mixes closer than 8 to a single colour that is not an ingredient:

| Mix (50 / 50) | Looks like | Distance | Chance a dino has this pair | Involves a new colour |
|---|---|---:|---:|---|
| Teal + Wine (#4E6462) | Stone | 3.6 | 0.001365% | yes |
| Blue + Black (#20537E) | Navy | 5.1 | 0.00512% | yes |
| Red + Black (#852725) | Wine | 5.2 | 3.277e-06% | yes |
| Blue + Green (#209A8F) | Teal | 5.7 | 2.134% | no (nine old colours) |
| Teal + Red (#826B5C) | Clay | 5.8 | 0.0002731% | yes |
| Purple + Red (#C63E76) | Pink | 6.7 | 1.638e-05% | no (nine old colours) |
| Teal + Purple (#5A7DB1) | Blue | 7.5 | 0.001365% | no (nine old colours) |
| Sky + Navy (#5897C2) | Blue | 7.9 | 0.03414% | yes |

Findings: (1) the one that matters is **Blue + Green looks like Teal** (2.1 percent of dinos), it exists today and is made only of old colours; a dino with a Blue main colour and a Green accent has a middle tint that looks like Teal (Rare), so Teal is partly "fake-able" by a mix. Not touched by this PR. (2) The new colours add only very rare mixes (every one of them under 0.04 percent of dinos) and Stone and Clay, which are the greys and browns that any two opposite colours mix to, so a mix landing on them cannot be avoided. (3) Red + Black looks like Wine, but needs two Mythic colours (1 in 30 million): irrelevant.

## 6. Where the colour is shown (hatch chip, cards, dino)
- **The colour name chip** (hatch buckets, `HatchSequence`): the chip fill is the fixed card colour (61,58,73) with white text and a dark outline; the colour is only the small square dot. So the text contrast does not depend on the colour and is unchanged: white on the card is 11.1 : 1, and the dot has the 3 px dark outline.
- **Swatch against the chip card** (information, WCAG ratio and CIEDE2000 distance): the weakest new swatches are Wine (1.2 : 1, distance 25) and Navy (1.3 : 1, distance 20). Both are still farther from the card than Black (1.4 : 1, distance 11), which already ships and relies on its dark outline. `tools/verify_colour_distinct.py` fails if a new swatch is not farther from the card than Black.
- **Text on the colour itself** (only the Fusion detail chips "Colour 1: Lime", `FusionMenu.chip`: white text with a dark 2 px outline on the colour fill): pale colours (Cream, Lime, Sky, Lilac, Amber) have 1.2 to 2.1 : 1 for the white text alone, so those chips rely on the outline (the same already holds for Cream). Dark text would be 9 to 16 : 1 on them. Left as is; **P2 row for a Studio look** (BD-1142).
- **Dino bodies**: the tint is the primary and accent blended, then the cave or island lighting. New colours stay inside lightness 30 to 90 (Black is 13). The darkest new ones are Wine (30) and Navy (32), both much lighter than Black; under the dim cave light they are the ones to look at first. Not seen in Studio.
- **Ground it walks on** (information, `TERRAIN` in the tool): Stone is near Slate (7.1) and Clay near Sandstone (10.8); they are natural colours and a grey dino on grey rock is the camouflage a dino game can allow, but it is for the Studio look. Existing: Cream near Sand (11.2) and Black near Basalt (6.9).

| Colour | Tier | Swatch against chip card | Distance to card | White text on it | Dark text on it |
|---|---|---:|---:|---:|---:|
| Cream | Common | 9.2 : 1 | 65 | 1.2 : 1 | 16.0 : 1 |
| Blue | Common | 2.8 : 1 | 34 | 4.0 : 1 | 4.9 : 1 |
| Stone | Common | 2.0 : 1 | 22 | 5.6 : 1 | 3.5 : 1 |
| Clay | Common | 2.4 : 1 | 28 | 4.7 : 1 | 4.1 : 1 |
| Green | Uncommon | 3.8 : 1 | 50 | 2.9 : 1 | 6.7 : 1 |
| Lime | Uncommon | 8.5 : 1 | 69 | 1.3 : 1 | 14.8 : 1 |
| Sky | Uncommon | 7.9 : 1 | 62 | 1.4 : 1 | 13.7 : 1 |
| Teal | Rare | 3.8 : 1 | 46 | 2.9 : 1 | 6.6 : 1 |
| Pink | Rare | 2.8 : 1 | 34 | 4.0 : 1 | 4.8 : 1 |
| Lilac | Rare | 5.6 : 1 | 52 | 2.0 : 1 | 9.7 : 1 |
| Amber | Epic | 5.2 : 1 | 59 | 2.1 : 1 | 8.9 : 1 |
| Navy | Epic | 1.3 : 1 | 20 | 8.7 : 1 | 2.2 : 1 |
| Purple | Legendary | 2.3 : 1 | 29 | 4.7 : 1 | 4.1 : 1 |
| Wine | Legendary | 1.2 : 1 | 25 | 9.4 : 1 | 2.0 : 1 |
| Red | Mythic | 2.6 : 1 | 40 | 4.2 : 1 | 4.5 : 1 |
| Black | Mythic | 1.4 : 1 | 11 | 16.0 : 1 | 1.2 : 1 |

## 7. Saves, seeds and Build 020 (CURRENT BUILD)
- **Stored profiles:** nothing is rewritten. Every id that existed still exists with the same name and value, so every stored dino, egg and discovery log is valid. New colours appear only in new rolls. Index discovery ("Colours N / 16") counts what the player has actually found; a player who found 5 of 9 sees "5 / 16" (a total, not a regression).
- **Seeded rolls change** because the table changed (weights moved and the table has 16 rows). The golden profile fixture `tools/fixtures/profile_golden.json` is **re-recorded on purpose** (as BD-1033 and BD-1036 did): 181 steps, the stored data differs only because new eggs roll other colours. `verify_profile_golden.py` passes against the new fixture.
- **Rollback to Build 020 (known lock-out class):** the frozen Build 020 reader does not know the seven new ids, so it **fails closed** (`SchemaError`, nothing written, the store byte-identical) on a profile that holds a dino of such a colour. Same class as an Epic species or a newer potion ([111](111-rollback-drill.md) section 2). The right rollback target is the previous playtest tag, not Build 020; a rollback to a tag BEFORE this change would lock out the players who already hatched a new colour, who recover on roll-forward. Proven by `tools/verify_rarity.py` (the Build 020 `EggGenetics.valid` says no to each new id; the current one says yes). The three drills that make Build 020 open a profile written by the current code (`verify_rollback`, `verify_skins`, `verify_secret_species`) now write their profiles with the nine Build 020 colours (`profile_sources.drill_progression_module`), because a random hatch would otherwise always carry a new colour; the lock-out itself is asserted separately.
- **Flags:** none. The colours ship in the default profile like the BD-1036 weights. The Index tabs and the boost stay behind their own flags (unchanged).

## 8. LEAD decision (owner delegated 2026-10-16, applied 2026-10-19)
- **Decision:** add the seven colours above, 16 in total, Common 4 / Uncommon 3 / Rare 3 / Epic 2 / Legendary 2 / Mythic 2; equal split inside a tier; all matte; limits 18 / 10 / 8.
- **Options not picked:** (a) 18 colours with an orange, a coral and a magenta (the tool says they cannot be told apart from Red, Amber, Pink and Purple); (b) only 14 colours, no Lime (Lime is the weakest pass, 1.01 on the pass mark; it is the one to drop first, see below); (c) fix the seven old weak pairs now (stored dinos would change colour: not allowed); (d) glowing, chrome and shifting colours (owner: low priority, first the Studio test BD-1046); (e) move Black or Red out of Mythic (owner's ladder).
- **To overturn:** drop a colour you do not like by deleting its row in `ProgressionConfig.EggColors` and running `python tools/generate_drop_odds.py --runner luau.exe`, `python tools/build_catalog.py` and re-recording the golden fixture (the weights then need the equal-split search again, `python tools/colour_distinct.py families` for hex and the weight helper in section 9). To change a hex: run the families command with a different window (`BD1037_FAMILIES`), copy the hex, and update handbook 5.4 (`verify_handbook.py` enforces it). Players who already hatched a removed colour keep a valid id only if the row stays: **do not delete a row once a profile can hold it**; hide it from new rolls by giving it weight 0 in the roll instead (needs a small change, ask).
- **Not verified:** Studio (the look of each colour on a dino body, on the hatch bucket and on the chip), a phone, a colour-blind person looking at it, the owner's taste. The numbers prove "different", not "pretty".

## 9. How the weights were chosen
Integer weights out of `EggColorWeightScale` 10,000,000, equal inside a tier, strictly smaller per colour for a rarer tier, adding up exactly: Common 4 x 2,000,134, Uncommon 3 x 533,364, Rare 3 x 106,670, Epic 2 x 32,001, Legendary 2 x 6,400, Mythic 2 x 1,280. The tier totals match the ladder to within 0.001 percentage points (80.0054 / 16.0009 / 3.2001 / 0.6400 / 0.1280 / 0.0256). `verify_rarity.py` checks all of it.

## 10. Full distance table (all 120 pairs, closest first)
Columns: normal vision, then as seen with protanopia, deuteranopia, tritanopia. "normal" or "colour-blind" in the last column means the pair is below the limit (only the seven old pairs).

| Colour A | Colour B | Normal | Protan | Deutan | Tritan | Flag |
|---|---|---:|---:|---:|---:|---|
| Pink | Purple | 17.7 | 11.0 | 21.2 | 18.7 | normal |
| Cream | Lime | 18.2 | 13.2 | 10.9 | 27.2 | ok |
| Green | Teal | 18.4 | 20.1 | 24.5 | 3.4 | colour-blind |
| Stone | Pink | 21.0 | 16.2 | 13.5 | 42.2 | ok |
| Navy | Black | 21.4 | 23.9 | 22.4 | 20.7 | ok |
| Clay | Red | 21.4 | 11.7 | 15.9 | 20.7 | ok |
| Blue | Navy | 21.6 | 21.4 | 18.7 | 21.5 | ok |
| Sky | Teal | 22.1 | 20.5 | 19.9 | 17.3 | ok |
| Green | Lime | 22.4 | 17.9 | 21.0 | 23.7 | ok |
| Wine | Red | 24.0 | 20.8 | 26.3 | 22.7 | ok |
| Lilac | Purple | 24.1 | 24.2 | 22.2 | 24.2 | ok |
| Clay | Wine | 24.2 | 20.1 | 15.2 | 20.3 | ok |
| Cream | Amber | 24.2 | 23.6 | 20.4 | 22.5 | ok |
| Stone | Teal | 24.8 | 20.1 | 16.8 | 24.5 | ok |
| Stone | Black | 25.5 | 24.6 | 23.7 | 24.2 | ok |
| Navy | Purple | 25.6 | 11.9 | 17.1 | 41.9 | ok |
| Stone | Clay | 25.7 | 11.6 | 16.4 | 33.8 | ok |
| Blue | Stone | 25.7 | 26.3 | 24.0 | 18.5 | ok |
| Pink | Wine | 25.8 | 29.7 | 29.7 | 21.8 | ok |
| Cream | Sky | 25.9 | 22.1 | 26.7 | 34.9 | ok |
| Pink | Lilac | 26.5 | 25.1 | 21.9 | 30.0 | ok |
| Stone | Purple | 26.5 | 25.9 | 23.0 | 28.1 | ok |
| Stone | Navy | 26.9 | 24.7 | 24.8 | 12.5 | ok |
| Clay | Amber | 27.3 | 26.6 | 26.8 | 21.5 | ok |
| Pink | Red | 27.7 | 39.8 | 30.3 | 13.6 | ok |
| Sky | Lilac | 28.1 | 17.5 | 12.2 | 38.7 | ok |
| Clay | Pink | 29.7 | 29.4 | 19.5 | 15.4 | ok |
| Wine | Black | 30.1 | 13.2 | 25.7 | 28.6 | ok |
| Blue | Lilac | 30.5 | 14.5 | 20.9 | 41.9 | ok |
| Stone | Green | 30.7 | 30.2 | 27.6 | 24.3 | ok |
| Blue | Purple | 30.9 | 9.9 | 1.8 | 47.1 | colour-blind |
| Lime | Teal | 31.1 | 27.8 | 34.6 | 23.4 | ok |
| Lime | Sky | 32.1 | 33.4 | 35.8 | 13.0 | ok |
| Blue | Sky | 32.3 | 29.0 | 30.8 | 23.3 | ok |
| Blue | Teal | 32.4 | 29.3 | 22.6 | 10.0 | colour-blind |
| Cream | Green | 32.7 | 22.0 | 24.0 | 41.9 | ok |
| Purple | Wine | 32.8 | 38.4 | 44.7 | 26.2 | ok |
| Amber | Red | 33.1 | 27.4 | 14.4 | 19.0 | ok |
| Cream | Teal | 33.7 | 20.9 | 29.8 | 41.2 | ok |
| Purple | Black | 34.1 | 33.8 | 34.6 | 36.3 | ok |
| Green | Sky | 34.5 | 36.3 | 37.3 | 18.8 | ok |
| Clay | Black | 34.7 | 31.3 | 35.4 | 37.7 | ok |
| Lime | Amber | 35.2 | 16.3 | 11.8 | 43.0 | ok |
| Navy | Wine | 36.5 | 31.4 | 42.9 | 54.4 | ok |
| Cream | Clay | 36.6 | 35.1 | 32.8 | 35.0 | ok |
| Stone | Sky | 36.6 | 36.4 | 35.8 | 37.3 | ok |
| Stone | Lilac | 36.6 | 34.0 | 33.4 | 35.7 | ok |
| Clay | Purple | 36.8 | 40.2 | 40.8 | 11.5 | ok |
| Blue | Clay | 37.0 | 38.6 | 41.5 | 53.9 | ok |
| Stone | Wine | 37.6 | 18.0 | 18.7 | 40.2 | ok |
| Blue | Black | 37.7 | 40.5 | 36.3 | 39.9 | ok |
| Clay | Navy | 38.4 | 38.8 | 44.8 | 47.3 | ok |
| Pink | Navy | 38.7 | 13.1 | 31.4 | 57.8 | ok |
| Clay | Lilac | 39.1 | 42.6 | 41.9 | 26.6 | ok |
| Clay | Teal | 39.2 | 18.9 | 20.5 | 48.2 | ok |
| Purple | Red | 39.8 | 51.8 | 55.9 | 28.2 | ok |
| Stone | Red | 40.0 | 20.7 | 30.2 | 43.5 | ok |
| Teal | Lilac | 40.3 | 27.3 | 20.0 | 40.3 | ok |
| Stone | Amber | 40.9 | 34.5 | 39.9 | 44.0 | ok |
| Sky | Purple | 41.5 | 38.0 | 31.8 | 53.3 | ok |
| Cream | Stone | 41.7 | 39.6 | 42.1 | 44.8 | ok |
| Clay | Green | 41.9 | 21.9 | 12.6 | 49.0 | ok |
| Pink | Black | 42.1 | 28.1 | 36.2 | 39.6 | ok |
| Sky | Amber | 42.2 | 38.8 | 40.8 | 52.3 | ok |
| Cream | Lilac | 42.7 | 39.3 | 38.4 | 14.7 | ok |
| Lilac | Red | 42.8 | 55.0 | 51.8 | 35.4 | ok |
| Blue | Pink | 43.6 | 13.1 | 21.3 | 67.2 | ok |
| Green | Amber | 44.1 | 6.0 | 14.7 | 57.9 | colour-blind |
| Stone | Lime | 44.1 | 43.8 | 44.3 | 37.0 | ok |
| Lilac | Navy | 44.5 | 38.0 | 43.9 | 50.5 | ok |
| Teal | Amber | 44.5 | 24.4 | 33.7 | 56.1 | ok |
| Clay | Sky | 44.7 | 38.8 | 38.1 | 52.9 | ok |
| Clay | Lime | 45.1 | 37.4 | 32.5 | 49.2 | ok |
| Teal | Purple | 45.5 | 35.3 | 22.7 | 49.9 | ok |
| Teal | Navy | 45.5 | 41.8 | 34.9 | 31.1 | ok |
| Red | Black | 45.6 | 33.7 | 48.6 | 48.6 | ok |
| Cream | Red | 45.6 | 42.1 | 29.7 | 38.6 | ok |
| Blue | Wine | 47.7 | 42.3 | 45.9 | 70.2 | ok |
| Navy | Red | 48.5 | 48.5 | 61.6 | 63.3 | ok |
| Teal | Black | 48.7 | 46.6 | 40.2 | 48.0 | ok |
| Green | Lilac | 49.6 | 49.5 | 44.9 | 39.6 | ok |
| Blue | Red | 49.8 | 50.8 | 56.5 | 57.2 | ok |
| Sky | Pink | 50.5 | 34.7 | 22.8 | 67.4 | ok |
| Lilac | Amber | 51.5 | 53.5 | 51.8 | 21.8 | ok |
| Cream | Pink | 51.5 | 47.5 | 32.5 | 36.4 | ok |
| Blue | Green | 51.9 | 52.1 | 50.3 | 12.3 | ok |
| Lilac | Wine | 51.9 | 58.2 | 54.8 | 49.9 | ok |
| Cream | Blue | 52.2 | 47.4 | 52.6 | 42.9 | ok |
| Pink | Amber | 52.4 | 50.4 | 35.2 | 16.9 | ok |
| Green | Black | 53.2 | 54.0 | 48.5 | 47.2 | ok |
| Amber | Wine | 53.5 | 48.2 | 42.7 | 40.2 | ok |
| Sky | Navy | 53.6 | 49.2 | 51.5 | 45.7 | ok |
| Blue | Amber | 54.0 | 56.8 | 61.8 | 63.0 | ok |
| Green | Purple | 55.1 | 57.5 | 49.8 | 49.1 | ok |
| Teal | Pink | 55.3 | 27.3 | 3.3 | 65.9 | colour-blind |
| Sky | Red | 55.8 | 49.3 | 43.8 | 64.3 | ok |
| Cream | Purple | 58.6 | 55.1 | 53.0 | 35.8 | ok |
| Green | Navy | 59.2 | 60.0 | 57.5 | 31.3 | ok |
| Lilac | Black | 60.0 | 59.6 | 60.1 | 60.9 | ok |
| Amber | Purple | 61.5 | 62.6 | 61.5 | 25.7 | ok |
| Cream | Wine | 62.3 | 62.5 | 50.4 | 56.8 | ok |
| Amber | Black | 63.1 | 58.6 | 66.7 | 57.8 | ok |
| Blue | Lime | 63.5 | 58.7 | 60.9 | 29.1 | ok |
| Teal | Red | 63.5 | 29.5 | 30.0 | 65.0 | ok |
| Amber | Navy | 65.5 | 65.0 | 73.0 | 61.7 | ok |
| Cream | Navy | 66.0 | 62.4 | 68.2 | 60.7 | ok |
| Lime | Lilac | 66.1 | 51.6 | 48.0 | 27.5 | ok |
| Teal | Wine | 66.5 | 39.5 | 32.8 | 68.1 | ok |
| Lime | Red | 66.9 | 40.8 | 24.2 | 55.8 | ok |
| Sky | Wine | 71.7 | 62.1 | 53.6 | 74.4 | ok |
| Green | Red | 73.6 | 24.1 | 8.0 | 67.2 | colour-blind |
| Green | Wine | 74.9 | 43.4 | 27.8 | 69.4 | ok |
| Lime | Navy | 75.5 | 71.2 | 74.4 | 48.3 | ok |
| Sky | Black | 75.8 | 75.4 | 72.7 | 76.0 | ok |
| Lime | Pink | 76.5 | 55.8 | 37.0 | 54.9 | ok |
| Lime | Wine | 77.4 | 64.5 | 49.4 | 67.8 | ok |
| Cream | Black | 80.5 | 79.5 | 81.0 | 79.6 | ok |
| Green | Pink | 82.2 | 45.9 | 25.2 | 68.2 | ok |
| Lime | Black | 82.8 | 82.2 | 81.8 | 76.7 | ok |
| Lime | Purple | 83.2 | 66.0 | 60.9 | 50.8 | ok |
