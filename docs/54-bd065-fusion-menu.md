# BD-065 Fusion Menu and BD-062 Dino Details (client)

Implemented 2026-10-13 on `claude/bd-065-fusion-ui`, based on `18856b4` (main).
Task status lives only in [Kanban](07-kanban.md). Owner intent is
[the fusion specification](46-pattern-fusion-dino-identity-and-cosmetic-progression.md)
sections 6–8. The server transaction it talks to is BD-057
([Phase 1](49-identity-fusion-phase1.md)); the `FusionAction` remote itself is built
by a parallel task and **is not part of this change**.

**Scope: client UI and pure client logic only.** There are no server, Config,
DataStore, odds or price changes. Nothing here has been run in Roblox Studio or on a
phone yet (see [Verification pending](#verification-pending)).

> **2026-10-14 update:** the recipe counts below are now 15 / 4 / 2 (Gold = 15 Base, Emerald = 4 Gold, Diamond = 2 Emerald; see [58](58-fusion-ladder-50-10-3.md)). The 10-Base text is the original BD-065 prototype; the menu reads counts from `FusionSelection.Stages`.

## Owner rules this UI follows (2026-10-13)

- 15 same-species + same-pattern **Base** dinos → **one NEW Gold**. All 15 are consumed (10 in the original prototype).
- The pattern is locked. Colors, condition, Shiny, BIG and mutation are rolled fresh,
  and the UI shows the numerical odds before you confirm.
- Every aura and trail on every donor is lost. The confirmation lists each one by
  name. Shiny, BIG and mutated donors are listed too.
- The wheels only **reveal** the result the server already saved. They can be skipped.
- Emerald and Diamond are shown but locked, with the text "Recipe not approved yet".
- Milestone 1 is a private playtest (desktop + Android landscape), with Robux off.

## Server contract used

`ReplicatedStorage.BeDinoRemotes.FusionAction` (RemoteFunction):

| Action | Request | Used for |
| --- | --- | --- |
| `list` | `{cursor?, limit<=200}` | The grid of individual dinos. The client reads up to 10 pages (2,000 dinos). |
| `details` | `{instanceId}` | Dino Details: original egg for hatched dinos, lineage for fused ones. |
| `quote` | `{targetStage, donorIds}` | Exact odds, loss manifest, consent and quote digests. |
| `fuse` | `{token, targetStage, donorIds, quoteDigest, consentDigest?}` | Commits the fusion. Returns `fused` or `duplicate` plus the committed result. |

Every failure reason in the brief has its own message and handling. These are
`Sel.FailureText` and `Sel.settle` in
[`FusionSelection.luau`](../src/shared/FusionSelection.luau):

- **Retry with the same token:** `rate_limited`, `save_failed`, `lease_lost`,
  and no answer (timeout or error).
- **Refresh the list and quote again** (a new token next time): `stale_quote`,
  `consent_required`, `donor_missing`, `donor_locked`, `wrong_donor_count`,
  `species_mismatch`, `pattern_mismatch`, `token_conflict`.
- **Stop with a message:** `fusion_disabled` (shows the unavailable screen),
  `recipe_not_approved`, `odds_not_approved`, `storage_limit`.

**Missing or disabled remote:** if `FusionAction` doesn't exist, or the server answers
`fusion_disabled`, the menu shows **"Fusion unavailable"** with a Close button. It
never throws an error. The Bootstrap entry loads the module through `pcall`, so a
module error can't break the main UI.

## Module structure

| File | Role |
| --- | --- |
| `src/shared/FusionSelection.luau` | **Pure** logic, no Instances: display catalog, eligibility reasons, filters, sorts, plain-only auto-fill, histogram and badges, odds formatting with exact 100% sums, loss summary, retry-token handling, reveal sequence and Dino Details view model. |
| `src/client/FusionMenu.luau` | The menu's own `ScreenGui` (`BeDinoFusionUI`, DisplayOrder 20, `DeviceSafeInsets`). Screens: browse, confirm, fusing/retry, reveal, resume, unavailable. Remote calls are wrapped in `pcall` with a 12 s timeout. |
| `src/client/DinoDetails.luau` | BD-062 details panel for one individual dino. |
| `src/client/FusionWidgets.luau` | Relative-layout helpers in the existing style (FredokaOne, outlined text, `Theme.decorate`). Text scales with size constraints, and buttons are at least 44 px. |
| `src/client/Bootstrap.client.luau` | **4-line hook:** a `pcall` require, plus a **PATTERN FUSION: 15 -> NEW GOLD** button on the existing FUSION page. That page is still the legacy 50→Gold screen and is otherwise unchanged. |

## Screens and flows

1. **Entry.** Nav **FUSION** → existing page → **PATTERN FUSION: 15 -> NEW GOLD**. This
   closes the main modal and opens the Fusion Menu.
2. **Browse.**
   - **Target stage tabs:** GOLD (active), EMERALD (LOCKED), DIAMOND (LOCKED). Picking a
     locked tab shows "Recipe not approved yet" and never asks for a quote.
   - **Sort:** eligible first (plain, then valuable, then ineligible), rarest, species,
     pattern, color, condition, newest, selected first.
   - **AUTO-FILL PLAIN.**
   - **Filter chips** (tap to cycle, scroll sideways on phones): species, pattern,
     stage, color (either gene), condition, Shiny, BIG, mutation, origin (hatched,
     fused, older), cosmetics (owns FX, no FX, equipped).
   - **Grid of individual dinos.** Each card shows species, pattern, stage, a two-gene
     swatch, and text badges (SHINY / BIG / mutation / *n* FX / LOCKED / FAV).
   - **Card status line:** "Tap to add", "Valuable: tap to add",
     "SELECTED (VALUABLE)" (purple border), or a red reason: Different species,
     Different pattern, Wrong stage, Egg pattern unknown, Locked, Favorited, Recipe not
     approved yet.
   - The **i** button (44 px) opens Dino Details.
   - Cards are drawn 120 at a time, with SHOW MORE for the rest.
3. **Ingredients column.**
   - `INGREDIENTS n/15`, CLEAR, and a compact n/N counter (slot cards only up to 10). Tapping a slot removes that dino.
   - A histogram, e.g. `2 Shiny / 15 • 1 BIG • Ember x1 • 1 with bought FX (lost)`.
   - "UPGRADED (guaranteed): 1 NEW Gold, stage + stats" is kept separate from
     "ROLLED (exact odds from the server)".
   - Any change to the selection asks for a fresh quote after a 0.35 s debounce. Quotes
     are only requested once 15 dinos are selected. With fewer, the column says
     "Select N more…", because the server rejects anything other than 15.
   - A quote that comes back late or for a different selection is thrown away.
   - Odds that are malformed or don't add up to 100% disable fusing.
4. **Confirm.**
   - States the guaranteed Gold result and "PATTERN LOCKED".
   - Lists all 15 consumed donors with traits; valuable ones are highlighted.
   - Shows the itemized loss line, e.g. "2 auras and 1 trail will be lost: Meadow Glow,
     Tidal Halo, Fern Drift", then the Shiny/BIG/mutation donors.
   - Shows the full exact odds and the odds/recipe versions.
   - If anything will be lost (or `consentRequired`), you must first tap **I UNDERSTAND
     …**. Only then does **FUSE NOW (CONSUMES 15)** appear.
   - The client sends `consentDigest` only when the quote requires it. Cancel consumes
     nothing.
5. **Fuse.**
   - Each confirmed attempt gets a new GUID token (`Sel.attempt`).
   - If there is no answer, or the server says `rate_limited`/`save_failed`, the client
     retries automatically up to 3 times with backoff (2 s, 4 s), using the **same token**.
   - After that it offers **RETRY (SAME REQUEST)**.
   - The token stays alive while the menu is closed. On reopen, **CHECK RESULT** resends
     the same request (the server returns `duplicate` if it already committed).
     **DISCARD** forgets it.
   - A changed request (new quote digest or different donors) always gets a new token.
6. **Reveal.**
   - Order: **PATTERN LOCKED: <pattern>** card, then reel wheels for Color 1 → Color 2
     (with blend) → Condition → Shiny → Mutation → BIG, then the **final card**.
   - Each wheel is a horizontal strip of segments sized by the quoted odds. It stops with
     the pointer at the middle of the **committed** segment. There are no fake near-misses.
   - If the committed value isn't in the quoted table, it's shown as a plain card and
     never animated.
   - **SKIP TO RESULT** / **NEXT**. With reduced effects (`Theme.MotionEnabled=false`)
     the strip doesn't spin.
   - The final card shows a Gold preview with the committed Shiny/BIG, the trait list,
     "Crafted Gold (earned)", "Bought cosmetics: none", and **VIEW DETAILS**.
   - A `duplicate` result (retry or reopen), or a result committed while the menu was
     closed, goes straight to pattern + final **without replaying the odds wheels**.
7. **Dino Details (BD-062).**
   - **Hatched:** "Hatched from: <pattern> • <colors with %> • <condition> • Event: <event>
     • <source egg>". It also says "Natural hatch odds: not calculated yet", rather than
     inventing a number.
   - **Fused:**
     - "Fused from N dinos", plus the recipe and odds versions.
     - The parent list with each parent's egg line.
     - Prestige reads **"Crafted Gold (earned)"**, with no drop % anywhere.
     - It notes that traits were freshly rolled and the stage was guaranteed.
   - **Older copies** say the original egg wasn't recorded; traits are never guessed.
   - Cosmetics (only this dino's own) are listed under a note that they never count
     toward rarity or prestige. The pure `rarityScore` excludes them too.

## Mobile / Android landscape

- The menu's `ScreenGui` uses `ScreenInsets = DeviceSafeInsets`. The panel is 97% × 95%
  of the safe area, capped at 1180 × 680 by `UISizeConstraint`.
- There is no whole-panel UIScale, so pixel touch targets stay real size. Every button
  is at least 44 px tall and wide: stage tabs, chips, slots, the card **i** button,
  confirm, reveal and back.
- Grids, filter chips, the odds list, confirmation and details all scroll.
- **Below 450 px of safe-area height** (phone landscape) the slots shrink to a read-only
  ten-chip strip. You remove a dino by tapping its card, which leaves more room for odds.
  Cards are 118 × 124 below 520 px height and 146 × 132 otherwise.
- This does **not** use the BD-054 TouchLayout module.

## Evidence (offline, 2026-10-13)

Windows, pinned Luau 0.741 (same as CI), Python with Pillow/NumPy.

```text
python tools/verify_fusion_ui.py --runner <luau>
Fusion UI logic passed: filters, sorts, eligibility reasons, plain-only auto-fill (fuzzed), exact 100% odds (fuzzed), loss summary, token reuse, committed reveal wheels (fuzzed) and truthful Dino Details
Fusion UI smoke passed: 52 buttons >= 44 px in phone layout, unavailable fallback, paged list, locked stages, plain auto-fill, debounced exact odds, valuable highlight, itemized consent, same-token retry and resume, skippable reveal, fused/hatched details
```

1. **Logic.** The pure module runs directly in Luau:
   - every ineligibility reason and filter;
   - deterministic sorts, with cosmetics excluded from rarity;
   - toggling rules, including the full and locked-stage cases;
   - auto-fill: valuable, locked and favorited dinos are never picked, the selection
     stays anchored, shortfalls are reported, and a 200-population fuzz passes;
   - odds: largest-remainder percentages add to exactly 100% at the displayed precision
     (300-case fuzz). 1/3 splits show as 33.4/33.3/33.3. Tiny odds show as
     `<0.001%`, never 0%. Malformed or non-normalized odds are rejected;
   - the loss summary text;
   - token reuse: the same request in any order reuses the token, while a settled,
     changed or abandoned request gets a new one;
   - the reveal: stage order, every wheel landing on the committed value (200-case
     fuzz), a plain card for a committed value outside the odds, and a duplicate
     replay with no wheels;
   - Dino Details for hatched, fused and older dinos, including the no-% prestige check.
2. **UI smoke** ([`tools/fusion_ui_smoke.luau`](../tools/fusion_ui_smoke.luau)). The
   **real** FusionMenu, DinoDetails, FusionWidgets and FusionSelection code runs against
   a small Roblox mock (Instance tree, signals, task scheduler, services) and a fake
   `FusionAction` server. Visual modules are stubbed. It checks:
   - the remote-missing "Fusion unavailable" screen;
   - a two-page list;
   - the locked Emerald tab;
   - auto-fill, then a debounced quote, then exact odds text;
   - swapping in aura and Shiny donors, then a re-quote and valuable highlighting;
   - the itemized loss list, and that FUSE NOW is hidden until acknowledged;
   - a lost `fuse` response retried with the identical token;
   - skip to the final card, with a Gold preview carrying the committed Shiny;
   - fused and hatched details, and the list refresh after consumption;
   - a close-during-fuse → resume → same-token CHECK RESULT flow;
   - a 740 × 340 phone layout: compact strip, and every button ≥ 44 px.

   Mutation checks (forcing a new token on resume, or skipping the acknowledgement)
   make it fail. This proves control flow only, **not** rendering, layout, fonts, touch
   input or performance.
3. **Full CI suite** passed, plus `bind_artwork --check`, `build.py` (rebuilt
   `build/BeDino-Build020.*`) and `unittest`. The new verifier is now in the CI workflow.

## Verification pending

- **Studio (desktop), against the real `FusionAction` server:**
  - The full flow: list → filter/sort → auto-fill → manual valuable donors → quote →
    consent → fuse → reveal → details.
  - Every failure reason.
  - Rejoin with a pending token.
  - Duplicate confirm.
  - Reduced effects.
  - Gamepad selection.
- **Android phone, landscape (owner):**
  - Safe insets.
  - Real 44 px touch on cards, the **i** button, chips and slots.
  - Scrolling grids/odds/confirm.
  - Text legibility at the minimum `TextScaled` size of 9.
  - Reel smoothness.
  - Frame time with 200+ cards.
- **Final details payload.** Field names in the real `details` / `quote` payloads must
  match the brief (`lineage.parentEggs` is accepted as either a map keyed by egg ID or
  an array).
- **Not done here:**
  - Natural hatch odds calculation for hatched dinos (BD-062 math; it's shown as "not
    calculated yet").
  - Per-dino cosmetic purchase (BD-059).
  - Paid-random/PolicyService gating (BD-064). Robux stays off.
  - Final audio/FX assets for the reveal.
