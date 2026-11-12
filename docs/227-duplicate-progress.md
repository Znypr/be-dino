# 227 Duplicates show progress: "3 of 6 for Gold!" (BD-1170 part A), 2026-11-12

Status: **Review / test**. Code and offline tests are done. **Not seen in Studio, not seen on a phone, not shown to a child.**
Why: [221](221-po-plan-team-and-research-2026-11-10.md) section 3 row 8 and the research behind it ([research 2026-11-10](research/2026-11-10-yt-and-game-design-research.md), C1 row 5 and C3 row 2): a duplicate should feel like a step forward, not like bad luck. Fusion already turns duplicates into something better ([90](90-fusion-ladder-v2.md): Gold = 6 Base of one species, any pattern; Emerald = 3 Gold; Diamond = 2 Emerald, both same pattern), but the player only saw that inside the Fusion Menu.

Labels: the behaviour below is **CURRENT BUILD BEHAVIOR of the playtest profile only**. The default build is unchanged (flag off). The idea is the lead's reading of the research, **not an owner decision**; the words are PROVISIONAL.

Part B of BD-1170 (goals for today / this week / the big dream) is **not built**; see section 7.

## 1. What the player sees (flag on)

**Hatch reveal.** When an egg gives a dinosaur and the player then has two or more copies that can go into a Gold fusion, one small line appears under the colour line:

- **"3 of 6 for Gold!"** (white), the count **after** this egg;
- **"Ready for Gold!"** (the happy green of every "ready" in the game) at 6 or more.

No line for the first copy (it is not a duplicate yet), for a failed Cracked egg, or while the game does not know the count (section 3). The line fades in last, after the name, the rarity and the colours. It only changes opacity, so Reduce Motion needs nothing. No sound, no new art.

**Index species page** (the My dinos column, [BD-150](07-kanban.md)). Above the cards there is one row of progress bars, one per step the player has started:

- Gold while at least one Base copy counts: "4 of 6 for Gold!  2 more to go";
- Emerald once a Gold copy counts: "2 of 3 for Emerald!";
- Diamond once an Emerald copy counts: "Ready for Diamond!".

One bar uses the whole width and adds the hint ("2 more to go", "Tap to fuse!"); two or three bars share the width and show the main words only. A ready bar is green. **A tap on a bar opens the Fusion Menu on that dinosaur and that step** (the menu's own Dino filter chip shows the filter and clears it). If the menu is not available the game says "Fusion is coming soon", as the FUSION button already does.

## 2. One count rule: the Fusion Menu's

A copy counts exactly when the Fusion Menu would let the player put it in a slot: `FusionSelection.ineligibility(copy, {targetStage, speciesId}) == nil`. `src/shared/DupProgress.luau` calls that function and holds no rule of its own (the verifier fails if it reads `locked`, `favorited` or a stage itself). So:

| Copy | Counts? | Why |
| --- | --- | --- |
| Locked, or marked as a favourite | No | the menu refuses it ("Locked", "Favourite") |
| Older dino without a saved pattern | No | the menu refuses it ("Hatch new dinos to fuse") |
| Shiny, BIG, with a mutation, or with an aura or trail | **Yes** | the menu lets the player pick it; only "Fill for me" leaves it out, and the itemized loss warning still appears before it is used |
| Other species, other stage | No | |

Emerald and Diamond need one pattern, so the bar shows the **best-stocked pattern** (the group `FusionSelection.bestGroup` picks; a tie goes to the smallest pattern id). Recipe sizes come from `FusionSelection.Stages`, so a ladder change moves the words with it.

**Known difference, not changed here:** the HUD goal line (`NextGoal.fusion`) counts favourites and so can show a higher number than the menu and this line. See section 6.

## 3. "After this hatch" without asking the server mid-party

The server can be ahead of the screen: a page of eggs is settled at once and then revealed one by one (`BufferedRevealCount`), so the server's copy list during a hatch party already holds dinosaurs the player has not seen. Asking it at each reveal would show "6 of 6" on the third egg.

So the screen keeps a **quiet copy list** and adds what it has revealed since:

- the list (the read-only `FusionAction` "list" answer that the Fusion Menu, the goal line and the Index already read) is taken only while **nothing is hatching**: no egg waits for its answer, the last hatch event is 1 s old, nothing is buffered;
- a list that was asked for before a hatch and arrives after it is **thrown away**;
- each reveal adds its own copies ("2x Compy" adds two, a failed egg none);
- no list yet (join, fusion off, a list longer than 2,000 copies) means **no line**, never a wrong number.

When the quiet list arrives while a revealed dinosaur is still on screen, the line is set from it. Cost: one list read per quiet moment after the save changed, no request during a party.

## 4. The fast reveal ([BD-1164](07-kanban.md)): decision

BD-1164 (commons in about 0.5 s) is **not merged** at the time of this change (`HatchFastCommonsEnabled` does not exist in the tree), so this was decided on paper:

**LEAD decision:** the line shows on **every** revealed duplicate, fast path included, and is not moved to the summary. Reasons: (1) it is at most 16 characters in the same place every time, and in a fast batch the number itself going up egg after egg ("3 of 6", "4 of 6", "5 of 6") is the feeling we want; (2) hiding it on commons would hide it exactly where duplicates happen (commons are most of the eggs); (3) it has no animation of its own beyond a 0.3 s fade, so it adds nothing to the reveal time. Not picked: summary only (the batch summary has no per-species rows today; it would need a new screen section) and full-show eggs only (rare eggs are rarely duplicates).
**Open for BD-1164:** when the fast path lands, the fade delay (0.7 s with motion, 0.3 s without) must be shortened for fast eggs or the line appears after the egg is gone; a per-species line in the batch summary ("Compy: Ready for Gold!") is the natural follow-up.

## 5. Flag, files, tests

- `Config.DupProgressEnabled`: **false** in Config and in the default profile, **true** in the playtest profile (standing rule [157](157-playtest-profile-newest-features.md)), in the rehearsal list. Free, no Robux. Flag off: the client module returns before any Instance, thread or request; the reveal and the Index page are exactly as before.
- **No server change, nothing stored, no economy change, no new art, no sound.** Bootstrap is not touched (it has 7 bytes left under its ceiling); the hooks are three lines in `HatchSequence.luau`, one in `DinoIndexPanels.luau`, the row callback in `DinoIndexScreens.luau` and `FusionMenu.preset`.
- Files: `src/shared/DupProgress.luau` (pure: count, words, hatch counting), `src/client/DupProgressClient.luau` (the line, the bars, the list read).
- `python tools/verify_dup_progress.py --runner <luau.exe>` (in CI): the count equals the Fusion Menu's own selection rule on a mixed list, the words and states, the hatch counting, flag-off inertness, wiring, **32 mutants**.

## 6. Not verified, and open points

- **Not seen in Studio or on a phone.** The line sits at y 338 to 358 between the colour line and the "Tap for next egg" hint, which moves 6 px down when a line shows; on screen this is unchecked (overlap, the phone card, the v2 hatch). The Index bars take one touch row (44 px or more) from the card grid; unchecked on the phone canvas.
- The line needs fusion to be on (the copy list comes from `FusionAction`); with fusion off there is no line.
- **Mismatch 1:** the board row and the research say "7 of **15** for Gold"; 15 was the ladder before 2026-10-15. The code uses the current recipe (6).
- **Mismatch 2:** `NextGoal.fusion` (HUD goal line and Goals panel) skips locked copies but counts favourites and has its own stage table; the Fusion Menu refuses both. This change follows the menu, as the task asked. Aligning the goal line is a separate small task.
- More than 2,000 copies: no line (the list read stops at 10 pages).

## 7. Part B (not built): goals for today, this week and the big dream

The other half of BD-1170. Notes for whoever builds it:

- Objectives already exist ([66](66-intake-mini-objectives.md), BD-075 to BD-078) and the goal line picks one. Part B is a **view**, not a new system: three rows, **Today** (one objective or "hatch 3 eggs"), **This week** (the nearest Gold from this document's `Dup.speciesSteps`, or the next Index milestone), **Big dream** (first Diamond, or the full Index).
- Reuse `DupProgress` for the fusion rows so every screen shows the same number.
- It needs a spec first (which three goals, where they live: the Goals panel or the Index), then the build; no reward may be added without an owner decision.
