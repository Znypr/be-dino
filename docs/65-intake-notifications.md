# 65 - Intake: popup/notification system

Template: [64](64-feature-intake-template.md). Status: **Proposal**, nothing built. Tasks BD-066 to BD-071 (Backlog).

## 1-3. Intention, new vs extension, fit
- **Intention:** tell the player something important happened without pulling them out of the run; make rare moments feel big and routine ones quiet.
- **Extension (Seen):** `notify(text,color)` in `src/client/Bootstrap.client.luau` (~line 150): one plain 440x56 card at y=80, 3 s, no icon, no stacking; a new call replaces the old one. Call sites include crystal gain (~832), potion refresh (~442), weather start (~871), growth (~1012), egg caught (~1024), purchases and errors.
- **Proposal:** keep `notify()` as the API and route it through a queue; new optional fields `{kind, icon, priority, key}`. Existing call sites keep working.
- **Fit:** client-only presentation. Events already exist as attributes/remote results; no new remotes; server stays authoritative.

## 4. Graphical fit (Proposal)
Top-center at the current toast slot (y=80), width min(440, 90% of screen), stack grows downward: max 3 cards x 56 px + 6 px gaps (about 180 px). Clear of the top-right crystal/goal line and the bottom thumbstick/jump zones (`TouchLayout`). Major cards wait while the hatch reveal or a modal is open. Cards are non-interactive; tap dismisses only the top card.

## 5. One design language (Proposal)
Backboard: one `toast-body` 9-slice plate tinted at runtime (Info dark, Good green, Rare blue/purple, Legendary gold with `reward-burst` behind the icon, Warning red), matching the `card-common/rare/legendary` and button palette. Left: 40 px icon in a round plate (native `UICorner` frame, no asset). Right: title (bold, 22) and optional one-line body (16). Rarity color = left accent bar + icon plate. Fonts from `UITheme`.

## Queue rules (Proposal)
- Max 3 visible. Priority: major 3 > warning 2 > info 1. A major card bumps the oldest info card.
- Dedupe by `key` (e.g. `potion_restock`): a repeat while visible refreshes the timer and shows a `x2` counter.
- Throttle: info max 1 per 1.5 s; same key min gap 5 s; queue depth 8, drop lowest priority oldest.
- **Hatch batches:** per-egg events never become popups (the reveal is the feedback). One summary card at the end ("40 eggs hatched" + best find). Only Legendary/Shiny/BIG/event-mutation finds get a card, max 1 per 5 s, the rest folded into the summary.
- Duration: info 2.5 s, good 3 s, warning 4 s, major 4.5 s.

## 6. Events and copy (Proposal; titles not final)
| Group | Event | Title / body | Kind | Icon | Sfx |
|---|---|---|---|---|---|
| Major | Fusion success (Gold/Emerald/Diamond) | "Gold Compy created" / "15 merged" | Legendary | fusion | fusion_reveal (already plays, none extra) |
| Major | Legendary/Shiny/BIG find (batch cap applies) | "Legendary Rex hatched" | Legendary | egg | existing hatch_* |
| Major | Event-mutation egg caught | "Magma egg caught" / "Hatch it at Home" | Rare | mutation-egg (new) | pickup_hi |
| Major | Level up | "Level 5 reached" / "New shop items" | Good | level (new) | level_up (already plays) |
| Major | Objectives done/claimed (doc 66) | "Daily goals done" / "+60 Crystals" | Good | star (new) | shop_buy |
| Major | New species collected | "New dino: Compy" | Rare | dinos | pickup_hi |
| Minor | Potion shop restocked | "Potion shop restocked" / "3 new offers" | Info | potion | shop_refresh |
| Minor | Weather started | "Rain started" / "Growth boost" | Info | weather icons | weather_start |
| Minor | Crystals gained | "+30 Crystals" (merge to one counter card) | Good | crystal (new) | none |
| Minor | Purchase ok | "Swift Sip bought" | Good | potion | shop_buy |
| Minor | Potion expired | "Swift Sip ended" | Info | potion | none |
| Minor | Bonus nest ready | "Bonus nest ready" | Info | egg-nest | pickup_hi |
| Minor | Plain egg caught, leap ready | no card (HUD counter / button) | n/a | - | existing |
| Warning | Hatch failed (Cracked egg, 20% success) | "Hatch failed" / "The cracked egg crumbled" | Warning | cracked egg (reuse `premium-egg-cracks`) | hatch_crack |
| Warning | Bigger dino blocks going Home | "Too dangerous to leave" | Warning | shield | none |
| Warning | Not enough Crystals/copies/level | "Need 150 Crystals" | Warning | crystal | ui_click |
| Warning | Generic failure / profile not loaded | "Something went wrong. Try again" | Warning | warning (new) | none |
| Warning | Nests full | "Nests full" / "Open one to claim more" | Warning | egg-nest | none |

Free-text error strings (`status:gsub("_"," ")`) must map to this copy table.

## 7. Reuse vs new
Reuse: `notify` API, `C` palette, `UIIconAssets` icons (egg, dinos, fusion, shield, home, weather x4, leap, trophy, amber), v2 card tints, reward-burst. New: the `toast-body` plate (1 image) and 5 icons below.

## 8. New icon list (5; v2 style, 1:1 transparent PNG, readable at 32 px)
1. crystal (faceted AMBER gem, corrected 2026-10-17 per handbook s5.3; it said "blue" before), 2. level (rounded star with up-chevron), 3. star (completion, 5-point, shared with doc 66), 4. mutation-egg (egg with flame swirl), 5. warning (rounded triangle with bar).
Potion already exists as `resources/ui/v2/scalable/potion.*` and needs an owner upload/binding (not in `UIIconAssets` today). Cracked egg reuses `premium-egg-cracks`; draw new only if unreadable at 32 px.

## 9. Animations (Proposal)
Slide+fade in 0.14 s from -12 px; stack reflow 0.12 s; exit fade 0.12 s; Legendary: reward-burst pulse 0.4 s once and icon pop to 1.15; `x2` counter bump. Motion off: no tween, instant show/hide, no burst. Via `Theme.animate`; 3 pooled cards, never created per event.

## 10-12. Data, performance, metrics
No persistence or remotes. Throttle is display-only. Cost: 3 pooled frames, no per-frame work. Metric: playtest "did you notice restocks" question; shown-vs-suppressed counters in an attribute.

## 13. Acceptance
Offline: queue tests (priority, dedupe, throttle, cap, batch summary). Studio: 400-egg auto-hatch yields at most one card per 5 s plus the summary. Android phone landscape: no overlap with thumbstick or HUD. Motion off and sound off verified.

## 14. Tasks
| ID | Size | Role | Task | Deps |
|---|---|---|---|---|
| BD-066 | M | design/code | Pure `NotifyQueue` module (priority, dedupe, throttle, cap, summary) + tests | none |
| BD-067 | M | UI | Toast v2 renderer, 3 pooled cards, tints, motion-off, `notify` shim | BD-066 |
| BD-068 | M | art | 5 icons + toast-body plate; owner upload and bind (plus potion binding) | none |
| BD-069 | M | UI | Wire the event table, replace ~25 `notify` sites, hatch summary | BD-067 |
| BD-070 | S | UI | Sfx mapping without double-playing existing hooks | BD-069, doc 63 ids |
| BD-071 | S | QA | Studio + Android acceptance | all |

## 15. Owner questions
1. Should every "+N Crystals" show as a popup? Recommended: merge into one counter card, max 1 per 3 s.
