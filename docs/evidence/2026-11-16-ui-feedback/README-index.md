# 2026-11-16 Dino Index milestone rewards (BD-1230)

Studio 2026-11-16, own built playtest place, Play mode. Flag `IndexMilestonesEnabled` on (playtest profile); the default build is unchanged.

| Picture | What it shows | How it was made |
| --- | --- | --- |
| `index-bar-next-reward.jpg` | the Index bar "Found 1/22 • 5 more: +50" and the locked "?" silhouettes (silhouettes existed before, BD-1194) | real new save after the starter run, opened with the Studio screen tour; nothing staged |
| `index-milestone-toast.jpg` | the toast "Dino Index 25%!" / "+50 Crystals" | the owner-only value IndexMilestonesJson was staged as display data only (a message to this client); no crystals were granted and the stored profile was not touched |

The grant itself (crystals added once inside the hatch transaction) is proven offline: `tools/verify_index_milestones.py` (rules, exactly once, wallet cap, additive field, 10 mutants), `verify_profile_golden`, `verify_rollback`, `verify_private_state`, and the all-flags-on rehearsal. Not seen in Studio with a real 6-species save; no phone check.
