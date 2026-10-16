# 86 Monetization ideas (parked, not scheduled)

Owner 2026-10-15: "pay to win options we can add later on, just ideas; not high priority". Nothing here is built.
The playtest keeps all Robux features off (`Config.PaidRandomItemsEnabled = false`, crystal packs "Coming soon").

## Principles (from the game's vision)
- **The audience is children and their parents.** We sell time, convenience, information and looks. We never sell a way to win fights or a guaranteed rare dino.
- **The free game is complete.** Everything paid can also be reached by playing; paid just reaches it sooner or looks nicer.
- **Never sell randomness for Robux** until odds disclosure and the platform's paid-random-item rules are met. Our odds screens exist, but the flag stays off.
- **No pressure.** No countdown "last chance" offers, no "buy now or lose it", no streak punishments. Passes are permanent, not seasonal.
- **Plain copy** (docs/72): "Auto-open: skip Common eggs", price in R$ shown once, no jargon.
- **Everyone benefits when possible.** Shared-world perks (weather) help the whole server, which fits the friends-playtest vision.

## Four kinds of products
| Kind | Player feeling | Examples below |
|---|---|---|
| Time saved | "I got to the fun part faster" | auto-open, nest warmer, instant open |
| Information | "I know when to play" | weather radar |
| Looks | "My dino and my hatch look amazing" | auras, trails, hatch styles, home skins |
| Capacity | "I can keep more" | more nest slots, more storage |

## Ideas
| Idea | What the player gets | What it never does | Fit | Size | Priority |
|---|---|---|---|---|---|
| **Auto-open pass** (built, flag `Config.AutoOpenRequiresPass`) | Per-rarity Auto-open: skip the reveal of Common and Uncommon eggs, summary at the end | Never skips Shiny, BIG or mutations; never changes odds | Saves the most time for heavy players; powerful, so a good first pass | done, needs the pass wiring | P2 |
| **Weather Radar** | Shows the next 1-3 weather events and a countdown, optional alert "Volcano in 4 min" | Does not change which weather happens or its odds | Rewards planning; the hidden weather rhythm stays for free players | small UI + server read | P2 |
| **Weather Call** (server gift) | Triggers the weather event of your choice for the whole server, with a long cooldown and a limit per server | Never only for the buyer: everyone gets the boost, and the shop shows who called it ("Zed called Aurora!") | Social, generous, great with friends; "pay-to-share" instead of pay-to-win | medium (server rules + cooldowns) | P3 |
| **Nest Warmer** | Halves or skips the 3 h timer of one nest | Still one nest at a time; does not improve nest luck | Time sink relief; matches the nest vision | small | P2 |
| **Second Nest Slot (pass)** | Two nests open at once | Does not raise rewards per nest | Convenience for players with many nests | small | P3 |
| **More storage** | Nest slots 5 to 8, bigger dino storage | Never more luck | Capacity, safe | small | P3 |
| **Hatch Styles** | Cosmetic hatch animations: gold fireworks, galaxy burst, candy pop, using the new hatch sequence | No effect on odds or speed | Pure looks, high perceived value, safe for kids | medium art | P2 |
| **Mythic auras and trails** | The Mythic Glow set (the owner-picked style) as shop items | Cosmetic only | Direct use of the Mythic Glow art | art in progress | P2 |
| **Sanctuary skins** | Home and sanctuary themes (Volcano Camp, Aurora Meadow) | None | Looks | medium art | P3 |
| **Crystal packs** | Crystals (already planned, "Coming soon") spent on cosmetics, potions, upgrades | Crystals never buy dinos or odds | Standard soft currency | exists | P2 |
| **Potion bundle** | A small stack of speed, growth or loot potions | Capped (no stacking beyond the normal limit, convenience multiplier at most 1.25x, see [114](114-handbook.md) section 11a); a free potion arrives daily | Convenience with a cap, so keep it small | small | P3 |
| **Collector titles and name tags** | Titles shown near the name ("Fossil Finder") | None | Looks and pride | small | P3 |

## Do not sell
- A specific rare dino, a rarity or mutation boost, extra fusion success, or protection from failure.
- Anything that gives a combat or predation advantage (speed, size, shield) for Robux.
- Paid eggs with hidden or changed odds.

## Open questions for later
1. Which first product proves the model with the lowest risk? Recommendation: **Auto-open pass + Hatch Styles**.
2. Do we want a shared **Weather Call** at all? It is the most original idea and the most social, but needs balance work.
3. Prices and Robux packs depend on the platform's current rules; check them when this is scheduled.
