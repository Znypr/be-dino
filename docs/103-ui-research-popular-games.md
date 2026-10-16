# 103 UI research: popular Roblox games (2026-10-16)

Owner request: look at the menus, shops, settings, animations and notifications of Grow a Garden, Steal a Brainrot and similar egg/pet games, and learn what is worth copying. Read with [87 vision and feel](87-vision-and-feel-guide.md), [72 UI copy and assets](72-ui-copy-and-asset-standards.md) and [43 paid-random policy](43-player-access-and-paid-random-policy.md).

## How this was researched, and the limits (read first)
Done with the Claude desktop built-in browser (Claude in Chrome was not connected). Read-only, one tab opened and closed, no sign-in, no downloads, no forms.

**Pages actually loaded and read as text:**
- growagarden.fandom.com: Home, Limited Time Shop, Seed Shop, Pet Eggs (Shop)
- stealabrainrot.fandom.com: Home, Index
- pet-simulator.fandom.com: List of Eggs (Pet Simulator 99) (only a table skeleton; prices/pets are images or collapsed)
- adoptme.fandom.com: Home
- blox-fruits.fandom.com: Settings
- create.roblox.com: Paid random items policy guidelines (first part)
- roblox.com game page for Grow a Garden (only title and tabs About / Store / Servers rendered; no description text)

**Not reachable or empty:** Pet Simulator "Egg Hatching" and Adopt Me "Shop" wiki pages (no text), YouTube/TikTok videos, any live in-game screen. A text read cannot show pixels, so **colours, exact layouts, animation timings and sounds are NOT observed**. Where this doc describes them they are labelled "general knowledge, unverified" and must be checked against screenshots or video by the owner or lead before any number is copied. No game was played. Nothing here is a measured timing.

## Per game: what was found

### Grow a Garden
- **Observed (wiki text):** The Shop button sits on the left of the screen and opens a "Limited Time Shop" for Robux offers (chests, premium eggs, tool packs, a "Forever Pack" pass, extra pet/egg slots, extra cosmetic slots, Seed Rain, Super Seed Packs, a one-time Starter Pack that disappears after 10 minutes). Some offers are hidden in Australia, Belgium, the UK and the Netherlands because of gambling laws.
- **Seed shop:** stock system; main stock refreshes every 5 minutes, "Daily Deals" every 24 hours; a few items always in stock, the rest chance-based (rarer = less likely, shown as "1 in N"). Sold-out buttons turn grey and say "NO STOCK". Players can pay Robux (79) or watch an ad to restock instantly. Items can be bought with in-game money, Robux or tokens, and gifted. Hovering a seed makes it expand and shake to show what it grows.
- **Pet egg shop:** eggs restock every 30 minutes (Robux refresh on demand); each egg shows a percent chance of being in stock. The wiki gallery lists screens for egg rarity info, sell pets, pet/egg equip slots, inventory capacity and a sort tab.
- **Rhythm:** weekly updates and events; quests give free seeds, gears and pets.
- **Pattern:** many parallel timers (5 min, 30 min, 24 h, 10 min starter) and several Robux entry points on one screen.

### Steal a Brainrot
- **Observed:** an "Index" menu lists every collectible; **owned ones are shown, unowned ones are black silhouettes**. Completing sections (Normal, Gold, Diamond, Rainbow, seasonal) gives a permanent multiplier or base skin; completion needs a percentage (60 to 100%) of items released before a date; hovering shows counts. A past bug: opening the Index with a huge list lagged the game (patched).
- **Pattern:** the collection screen is the long-term goal; silhouettes drive curiosity; percent milestones keep it reachable; sections per "mutation" tier.
- Not reached: shop, hatching, HUD.

### Pet Simulator 99
- **Observed:** egg list has 281+ eggs grouped by world and number ranges, with an "unlocked by" column; pets follow the player and collect coins. Odds/pet tables are images and were not readable.
- **General knowledge, unverified:** very fast hatch animation with auto-hatch and a skip option, big rarity-coloured reveals, a huge Index with event sections.

### Adopt Me
- **Observed:** five pet rarities (common, uncommon, rare, ultra-rare, legendary); age stages newborn to full-grown; combine four full-grown pets into a Neon and four Neon into a Mega Neon (the closest cousin of our Fusion); trading; potions.
- **Policy note:** this kind of combine mechanic is a "combination item" in Roblox's paid-random policy when inputs were bought with Robux.

### Blox Fruits
- **Observed:** Settings is a small panel next to the Crew button with only: Background Music, Ally VFX, Camera Shake, Damage Counter, Update Log, Codes, Fast Mode. A short toggle list; no sliders or language listed.
- **Pattern:** performance/effect toggles (Fast Mode, Ally VFX, Camera Shake) live next to music, which supports our Effects Full/Lite/Off plan.

### Roblox policy (official)
Paid random items (egg hatches, wheels, chests, luck boosts, **consuming or synthesizing items for a better chance**, pity systems) require showing all outcomes with numerical odds that sum to 100% before purchase, through a "Details" or "Info" word button (a bare (i) is not enough), including indirect purchases of keys/tickets and luck boosts. This matches docs/43.

## Synthesis

| Topic | What popular games do (observed or labelled) | Be Dino! stance |
| --- | --- | --- |
| HUD | Left-edge shop button; currency at top; counters (wiki text only) | Few big buttons; already planned in BD-056/080 |
| Shop structure | Sections per NPC/shop (Seeds, Gear, Eggs, Cosmetics, Limited Robux); stock and restock timers; grey "NO STOCK" | Copy sections and the clear sold-out state. Not Robux restock or stacked timers |
| Cards | Icon, name, price button, rarity (colour unverified), hover/expand preview | One card pattern, price button always at the card bottom, rarity colour from our palette |
| Currency | Money + Robux + tokens mixed on one card | One currency per card; crystals separate from Robux ([43](43-player-access-and-paid-random-policy.md)) |
| Timers | 5 min, 30 min, 24 h, 10 min starter pack | Calm copy ("Back in 3 min", [72](72-ui-copy-and-asset-standards.md)); never a countdown on a purchase offer |
| Hatching | Short, skippable, rarity-coloured reveal (general knowledge) | One egg at a time, about 5 s, skippable ([87](87-vision-and-feel-guide.md)); add batch skip and summary |
| Index | Silhouettes for unowned, percent milestones, per-tier sections | Copy; paginate or virtualise (SaB lagged) |
| Settings | Short toggle list (Blox Fruits) | Group by Sound / Look / Controls / Help (spec below) |
| Menu open/close | Pop/scale-bounce with dimmed backdrop (general knowledge, unverified) | Our own timing table below, owner to confirm by eye |
| Toasts | Short strips; weekly event banners | Existing Toast v2 ([80](80-notifications.md)) |
| Daily/quests | Free seeds/gears/pets from quests and events | Gentle daily gift, no streak loss |

### Worth copying
1. Index with silhouettes and milestone rewards (Steal a Brainrot).
2. Shop split into clearly named sections with one card layout.
3. Grey "Sold out" state with no extra text.
4. Hover/long-press preview on a card (what it becomes).
5. A short toggle-style settings list with a Fast/Lite option (Blox Fruits).
6. An odds "Details" button before any random purchase (policy, and good practice).
7. A weekly "something new" rhythm with a quiet banner.

### Do NOT copy (young audience, docs/87, docs/43)
- Paid instant restock or paid timer skips.
- Stacked countdowns and one-time "disappears in 10 minutes" offers (pressure).
- Robux beside every random item, luck boosts, pity systems, Robux-linked combine/fusion without disclosed odds and `PolicyService` checks.
- Ads-for-rewards in a kids game.
- Regional hiding of offers as a workaround: we simply have no paid-random offer until reviewed.
- Loud, rapid, screen-filling hatch effects and "NO STOCK" in capitals. Use "Sold out".
- Long Robux packs or bundles above the fold.

## Motion proposal (our own values, not copied; owner approves by eye)
| Moment | Proposal |
| --- | --- |
| Menu open | Backdrop fades 0 to 40% in 150 ms; panel scales 0.92 to 1.0 with soft overshoot, about 220 ms |
| Menu close | Reverse, no overshoot, 150 ms |
| Card tap | 0.96 squash 80 ms then back |
| Toast in/out | Slide 12 px + fade, 200 ms in, 150 ms out |
| Calm motion | Fade only, 100 ms, no overshoot or shake |

## Settings menu spec proposal
Fits BD-095 (Effects Full/Lite/Off), BD-202 (audio mixer, session-only today) and BD-081 (sound style). Four tabs, big toggles and segment buttons, short words.

| Section | Option | Control | Notes |
| --- | --- | --- | --- |
| Sound | Everything | slider | existing mixer group (BD-202) |
| Sound | Sounds | slider | UI and game cues |
| Sound | Weather | slider | ambience beds |
| Sound | Music | slider | hide until music exists |
| Look | Effects | Full / Lite / Off | BD-095; Lite halves particles, Off keeps only essentials |
| Look | Weather look | Full / Lite / Off | weather particles and haze (docs/84); readability radius unchanged |
| Look | Calm motion (Reduce Motion) | toggle | fade-only menus, no camera shake/zoom |
| Look | Camera shake | toggle | off with Calm motion |
| Look | Fast mode | toggle | one switch that sets Effects Lite and Weather Lite, for phones |
| Controls | Camera speed | slider | |
| Controls | Jump button size | Small / Normal / Big | phones |
| Help | Text size | Normal / Big | |
| Help | Language | list | only when a translation exists |
| Help | Codes, What is new | buttons | optional later |

Rules: settings save per player (not session-only), apply instantly, one fact per line, no hidden thresholds.

## Recommendations
Added to the Kanban as BD-263 to BD-274 ([07](07-kanban.md)).

| BD | P | Task | Acceptance | Related |
| --- | --- | --- | --- | --- |
| 263 | P1 | Settings menu v2, 4 tabs per spec | Options work on phone and desktop, Studio screenshot | BD-095, BD-202, BD-081 |
| 264 | P1 | Persist settings per player | Survive rejoin, default Full, bad values fall back | BD-202 |
| 265 | P1 | Effects and Weather Full/Lite/Off plus Fast mode | Particle counts lower in Lite (counted), Off keeps essential cues | BD-095 |
| 266 | P1 | Calm motion switch for menus, camera, hatch | Fade-only menus, no shake, hatch readable | BD-095, BD-202 |
| 267 | P1 | One shared shop card component | All shops use it; grey "Sold out"; copy per docs/72 | BD-051, BD-260 |
| 268 | P1 | Menu open/close motion pass | Owner approves by eye; Calm variant exists | BD-266 |
| 269 | P1 | Index screen with silhouettes and percent milestones | Paginated, no lag at 200 entries | BD-062 |
| 270 | P1 | "Odds / Details" word button before any random action | Odds sum 100%, luck effects explained, no bare (i) | docs/43 |
| 271 | P2 | Hatch batch skip-all and summary card | Counts by rarity, one reward cue only | BD-069, BD-262 |
| 272 | P2 | Calm restock copy and timers | "Back in 3 min", no paid skips, no pressure countdowns | BD-051 |
| 273 | P2 | Gentle daily gift, no streak loss (owner to confirm) | One claim per day, toast v2 message | BD-067 |
| 274 | P2 | Card preview on hover/long-press | Touch and mouse, phone screenshot | BD-267 |

## Open questions for the owner
1. Can the owner share screens or a recording of Grow a Garden / Pet Simulator 99 so colours and timings can be checked (not observed here)?
2. One "Fast mode" switch, or only the separate Full/Lite/Off toggles?
3. Is a daily gift wanted at all (BD-273)?
