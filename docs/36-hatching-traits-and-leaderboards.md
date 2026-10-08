# Hatching, traits and leaderboards

2026-10-08. Branch redesign/resources-and-core-fixes, Build redesign-019.
Baseline 3d8d1e4. Canonical acceptance remains docs/07-kanban.md, BD-035.

## Eggs and reveals

Server settlement precommits species, quantity, Shiny/BIG and catch-time event
metadata once, outside UpdateAsync. Within each run batch, rewards are sorted by
species rarity, stable within a tier. Older queued batches remain ahead. Overflow
preserves full metadata FIFO. New eggs are ready immediately; historical readyAt
timestamps are not rewritten. Legacy unrolled eggs keep the old claim-time roll.
Duplicate settlements/claims do not reroll or add copies twice.

After a run, the client waits for sanctuary respawn and automatically starts.
Each egg has a five-second sequence: native 3D egg, shake, branching fracture,
dinosaur reveal around 3.4s, then the next egg. Existing textured models/native
fallbacks are reused; no Pokemon assets are used. Closing stops auto-claiming;
the current claimed reward is already saved, remaining eggs stay in the queue.
Reduced effects suppress shaking, confetti and animated preview glints.

Rarity boost: b = 1 + 0.25 * (min(batch eggs,15)-1). Species weights multiply by
b^(rarity tier-1). One egg is 70% Common / 25% Rare / 5% Legendary; three eggs
are approximately 58.95% / 31.58% / 9.47%. More eggs improve both Rare-or-better
and Legendary chances. The current 10/100/500 catches -> 1/2/3 egg thresholds,
quantity rolls, direct run stacks and 500 food -> 15 catches remain unchanged.

## Independent traits

- Shiny: 5% for Volcano, Northern Lights, Earthquake and Blood Moon eggs. Ordinary
  Rain/Thunderstorm/Blizzard and clear eggs do not roll Shiny.
- BIG: 10% in every condition, including clear. Separate random draws, independent
  of Shiny and existing event mutation rolls. Both traits together: 0.5% in events.
- Catch-time event tags determine eligibility, not return/hatch-time weather.
- BIG makes the equipped dinosaur 1.3x larger, including horizontal collider and
  existing camera scaling. It adds no speed/growth multiplier. Maximum growth is
  now 5.2x visually for BIG versus 4x ordinary; maximum-size terrain QA is pending.
- Shiny only adds preview glints/badges. No world shimmer or gameplay perk.
- Trait variants store counts keyed by event mutation + both flags. They are
  separate from Base/Gold/Diamond/event-only counts and cannot be fused away.
  A species auto-uses its highest trait combination: stacked > BIG > Shiny,
  with stable key ordering for ties. Existing strongest event-perk selection is
  unchanged. Individual variant selection is not implemented.

## Boards and purchase safety

Three server-created sanctuary SurfaceGui boards, refreshed every 60s:
highest rarity tier obtained from banked run stacks/hatched eggs (Common/Rare/
Legendary), total time in the experience, and verified developer-product Robux.
Rarity ties remain ties; this is not a total-copy or Shiny/BIG leaderboard.
Metrics start with this feature; unavailable historical totals are not invented.
Playtime checkpoints use the owned profile lease, plus final release accounting.
OrderedDataStore publications are monotonic and separate from authoritative
profiles. Unpublished Studio uses only memory and labels boards UNSAVED PREVIEW.

ProcessReceipt grants configured crystal products and records PurchaseId plus
receipt CurrencySpent atomically in the leased profile. Receipt history is never
trimmed; a conservative 10,000-receipt guard fails closed. Unknown products or
failed saves return NotProcessedYet. No client supplies paid amounts. Product IDs
are deliberately unconfigured: no paid offers or fabricated IDs are introduced.
Game passes and past spending cannot be reconstructed by this receipt hook.
See [Roblox receipt documentation](https://create.roblox.com/docs/reference/engine/classes/MarketplaceService#ProcessReceipt).

## Verification boundaries

Offline: 54 sources compile; 27 Python tests; all existing Luau harnesses plus
verify_eggs pass. New tests cover monotonic weights, all six species, independent
roll grid, metadata/order, overflow, rejoin, duplicate claims/receipts, metrics,
legacy migration and fusion regressions. Syntax compilation is not type analysis.

Studio: only BeDino-VisualUpgrade.rbxlx, PlaceId=GameId=0, Build019. Actual remotes,
run lifecycle, repository and UI were exercised using disposable Script fixtures
with deterministic rewards/traits. All fixtures disappeared at Stop. No real paid
transaction, persistent profile, published place or OrderedDataStore was modified.
Screenshots and measured traces are archived beside the canonical checklist.
Live cross-server/persistence, real purchases, physical phones, maximum BIG
physics/load and art approval remain open, not certified by this local pass.
