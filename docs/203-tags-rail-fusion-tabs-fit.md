# 203 Words that fit: hatch ribbons and tags, panels off the rail, Fusion tab names (BD-1107, BD-1108, BD-1103)

Written 2026-10-19. Label: **CURRENT BUILD** after this change, proved **offline only** (pure numbers and a layout mock, no Studio, no phone). Source of the defects: Studio round 7 ([200](200-studio-round7-real-size-checks.md), pictures 391, 393 and 416 at 498 x 463 and 516 x 481) and Studio round 6 ([199](199-studio-round6-shop-toasts-check.md), picture 379). The Studio re-check is a new P2 row (see section 5).

## 1. What the owner saw (plain words)

1. A Rainbow egg: the words "Rainbow egg!" ran out of their little tag on the left and were cut by the edge of the card. The tag "Skip stops here" lay over them, and the class picture lay over the first letters of the dinosaur's name.
2. The Goals sheet, when opened, covered the right half of the buttons on the left (Fusion, Settings).
3. The Fusion tab names read "EMERA" and "DIAMO".

## 2. What was really wrong

| # | Cause | Fix |
| --- | --- | --- |
| 1 | The ribbons (SHINY, BIG, the mutation, New pattern!, New colour!) and the stop tag were put on **fixed spots**, and their words **shrank to fit** the box (TextScaled). A shrinking word cannot go under its minimum, so a long word simply runs out of a short tag. The class picture was placed from the name's width as the engine measured it, and the engine often answers 0 or too little right after the text is set. | One helper measures every word first (`src/shared/TagFit.luau`, at the 14 px floor of the window it is drawn in) and `src/shared/HatchTagLayout.luau` **stacks** the tags down the two sides of the card (left: Shiny, mutation, stop tag; right: BIG, New pattern!, New colour!). Each tag is as big as its words need; a long word wraps onto two lines; a tag that does not fit its side goes to the other side. The word is a fixed size, never shrink-to-fit. The name is left-aligned right of the class picture, so they can never touch. |
| 2 | The open Goals card opens leftwards from the right edge and nothing told it where the rail is. | `HudPanelStack.clearRail`: an open panel that would cover the rail (the rect `HudV2.layout` publishes: six buttons at home, two in a run) opens **under** the rail. The Tasks panel hides under the real open Goals card (`GoalsOpenRect`). |
| 3 | The three tabs were each a third of the left column: 54 px at 500 px wide. "EMERALD" and "2 Emerald" at 14 px need about 63 and 70 px. | `TagFit.fusionTabs`: the tabs are as wide as their words need (equal thirds when they fit, like before). When even that does not fit the left column, the tab row takes the **whole width** of the Fusion screen and the three columns start under it. |

## 3. What changed

* New pure modules `src/shared/TagFit.luau` (width estimate, floor size, wrap, short word, tab row) and `src/shared/HatchTagLayout.luau` (stack and place the hatch tags).
* `src/client/HatchSequence.luau`: ribbons and the stop tag come from `HatchTagLayout`; text sizes are fixed numbers; the class badge and the name are laid out as a group (badge left, name left-aligned right of it). `Bootstrap.client.luau` is **not touched**.
* `src/shared/HatchFxPlan.luau`: the foreground sparkles keep out of the two tag columns (they now start under them); the old `Card.stopTag` rectangle is replaced by `Card.tagColumns`.
* `src/shared/HudPanelStack.luau`, `GoalsPanel.luau`, `ObjectivesPanel.luau`: the rail rule (`clearRail`); GoalsPanel publishes `GoalsOpenRect`.
* `src/client/FusionMenu.luau`: tab sizes and the wide row from `TagFit.fusionTabs`.
* Desktop windows: the tab row is three equal tabs like before; the hatch ribbons keep their old centre line, width and 26 px words where the words fit. The stop tag now sits under the ribbons of its side (a lone one at the top) instead of at a fixed height.

## 4. Checks (offline)

* `python tools/verify_tag_fit.py --runner luau.exe` (in CI): the pure maths (TagFit), the Fusion tabs with the real words at 18 window sizes (with and without the left rail; the old "third of the column" rule really fails at 7 of them, the wide row is used at 7, three equal tabs on a desktop window), and the hatch tags for **every subset** of the six ribbons plus the stop tag at 7 window scales (63 subsets x 7 = 441 plans) plus the long-word and crowded cases: nothing leaves the card (turned boxes included), nothing overlaps, nothing is cut with "...", every word fits its box with the plain 0.5 em estimate and with TagFit's own wider one, every size is at least 14 px on screen. 15 mutants.
* `python tools/verify_small_window.py --runner luau.exe`: the real `HatchSequence` in the geometry mock at 11 window sizes, with and without Reduce Motion, for the new stages: **Rainbow egg and BIG**, **Rainbow + Shiny + BIG + a mutation + New pattern! + New colour! at once**, **New pattern! + New colour! + the stop tag**, **the longest words** (a long mutation name on two lines) and **a lone Rainbow egg**. Every ribbon and the stop tag is inside the card and above the name, no two overlap, every label is a fixed size (no shrink-to-fit), fits its box with the plain estimate, is at least 14 px on screen and is not cut; the class badge ends before the name starts, and the name is left-aligned beside it. 27 mutants in all (12 new).
* `python tools/verify_hud_panel_stack.py --runner luau.exe`: 232 states on 29 canvas sizes, touch and mouse, with the **six-button rail at home and the two-button rail in a run**: without the rail rule 50 layouts have an open panel over the rail; with it the panel opens under the rail in 48 of them. The other two are a 500 x 300 window with the six-button rail, where there is no room under the rail: the panel stays where it was (reported, not hidden). 9 mutants.
* `python tools/verify_fusion_ui.py` and the other hatch checks still pass (the whole CI list was run on this PC).

## 5. Not verified (needs Studio)

* **Nothing here is a Studio or phone picture.** The mock draws nothing. Text widths are an estimate: the real font may differ a little (TagFit measures wide on purpose, and the labels end in "..." as a last net instead of leaving their box).
* How the stacked tags look next to the dinosaur at 498 x 463, 516 x 481, 848 x 423 and 1156 x 841 (a Rainbow egg, a Rainbow + BIG egg, a mutation egg); that the name and the class picture look balanced; whether a **real** class picture and word (Fly, Armored) is as wide as estimated.
* The Goals sheet under the rail in the hub and in a run (the tap on the header places it on the next frame); a 500 x 300 hub window has no room under the rail.
* The Fusion screen at 500 px with the wide tab row: the three columns are 62 px shorter; the Fusion Admin button and the other cut text of picture 379 (the goal sentence, "You need 6 Base dinos...") are **not** part of this change.
* LEAD decisions (owner delegated 2026-10-16) that are easy to overturn: the stack order (Shiny, mutation, stop tag on the left; BIG, New pattern!, New colour! on the right), a tag moving to the other side when its side is full, the Goals card opening under the rail (the other option was folding the rail buttons it covers), and the wide Fusion tab row (the other options were scrolling or two rows of tabs).
