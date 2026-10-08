# Be Dino game design: intended experience

**Owner clarification (2026-10-08):** The final reward fantasy is **catch eggs while surviving**, then **hatch all of those caught eggs individually after the run**, with crystals and separate egg nests as bonuses. [Canonical target economy and numeric examples](09-reward-economy.md) take precedence over 2026-09-17 private-alpha direct-copy/chest math. Existing code remains the historical prototype until migrated. The three-species/one-Gold starter plan below describes initial scope, not the full desired catalog.

## Player journey
Lobby -> select dinosaur -> spawn protected -> collect food / eat smaller dinosaurs -> end run or be eaten -> summary and rewards -> collection / egg queue -> next run.
Death resets run size, not owned dinosaurs. Avoid gore: a pop, dust puff and short result card communicate defeat.

## Distinct quantities: player-facing contract
- **Raw food/growth score:** temporary points/size accumulated while playing, relevant to survival and growth; resets next run.
- **Catches = run eggs:** each earned catch adds one individual egg to the post-run hatching batch. The existing example conversion is 500 raw food points -> 15 catches -> **15 eggs**, not 15 automatic Compy copies.
- **Collection copies:** persistent dinosaurs actually granted by successful hatch outcomes or other explicitly defined sources; may include duplicates. Do not conflate this with the number of eggs earned.
- **Crystals:** a separate persistent currency from runs and map pickups; not a surrogate for egg count.
- **Bonus egg nests:** separate slot-based loot, not the ordinary run eggs. Five nest spots are the intended capacity, distinct from the current prototype's ordinary-egg queue.

Label each independently in the HUD, summary, data model and analytics. A five-minute run's score is not fixed by its duration.

## Arena and movement
One compact mostly flat prehistoric clearing with rocks, low plants and a safe lobby.
Third-person ground movement using desktop and touch inputs. No flight, underwater movement, climbing or complex combat.
Prototype one fixed gameplay collider with a growing visual model; explicitly test visual/contact mismatch. Tune capped bite range alongside visual growth.
Proposed visual scale curve: clamp((1 + score / 100)^0.25, 1, 4). This is a trial curve, not final balancing.
Keep speed differences small and cap them; a rare dinosaur should not automatically catch every starter.

## Eating and growth
Server validates food proximity, claims each pickup once and applies score.
Proposed PvP rule: attacker score must exceed target score by 10%; equal/near-equal dinosaurs cannot eat one another. This differs from a strict 'any smaller score' rule and requires owner review.
Use server-validated proximity and state, not visual mesh touches alone. Resolve competing claims deterministically; only one run-end event per victim.
Proposed spawn protection: 5 seconds; protected players can neither eat nor be eaten. Show a visible countdown.
Manual exit proposal: 3-second channel, canceled by movement; still vulnerable until complete. Death wins if processed first. This prevents an instant escape button eliminating chase tension.
Disconnect proposal: finalize last validated checkpoint rewards without a voluntary-exit bonus. Reconnection does not restore arena position/size. Crash recovery is limited to durable checkpoints.

## Collection and rarity
Proposed species: starter Compsognathus, Triceratops and Tyrannosaurus. All use the same movement controller and simple shared animation approach.
Species identity is visual first. Trial growth multipliers 1.00 / 1.05 / 1.10; speed initially equal.
Use three base tiers for three species initially; defer a full common-to-legendary catalog. More tiers with only three species would imply variety we do not have.
One Gold mutation tier. Proposed conversion consumes 50 base copies and grants one Gold copy. Decide whether the last equipped base copy is protected before implementation.
Keep species rarity and mutation separate data fields. Gold can add a small configured growth bonus with a total cap.

## Owner-confirmed reward vision (2026-10-08)

A player finishes or loses a run and banks **all caught run eggs** for individual hatching, plus separately earned crystals and bonus egg nests. The exciting reveal is the core feedback loop. Each egg can have its own rarity, species, condition, color/genetics and mutation; save outcomes once on the server. A Cracked egg can still fail to hatch.

- **Five-minute illustrative run:** 500 food score -> 15 catches -> **15 individual eggs** -> e.g. 11 Common / 4 Uncommon eggs; **1 bonus nest** and some crystals (30 is an illustrative amount, not approved balance). Show the 15 hatches one by one.
- **Longer illustrative run:** 5,000 food score -> 150 catches -> **150 individual eggs** -> e.g. 80 Common / 50 Uncommon / 17 Rare / 3 Epic eggs; **220 crystals** (example, not fixed formula) and **6 bonus nests offered**, of which at most **5** can be claimed with five free nest spots.
- The rarity compositions are *sample outcomes*, not predetermined quotas, published rarity weights or a guarantee that every egg hatches. Each earned egg is a reward attempt with one reveal, not a guaranteed direct-copy award **plus** another egg.
- The existing direct-copy table (`N(c)=c`) and old 10/100/500 catches -> 1/2/3 extra eggs are **historical implementation only**, not the intended payout. See [canonical intended + archived economy spec](09-reward-economy.md), [current hatching behavior](37-hatching-traits-and-leaderboards.md), and [tracking task BD-044](07-kanban.md).
- Favor an enticing rarity progression with scarce high tiers and persistent duplicates for fusion. Exact probabilities, species counts, crystal pacing and nests-per-run require tuning. Large 150-egg runs need reveal controls and efficient persistence/UI.

## Two distinct egg systems

**Run eggs:** one earned per catch, individual automatic post-run reveals, approximately five seconds each in the current prototype. They are the player's primary collection reward and should not consume the five *nest* slots by definition. Closing/rejoining must preserve unclaimed eggs and never reroll or duplicate awards.

**Bonus egg nests:** separately earned/unboxed rewards, with **five nest slots maximum**. In the six-nest example only five can be claimed when every slot is empty. Define explicit pending/overflow/expiry behavior for the sixth and for partly occupied nests. Never silently discard earned items. Nest contents and timers are unapproved; the old 60-second chest timer and current five-slot egg queue are not an approved final nest design.

## Proposed expanded egg/shop progression (2026-10-08)

The earlier three-species/no-paid-shop plan remains the **historical first private test scope**, not the desired long-term catalog. The new **Todo** direction includes crystals from the map and run-end rewards, optional Robux crystal packs, crystal-purchased random eggs in the existing hatch queue, level-gated priced speed trails, temporary potions and a progressively upgraded Condition Shop. Cracked/Dirty/Normal/Rainbow/Astra condition outcomes have requested base-stat factors 0.8/0.8/1.0/1.2/1.8, with Cracked additionally able to fail hatching. Exact probabilities and balancing remain open. Each egg has two rarity-weighted colour slots and a saved random blend, independent shiny status, and Normal/Big size; Big grows the dinosaur's appearance by 20% without intrinsic stat advantages.

These are the owner's progression **goals**, with multiple systems already implemented in the Build 020 prototype. The corrected caught-egg/nest reward loop is **not yet implemented** and requires BD-044. See [full expanded spec](36-crystal-shops-egg-genetics-and-progression.md), [current implementation record](44-main-integration-checklist.md) and [task board](07-kanban.md).

## UI
Lobby: Play, Collection, Eggs, Settings.
Run: score, reward progress, nearby relative-threat indicator, End Run, optional small session ranking.
Summary: why run ended, food/PvP contribution, **total earned run eggs/catches**, rarity reveal preview, crystals, separately earned nests and available nest slots, Play Again. No automatic Base Compy duplicate reward route.
Collection: owned/locked cards, rarity text plus color, stats, equip, duplicate count, mutation confirmation.
Eggs: sequential post-run hatch progression (including 150-egg batch UX), immutable outcomes, remaining count, nest inventory/slot capacity separately, failure/reconnect/overflow, empty and saving/error states.
A new player sees a one-line instruction: 'Eat food. Grow bigger. Watch out for larger dinos.'

## Fairness and pacing review
Test whether giant players trap new spawns; adjust spawn selection, protection and map sightlines before adding content.
Test 50-copy mutation time from actual rolls/hour; lower alpha threshold only through clearly isolated test config if demonstration would otherwise be impractical.
Prevent repeated victim farming from becoming the best reward source. Candidate mitigation: reduced repeat-pair rewards in a time window.
No retention, monetization or engagement target is treated as validated until observed.
