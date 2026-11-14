# 235 Top-games benchmark (BD-1191 loop), 2026-11-14

Owner 2026-11-14: "always cross reference the game ui, assets, behavior, retention etc. with the top performing roblox experiences and make sure its up to standard." This page is the standing benchmark the polish loop (docs/234) checks against every run; the `benchmark` role of the review panel scores each area. Labels: **CURRENT BUILD** = what the source does today (playtest profile), **TARGET** = the top-game standard.

Reference set (look at their current versions before a review): Grow a Garden, Pet Simulator 99, Adopt Me!, Steal a Brainrot, Bee Swarm Simulator, Fisch. Outside data: GameAnalytics' 2025 Roblox benchmark report (return frequency up ~33% year on year, driven by re-entry design and offline progress; games with 0-6 minute sessions fall under 10% Day-1 retention, hits sit at 19+ minutes; checklist: quests, streaks, offline progression, co-play). Grow a Garden's crops grow while the player is offline, which is its main reason to come back.

## 1. Retention and return (biggest gap)

| Mechanic | Top games | CURRENT BUILD | Gap |
| --- | --- | --- | --- |
| Offline progress | crops / pets / eggs keep going offline | egg nests incubate 3 h one at a time, server time (BD-090) | **has it**; make the "ready" moment loud and visible on join |
| Session length | 19+ min | a run is about 5 min, then the hatch | **risk**: chain runs (next run in one tap, run streak bonus) and give the lobby things to do |
| Daily login reward / streak | yes (3-7-21 style) | none | **missing** |
| Playtime rewards (gifts at 5/10/20/30 min) | yes, nearly all | none | **missing** |
| Quests / objectives | daily + weekly | Objectives panel built, `ObjectivesEnabled` false | **switched off**: turn on in playtest, add daily set |
| Co-play bonus (friends in server) | yes (luck / coin boost) | none (only measured in FunnelService) | **missing** |
| Codes | yes (social codes) | admin tools only | **missing** player codes |
| Group reward | yes (join group = bonus) | none | **missing** |
| Badges | many | none | **missing** (first hatch, first Rare, Index milestones) |
| Collection completion rewards | Index milestones give rewards | Index shows progress, no reward | **missing** |
| Limited-time events | weekly events, admin abuse events | weather events with mutation eggs | **has it**; needs a visible schedule and event UI |
| Leaderboards | yes | `Leaderboards.luau` exists | check it is shown in the lobby |
| Return notifications | Roblox experience notifications ("your egg is ready") | none | **missing** (nest ready) |
| Trading | top pet games | none | later (policy + scam risk), not now |

## 2. UI (docs/232 rules, polish loop scores)

Target: every screen 8+. Run 1 average 4/10. Top games: one style, big readable icons, full-width layouts, one primary button, price on the button, rarity colour everywhere, juicy open / buy / reward feedback.

## 3. Assets

Target: no code-drawn shapes or stand-ins anywhere a player looks. CURRENT BUILD: ~250 icon drafts waited unpicked (34 bound 2026-11-14, docs/233); missing dino portraits (31), pattern icons (8), aura icons (remake), Legendary aura art, one potion icon (Prime Feast blank tile).

## 4. Behaviour and feel

Top games: instant feedback on every tap (sound + bounce), reward explosions, number pop-ups, clear "what next" arrow. CURRENT BUILD: motion presets exist (BD-1182, flag), hatch pacing tuned (BD-1164). To check each run: does every button press animate, does every reward pop, is the next goal always visible.

## 5. How the loop uses this page

Every polish run adds a `benchmark` review: for each row above that is "missing" or "risk", one finding (kind `retention`, `ui`, `asset` or `feel`) with severity and reach; `tools/polish_loop.py rows` turns the top ones into rows. New features go through spec + backlog first (feature intake rule), economy numbers stay PROVISIONAL and never touch Robux.
