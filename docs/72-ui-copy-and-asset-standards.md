# 72 UI copy and UI asset standards (owner, 2026-10-14)

Short rules every contributor and agent follows. The audience is children: keep information minimal and obvious.

## In-game text
- Time: round and drop zeros. "5 min", "10 min", "2 h", "Ready in 3 h", "Back in 40 s" only under a minute. Never "5m 0s" or "2h 0m".
- Multipliers: plain words or percent. "Speed +20%" not "1.2x"; "Growth +25%". One number per line.
- One short line per fact. No jargon (no 'transform', 'window', 'idle', 'ledger'). Name the thing and the benefit: "Swift Sip: run faster for 5 min".
- Counts are plain: "1 left", "Sold out". No decimals except where a real number is the point.
- Errors say what to do next in a few words.
- No visible internal rules or hidden thresholds (for example, nest drop requirements stay invisible).

## Text size floors (BD-1119, BD-1117, [208](208-text-style-window-chrome-rarity-words.md))
- 14 px on screen stays the absolute floor of any text. One outlined text style (`Shared/TextStyle`, `outlined(label, kind)`): a window title is **22 px or more**, card text is **16 px or more on a desktop window** (a small, phone-size window keeps 14 px until the Studio re-check), fine print (a hint, a caption) is marked a *note* and is 14 px.
- The window X is a red **square of 48 px or more**; every other tap target stays at 44 px.
- A rarity is written with its colour: use `RarityWord` (`Shared/RarityWord`), never a hand-picked colour. Checked by `tools/verify_text_style.py` and `tools/verify_rarity_words.py`.

## UI art and icons
- Do not generate UI art or icons ad hoc in code (vector shapes, native shape stacks) as final art. Such code drawings are PLACEHOLDERS: mark them `PLACEHOLDER` in code and in the task, and they never count as done.
- Final UI art is its own task with this flow: brief (what, where, size, states) -> 2D drafts in 2-3 styles -> lead/owner picks -> final export at target sizes (plus phone size check) -> import/upload by the owner -> verified in Studio next to neighbouring UI.
- Quality bar before 'done': matches the v2 kit (chunky outline, saturated palette, rounded forms, same light direction), readable at 64 px and at phone size, distinct from every sibling icon, no leftover placeholder symbols.
- Do not invent Roblox asset IDs.

## Review
- The lead checks every new screen in Studio with a screenshot before merge (copy rules and art rules above included).

## Close paths (owner bug 2026-10-18, BD-1019, [181](181-ui-close-paths-audit.md))
- Every menu, popup and sheet has a way out that works: the red X (at least 44 px on screen), a tap on the dark backdrop (unless something is being saved or revealed), Escape and gamepad B, plus the screen's own Back / Cancel / Done button.
- Nothing may sit above X or the backdrop: no full-screen button or Active frame over a menu. A tap catcher covers only the card body, never the header strip or the buttons. If you add a full-screen button in `src/client`, review it and list it in `tools/verify_close_paths.py`.
- Closing never claims, skips or buys anything. Test it with `ModalClose.coverOf` (offline) and `W.cover` (Studio walk).

