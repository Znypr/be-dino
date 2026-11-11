# 225 Starter run: the first 3 minutes of a brand-new player (BD-1163 spec)

Label: **OWNER TARGET (decision 2026-11-10, docs/115) + LEAD spec**, 2026-11-11. Numbers are PROVISIONAL. Builds on the first-time audit ([112](112-first-time-player-audit.md)) and its fixes (BD-365 safe first eggs, BD-440 hidden goals), the research ([221](221-po-plan-team-and-research-2026-11-10.md) C2) and the watch sheet ([222](222-playtest-watch-sheet.md)).

## 1. Why

Roblox counts a player who leaves within 60 s or 180 s as a bounce, and that hurts Home ranking. Today a bot needs about 4 minutes to find its first egg and longer to see a hatch (docs/112). The payoff of Be Dino is the hatch, so a new player must see one inside about 3 minutes.

## 2. The owner decision

Only the **first run of a brand-new profile** is short and generous: guided food nearby, it ends at about 2 to 3 minutes, a few guaranteed eggs, first hatch within about 3 minutes of joining. From run 2 the normal economy applies.

## 3. Player journey (target times from joining)

| Time | What the child sees | Rule |
| --- | --- | --- |
| 0:00-0:10 | Spawns in the run, no lecture modal. One soft arrow points at a glowing food trail. | Starter run starts by itself for a new profile (no EXPLORE press needed). The welcome cards move to Settings > HOW TO PLAY. |
| 0:10-1:30 | Eats along the trail; each egg-food on it gives a visible "Egg!" pop. | The trail is a short path of food placed near spawn, only for this player (client-visible, server-validated pickups like all food). Enough egg-value food for `StarterRunEggs` eggs. |
| ~1:30 | When `StarterRunEggs` eggs are caught: a big happy card "You found 3 eggs! Take them home!" with ONE button. | The button ends the run directly (no "Return to Sanctuary?" confirm on the starter run). |
| ~1:45 | Run Complete, then straight into the hatch. | OPEN EGGS is the only big button on the starter run. |
| ~2:00-2:30 | Three eggs hatch, rising rarity, none Cracked. | `SafeEggs` 2 -> 3 so every starter egg hatches. |
| after | "Run again to find new dinos!" and the Index silhouettes. | Normal economy from run 2. Goals panel appears (BD-440 rule). |

If the child ignores the trail, nothing breaks: the run is a normal run, and the starter card still appears when `StarterRunEggs` eggs are reached. If they die, the run settles normally and the eggs they caught still count (the floor below applies).

## 4. Rules (server-authoritative)

- **Who:** a profile with zero settled runs (derived from existing data; no new stored field if a run counter already exists, otherwise one additive field, checked by the profile golden and rollback gates).
- **Egg floor:** the starter run settles at least `StarterRunMinEggs` (3, PROVISIONAL) eggs if the player reached the starter card or caught at least one egg; settlement stays exactly once.
- **Never twice:** a second join with the run unfinished does not restart the starter run unless no run was ever settled.
- **Flag:** `StarterRunEnabled`, false in Config and default profile, true in the playtest profile (docs/157), in the rehearsal list.
- **Telemetry:** BD-1166 already records first bite, first run end, first hatch and bounce; add `starter=true` on the first `run_end` so the report can compare.
- **Copy** (docs/72): "Follow the shiny food!", "You found 3 eggs!", "Take them home!", "Run again to find new dinos!". No numbers with units, no jargon.
- **Art:** the trail glow uses an existing effect or a registered texture; no code-drawn final art (art rule). If none fits, ship with plain food and a kanban row for the effect.

## 5. Tests

Pure rule tests (who gets it, floor, never twice, flag off = old behaviour), a settlement test with the floor (exactly once, retry, reconnect), a bot run in Studio measuring join-to-first-hatch (target under 3:00), then the watch sheet with real children. Not done until a person has played it (owner testing).

## 6. Open

- The trail's exact food values and length are tuned in Studio with the smart bot (docs/194).
- Whether the starter card should also appear for players returning after a long break: no, not now.
