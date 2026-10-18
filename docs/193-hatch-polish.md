# 193 Hatch screen polish (BD-1069 to BD-1073)

Written 2026-10-18. Label: **CURRENT BUILD** after this change (offline proof plus Studio pictures, see the evidence folder); the owner judges taste. Source of the defects: Studio QA round 4, [192](192-studio-round4-qa-close-paths-walkthrough-hatch-audit.md) part C and section 4 (pictures 213, 239, 243 to 249). The release flag `HatchV2` stays off, so this is the normal hatch (the flat egg, then the 3D egg).

## What changed (plain words)

| Row | Before | Now |
| --- | --- | --- |
| BD-1069 | The bucket was a flat grey rectangle with a thin band. The dot in the colour chip was a mix of the egg's two colours (a "Cream" chip showed a green dot). | The bucket is a chunky tin bucket with the paint dipped over the rim and three drips, filled with the colour's own palette colour. The chip dot is a small rounded square in exactly that colour. The pour stream, splash and drops use it too. |
| BD-1070 | Round pills, thin lines, different from the rest of the game. | One shared helper, `src/shared/ChipStyle.luau`: rounded rectangle (corner 9 px), 3 px dark outline, flat palette fill, text at least 14 px. The colour chip, tier tag, pattern chip, condition chip, rarity line and the ribbons use it. |
| BD-1071 | The egg was 188 px wide, then 114 px, then 147 px when the second colour arrived. | `src/shared/HatchEggSize.luau` decides the size once (the flat egg picture is the reference, about 189 px). The 3D egg's camera is zoomed and centred to match. A check fails if the two sizes differ by more than 3 percent. |
| BD-1072 | Pale thin streaks and white crosses. | A soft rainbow behind the egg: six rings from red (outside) to violet (inside), built from the existing `ringSoft` effect texture, plus rainbow rim sparks and rainbow confetti at the burst. Calm limits, one static glow with Reduce Motion. |
| BD-1073 | "Egg N of M" over the dino's head, head cut off, "BIG" on the plinth, no reason when Skip stops. | The counter is in the header, left of the X. The dino view starts at the top of the card, ends where the name starts, and is zoomed less. The view's own BIG label is hidden (the ribbon already says it). A small tag in the left margin says why Skip stopped ("Rainbow egg! / Skip stops here"). |

## What is still open

* **Paint bucket art is a PLACEHOLDER.** It is built from UI shapes in the game's style (docs/72 allows that only as a marked placeholder). The final `paint_bucket` icon (docs/83 item 31, `resources/ui/v2/icons/paint-bucket-v1.png`) is still **Missing** in the catalogue; when it is uploaded and bound the shapes switch off by themselves.
* **Rainbow sheen texture** is still **Missing** for a really good look: the `rainbowStrip` slot (docs/120) is empty. This change makes the best use of the effect textures that exist.
* The egg zoom (1.42) and fill (0.497) were measured in Studio on this change (3 to 4 percent difference between the flat and the 3D egg; see the evidence README). The first guess from the QA pictures (1.65) made the 3D egg 16 percent too big.
* Studio pictures: `docs/evidence/2026-10-18-hatch-polish/` (numbers 280 to 293 in the review folder). A real Rainbow egg appeared and shows the rainbow rings; an Astra egg did not appear.
* Other places that still used their own pill-shaped tags (shop rarity tags, Dino Index tags, fusion tags) are converted by BD-1077, see section 5.
* A secret dinosaur does not show a stop tag (the hatch result does not carry the secret flag); Shiny, BIG, event, Rainbow and Astra do.
* Not tested: phone, gamepad, Astra egg.

## Checks

`python tools/verify_hatch_polish.py --runner <luau.exe>`: pure numbers (one egg size, chip spec, exact colour for every EggColors row, Rainbow budget, card layout), the real hatch screen in the close-path mock (bucket paint and swatch equal the palette rgb, every chip is a px-corner rounded rectangle with a 3 px outline, counter in the header, dino view inside the card), and 9 mutants (each old defect put back must fail). The close-path rules of [181](181-ui-close-paths-audit.md) still pass.

## 5. Round tags everywhere else (BD-1077): inventory, decisions, check

Written 2026-10-18. **CURRENT BUILD** after this change, **offline proof only** (no Studio): the numbers and the source scan are checked, how it looks is not. Owner words: round pill-shaped tags exist nowhere else in the game's style. Rule now: **a tag is a rounded rectangle with a dark outline, a flat palette fill and text of 14 px or more, built through `src/shared/ChipStyle.luau`**. Everything else that is round on purpose (a real button, a bar, a dot, a circle, a picture panel, an effect shape) is listed in `tools/targets/round_ok.json` with a kind and a plain reason.

**New in the helper:** `Chip.apply(frame, fill, outline, small)`. The **small** variant (`Chip.Small`: 6 px corner, 2 px outline, at least 17 px high) is for tags in tight cards (My dinos cards, the mutation badge, a hint over a 3D view) that cannot be 28 px high. `Chip.apply` also removes an old `Theme.decorate` gradient (a chip is a flat fill) and reuses an old outline, so an old tag converts with one call. **LEAD decision (owner delegated 2026-10-16):** small chips are the same style at a smaller size, not a second style; overturn by removing `Chip.Small` and growing the My dinos card rows (`MyDinos.Card`, tests in `tools/verify_inspect.py`).

**Counts:** 10 tag builders converted (10 sites: the Eggs screen, My dinos, mutation badge, class word, three Fusion places, shop cards, tasks chip, drag hint); **38 round shapes left round on purpose** (38 lines, listed below); 0 unexplained.

### Converted (these were tags)

| file:line | what it is | round on purpose? | converted? |
| --- | --- | --- | --- |
| `src/client/EggsScreen.luau:65` | The Eggs screen tag helper: the five nest chips (READY, Queued, the timer), the rarity chip, the condition chip, the mutation / weather badge and the 'Ready to open!' status line. Was a full-round pill (corner 0.5 scale), 2 px outline. | no | yes, `Chip.apply` (3 px outline, rounded rectangle) |
| `src/client/DinoIndexPanels.luau:90` | My dinos card tags: the stage tag (GOLD, EMERALD, DIAMOND), SHINY, BIG and EQUIPPED. Was a 6 px corner with no outline. | no | yes, small chip (2 px outline, 6 px corner) |
| `src/client/MutationBadge.luau:36` | The mutation badge in the Dino Index, the dino page and My dinos (name on the mutation's own colour). Was a full-round pill (0.5 scale). | no | yes, small chip; the mutation's own rim colour is its outline |
| `src/shared/ClassBadge.luau:52` | The class word (Ground, Water, Fly) when no class picture is bound. Was a full-round pill. | no | yes, small chip |
| `src/client/FusionMenu.luau:373` | The 'NEW GOLD / EMERALD / DIAMOND' tag on the fusion result. Was a round pill (13 px on 26 px). | no | yes, small chip |
| `src/client/FusionMenu.luau:425` | The trait filter chips in the Fusion menu (colours, patterns, Shiny, BIG, mutation). Were near-round (12 px on 36 px). | no | yes, `Chip.apply` |
| `src/client/FusionMenu.luau:866` | The five result chips of a fusion (Shiny, BIG, mutation, two colours). Were near-round (12 px on 36 px). | no | yes, `Chip.apply` |
| `src/client/ShopCards.luau:25` | The Aura and Trail shop cards: the rarity tag (Common ...) and the 'Tier 1' tag. Were 26 px boxes with a 5 px corner and a gradient. | no | yes, `Chip.apply` (28 px high, flat fill) |
| `src/client/ObjectivesPanel.luau:88` | The progress chip ('3/10', 'Done!') of the tasks panel. Was a 6 px box with a gradient. | no | yes, `Chip.apply` |
| `src/client/InspectView.luau:74` | The 'Drag to turn' hint over the 3D dinosaur. Was a full-round pill (13 px on 26 px). | no | yes, small chip, a little see-through |

### Left round on purpose (the allowlist, `tools/targets/round_ok.json`)

| file:line | what it is | round on purpose? | converted? |
| --- | --- | --- | --- |
| `src/client/AdminPanel.client.luau:207` | slider knob of the QA panel: a round handle (and the panel is hidden from players) | yes (dot) | no, left round |
| `src/client/Bootstrap.client.luau:193` | a big 22 px plate corner on a large panel, not a tag (Bootstrap is not changed by this task) | yes (panel) | no, left round |
| `src/client/CombatHud.luau:66` | the round '!' alert bubble over a dinosaur head, one glyph in a circle | yes (circle) | no, left round |
| `src/client/CombatHud.luau:88` | health bar track: a bar is round on purpose | yes (bar) | no, left round |
| `src/client/CombatHud.luau:92` | health bar fill: a bar is round on purpose | yes (bar) | no, left round |
| `src/client/CombatHud.luau:154` | the CHOMP button (a true 60 px button, not a tag) | yes (button) | no, left round |
| `src/client/CombatHud.luau:160` | the small F key-cap on the CHOMP button: one letter in a 22 px circle, a keyboard hint and not a tag | yes (key) | no, left round |
| `src/client/CombatHud.luau:165` | own health strip track: a bar | yes (bar) | no, left round |
| `src/client/CombatHud.luau:168` | own health strip fill: a bar | yes (bar) | no, left round |
| `src/client/ConditionStage.luau:26` | the jungle stage picture frame: a big picture panel (24 px corner), not a tag | yes (panel) | no, left round |
| `src/client/ConditionStage.luau:52` | the hero egg stage frame: a picture panel, not a tag | yes (panel) | no, left round |
| `src/client/DinoIndexPanels.luau:320` | the round 48 px egg icon button on a dino page: a round icon button | yes (button) | no, left round |
| `src/client/EggPicture.luau:28` | the fallback egg blob when no egg picture loads: drawn art, an oval egg | yes (art) | no, left round |
| `src/client/EggPicture.luau:80` | the egg picture stage tile: a picture panel | yes (panel) | no, left round |
| `src/client/FusionMenu.luau:345` | the round check mark on a chosen fusion card: a 30 px selection dot | yes (dot) | no, left round |
| `src/client/HatchEggV2.luau:63` | a light streak in the HatchV2 egg effect (flag off): effect shape | yes (effect) | no, left round |
| `src/client/HatchFx.luau:38` | round spark and ring pieces of the hatch effects | yes (effect) | no, left round |
| `src/client/HatchSequence.luau:56` | the hatch effects helper (rings, splashes, drops); tags use ChipStyle (checked by verify_hatch_polish.py) | yes (effect) | no, left round |
| `src/client/HatchSequence.luau:964` | the DONE / TRY AGAIN end buttons: true 60 px buttons | yes (button) | no, left round |
| `src/client/HubGuideClient.luau:58` | round glow halo behind the hub guide arrow | yes (effect) | no, left round |
| `src/client/HubWalkUpClient.luau:76` | the big round tap button of a walk-up prompt: a true round button | yes (button) | no, left round |
| `src/client/HudV2.luau:77` | the level bar track on the HUD: a bar | yes (bar) | no, left round |
| `src/client/HudV2.luau:82` | the level bar fill on the HUD: a bar | yes (bar) | no, left round |
| `src/client/IndexTabs.luau:77` | the red 18 px new-find dot and the three placeholder colour dots of the tab icon: dots | yes (dot) | no, left round |
| `src/client/IndexTabs.luau:123` | the red 18 px new-find dot and the three placeholder colour dots of the tab icon: dots | yes (dot) | no, left round |
| `src/client/MutationBadge.luau:53` | the tiny 9 px colour dot inside a mutation tag when no icon is bound (the tag itself is a ChipStyle tag) | yes (dot) | no, left round |
| `src/client/MutationReveal.luau:33` | round spark and ring pieces of the mutation reveal effects | yes (effect) | no, left round |
| `src/client/PatternColourCards.luau:49` | the big 84 px colour sample tile of the Colours index is a circle of the exact colour (a picture tile, not a tag); owner may want rounded squares | yes (circle) | no, left round |
| `src/client/PatternColourCards.luau:94` | the 20 px progress pips on an index card: dots | yes (dot) | no, left round |
| `src/client/PatternColourDetail.luau:36` | the pattern and colour detail card: a big popup panel with a 24 px corner, not a tag | yes (panel) | no, left round |
| `src/client/PreviewTraits.luau:41` | the 22 px mutation colour dot on a dino preview while no mutation icon is bound | yes (dot) | no, left round |
| `src/client/RareHatchClient.client.luau:48` | the rare-hatch banner: a wide 40 to 56 px banner with a 14 px corner, a rounded rectangle and not a pill | yes (panel) | no, left round |
| `src/client/VolumeSliders.luau:38` | slider knob: a round handle | yes (dot) | no, left round |
| `src/shared/FxUi.luau:29` | round shapes of the effect previews | yes (effect) | no, left round |
| `src/shared/HatchPresentation.luau:92` | round glow halo behind the 3D egg | yes (effect) | no, left round |
| `src/shared/ModelPreview.luau:25` | the round floor disc under a 3D model preview | yes (art) | no, left round |
| `src/shared/TrailArtwork.luau:22` | round trail dots of the trail icon art | yes (art) | no, left round |
| `src/shared/UITheme.luau:131` | blobs of the code-drawn egg nest fallback icon (art, used only while the icon id is empty) | yes (art) | no, left round |

### Decisions the owner may want to overturn

* The **Colours index tile** (84 px colour sample, a circle) stays a circle: it is a picture tile, not a tag. The hatch screen's colour dot is a rounded square (section 1); changing the tile is one line in `PatternColourCards.tile`.
* The small **F key cap** on the CHOMP button stays a 22 px circle (a keyboard hint).
* **Not changed, reported as a follow-up:** tags built by `Bootstrap.client.luau` itself (it is being slimmed by another helper and is off limits here). They are not full-round pills (`box` makes a 5 px corner with a gradient), so they do not break the owner's complaint, but they are not on `ChipStyle` yet: e.g. the Crystal pack "+N% extra" tag line and the plain rarity text lines. Row BD-1087.

### Check

`python tools/verify_chip_style.py --runner luau.exe` (in CI, next to `verify_hatch_polish.py`): scans every `src/**/*.luau` line that makes a scale corner of 0.5 or more or a corner / `Theme.decorate` radius of 13 px or more. Each must be on the allowlist with a kind and a reason, so a **new round tag cannot slip in**; an allowlist line that matches nothing is stale and fails; the converted builders must still call `ChipStyle`; `ChipStyle` itself may never round fully (normal and small numbers checked in Luau). 12 mutants (a round pill back in the Eggs screen, a new round tag, a big-radius decorate, a removed / reason-less / wrong-kind / stale allowlist line, a fully round `ChipStyle`, a builder that drops `ChipStyle`, a huge small chip) must fail.
