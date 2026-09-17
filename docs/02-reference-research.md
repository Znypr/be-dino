# Be Fish reference research
Observed 2026-09-17. Sources: official experience page, ten user screenshots, and Znypr's gameplay description.
This is a visual/gameplay teardown, not access to the game's source code or backend. No live session or video was played during this research.

## Identity
[Be Fish by Goofy Vegetables](https://www.roblox.com/games/94503612388426/Be-Fish) describes starting small, eating food, unlocking fish and avoiding other players.
Search results included unrelated games/videos; they were excluded. Exact loot tables, collision rules and save implementation cannot be inferred from the listing.

## Evidence ledger
Screenshot names below refer to the supplied files dated 2026-09-17. Raw screenshots are not copied into the public repository.

| File time | Direct observation | Design implication |
|---|---|---|
| 150349 | Lobby dock, Play portal, shop, Fishdex, Switch Fish, gems, leaderboard, Auto Farm | Lobby selection is distinct from the arena run |
| 150409 | Passes for luck, XP, double loot, food magnet and double growth | Several monetization multipliers compound progression; defer all for alpha |
| 150415 | Gem packs and Robux prices | Separate premium economy exists; unnecessary for our first test |
| 150421 | Five chest cards; text says each contains three fish rolled with +10000% luck; unlocked chests give permanent luck; 114 unlocked, 840.4% bonus displayed | Chests are an additional reward and permanent progression system |
| 150431 | Fishdex 125/300; Gold/Rainbow/Glowing/Shadow columns; collection milestone offers luck, growth and gems | Collection completeness itself increases power |
| 150447 | Luck, Growth, XP, Speed, Super Luck and Super XP boosts | Temporary buffs are another progression layer |
| 150456 | Like/group prompt offers rare fish and +50% luck | Acquisition incentive, not essential gameplay |
| 150521 | Arena with floor pickups, score 10,140, net 8, End Run, luck 1690%, XP multiplier 12.15 | Score and banked reward count are distinct variables |
| 150530 | Score 22,976, net 18, nearby much larger fish and pickups | Growth and reward accumulation coexist; no formula established |
| 150543 | Score 41,022 and top-down camera view | Large scale and camera distance affect readability |

## User-reported mechanics, not independently verified
- Smaller-score fish can be eaten; score grows from floor food and eating.
- Longer/more productive runs add fish to a net; manual ending or being eaten ends the run and yields loot.
- Higher reward counts can yield rarer fish; the examples of 10, 100 and 1000 are illustrative, not established thresholds or probabilities.
- Random treasure chests take about three hours each and stack sequentially, e.g. five take fifteen hours.
- Collecting 50 copies enables a mutation; species and mutations affect stats.

## Important ambiguities and corrections
1. Score is not loot count: 10,140 score with 8 net items is directly visible. Do not implement one score point = one dinosaur.
2. The screenshots label Gold and Rainbow Goldfish as Common. Thus a mutation changes displayed rarity odds, but a change to the named base rarity tier is not demonstrated.
3. Screenshots establish chest contents and permanent luck, but not a three-hour timer or queue behavior.
4. The user's description is unclear whether ordinary run fish are granted immediately plus bonus chests, or all loot is chest-gated. This must be clarified before claiming exact parity.
5. Equal-score interactions, predator reward transfer, exit delay, disconnect outcomes, offline queue progression and food respawn are unknown.
6. Nominal '1 in N' collection labels do not establish effective probabilities under luck boosts.
7. Two score/net observations do not establish causality or a conversion rate.

## Transferable design
Immediate loop: find food -> grow -> pursue/escape -> run ends.
Persistent loop: receive collection rewards -> unlock/equip -> accumulate duplicates -> mutate -> repeat.
Status loop: show size and rare appearance to other players.
The appeal likely combines visible growth, pursuit tension and collection anticipation. This is a design hypothesis to test, not an empirical finding.

## Critical assessment
Multiplying rarity power, collection boosts, luck and paid growth can snowball veteran advantage. A ground dinosaur game also introduces obstruction and leg-animation problems absent from swimming.
Be Dino should preserve visible growth and collection while limiting speed advantages, separating visual size from collision, and giving new spawns temporary protection.
Long timers can support return visits but prevent a short first test from exercising the loop. Test short timers first.
Exact recreation is neither required nor feasible from screenshots; use original prehistoric art, terminology and interface.

## Remaining research task
Ask Znypr for a short recording of start -> food -> eat/be eaten -> summary -> chest queue -> mutation.
Log displayed values and outcomes across a few runs. Use it to resolve questions, not to pretend small samples recover true loot odds.
