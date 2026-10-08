# Build 018: integrated progression and Build 017 fixes

> **HISTORICAL Build 018 handoff.** Its phrase "This is the current full build" applied only to this milestone. **Build 020 is now on GitHub main**. For current instructions use [Build 020 handoff](34-studio-handoff.md) and [integration checklist](44-main-integration-checklist.md).

## Downloads and scope

- `build/BeDino-Build017-Final.rbxlx`, badge `BUILD redesign-017-final`: isolated menu/icon/egg/dinosaur-preview fixes. Historical Build017 is retained unchanged.
- `build/BeDino-Build018.rbxlx`, badge `BUILD redesign-018`: those fixes plus crystal currency, Aura Shop, leap, weather and Potion Shop. This is the current full build.

Source implementation is complete for BD-023–026 and BD-028–033. Tasks remain Review / test until Roblox Studio acceptance. BD-027 still requires live floor-food and sanctuary-return evidence. Local stubs do not establish that the user's no-food issue is resolved in the engine.

## Implemented behaviour

Crystal currency: 64 random accessible map pickups, 3 crystals each, 90-second respawn at a new location. Saved immediately through the leased profile repository, independently of run growth. Existing high-value amber food remains a separate +50-growth item; the currency pickup is labelled +3 Crystals. No public grant remote exists.

Aura Shop: Meadow Glow (60 crystals, 1.15x eating growth), Tidal Halo (240, 1.35x), Royal Nova (900, 1.7x). Permanent ownership, one equipped aura, ring of eight scaled particle attachments and coloured light. Buy, insufficient funds, owned, equip and unequip states. Price/growth values are configurable private-test balance.

Leap: Q on desktop, controller Y, or bottom-right touch action. Grounded, active-run use only, forward velocity 72 and upward velocity 62, 0.7-second server-owned movement window, exact 60-second cooldown. Blockcast checks initial/swept path, stops at obstacles and restores automatic network ownership. Cooldown survives run restarts in the same server.

Weather: 600 seconds of clear weather followed by a randomly selected 180-second event. Next-event timing is visible; type is selected only when it begins. Rain, Thunderstorm and Blizzard affect growth, speed and reward catches. Common/Rare/Legendary event bonus factors are 1/1.35/1.75, applied to the bonus above 1x. Weather loot increases earned reward-catch units using fractional carry; it does not multiply wallet crystal grants. Rain/snow and thunder flashes use a bounded client-local effect pool.

Potions: six products, Speed and Growth in Common/Rare/Legendary tiers. Common lasts 5 minutes, Rare 10, Legendary 15. Exact catalog prices/multipliers are in ProgressionConfig. Inventory and active expiry timestamps persist. Same-type buffs require explicit replacement confirmation; remaining old time is discarded. Different types coexist. Timers continue offline.

Combined eating-growth multiplier = aura × rarity-adjusted weather × active growth potion, capped at 8x. Speed = rarity-adjusted weather × speed potion, capped at 2.2x. The existing physical size curve still caps dinosaur size. Weather loot multiplier is independent. Server-owned movement limits account for permitted speed buffs and leap.

UI: wider navigation with separate text/icon regions, screen-sized modal fit without overshoot, tight mesh-vertex preview cameras, coloured smooth egg previews, Aura/Potion screens and confirmations, crystal balance, leap/weather countdown tiles and active buff timers. Existing crystal model supplies the native crystal icon; full-resolution original crystal PNG remains available for owner image binding.

20 individual 512px transparent PNGs and SVGs in `resources/ui/v2/scalable`, with shared geometry rendered using native GUI primitives. No enlarged 32px tile rendering remains in UITheme. Original generated PNGs remain available; this build uses the sharp scalable style without requiring external asset IDs.

## Completed local validation

- Official parser: all 38 Luau files accepted.
- 19 Python packaging, economy and resource tests pass.
- Actual FoodService/RunLifecycle modules pass deterministic stub execution checks.
- Terrain, routes, movement envelope and existing mesh/icon data execute successfully.
- Actual progression rules and ProfileRepository transactions pass repeated transform, duplicate grant/purchase/use, token-conflict, reconnect, potion replacement/expiry, outage rollback and lease-loss checks.
- Actual WeatherClock passes start/end boundary checks and selects no future type early.
- Actual LeapService handler passes malformed request, exact cooldown, wall/air rejection, failed network ownership and cleanup checks.
- Actual PreviewCamera projects every vertex of all three species inside the frustum across four card aspect ratios while retaining tight framing.

## Studio acceptance, in order

1. Open Build018, verify badge, Output and FOOD count/status. Enter island; record visible berry/fruit/egg/high-value food and labelled currency crystals.
2. Collect currency with two clients racing one pickup: exactly one grant. Wait for respawn and verify a new location. End run/die/rejoin a published private test and confirm saved balance.
3. Open all menus at desktop, small Studio viewport and phone orientations. Inspect navigation text, egg states, large centered dinos, Home/Trophy quality and unobstructed timers/touch controls.
4. Buy each aura, repeat a request and try insufficient funds. Equip/unequip; compare eating growth and size-scaled VFX. Rejoin to verify ownership/equipment.
5. Leap on ground, beside walls and toward mountains. Verify 60-second countdown, no airborne repeat, no impossible-movement rejection and cooldown continuity after death/return. Test controller/touch.
6. Wait for weather or temporarily reduce ProgressionConfig.WeatherInterval in an isolated test build. Verify hidden next type, late-join timers, rarity bonuses, event cleanup and precipitation. Restore production test tuning afterward.
7. Buy/use potions, replace same type, combine different types, let expire, leave/rejoin and verify offline expiry. Check caps with aura plus weather plus potion.
8. Verify End Run settlement, egg claims, Gold fusion and historical persistence security regressions. Profile 8–12 clients and reduced-effects setting.

No balance, rendering, physics, DataStore budget or mobile performance signoff is claimed without this evidence. These builds are private-test deliverables.
