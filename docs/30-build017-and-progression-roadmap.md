# Build 017 completion and progression roadmap

> **HISTORICAL Build 017/018 task plan.** Older unchecked boxes reflect then-pending Studio acceptance, not necessarily absent Build 020 code. Use [current integration](44-main-integration-checklist.md), [owner tasks](45-owner-feedback-shop-hud-world-weather-tasks.md) and [Kanban](07-kanban.md).

Recorded 2026-10-04 from Znypr's playtest feedback and feature requests. Status is tracked only in [07-kanban.md](07-kanban.md). Implementation is now prepared in Build 017 Final and Build 018; [current implementation and local verification](31-build018-progression-test.md). Checkboxes below represent open Studio acceptance, not missing source code.

## First: finish Build 017

- [ ] BD-023: prevent menu cropping. Fit the full popup, title, close button and action footer within the usable screen with consistent margins; scroll overflow content. Check desktop, narrow Studio viewport, phone landscape and portrait.
- [ ] BD-024: restore egg previews in Growing Eggs, hatch and any egg cards; verify empty/occupied/ready states, reopen and resize. Investigate the actual runtime error instead of assuming the previous smooth-mesh change works.
- [ ] BD-025: enlarge dinosaurs in Index, sanctuary and detail previews. Fit visible geometry tightly, center it, reserve room for labels, and avoid cropping horns/tails during motion. Test all species and Gold variants.
- [ ] BD-026: audit every UI image, including Home and Trophy. Remove enlarged 32px native-raster representations from the final presentation; integrate existing full-resolution originals and verify asset access under the experience owner. Use clean scalable geometry where suitable, never silently substitute a visibly pixelated icon.
- [ ] BD-027: verify floor food appears, can be eaten, grants correct growth and respawns. Inspect FoodSpawnStatus/count/error if absent. Recheck End Run returning to sanctuary and menu regressions. Record actual Studio evidence before closing Build 017.

## Then: implementation order

1. Crystal wallet and pickups, including safe persistence and collection.
2. Aura catalog, purchase/equip logic, visible effects and eating-growth multiplier.
3. Leap movement and cooldown UI, with multiplayer movement validation.
4. Weather scheduling, rarity-adjusted buffs and timer UI.
5. Potion catalog, timed buff inventory and purchase/use UI.
6. Integrate matching icons alongside each system, then run combined economy, multiplayer and device checks. BD-033 art preparation can start after the icon rendering fix.

## BD-028: crystals as currency

- [ ] Reuse the existing crystal artwork (`resources/ui/v2/icons/amber.png`) and crystal world model; use one player-facing name, Crystals.
- [ ] Spawn collectible crystals randomly throughout accessible map areas in small scattered clusters, with configurable rarity, amount and respawn rules.
- [ ] Separate currency grants from food growth points. Define the existing high-value crystal food interaction explicitly so a single pickup cannot accidentally grant duplicate wallet rewards.
- [ ] Persist wallet balance independently of run growth. Provisional rule: collected crystals remain banked when a run ends or the player dies.
- [ ] Add crystal HUD counter, pickup feedback and insufficient-currency state.
- [ ] Server validates pickup distance, ownership/claim races and amount. Purchase retries cannot deduct twice; load failures cannot overwrite saved currency.

## BD-029: aura shop

Adapt the [Trail Shop reference](../resources/references/steal-an-egg/reference-212804.png) with original aura art and dinosaur logic.

- [ ] Aura product grid: rarity border, large preview, name, eating-growth multiplier, crystal price, Locked/Buy/Owned/Equipped states and close control.
- [ ] Purchase confirmation, success feedback, insufficient-crystal feedback and direct equip/unequip.
- [ ] Permanent owned auras, one equipped at a time; persist ownership and equipment.
- [ ] Attach aura effects to the dinosaur and scale their radius with dinosaur size. Include reduced-effects settings and performance limits.
- [ ] Apply the aura multiplier to growth gained when eating; recalculate physical dinosaur size from resulting growth using the existing size curve. Do not give passive growth merely for wearing an aura.
- [ ] Configurable catalog of aura tiers, visual themes, prices and multipliers. Balance is provisional until crystal income is measured.

## BD-030: leap ability

- [ ] Super jump combined with a fast forward dash, usable for attack positioning or escape.
- [ ] Exact cooldown: 60 seconds after an accepted activation. Server owns readiness and validates active-run state, direction and movement.
- [ ] Configurable leap height/distance/duration; sweep collision path and stop at obstacles. Integrate with movement envelope validation so legitimate leaps are accepted without permitting arbitrary teleports.
- [ ] Bottom-right timer tile: leap icon, countdown, ready state and activation feedback. Keyboard/controller input plus a touch button; block activation while typing or interacting with a modal.
- [ ] No automatic damage exemption or guaranteed kill; normal predation rules still decide the result.
- [ ] Test spam, death/respawn, cooldown reset rules, terrain, walls, maximum dinosaur size and competing requests. Provisional rule: cooldown persists across run restarts in the same server.

## BD-031: random weather and rarity benefits

- [ ] Random weather types including Rain and Thunderstorm; expand with Blizzard and other existing weather concepts after auditing current systems.
- [ ] Bottom-right timer shows time until the next event. Keep the future event type hidden until it begins. During an event show its icon/name, time remaining and actual bonuses.
- [ ] Server selects the event type at event start. Randomness and hidden selection prevent predicting the type; a visible countdown intentionally reveals timing.
- [ ] Start with the requested earlier cadence of approximately 10 minutes between events and 3-minute duration, configurable after reviewing existing weather code. Document whether interval includes event duration.
- [ ] Weather can affect eating-growth rate, movement speed and obtainable run loot. Choose per-event bonuses; no promise that all buffs apply in every event.
- [ ] Every dinosaur rarity has a configurable event-benefit multiplier, increasing with rarity. Apply it to the bonus above baseline: effective multiplier = 1 + (event multiplier - 1) * rarity factor. Normal weather remains 1x for every rarity.
- [ ] State the actual rarity-adjusted bonuses in the UI. Define which loot systems receive bonuses and avoid multiplying crystal currency unintentionally.
- [ ] Sync event clock/state for late joiners. Reuse or extend existing scheduling rather than introduce duplicate event controllers.
- [ ] Test join-in-progress, event end cleanup, dinosaur equip during weather, rarity extremes and effect performance.

## BD-032: potion shop

- [ ] Buy potions with crystals. Initial types: Speed and Growth.
- [ ] Include 5-minute versions plus distinct rarity tiers with configurable durations, multipliers and increasing crystal costs.
- [ ] Product cards show type, rarity, exact multiplier, duration, price and quantity owned. Purchase confirmation, insufficient funds and success states.
- [ ] Potion inventory allows Use; active buff HUD shows icon and remaining time.
- [ ] Provisional policy: same-type potion buffs do not multiply each other. Ask for confirmation when replacing an active potion; make the remaining-time consequence clear before consumption. Different types can coexist.
- [ ] Persist inventory and active expiry timestamps; timers continue while offline, with clear wording. Server validates and atomically consumes one potion.
- [ ] Centralize combined aura/weather/potion growth and weather/potion speed calculations; apply configurable caps and show effective bonuses. Potions do not reduce leap cooldown unless a separate feature is approved.
- [ ] Test duplicate purchases/use, expiry, reconnect, death, event transitions and combined boosts.

## Screens and UI elements to build

| Screen/element | Required content |
|---|---|
| Crystal HUD | Existing crystal art, saved balance, pickup feedback |
| Aura Shop | Rarity grid, 3D/VFX preview, growth bonus, price, ownership/equip states |
| Aura confirmation | Item, cost, resulting balance, buy/cancel |
| Potion Shop | Tier/type filters, multiplier, duration, crystal price, inventory count |
| Potion inventory/use | Owned items, activation, replacement confirmation |
| Bottom-right ability tile | Leap action, ready/cooldown state, 60-second timer |
| Bottom-right weather tile | Unknown next event countdown, active event/expiry and rarity-adjusted buffs |
| Active boosts | Potion timers and effective bonuses, compact responsive layout |
| Shared feedback | Purchase success/error, insufficient currency, locked/owned/equipped states |

Inspect the existing [gameplay HUD](../resources/references/steal-an-egg/reference-212704.png) and timer/queue references before layout work. The gallery identifies a Trail Shop screenshot, but does not yet establish exact leap/weather timer visuals; do not invent observed reference details. Keep timer tiles clear of Roblox controls and mobile jump buttons.

## BD-033: matching icon and effect backlog

Keep the existing dimensional, outlined, saturated art style. Save individual transparent high-resolution assets under `resources/ui/v2/icons/`; document prompts, logical keys and Roblox image bindings. 20 sharp scalable assets now exist in resources/ui/v2/scalable. Tier colours are configurable variants of the shared aura/potion artwork; existing crystal artwork remains available.

| Asset/key | Needed for | Reuse/new |
|---|---|---|
| crystals | Wallet, prices, map rewards | Reuse amber/crystal original |
| aura-shop | Navigation and shop header | New glowing dinosaur silhouette/ring |
| aura tier thumbnails | Individual aura products | New, one per configured aura |
| leap | Ability action and cooldown | New forward-leaping dinosaur |
| weather-unknown | Next event type hidden | New cloud with question mark |
| rain | Rain event/timer | New |
| thunder | Thunderstorm event/timer | New |
| blizzard | Blizzard event/timer | New if included |
| potion-shop | Shop navigation | New potion bottles |
| potion-speed | Speed consumables | New, tier variants |
| potion-growth | Eating-growth consumables | New, tier variants |
| clock | Duration and remaining time | New reusable |
| equipped/check, lock | Shop states | Reuse existing if suitable, otherwise new |
| home, trophy | Existing navigation/results | Integrate full-resolution originals |

World/VFX work: collectible crystal variants, aura attachments/particles per tier, leap launch/landing effect, potion activation burst and weather ambience. Prefer shared effect templates with configurable colours/intensity; profile large dinosaurs and 8–12 players.

## Completion evidence

For every task record commit, artifact/build badge, source checks and Studio screenshots/video for its acceptance cases. Combined tests must cover crystal exploits, inventory saves, stacked buffs, movement security, UI cropping, asset permissions and mobile controls. Do not mark a task Done merely because code or artwork exists.
