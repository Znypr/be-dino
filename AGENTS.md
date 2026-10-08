# AI / contributor instructions: Be Dino!

Read this file before interpreting reward requests, editing game-design documents, or changing game economy code. Source of truth for **owner's intended target**: [docs/09-reward-economy.md](docs/09-reward-economy.md), **2026-10-08 Owner-approved target**, and [docs/03-game-design.md](docs/03-game-design.md). [docs/07-kanban.md](docs/07-kanban.md) is the sole task/acceptance tracker.

## Game vision
Be Dino! is a Roblox dinosaur survival, growth, collection, and hatching game. In a run, a player collects food, grows, hunts/avoids predators, and eventually settles the run. The exciting payoff is watching **the eggs actually caught during that run** hatch **one at a time**, progressing from ordinary to exceptional discoveries. Runs also earn crystals and *separate bonus egg nests*. Duplicates, genetics, condition, event mutations, Shiny/BIG, collection, fusion, shops, and new playable dinosaurs give long-term progression.

The player-facing count of **catches** in the target reward loop means **the number of individual run eggs earned**, not a separate score that only unlocks 1-3 eggs or a guaranteed grant of one Base Compy per catch. Keep raw food/growth score, catch/egg count, hatched dinosaur copies, account XP, crystals, and bonus nest count distinct.

## Owner-approved examples, NOT final balance formulas

| Sample run | Food/growth points | Run eggs / catches | Example egg rarities | Run crystals | Bonus nests |
| --- | ---: | ---: | --- | ---: | ---: |
| Five-minute example | 500 | **15** | 11 Common, 4 Uncommon | **30 (illustrative; amount NOT owner-approved)** | **1** |
| Longer, more successful run | 5,000 | **150** | 80 Common, 50 Uncommon, 17 Rare, 3 Epic | **220 (owner's example, NOT a final formula)** | **6 earned/offered; max 5 claimable into five free nest spots** |

The current test conversion `FoodCatchRate = 15/500` happens to fit both egg-count examples. Do **not** confuse `5,000 food points` with the old `MaxCatchScore = 5000`: they are distinct quantities. Five minutes does not automatically imply 500 food points. Neither rarity distribution is a committed probability table; drops should generally be common-heavy, with longer/better runs exposing more rare tiers.

- **Every earned run catch corresponds to one run egg**, stored/settled server-side. Reveal the **15 or 150 eggs sequentially**, one at a time, approximately five seconds each at the current prototype speed, preferably in increasing species rarity within a batch. Do not invent additional separate immediate eggs from the old 10/100/500 catch thresholds.
- Do **not** grant direct guaranteed Base Compy copies *on top of* those eggs. A run egg can yield a random species/condition/traits when revealed; current code can also give 1-3 copies per successful egg and Cracked eggs can fail. That separate **per-egg quantity/hatch contract is a provisional prototype mechanic**, not owner confirmation that every egg must yield exactly one copy, nor permission to double-credit direct rewards.
- **Crystals** are another end-of-run reward, with map pickups as an additional source. Do not treat the example 30/220 values as an approved curve or assume the same crystal box mechanics must remain.
- **Bonus egg nests are separate from ordinary run eggs.** Nests occupy **up to five nest slots**. The long-run example offers six nests, so at most five can be claimed when all slots are empty. Show the sixth as capacity-blocked/pending rather than silently losing or covertly granting it; the final excess/expiry/claim UX is an unresolved design decision. Do not confuse this five-slot nest capacity with the currently coded five-slot ordinary egg queue.
- Score-to-egg conversion, crystal formula, exact rarity odds, per-egg 1-3 quantity, nest contents/timing, overflow, caps, and storage/UI performance for 150-egg batches all require balancing/implementation/verification. Do not report them as shipped.

## Latest owner-requested work (2026-10-08)

The [single canonical Kanban](docs/07-kanban.md) now includes **BD-045–056**, researched and categorized in [the detailed follow-up specification](docs/45-owner-feedback-shop-hud-world-weather-tasks.md). Future AI agents must read these before editing condition rates, Crystal Shop menus, rotating Potion Shop offers, Home exit flow, terrain movement, touch zones, HUD or weather.

**New owner-target default condition weights**: Cracked 50%, Dirty 30%, Normal 15%, Rainbow 4.5%, Astra 0.5%. These **are not** the current Build 020 config. Preserve Cracked's separate 20% hatch success, note the implied 40% average failed eggs at tier 0, and rebuild upgrade curves/disclosure/versioning before implementation. Six trail **rarity categories** is a proposed interpretation; keep existing ten trail products until confirmed. All added visual art and Blender models remain TODO until actual owner uploads and runtime tests; do not invent asset IDs.

## How to answer and implement

1. **For "what would a 5-minute / 500-food run reward?"** use the 15-egg example above. Mark any invented value as an illustrative assumption. Never answer "15 guaranteed Compies + 1 egg + 1 nest".
2. Explicitly label **OWNER TARGET**, **CURRENT BUILD BEHAVIOR**, or **HISTORICAL TEST SPEC**. The older `N(c)=c` direct-copy allocation and 1/2/3 egg threshold appear in code and tests but are **not the owner's desired game loop**.
3. Prioritize the newer owner's explicit direction over older alpha docs, test fixtures, generated summaries, or implementation defaults. Do not rewrite history: preserve legacy specs as historical, update conflicting high-visibility references, and keep one canonical task board.
4. If asked to implement, plan a safe, server-authoritative migration: egg ownership/settlement exactly once, immutable outcome RNG, existing saves/queues, Cracked failure, five-second reveals, trait versioning, duplicate species stacks, UI scalability and reconnect/overflow behavior. Validate with tests and Studio evidence. **Never rewrite persistent profiles, enable Robux packs, or claim Studio/phone acceptance without evidence.**
5. If asked for concrete examples, show actual counts whose rarity totals sum to the egg count and identify any open economic assumptions. Ask for specific unresolved balancing decisions only if necessary for implementation; examples do not require clarification.
