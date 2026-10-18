# 181 UI close paths audit (BD-1019)

Written 2026-10-18. Label: **CURRENT BUILD BEHAVIOR** read from source (every row below comes from the code of this branch, `origin/main` `84001c99` plus the fix), plus **OWNER BUG** from the playtest. Nothing here was seen in Studio, on a phone or with a gamepad: the Studio check is BD-1027. The offline proof is `tools/verify_close_paths.py` (a mock GUI with geometry and Roblox's sibling ZIndex rules runs the real hatch screen) plus extra checks in the Fusion smoke, the regression walk, the Eggs and Inspect verifiers and the session smoke.

## 1. The owner bug in plain words

> "when hatching the egg, pressing X doesnt work", and pressing outside the hatching screen should work too. "some things dont work at all."

**Why X did nothing.** While an egg hatched, the game put an invisible button over the WHOLE screen (the "tap for next egg" catcher, `HatchTapCatcher`, layer 46). The menu itself (`ModalScrim`, the dark backdrop with the card and its X) is layer 20. The higher layer wins every tap, so a tap on X, on the dark backdrop or on the end buttons landed on the catcher, which only means "go to the next egg". Three things were broken by that one button:

| What the player tapped | What really happened |
| --- | --- |
| X during a hatch | Counted as a tap on the egg: sped the egg up, or went to the next egg. Never closed. |
| The dark area outside the card | Same: a tap on the egg. Never closed. |
| **TRY AGAIN** after a splat (and DONE) | Same: the tap landed on the catcher, so TRY AGAIN acted as DONE. Its own handler never ran. This is one of the "some things dont work at all". |

Everything else (Escape key, all other menus) was fine. Only the hatch screen had a cover.

## 2. The fix, smallest root change

- The catcher is no longer full-screen. `ModalClose.hatchZone` (`src/client/ModalClose.luau`) places it over the card body only: the card minus its header strip (X lives there) and minus the row of end buttons (DONE / TRY AGAIN) once that row shows. It follows the card every frame (the card slides in, the phone layout moves). X, the end buttons and the dark backdrop now get their own taps by the normal Roblox rules, with no special code for them.
- "Skip the rest" and the "drag to turn" hint moved to a second, full-screen frame that does NOT take taps (`HatchUiLayer`), so they stay exactly where they were and still work.
- The dark backdrop now asks the hatch screen what to do (`ModalClose.outsideTap`, rules in `src/shared/ModalCloseRules.luau`): see the table in section 4.
- Escape closes an open menu (as before, but only an open one) and gamepad B does the same. The Fusion menu got the backdrop tap and B too.
- The offset of the catcher is measured from a full-screen frame at the same origin, never from `ScreenGui.AbsolutePosition`, so a top inset (the Roblox top bar) cannot shift it. The offline test has a shape where the ScreenGui reports origin 0 while its children sit below the inset.

No server code, remote, flag or profile changed. The server still decides every hatch and credits it once.

## 3. What closing a hatch does (exactly)

| Moment | X, Escape, B, tap outside | Result |
| --- | --- | --- |
| The egg is being opened, the answer from the server has not arrived yet | X, Escape and B close the menu at once. A tap outside does nothing (it could be a finger meant for the egg). | The egg was already claimed when OPEN was pressed. When its answer arrives the egg shows once (it is already hatched and saved, so you never miss a dino); press X again to leave. See BD-1028. |
| Egg wobbling or cracking (build-up) | X, Escape, B close. A tap outside counts exactly like a tap on the egg did before this change (the game ignores it while a normal egg is being built; a splat speeds up). It never closes. | The egg on screen is hatched and saved. |
| Dino shown, first 0.6 s | X, Escape, B close. A tap outside is ignored (a kid's last quick tap must not close the dino). | |
| Dino shown, after 0.6 s | X, Escape, B and a tap outside all close. | The dino is in the collection. |
| Last egg or splat (end buttons) | X, Escape, B and a tap outside close. DONE goes on, TRY AGAIN starts a run. | |

What stays true for every row:

- **Nothing is skipped or claimed twice.** Closing only hides the screen. It never sends "next egg", "skip" or "try again". The offline test checks that closing never calls next / again / skip-all and reports the abort exactly once, and `tools/session1_smoke.luau` now replays a claim of an already opened egg and checks that it hatches nothing.
- **Eggs not opened yet stay in the queue** (they show on the Eggs screen).
- **"Skip the rest" ends:** the flag is reset and the delayed next claim of a running skip loop is cancelled (it used to go on claiming after X). The eggs that were opened quietly before you closed are reported once in the usual "N dinos hatched" toast (when there were two or more). The "Auto-opened eggs" page is shown only when a party ends on its own (DONE), not after X.
- A hatch result that arrives after you closed shows once (see row 1) and then X works.

## 4. Close paths per screen

Legend: **X** = the red X in the header; **Back** = the screen's own Back / Cancel / Done button; **Out** = a tap on the dark backdrop; **Esc** = Escape key; **B** = gamepad B; **Hit?** = can a higher layer swallow the tap (ZIndex / Active / full-screen cover). "new" = added by this change.

### 4.1 The main menu (`ModalScrim` in `Bootstrap.client.luau`, one panel for all of these screens)

Shared by every screen below: **X** `closeButton` (built 80x76; `ModalCompact` keeps it at least 46 px on screen on desktop and `PhoneScale.floorButton` on a phone) runs `close()`; **Out** `shade.Activated` runs `close()` after asking the hatch rule (new, section 3); **Esc** `InputBegan` Escape runs `close()` if the menu is open (before: always, even with nothing open, which also bumped the hatch-cancel serial and could cancel the Run Complete wait); **B** new, same rule. `close()` stops auto-hatching, bumps `modalVersion` (running timers and sequences end), fades the menu and the blur.

| Screen (`open(name)`) | Back / Close inside | Hit? before | Hit? now | Notes |
| --- | --- | --- | --- | --- |
| Sanctuary (`home`) | Explore button | no | no | |
| Dino Index (`collection`) and species page (`detail`) | BACK (species page) | no | no | Egg origin popup: OK button, and a tap on the dark area or the card closes it (`DinoIndexPanels.eggPopup`). Sort and filter sheet: DONE only (no Out; Esc closes the whole menu) -> BD-1029. |
| Eggs (`eggs`) with nest slots and Next egg card | OPEN, Settings, Explore | no | no | OPEN starts a hatch. Cards sit below X. |
| **Hatch (`hatch`)** | NEXT EGG / DONE / TRY AGAIN, Skip the rest | **YES: full-screen catcher above X, the backdrop and the end buttons** | **no** (fixed, section 2) | The only screen with a cover. |
| Auto-opened eggs (`batchSummary`) | COLLECTION, DONE | no | no | |
| Run Complete (`results`, `crystalReveal`) | Back home, OPEN EGGS | no | no | Crystal box closes itself after 3 s and shows Run Complete; X during the box skips Run Complete (rewards are already saved). |
| Go home? (`exit`) | CANCEL | no | no | X, Out, Esc, B all mean CANCEL (nothing ends the run). Only GO HOME ends it. |
| Settings (`settings`) | Sound lab has BACK; tabs | no | no | |
| Food guide (`food`) | none | no | no | X, Out, Esc. |
| Welcome (`tutorial`) | Let's play | no | no | |
| Shop tabs (`auras`: auras, trails, conditions, eggs, crystals; `oddsSimple`, `eggOdds`, `eggOutcomes`) | tab buttons, odds pages | no | no | |
| Buy confirms (`eggPurchase`, `conditionConfirm`, `auraConfirm`, `potionConfirm`, `potionReplace`) | CANCEL / Not now | no | no | Out and X never buy (`verify_potion_purchase`). |
| Potion shop (`potions`) | | no | no | |

### 4.2 Other screens and floating pieces

| Screen | X | Back / Close | Out | Esc | B | Hit? | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Fusion menu (`FusionMenu.luau`, own ScreenGui, layer 20 above the main menu) | yes (`W.button "X"`, 44+ px) | "Close" on Fusion unavailable; "Not now" on confirm; BACK on Dino Details | **new**: closes browse, confirm, resume and unavailable. Ignored while a fusion is being saved (`fusing`), during the reveal and on Dino Details. | yes | **new** | no | X always works, also while saving (the fusion goes on saving and shows its result on the next open). |
| Fusion confirm | yes | Not now | new (cancels, fuses nothing) | yes | new | no | Tested: a backdrop tap on confirm sends no fuse. |
| Fusion reveal (wheels) | yes | Skip, Next, See my dino | ignored on purpose (do not cut the ceremony short) | yes | new | no | |
| Egg origin popup (Dino Index) | none (card) | OK | tap anywhere | via the menu | via the menu | no | |
| Objectives (tasks) panel | none | header tap folds / opens, CLAIM per row | none | none | none | no | A HUD panel, not a modal: nothing to close. |
| Goals panel | none | header tap folds / opens | none | none | none | no | HUD panel. |
| Gift popup (`GiftPopup`) | none | OK ("ack"), Mute, Turn off | none | none | none | no | Hidden while a menu is open. Not a modal. |
| Playtest feedback (`FeedbackClient`, flag) | toggle button | CLOSE (190x48) and auto-close after sending | none | none | none | no | Off in the default build. |
| Admin panel (dev only) | toggle | | none | none | none | no | Hidden while a menu is open. Never in a player build. |
| Rare hatch banner, weather title, toasts | none | tap a toast to dismiss it | none | none | none | no | Banners fade by themselves; none takes input except the toast card. |
| Cave hub rail, fast travel, Back to the middle chip | | `HubTravelClient`: a tap on a rail button or the chip while a menu is open closes the menu and travels (`routeTap`) | n/a | n/a | n/a | no | The travel fade is not Active. |
| Pickup pop, food glow, world text | n/a | n/a | n/a | n/a | n/a | no | Not interactive. |

"Roblox menu button" (`GuiService.MenuOpened`): not wired on purpose. Opening the Roblox menu does not close Be Dino menus; the player closes ours with X, Back, Escape or B first. Say so if you want it (one line).

## 5. How the cover test works (the check for every new screen)

`ModalClose.topAt(root, x, y)` mirrors the engine: with ZIndexBehavior.Sibling the higher ZIndex wins inside one parent (a later child wins a tie), a child draws above its parent, a visible button or an Active GuiObject takes the tap, others let it fall through, a higher DisplayOrder ScreenGui wins. `ModalClose.coverOf(root, X)` answers "who covers X?" (nil = reachable). Uses:

- `tools/close_paths_smoke.luau` (run by `tools/verify_close_paths.py`): a full-screen Active frame above X is found; hidden, not Active or below the menu is not; the real hatch screen keeps X, DONE, TRY AGAIN, Skip the rest and the backdrop reachable on five screen shapes (desktop, a top inset, a ScreenGui that reports origin 0, a scaled panel, a phone) with and without Reduce Motion; 7 mutants (the old full-screen catcher, a catcher over the header, a catcher over the end buttons, no moment rules, never closing, an offset taken from the wrong origin, a catcher left behind) must make it fail.
- `verify_close_paths.py` also lists every full-screen button in `src/client` with the reason it cannot cover a close control; a new one fails CI until it is reviewed.
- The first-session walk (`tools/qa/regression_walk/`) now does the same in Studio with the engine's own hit test (`W.cover`, `GetGuiObjectsAtPosition`) for the open menu at the end of every step, and step 7 taps the real X in the middle of a hatch party and checks that the eggs not opened yet stay queued. A new self-test scenario (`xcovered`) puts the old catcher back and must FAIL step 7.
- `tools/fusion_ui_smoke.luau`: X, backdrop, Escape, B and "other keys do nothing", plus the saving and reveal exceptions.
- `tools/session1_smoke.luau`: a replayed claim of an opened egg hatches nothing.
- `tools/verify_eggs_screen.py` and `tools/verify_inspect.py`: the Eggs screen has no full-size cover; the drag-to-turn hint lives on the layer that does not take taps.

## 6. Not verified, and why

- Studio, phone, gamepad: nothing was run there. The things only Studio can show: that a tap on X during a real hatch closes it (walk step 7 does this), that Escape reaches the game script (Roblox may mark the Escape key as already used for its own menu; the code only reacts when it is not), that gamepad B is not used by something else, the catcher position on a phone with the real layout and top bar, and `Skip the rest` placement. BD-1027.
- The catcher moves by one frame when the card slides in; at 60 fps this is not visible, but it is a measured claim only in the mock.
- Outside-tap behaviour was chosen as a kid-friendly default (LEAD decision, section 7). The owner can overrule it.

## 7. LEAD decisions (owner delegated 2026-10-16), overturn by editing `Rules.outsideAction`

- A tap on the dark backdrop closes the hatch only when the dino has been shown for 0.6 s; before that it acts like a tap on the egg (which the game ignores during the build-up) or does nothing. Options not picked: always close (a kid tapping fast near the edge would lose the animation), never close (the owner asked for it to work).
- The hatch header strip (title bar) no longer advances the egg when tapped; only the card body does.
- In the Fusion menu the backdrop never closes during saving, the reveal or Dino Details. X always works.

## 8. Rows

BD-1019 (this change, Review / test, offline), BD-1027 (Studio / phone / gamepad check), BD-1028 (quiet arrival of an egg opened just before X), BD-1029 (sheets and sub-pages without a backdrop tap).
