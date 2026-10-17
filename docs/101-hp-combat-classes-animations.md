# 101 HP, combat, dino classes and movement animations (design, 2026-10-16)

**Status: Phase 1 (pure rules), Phase 2 server (BD-243/244) and the Phase 4 placeholder UI (BD-247) are implemented behind `Config.CombatEnabled=false` (2026-10-16, see the Kanban rows for what is tested and what is not). All numbers are PROVISIONAL, not final balance.** Owner direction 2026-10-16 (kanban BD-230, BD-231, BD-233, BD-234). Feel rules: [docs/87](87-vision-and-feel-guide.md). Copy rules: [docs/72](72-ui-copy-and-asset-standards.md). Defeat animations per skin: [docs/97](97-dino-skins.md). Reward loop: [AGENTS.md](../AGENTS.md) and [docs/09](09-reward-economy.md). Tasks live only in [the Kanban](07-kanban.md) (BD-239 to BD-252 added by this doc).

Labels: **OWNER TARGET** = from the owner. **PROPOSAL** = this doc, needs owner review. **CURRENT BUILD** = what ships now (instant "bigger eats smaller", [docs/03](03-game-design.md): the attacker needs about 10% more score and the victim is eaten).

## 1. Goals (OWNER TARGET)
1. Every dino has HP and a visible health bar.
2. Fights are about attacking. Bigger = more HP and harder hits, but never an instant kill, so several small dinos can team up on a big one.
3. Classes: GROUND (baseline), FLY, WATER, ARMORED.
4. Idle and walk animations (chicken/dino mix), jump and leap animations for every class.
5. Calm, bubbly, no gore, gentle defeat. Reward safety first: **run eggs and score are never lost or duplicated.**

## 2. Classes and PROVISIONAL stat table
Multipliers apply to a shared baseline (GROUND = 1.0). `s` is the existing growth/size scale (clamp 1 to 4, docs/03).

| Class | Species (roster, BD-232) | HP x | Speed x | Jump | Damage taken x | Damage dealt x | Special |
|---|---|---:|---:|---|---:|---:|---|
| GROUND | Compy, Raptor, Triceratops, Stegosaurus, T-Rex, Brachiosaurus, Parasaurolophus, Gallimimus ... | 1.00 | 1.00 | normal | 1.00 | 1.00 | Baseline. Leap = forward lunge bite. |
| FLY | Pteranodon, Quetzalcoatlus, Dimorphodon, Archaeopteryx, Microraptor | 0.75 | 1.20 | faster, higher; glide on hold | 1.00 | 1.32 | Wings folded when walking. Leap = swoop dive. |
| WATER | Plesiosaurus, Mosasaurus, Ichthyosaurus, Liopleurodon (Elasmosaurus is a normal Ground dino, owner 2026-10-16) | 1.25 | 0.85 | **none** | 1.00 | 0.80 | Stays low to the ground. Jump button = forward dash. Leap = aggressive dash. |
| ARMORED | Ankylosaurus, Sauropelta, Styracosaurus (more later, owner decides) | 1.10 | 0.80 | short hop | **0.80** | 0.73 | Tank. Gentle tail-club/horn bump. |

Speeds stay inside the "small speed differences" rule of docs/03. The class is shown as a small badge on the HUD and species card (BD-231). Class is per species in config (`Species.class`), never per skin (skins are cosmetic only, docs/97).

## 3. Core formulas (PROVISIONAL)
All values live in `Config.Combat`; the server reads them, the client only displays.
- `s = clamp((1 + score/100)^0.25, 1, 4)` (existing growth curve).
- `maxHP = 100 * classHp * s^1.3` (s=1: 100; s=4: about 610 for GROUND).
- `damage = 6 * classDmg * s^0.2 * (1 + 0.05 * attackTier)` per hit (s=1: 6; s=4: about 7.9; tuned in section 17). `attackTier` is 0 for now, an extension hook.
- Feel check: one small hit is about 1.3% of a big GROUND dino's HP; 6 small dinos at 1 hit per second defeat it in about 13 s; the big dino defeats a lone small one in about 5 hits. Teaming up wins, going alone loses. Confirmed by simulation in BD-241.
- Armor: `final = max(damage * damageTakenX, 1)` (every hit counts at least 1).
- Optional size damper: if attacker `s` is under half the target `s`, damage x0.9. Tune in simulation.
- Growth keeps the HP **ratio** (50% HP stays 50%), so eating never fully heals and never kills.

## 4. Attack input and cooldown (PROPOSAL)
- One big **Bite** button (bottom-right thumb zone on touch; E or left click on desktop). Tap to attack; no aiming or holding.
- The server auto-targets the nearest valid enemy in a front cone (range `2.5 + 1.0*s` studs, 70 degrees). A soft ring marks the target so the child sees who is hit.
- Cooldown **0.9 s**, shown as a filling ring on the button (no number). Server enforces; the client only predicts the animation.
- **Leap**: forward lunge, 3 s cooldown, bites for 1.6x plus a small push if it lands. WATER: the jump button is the dash (forward boost, no hit); the leap is the same dash but longer with a bite snap (1.5x damage, bigger splash). One remote with a `kind` field.
- Knockback is a short soft push (about 4 studs, less for big targets), clamped to safe ground by the server, never off the map.
- Regen: after 6 s without hitting or being hit, HP refills 4% of max per second. A food pickup heals 5% of max, so eating stays a reward.

## 5. Team-up rules (PROPOSAL)
- No party system. Anyone hitting the same target counts; damage simply sums.
- **Assist credit:** everyone who dealt at least 10% of the victim's max HP in the last 15 s shares a small bonus by damage share (last hit does not matter, so no kill-steal).
- **No egg theft:** the victim's run eggs are never given to attackers (section 6). The bonus is a separate server-minted food-score amount, capped at `0.25 * victimScore`, split among assisters, settled once.
- Repeat pair limit: the same attacker/victim pair within 3 min gives 50% bonus, then 0 (anti-farm, docs/03 candidate).
- Crowd soft cap: if 5 or more enemies hit a target within 2 s, damage taken x0.9 so swarms do not feel cheap. Tune in simulation.

## 6. Defeat, respawn and what is lost (PROPOSAL; reward safety is mandatory)
Run eggs and score are earned server-side and settled **exactly once** (AGENTS.md, docs/03). Combat adds no second path to lose or double-grant them.
1. At `hp <= 0` the server marks the run `Defeated` once (idempotent machine `Alive -> Defeated -> Settled`). Later bites are ignored.
2. A defeat **ends the run like today's "eaten" ending**, running the same settlement once for that `runId` ("death wins if processed first", docs/03). **The player keeps all run eggs caught, crystals and bonus nests earned so far.** Lost: the run position and size, and the chance to keep growing (and the voluntary-exit bonus, if the owner wants that; open question 4). Owned dinosaurs, eggs and crystals are never touched.
3. Eggs and score are **never transferred** to attackers. Attackers only get the capped separate bonus above, minted by the server, not taken from the victim's ledger. So there is no duplication path and no loss path.
4. Settlement is keyed by `runId`, so a disconnect during defeat, two bites in one frame, or a simultaneous self-exit still settle once.
5. Presentation (gentle, per skin, docs/97): dizzy stars, soft flop and poof for Base; bricks scatter, clay squish, plush deflate. About 1.5 s, quiet cue, Reduce Motion = a simple fade. Copy: "Oops! Good try!" then the normal result card. No red flashes, no blood, no skull.
6. Respawn goes via the lobby and the normal result/hatch flow. The next run starts at full HP with **5 s spawn protection** (soft bubble; protected dinos cannot attack or be hit).
7. Revive is **not in v1** (open question 3).

## 7. Anti-grief (PROPOSAL)
- Spawn protection 5 s (ends early if the player attacks). Lobby/spawn area is a no-combat safe zone.
- Repeat-pair bonus limit (section 5) plus a short "friend shield" after the same victim was defeated 3 times in 3 min, so nobody is chased repeatedly.
- Bonus split by damage share, so there is no kill-steal incentive.
- Server validation: per-player attack rate limit, range and angle check, reject teleport or distance spikes, rate-limited remote like existing remotes.
- ~~If the owner picks optional PvP: a "Peaceful" choice at run start disables hits to and from that player (it also cannot attack). Open question 1.~~ SUPERSEDED 2026-10-16 (owner correction, docs/115 and docs/128): there is NO Peaceful opt-out; hunting stays on for everyone.
- Reporting/blocking is Roblox's own tooling and out of scope.

## 8. AI predators use the same HP (PROPOSAL)
- Predators take `maxHP`, class, damage and cooldown from the same `CombatStats` module as players.
- A predator bite does normal damage, never an instant kill, and has a 0.5 s lean wind-up with a soft sound so children can dodge.
- Predators can be team-attacked too; defeating one gives the capped bonus and no eggs; they respawn after about 30 s away from players.
- Spawn protection and the safe zone apply to NPC targeting.

## 9. Interaction with growth, size and the reward loop
- **Food and growth unchanged:** raw food score still maps to size, catches and eggs per [docs/09](09-reward-economy.md) and AGENTS.md (500 food -> 40 eggs, and so on). Combat adds no egg source and removes none.
- The "attacker needs 10% more score" instant-eat rule is **replaced** by HP fights. Size still matters (more HP, more damage) but the biggest dino can be worn down. This supersedes the instant-kill-by-size rule of docs/03; docs/03 gets a pointer when BD-230 ships (docs-only now).
- Distinct quantities stay distinct: HP, food score, catches/eggs, crystals, bonus nests, account XP. HP is run-local and never persisted.
- The colour growth bonus (docs/94) raises score and so HP through `s`; it adds no direct HP.
- Skins and auras stay cosmetic; they never change HP or damage (docs/97).
- Fusion tiers (docs/46) could later add a small permanent stat step. That is a separate owner decision, not applied here; `attackTier` is the hook.

## 10. Health bar UI mock (docs/72 rules)
A soft pill-shaped bar floats above each dino, and a bigger one sits on the player's HUD.
- Look: chunky outline, rounded ends, no text on world bars. Fill green above 50%, yellow 25 to 50%, soft orange below 25%, and a heart icon that goes full, half, small so it never relies on colour alone.
- World bar: scales slightly with size, at least 60 px wide on phones. Own HUD: heart on the left, bar under the food/score line. Enemy bars show only within 40 studs or after being hit.
- Feedback: the bar drains with a 0.3 s ease and a bubble wobble; the dino squashes a little. Heal: soft sparkle. No screen shake, no red vignette. Reduce Motion: bar just updates.
- Damage numbers: **off by default** (open question 2).
- Copy: "Bite" button, ~~"Peaceful" toggle~~ (removed 2026-10-16), "Oops! Good try!". No "HP", no percent text; heart and bar are the whole message.
- Class badge (leaf, wing, wave, shield) sits beside the bar. Art (heart, badges, bite button, bubble) is a Blender/ChatGPT task with a docs/77 line; no code-drawn final art (BD-248).

## 11. Movement animations (OWNER TARGET; detail for BD-233 and BD-234)
Client-side only, driven from the low-poly part rig (body, head, tail, legs, wings; BD-225). The server stays authoritative for position and combat. Reduce Motion shrinks amplitudes.

| State | GROUND | FLY | WATER | ARMORED |
|---|---|---|---|---|
| Idle | breathing, slow head tilt, tail sway, blink, foot shuffle | same, wings folded, tiny wing shuffle | floating bob, slow tail swish | slow heavy breathing, head dip |
| Walk | chicken/dino mix: quick bobbing waddle, forward head-peck rhythm, alternating legs, tail counter-swing, speed-scaled | same, **wings folded close to the body** like a walking bird | low heavy waddle/slither near the ground | slow stomp, tiny body bounce |
| Jump | crouch, push-off, airborne pose, landing squash | higher and quicker, wings spread, flutter landing | **no jump**; button = forward dash with streak, tail kick, small splash | short hop, heavy landing puff |
| Leap | forward lunge, bite snap, landing squash | swoop dive, wing tuck | aggressive dash, bigger lunge and splash, bite snap | shoulder-bump lunge, tail-club bump |

**CURRENT BUILD BEHAVIOR (BD-555, BD-556, 2026-10-17):** the Humanoid reports Jumping only after the dino has left the ground, so the animator no longer plays the crouch and the push-off for a jump or leap: it eases from the current pose straight into the air tuck over `Pose.DirectBlend` (0.4 s) and lands from the weight it reached (a short hop squashes less). No part turns 8 degrees or more in one frame on take-off. The crouch and push-off maths stay in `LowPolyPose` (tested) for a later input-triggered anticipation. Water flipper tips are held at their rest height (`Pose.restLift`). Studio frame log: see the BD-555 row.

Species flavour (Brachiosaurus neck sway, T-Rex arm twitch) is data, not new code. Skins keep their own style (docs/97). The chicken/dino walk is the one shared language for every class.

## 12. Class movement rules and map access (BD-231, BD-246)
- FLY: hover height capped (about 6 studs, only during jump/glide), no sustained flight, server clamps Y, cannot leave the map or reach unreachable spots, normal pickup range for food.
- WATER: ground-bound, no `Jump`; water zones give a small flavour speed bonus (+10%); can still pick up food and settle everywhere.
- ARMORED: normal terrain, slower; knockback halved.
- A check in `tools/verify_classes.py` proves every class can reach food and the settle point in every map region.

## 13. Network and performance budget (12 players, phones)
- Combat tick on the server at 10 Hz; at most 2 attack requests per second per player; payload under 40 bytes (target id, kind, sequence).
- HP is sent as **deltas** at 5 Hz, quantised to 1 byte (0 to 255 of max); full snapshot on join. Target: under 1.5 KB/s per client from combat with 12 players and 8 NPCs.
- Health bars are pooled client billboards: at most 12 visible, hidden beyond 60 studs, plain Frames, no per-frame allocation.
- Hit/defeat VFX use the shared pool and docs/87 budgets (up to 20 particles per hit, 40 per defeat, none under Reduce Motion).
- Animation: procedural offsets on a small part set, 30 Hz on phones and 60 Hz on desktop, skipped beyond 80 studs. No keyframe asset loads.
- Knockback is a server position nudge, not physics impulses; no new unanchored parts.
- Must be measured on a real phone and in a 12-player test before being called done. Never claim acceptance without evidence.

## 14. Phased implementation plan (kanban BD-239 to BD-252)
Pure Luau modules in `src/shared`, each with a `tools/verify_*.py` test (same pattern as `tools/verify_colour_bonus.py`). Server first, UI last, everything behind `CombatEnabled=false`.

Phase 1, pure rules (no gameplay change)
- BD-239 `CombatStats`: class table, maxHP, damage, armor. `tools/verify_combat_stats.py`: tables, clamps, monotonic with size, class multipliers.
- BD-240 `CombatState`: HP, damage, idempotent defeat machine. `tools/verify_combat_state.py`: double hit, simultaneous defeat, overkill.
- BD-241 Team-up module: damage ledger, assist split, repeat-pair limiter, crowd cap. `tools/verify_combat_teamup.py`: split sums exactly, simulation (6 small beat 1 big, 1 small loses).
- BD-242 Settlement safety: `tools/verify_combat_settlement.py`: eggs before = eggs settled, once per runId, no egg credit to attackers.

Phase 2, server
- BD-243 `CombatService`: rate-limited attack remote, cone/range check, cooldown, knockback clamp, regen, spawn protection; Studio test with 2 dummies.
- BD-244 Defeat -> run-end through the single settlement path; disconnect and race cases.
- BD-245 AI predators on `CombatStats`, wind-up, respawn.

Phase 3, classes: BD-246 class data per species, speed/jump multipliers, FLY cap, WATER dash; `tools/verify_classes.py`.

Phase 4, UI and feel: BD-247 health bar and Bite button (art PLACEHOLDER until BD-248); BD-248 UI art; BD-249 per-skin defeat hook and sound brief.

Phase 5, animations: BD-250 idle/walk driver (pure pose function, `tools/verify_motion_poses.py`: bounded offsets, speed scaling, reduced motion); BD-251 jump/leap/dash per class.

Phase 6: BD-252 12-player phone test and balancing pass; owner playtest; `CombatEnabled` stays off until it passes.

Dependencies: 239 -> 240 -> 241/242 -> 243 -> 244/245; 246 after 239; 247 after 243 (art 248 in parallel) -> 249; 250/251 after BD-225 rigs; 252 last.

## 15. Open questions for the owner
1. **PvP always on, or optional?** ANSWERED 2026-10-16: always on for everyone, each player chooses whether to hunt; no Peaceful toggle or servers; food alone must be enough progression (docs/115, 128). ~~PROPOSAL: Peaceful option for young players.~~
2. **Damage numbers shown or not?** PROPOSAL: not shown, hearts and bars only.
3. **Revive?** (A teammate helps a defeated dino up within a few seconds.) Not in v1; wanted later?
4. On defeat, keep **everything earned so far** (PROPOSAL, safest) or lose a bonus such as the voluntary-exit bonus? Eggs and score are never lost either way.
5. Is ARMORED a fourth class shown to players, and which extra species join it (Triceratops, Stegosaurus)?
6. Should attackers get a small food/crystal bonus on a defeat, or nothing?

## 16. Lead decisions on the open questions (2026-10-16, made on the owner's behalf; owner may overrule)
1. **PvP:** on in the arena, ~~with a Peaceful option at run start for young players~~ (SUPERSEDED 2026-10-16: no Peaceful; hunting stays on for everyone, docs/115).
2. **Damage numbers:** not shown. Hearts and bars only (docs/72, docs/87).
3. **Revive:** not in v1. Revisit after the 12-player phone test.
4. **On defeat:** keep everything earned so far (eggs, score, crystals, nests); no punishment bonus loss. Gentle failure beats any penalty for this audience.
5. **Armored:** a fourth class shown to players. Members for now: Ankylosaurus, Sauropelta, Styracosaurus only. Triceratops and Stegosaurus stay Ground until balance tests justify moving them.
6. **Attacker reward:** only the capped assist bonus already in section 6; no extra food/crystal bonus per defeat (avoids farming small players).

## 17. Balance tuning results (2026-10-16, BD-252 offline part; PROVISIONAL, offline simulation only)
Numbers changed in `CombatConfig` only (flag still OFF, nothing reads it). Sim = `tools/combat_harness.py` `fight()` (0.1 s steps, 0.9 s cooldown, each fighter hits the first living enemy, crowd cap on). Regenerate with `python tools/combat_balance.py --runner <luau>`. Sim assumptions: no regen, no dodge, no knockback, speed ignored, perfect hit rate, so real fights will be longer/messier. Scales: s2 = score 1500, s3 = 8000, s4 = 25500.

**Constants (before -> after):** BaseDamage 8 -> 6, DamageSizeExponent 0.75 -> 0.2 (a big bites only about 1.3x harder than a small; its edge is HP), SizeDamperX 0.8 -> 0.9, CrowdDamageX 0.85 -> 0.9, HpSizeExponent 1.3 (unchanged). Classes (HP x / taken x / dealt x / speed x): Fly 0.70/1.0/0.90/1.20 -> 0.75/1.0/1.32/1.20; Water 1.40/1.0/1.0/0.85 -> 1.25/1.0/0.80/0.85; Armored 1.50/0.70/0.90/0.80 -> 1.10/0.80/0.73/0.80; Ground unchanged.

**Team-up targets (Ground, then other classes):**
| Scenario | Before | After |
|---|---|---|
| 1 small (s1) vs s4 | big wins, 5 hits, 4.1 s | big wins, 13 hits, 12.1 s (>= 3 s, no one-shot) |
| 3 small vs s2 / s3 | win / lose | win (13 s, 3 left) / win (36 s, 1 left) |
| 3 small vs s4 | lose | lose (38 s) |
| 6 small vs s2 / s3 | win / win | win 7.5 s, 6 left / win 14 s, 5 left |
| 6 small vs s4 | win, 29 s, 1 survivor | win, 22.4 s, **5 survivors** |

Other classes (smalls and big of the same class, 6 vs s4): Fly 12.5 s, 5 left; Water 34.7 s, 5 left; Armored 42.2 s, 5 left (a bit over the 35 s target; armored fights are slow by design). 3 small lose to s4 in every class and a lone small loses in every class (first defeat at 7 s Fly, 12 s Ground, 19 s Water, 23 s Armored). Ground x6 vs a big of each class (s4): Fly 16.6 s, Ground 22.4 s, Water 27.7 s, Armored 30.5 s, always 5 survivors.

**Class matrix (1v1, equal size).** Cell = hits row needs to defeat column / hits column needs. Fewer hits wins; within 1 hit is a draw (first strike decides).
| s=1 | Ground | Fly | Water | Armored |
|---|---|---|---|---|
| Ground | = | D 13/13 | D 21/21 | D 23/23 |
| Fly | D 13/13 | = | D 16/16 | D 18/18 |
| Water | D 21/21 | D 16/16 | = | D 29/29 |
| Armored | D 23/23 | D 18/18 | D 29/29 | = |

At s=2 and s=4 the same ladder holds within 1 hit (for example s=4 Armored beats Ground 105/106 and Fly 79/80, Ground beats Fly 58/59, Water draws); Armored never beats everyone. Effective HP vs a Ground hit: Armored 137, Water 125, Ground 100, Fly 75; damage per hit at s1: Fly 7.9, Ground 6.0, Water 4.8, Armored 4.4; speed Fly 1.2 > Ground 1.0 > Water 0.85 > Armored 0.8.

**Honest note on rock-paper-scissors:** class stats are pure multipliers, so a 1v1 at equal size is a total order of `hpX * dealtX / takenX`; true cycles are impossible without a counter mechanic. We set that product to about 1.00 for every class (Fly 0.99, Ground 1.00, Water 1.00, Armored 1.00), so 1v1 is a near-draw and class identity comes from speed, jump, map access (section 12) and team role. A real counter (for example Fly dodge vs Ground, Water slow vs Fly) is a code change and left as a proposal for the owner. Equal-size duels at high size are long (s4 vs s4 Ground about 57 s in the sim): fine for kids, but real play has regen and dodging, so re-check in the phone test.

**Regression tests:** `tools/verify_combat_stats.py` (class roles, near parity, no strict dominance, no one-shot: a max hit is at most 15% of a small target) and `tools/verify_combat_teamup.py` (all four classes: lone small loses after >= 3 s, 6 small beat s4 with >= 3 survivors in 20-35 s for Ground, 3 small lose to s4 and beat s2/s3).

## 18. NPC predators (BD-245, 2026-10-16; PROVISIONAL, offline-verified only)
Flag: `Config.CombatEnabled` (false) and `Config.NpcPredatorsEnabled`. Pure rules: `src/shared/NpcPredatorRules.luau`; glue: `src/server/NpcPredatorService.luau`; test: `tools/verify_npc_predators.py`.
- **Same rules as players.** Each NPC joins the shared `CombatRules` world (class from the species registry, HP/damage from `CombatStats`, score 60 to 250 so s is about 1.1 to 1.3). Its bite is a normal `CombatRules.attack`, so range, cone, spawn protection and Peaceful are checked twice. Never one-shot: one bite takes at most 20% of any player's max HP (tested over all classes and sizes).
- **Calm behaviour.** Patrol slowly near home (5 studs/s). A player inside 26 studs gets an alert pause (0.8 s, "!" over its bar), then a chase at 11 studs/s (players walk 22), a 0.5 s windup without re-aiming (moving away dodges), then a bite. At most 2 bites per aggro, 2.5 s soft cooldown, 4 s grace on a bitten player (no NPC may target them), then it gives up and ignores that player for 15 s. It also gives up beyond 42 studs, after 7 s, or past a 70-stud leash.
- **Never targets:** spawn-protected, dead, not in a run, anyone inside the start meadow (80 studs around 0,30), a just-bitten player.
- **Defeat.** A defeated player goes through the existing exactly-once `tryEnd` path and keeps eggs, score, crystals and nests. Teams can defeat an NPC: capped assist growth only (25% of the NPC score, repeat-pair limiter applies), no eggs. It respawns after 30 s (+ up to 6 s) at a point at least 90 studs from every player.
- **Budget.** Hard cap 6 NPCs (2 for 1 to 3 players, +1 per 3 players, 5 at 12); an NPC with no player within 160 studs does nothing; movement is server Humanoid physics replicated by Roblox, not custom remotes; HP uses the existing 1-byte attribute at 5 Hz; at most 30 NPC steps per second.
- **Visuals.** Existing species model through `DinosaurVisual.render` (raptor, baryonyx, tyrannosaurus, spinosaurus), tinted darker; purple "wild" bar in `CombatHud`. No new art.
- **Open / unverified:** Studio behaviour (tint on textured meshes, movement around trees and water), phone and 12-player cost, walk animation, a lean pose, a dedicated windup sound.

