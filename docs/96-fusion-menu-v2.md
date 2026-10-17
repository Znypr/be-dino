# 96 Fusion Menu v2: one glance for a child (BD-217)

Status: **Review / test** (offline verifiers pass; see section 7 for what was and was not checked in Studio). Owner feedback from playtest 3 (2026-10-15): complex menus, Fusion first, need a redesign; a child must understand the screen in one glance ([docs/87](87-vision-and-feel-guide.md), [docs/72](72-ui-copy-and-asset-standards.md)). Server rules, exact odds disclosure, consent, retry tokens and the paid-random policy ([docs/43](43-player-access-and-paid-random-policy.md), [docs/53](53-bd064-fusion-server.md)) are **unchanged**; only the client screens and their words changed. The ladder is 6 / 3 / 2 ([docs/90](90-fusion-ladder-v2.md)).

## 1. What was wrong (Build 020 + BD-065 menu)
A dense top row (GOLD (6) / EMERALD (3) / DIAMOND (2), SORT, AUTO-FILL PLAIN), a second row of nine cycling filter chips, 146 x 132 px cards with only text ("Unknown pattern • Base", "Wrong stage for this recipe"), three tiny numbered slots, a text histogram ("0 Shiny / 6 • 0 BIG") and an odds list headed "UPGRADED (guaranteed)" / "ROLLED (exact odds from the server)" with version strings. The result of the fusion was nowhere on the browse screen; the only action was "FUSE (0/6)".

## 2. References: how big Roblox games present crafting and fusing
Observations from memory of popular simulators (no screenshots were copied; the patterns are generic and widely shared):

| Game | Pattern we borrow |
| --- | --- |
| Pet Simulator 99 (Golden / Rainbow machines, Fuse machine) | One machine per goal; big pet icons in a grid; tap a pet to put it in a slot; the number needed is a plain "x / 8"; one big button; a short drop-in animation and a reveal of the upgraded pet. Filters and "auto select best" are secondary buttons. |
| Adopt Me (Neon cave) | Four big platforms (slots) you fill by walking pets in; a glowing preview of the Neon pet in the middle; nothing to read but the count. |
| Bee Swarm Simulator (hive / crafting) | Recipe shown as pictures and a number, not a sentence; the result item is shown large beside the recipe; one craft button. |
| Grow a Garden / anime pet games (evolve, fuse) | Left list of eligible items (already filtered to what works), centre or right a large result preview with rarity badge, trait chances shown as short labels ("Shiny 5%"), one big coloured button, a celebratory burst when done. |

Common ingredients: **big cards with pictures**, **tap to add**, **auto-fill**, **a big result preview**, **one obvious button**, **a satisfying reveal**, **filters hidden behind one button**.

## 3. Principles (apply to My dinos and Shop later)
1. One idea per column: *your dinos* -> *the slots* -> *what you get*.
2. The screen filters itself: you only see dinos that can go in (right stage for the tier). Wrong-stage copies are not listed and never need explaining.
3. Everything a child needs is a picture or a number: dino preview, "2 of 6", "Shiny 8%".
4. One sentence tells you what to do next: "Tap 6 Compy, or Fill for me." / "You need 6 Compy to make a Gold Compy. You have 2." / "Tap 4 more Compy." / "Ready! Tap FUSE."
5. One big button that changes colour when it is ready: "Pick 4 more" (grey) -> "FUSE!" (green).
6. No jargon: no "ROLLED", "UPGRADED", "INGREDIENTS", "recipe", "species", "quote"; a locked tier says "Soon"; an older copy without saved DNA says "Older dino" and "Hatch new dinos to fuse" (BD-381) instead of "Unknown pattern".
7. Exact odds stay exact: the same server numbers, the same largest-remainder rounding to 100%, now as chips ("Shiny 8%", "Green 60%") on the browse screen and again on the confirm screen, with the odds/recipe version in a small grey line.
8. Phone first: three columns fit a 740 x 340 safe area, every button is at least 44 px, slots are real tap targets (tap to take a dino out), cards shrink to 132 x 150.
9. Protect value: special dinos (Shiny, BIG, mutation, bought effects) are never auto-filled, are marked "Special" when chosen by hand, and the confirm screen lists exactly what goes away and needs an "I understand" tap first.

## 4. Wireframe (desktop; the phone layout is the same three columns, smaller)
```
+----------------------------------------------------------------------------------+
| Make a Gold dino                                                             [X] |
+-----------------------------+--------------------------+-------------------------+
| [  GOLD  ] [EMERALD] [DIAMOND]| Put in 6 Base      2 of 6| +---------------------+ |
| [ 6 Base ] [ 3 Gold ] [2 Emer]|                          | | NEW GOLD            | |
| Tap 4 more Compy.   [Filter]  | +------+ +------+ +------+| |                     | |
|                               | |dino 1| |dino 2| |  3   || |   (big preview of   | |
| +--------+ +--------+ +------+| |  pic | |  pic | |      || |   the Gold Compy)   | |
| | Compy  | | Compy  | |Compy || +------+ +------+ +------+| |                     | |
| |  (pic) | |  (pic) | | (pic)|| +------+ +------+ +------+| |   Gold Compy        | |
| | Wavy   | | Spots  | | Wavy || |  4   | |  5   | |  6   || +---------------------+ |
| | [==]   | | [==]   | |[==]  || |      | |      | |      || Guaranteed: Gold!       |
| | In slot 1 | Shiny | | Tap  || +------+ +------+ +------+| [Shiny 8%] [Not shiny ] |
| +--------+ +--------+ +------+|                          | [BIG 3%] [Not big 97%]  |
| +--------+ +--------+ +------+| [   Fill for me   ][Clear]| [Green 60%] [Blue 40%]  |
| | Raptor | | ...    |        |                          | +---------------------+ |
| | Different dino    |        |                          | |       FUSE!         | |
+-----------------------------+--------------------------+-------------------------+
```
* **Tier tabs** are big two-line buttons (title + "6 Base"); the active one takes the tier colour (gold / emerald / diamond) and the header follows.
* **Cards** (160 x 176, 132 x 150 on short screens): dino name, live preview with its own colours (Gold/Emerald/Diamond copies show their stage material), pattern name, two-colour swatch, trait words in purple (Shiny, BIG, mutation name, Effects, Locked, Favourite), a status line ("Tap to add" / "In slot 3" / a red reason) and the **i** details button. A chosen card gets a green numbered tick; a card that cannot go in is dimmed.
* **Filter** opens one row of chips (Sort, Dino, Pattern, Colour, Shiny, BIG, Mutation, From, Effects, Clear) and is blue while a filter is on.
* **Slots** are a grid (3 x 2 / 3 x 1 / 2 x 1) with the dino's preview and swatch; tap a slot to take that dino out; empty slots show their number.
* **Result**: the preview is built from the first chosen dino's species (or the quote's) with the tier material and a "NEW GOLD" badge; before the slots are full the chips area says "Pick 4 more to see your chances." The FUSE button reads "Pick 4 more" until the quote is in, then "FUSE!".

**Confirm** (one screen): left the result preview with "Guaranteed: Gold Compy!", "Pattern: Wavy Stripes", "Colours, Shiny, BIG and mutation are rolled new."; right "All 6 dinos go away. You get 1 new Gold Compy.", the six dinos by name and traits, the itemized effects line, "Special dinos going away: ...", "Your chances:" chips, the version line; buttons "Not now" and "I understand: ..." then "FUSE! (6 go away)".

**Reveal**: "Pattern: Wavy Stripes" card, then the server-committed reels titled "Colour 1", "Colour 2", "Shiny?", "Mutation?", "BIG?" (unchanged mechanics: segment widths equal the quoted odds, the pointer stops in the middle of the committed segment, no fake near-miss), then **Ta-da!**: the new dino pops in with a soft Back-ease (no pop under Reduce Motion), chips for Shiny / BIG / mutation / colours, "Gold stage: guaranteed. Made by you." Buttons: Skip, Next, See my dino.

## 5. Code
* `src/shared/FusionSelection.luau` (pure, tested): `ReasonText` reworded; new `tabText`, `visibleFor` (auto-filter by the tier's source stage), `bestGroup`, `goalText`, `oddsChips` (same numbers as `formatOdds`), `cardPattern`, `cardTraits`.
* `src/client/FusionMenu.luau`: browse, confirm and reveal screens rebuilt; data loading, debounced quote at exactly N, token reuse, retries, resume, duplicate replay, unavailable screen and Dino Details are unchanged. Card and slot previews use `DinosaurPreview` (lazy, culled when off-screen) and `PreviewTraits`.
* `src/client/Bootstrap.client.luau`: only the stale legacy button text ("15" -> "6"); no new locals (the file is at the 200-register limit).
* Tests: `tools/verify_fusion_ui.py` (new helper checks) and `tools/fusion_ui_smoke.luau` (new layout: auto-filter counts per tier, collapsed chips, slot taps, goal sentences, chips, jargon absent, 161 buttons >= 44 px at 740 x 340).

## 6. Not changed on purpose
Server odds coefficients, consent digests, PolicyService gating, Robux flags (off), the legacy Build 020 FUSION page (development profile only), Dino Details content, the reel mechanics. No new art: the menu uses existing previews, theme colours and FredokaOne text; chips and ticks are plain rounded frames (UI kit, not icons).

## 7. Evidence and what was not verified
* Offline: `verify_fusion_ui.py` (logic + smoke), `verify_sources.py`, `verify_luau.py`, `verify_fusion.py`, `verify_next_goal.py`, `python -m unittest discover -s tests`, `build.py` (default and playtest) pass on this branch (2026-10-16).
* Studio (desktop, one `BeDino-Fusion` window, 2026-10-16, [evidence](evidence/2026-10-16-fusion-menu-v2/README.md)): the browse screen against the **real** `FusionAction` server (the playtest profile owns one older Compy: "Older dino: can't fuse", "You have 0.", six empty slots); then with a temporary fixture remote (14 Base dinos, same contract) the whole flow: Fill for me -> odds chips -> FUSE! -> confirm -> reels -> Ta-da card. Screenshots in that folder.
* Not verified: a real phone (touch, safe insets, frame time with 100+ card previews), gamepad, the live server with many owned dinos, how the slot previews perform on low-end devices (each slot and card holds a culled ViewportFrame). My dinos and Shop are still to be redesigned with the same principles (BD-217 follow-ups).
