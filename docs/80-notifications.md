# 80 Notifications v2 (BD-066, BD-067, BD-069), 2026-10-14

Status: **Review / test**. Code and offline queue tests are done; Studio and phone checks are pending.
Spec: [65](65-intake-notifications.md). This is playtest scope (owner, 2026-10-14: "the notifications should also work").

## What players see
- Up to **3 cards** stacked under the old toast slot (top centre, y=80). Each card has a coloured side bar,
  an icon plate, a title and an optional short second line. Tapping a card closes the newest one.
- The colour shows the kind: blue for info, green for good news, red for problems, gold for big moments.
  Hatch summaries use the rarity colour of the best find.
- **Fewer, calmer popups.** The "+Growth" toast on every bite was removed (the floating `+N` and the
  sound already show it). Plain egg catches no longer pop up (the HUD counter shows them). Crystals
  merge into one counting card ("+17 Crystals"). The same message repeating shows once with x2, x3.
- **Big moments wait.** Level-ups and special egg catches wait while a menu or the hatch reveal is open,
  and can push out an older info card when the stack is full.
- **Hatch batches:** each egg's reveal is the feedback. When a batch ends, one card says
  "12 dinos hatched / Best: Shiny Rare Triceratops". It is gold when the best find is Epic, Legendary or Shiny.
- **No raw error codes.** Server codes such as `insufficient_crystals` map to short copy ("Not enough
  Crystals"). Unknown codes show "Something went wrong. Try again".

## How
- `src/shared/NotifyQueue.luau` is pure and has no Roblox dependencies, with the clock passed in. It
  handles max 3 visible and priority (major > warning > good/info). It merges by `key`, adding counters
  together through `amount`/`format`. Info cards are limited to one per 1.5 s, an info key that just
  expired is held off for 5 s, and at most 8 cards wait (the lowest priority, oldest card is dropped).
  Majors are held while `blocked`. It also provides `hatchSummary` and `statusText`.
- `Bootstrap.client.luau`: 3 pooled card frames (never created per event), redrawn only when the queue
  changes, pumped every 0.1 s. `notify(text, color, opts?)` keeps every old call site working; `opts`
  adds `kind/key/icon/body/tint/amount/format`. Motion off means no slide or pop.
- Icons reuse bound art: `amber` (crystals), `trophy` (level), `egg`, `egg_nest`, `shield`, the weather
  icons, and a native potion bottle. No new art was made in code. The 5 dedicated icons and the
  card plate remain BD-068 (art pipeline, docs/72).

## Wired events
Crystals gained, weather started, level up, special (event-mutation) egg caught, new egg nest, nest
opened, nest status, too dangerous to go home, potion shop restocked, shop/equip/mutate success and
failures, hatching stopped, hatch-batch summary.
**Not yet:** fusion success (the fusion reveal already celebrates), "new dino discovered", potion expired,
daily objectives (BD-072+). Sounds keep their existing hooks (BD-070 not needed for the playtest).

## Evidence
`python tools/verify_notify.py --runner <luau>` (added to CI) covers the cap, info throttle and expiry,
warning priority, merging and counters, the key gap, waiting overflow, majors held while blocked and
bumping info, warnings that cannot be bumped, dismissal, bad input, the hatch summary (single egg = none,
best-find ordering, all failed) and that the status copy contains no raw codes. The full CI command list
passed locally.

## Not verified
Card layout and stacking in Studio, the phone (no overlap with the thumbstick, jump or HUD), a
400-egg auto-hatch in Studio (expected: one summary card), and motion off.
