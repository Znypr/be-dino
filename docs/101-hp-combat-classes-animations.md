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

**CURRENT BUILD BEHAVIOR (BD-556 surge, 2026-10-17, Studio look pending):** the Water SURGE is a swim burst: a left-right body wave runs from the head to the tail (each part follows the one in front by a phase lag, `Pose.SurgeWaveLag`; tail 26 degrees, head 14, body 5) and the four flippers row in a stroke (front pair first, back pair a beat later). One undulation over a jump surge (0.40 s), 1.4 over a leap surge (0.55 s); no part turns 8 degrees or more in a 60 Hz frame; Reduce Motion keeps everything at rest. After a hard landing the local dino lifts the whole visual by the humanoid's hip compression for 0.3 s (`Pose.hipDip`, at most 0.7 stud, a ray 4 times a second while settled, one a frame while falling and for 0.3 s after touch-down, none while rising, none under Reduce Motion; measured hip dip 0.5 stud for one frame, the touch-down frame itself is not covered), so the feet stay on the ground while the squash plays. `ClassDash` (server, flag `ClassMovementEnabled`) accepts a grounded Water dino on any ground, land or water: 48 studs/s for 0.35 s, 3 s cooldown, applied once by the client. The class table's Water `leap` dash is not used by any code: the Water E leap is the ordinary leap (BD-569, a design call).

Species flavour (Brachiosaurus neck sway, T-Rex arm twitch) is data, not new code. Skins keep their own style (docs/97). The chicken/dino walk is the one shared language for every class.

## 12. Class movement rules and map access (BD-231, BD-246)
- FLY: hover height capped (about 6.5 studs of feet height, only during jump/glide; FH2, s20.6), no sustained flight, server clamps Y, cannot leave the map or reach unreachable spots, normal pickup range for food.
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


## 19. BD-569 decision brief: what the Water E leap does (2026-10-17; PROPOSAL, a feel call for the OWNER)

Question: Water dinos have no jump; the jump button is a forward dash. What should the **E leap / LEAP button** do for them? Today it is the ordinary upward leap, while s2 and s11 of this doc say "aggressive dash" and s12 says "ground-bound". No speed number is changed by this brief. Owner question: C-46 / Q20 in [116](116-handbook-conflicts.md).

### 19.1 Today (CURRENT BUILD BEHAVIOR, read from `main` after PR #409; PR #410 is open)
| Input | What runs | Numbers |
|---|---|---|
| Jump button / Space (Water) | `ClassDash.client.luau` fires the `ClassDash` remote; `ClassMovementService.luau` (flag `ClassMovementEnabled`, off by default, on in the playtest profile) checks class, grounded, 3 s cooldown and a wall within 3 studs, then answers with `CM.launchVelocity("Water","jump")`. JumpPower is 0. | 48 studs/s for 0.35 s = 16.8 studs, never upward. The client writes the answer once; PR #410 (BD-572, open, not on main) holds it every frame instead. |
| E / ButtonY / LEAP button (every class, Water too) | `Bootstrap.client.luau` `requestLeap()` fires `RequestLeap`, calls `ChangeState(Jumping)` and sets a velocity of `LeapHorizontalSpeed` forward plus `LeapVerticalSpeed` up; `leapHold` then re-applies the horizontal speed every Heartbeat for `LeapDuration`. `LeapService.luau` only validates (grounded, `LeapReadyAt`, wall ahead 3 studs, then a per-frame envelope check with rollback and a 30 s penalty). It knows no classes and does not read `ClassMovementEnabled`. | `ProgressionConfig`: 72 studs/s forward, 72 up, 0.7 s, cooldown 60 s. With gravity 250 that is an apex of 72 x 72 / 500 = 10.4 studs, about 0.58 s in the air and about 50 studs along the heading. |
| Class table `ClassMovement.Classes.Water.leap` | kind `dash`, `dashSpeed` 90, `dashSeconds` 0.5, `hitWindow` 0.4, cooldown 60 s, never upward (`launchVelocity` returns 0 up for every dash). **No game code calls it:** `launchVelocity(class, "leap")`, `duration(class, "leap")` and `rules(class).leap` are used only by `tools/verify_class_movement.py`; `ClassMovementService` asks for `"jump"` only. `hitWindow` has no reader at all (a bite is the separate Bite button, `CombatService`). | 90 x 0.5 = 45 studs, flat; 4.8 times the Water walk speed of 18.7 (22 x 0.85). |

Two more facts. (1) **All four classes leap the same today.** The Fly (93.6 studs/s, 43 up, 1.12 s, glide) and Armored (61 studs/s, 58 up) table entries are unused as well; only the animator differs per class. (2) The animator already plays the Water **surge** pose (swim wave, 0.55 s, BD-556) for a Water E leap, so the picture says "dash" while the dino flies about 10 studs up and lands with the hip dip of BD-556.

### 19.2 What this doc intended
s2: "Jump button = forward dash. Leap = aggressive dash." s11: jump is "no jump; button = forward dash with streak, tail kick, small splash"; leap is "aggressive dash, bigger lunge and splash, bite snap". s12: "WATER: ground-bound, no `Jump`". The table entry encodes exactly that (longer, faster, a 0.4 s hit window, never upward). Nothing asks for a dash that only works in water: s12 gives water zones only a +10% flavour speed, which is not built either (no code reads it).

### 19.3 Options
| | A. Keep the ordinary leap | B. E becomes a long, low dash (use the table entry) | C. E is a dash only in water zones |
|---|---|---|---|
| Rule a child sees | "E makes every dino hop forward and up." The Water jump button dashes but E flies, so "water dinos stay on the ground" is only half true. | "Water dinos never leave the ground. Jump button = short zoom, E = big zoom." | "E zooms in water, hops on land." Two behaviours on one button. |
| Feel | Same big hop as everyone, 10 studs up and a drop to land (the BD-556 hip dip). Water dinos can cross low walls and reach spots a ground-bound dino would not. | Fast flat burst, 45 studs in 0.5 s, no air time and no hard landing. Risk: 90 studs/s is 4.8 times walking speed and may feel too fast on a phone. Needs a Studio feel test. | Surprising: the same press does different things a few steps apart, and where "water" starts must be obvious on screen. |
| Phone controls | Two buttons: jump = dash, LEAP = hop. No layout change. | Two buttons, both go forward (short with 3 s cooldown, long with 60 s). No layout change; LEAP text and icon stay the same for all classes. A one-button variant (hide LEAP for Water) is possible but drops the bite-snap lunge and the 60 s special. | Same two buttons as B, but what LEAP does changes with the ground, which is hard to show on a small screen. |
| Fly and Armored parity | Full parity: all four classes leap the same; the unused table entries (Fly swoop, Armored bump, Water dash) stay dead data or are deleted. | Water becomes the only class whose leap differs. Fly and Armored stay as they are until the owner also wants swoop and shoulder bump (a follow-up per class). If B is built as one pure class-keyed lookup, adding them later is data plus verifier cases. | Water is special twice (dash, and only in water); same Fly and Armored gap as B. |
| MovementGuard | Nothing new (limit 72 studs/s during the leap; planar allowance = limit x dt x 3 + 4 studs). | `CM.speedLimit` gives 90, so the same guard formula allows it, and `Leap.violation` with Water numbers (90 forward, 0 up) passes. The 48 studs/s jump dash already passes at every sampling interval (BD-572 note). Needs a Water config in `LeapService` and an offline check with a mutant. | As B, plus a zone query on the server (see size). |
| Pose work (BD-556 surge) | The surge pose plays while the dino is airborne; the hip-dip cover and landing squash keep mattering for Water. | The surge pose (swim wave, flipper stroke) finally matches the movement; no landing, so no hip-dip cover is needed for Water leaps. The 0.55 s leap surge fits a 0.5 s dash. | Two looks needed: surge in water, hop outside. |
| Implementation size | Docs only: correct s2, s11 and s12 and the table comment; park or delete the unused `leap` entry. | Small to medium, about 4 files: a pure shared leap-shape lookup by class (so `Bootstrap` gets no new locals; it is near Luau's 200-local limit), a class branch in `LeapService` (speed, 0 up, duration, speed limit), the same branch in `requestLeap` and `leapHold` (reuse `DashHold` from PR #410 for the wall stop), more cases and mutants in `tools/verify_class_movement.py`, then a Studio flat-ground, slope and wall check. The `hitWindow` bite snap stays dormant (a later `CombatService` task). | Medium to large: all of B plus a runtime "is this dino in a water zone" query on server and client (today only `BiomePlacement` knows the pools, at placement time; nobody has checked what a Humanoid in terrain water reports as `FloorMaterial`), a second pose, and tests for entering and leaving the zone. |

### 19.4 Recommendation (PROPOSAL, not a decision)
**B**, as a Water-only change at first: it follows the owner target text (s2, s11, s12), gives children one simple rule ("water dinos never leave the ground"), keeps both buttons, makes the new surge pose match the movement, and adds no place-dependent rule. Build it as a small class-keyed lookup so Fly swoop and Armored bump can be wired later if the owner wants them, and keep the first slice to the numbers already in the table (90 studs/s, 0.5 s, cooldown 60 s). A is the honest fallback if the owner likes the big hop; then only the text changes. C is not recommended. Open risks for B: the 90 studs/s feel on a phone, slopes (the wall cast of BD-572 ignores surfaces flatter than `MaxSlopeAngle`) and `hitWindow` doing nothing until `CombatService` reads it. If the owner picks B, open an implementation row that depends on BD-572 (PR #410) being on `main`.

## 20. BD-595 decision brief: the Fly hover cap (2026-10-17; LEAD decision, owner delegated 2026-10-16; no code changed here)

Question: s12 says "FLY: hover height capped (about 6 studs, only during jump/glide)". The code has such a cap (`heightCap = 6.5` in `ClassMovement.Classes.Fly.jump`, applied by `limitVertical`), but it never acted. What should it be?

### 20.1 Today (CURRENT BUILD BEHAVIOR, read from `main` and the BD-593 measurement in [the re-walk](evidence/2026-10-17-rewalk/README.md))
* The cap runs in the server Heartbeat loop of `ClassMovementService.luau` as a velocity write. The character is owned by its client, so a server write moves the root 0.00 studs (measured). The cap and the glide in that loop never acted; BD-593 (PR #422) moves the glide to the client and deliberately leaves the cap out.
* The cap compares `root.Position.Y - groundY` with 6.5. That is the height of the **root centre**, which is already 3 to 4 studs while standing (`HipHeight + root.Size.Y / 2`, see `DinosaurVisual`). So the cap leaves a rise of only about 3 to 3.5 studs.
* The numbers (`Config.Gravity` 250, `JumpPower` 50): a Ground jump rises v^2 / 2g = 50^2 / 500 = **5.0** studs; a Fly jump (powerX 1.1, JumpPower 55) rises 55^2 / 500 = **6.05** studs, which is the "about 6" of s12. A leap (72 up) rises 10.4. Measured with the real Space key: Fly root peak 9.9 to 10.7 (3.5 standing + 6.05 + a little).
* So moved to the client **as written**, the cap would cut the Fly jump from 6.05 to about 3.5, **below the Ground jump** (5.0), and would also cut the leap (a lunge that must reach 10 studs), because the loop does not know about leaps.

### 20.2 Options
| | A. Measure the feet, keep 6.5, exempt the leap | B. Raise the cap on the root centre (about 10) | C. Remove the hover cap, rely on the glide |
|---|---|---|---|
| What changes | The cap compares `root height above ground - standing root height` (feet height) with 6.5, on the client, only while the character is not leaping (`LeapUntil`). Cap 6.5 sits just above the 6.05 apex, so a plain jump is untouched. | One number: 6.5 to about 10 (standing 3.5 + 6.05 = 9.55 to 10.05). | Delete the `limitVertical` height branch for jump; the jump height is its jump power (6.05). Glide stays (1 s, fall 12 studs/s, already client side). s12 wording changes. |
| Children (fun vs breaking the island) | Flying feels exactly as the table says ("higher and quicker"); nothing new to break. A hop that cannot be talked past about 6 studs even if jump power is tuned up. | Same feel today, but the cap would bind or not depending on size and stance (standing 3 to 4, scale grows), so two Fly dinos jump differently. A leap is cut at 10 unless exempted. | Same feel today. If jump power is ever raised (admin `Admin_jumpPower`, a future potion) the Fly dino has no ceiling, and rooftops, rocks and the cave top become reachable. |
| MovementGuard | None. A cap only lowers vertical speed, so it cannot create a false positive; the guard's vertical rule (`MovementGuardMaxVerticalSpeed` 120, gravity term) is unchanged. The cap is a feel rule, not anti-cheat: the client owns its physics, and no class has a server height check. | Same. | Same; nothing to break, nothing gained. |
| NPC / predator reach | A bite needs the target within `BiteVerticalLimit` (7 studs, centre to centre). A 6.05 hop stays inside it, so hopping never dodges a bite; the cap keeps it that way. | Cap 10 on the root is a 6.5 rise: still inside 7, but only by luck of the number. | A boosted jump above 7 would dodge every NPC bite. Not a problem at 6.05. |
| Size | Small: about 15 lines in `ClassGlide.client.luau` (after PR #422 merges), one pure function `ClassMovement.hoverStep` (or a feet-height argument for `limitVertical`), delete the dead server loop, verifier cases (apex 6.05 not cut, leap exempt, mutants). No Studio change needed besides one re-measure. | Tiny, but needs the same leap exemption, and an unstable number. | Small: delete code, reword s12, verifier cases. |

### 20.3 Decision (LEAD, delegated 2026-10-16): A
It is a pure bug fix that follows the intent of this doc: s12 says "about 6 studs" and the table says the Fly jump is "higher", and the numbers already give 6.05. With A the felt behaviour is identical to what players have today (the cap never worked, a Fly jump already rises 6.05), and the cap finally means what s12 says: feet height, not root centre. It adds no mechanic and changes no number. B and C change the design (a new number depending on stance, or dropping the s12 guarantee), so they stay unchosen; C remains an easy later step if the owner ever dislikes a ceiling. If the owner wants Fly to **hover higher** (for example a flutter that lifts to 10 studs), that is a new design and needs a new question; none is asked now. Implementation is **BD-595** (Backlog, after PR #422 / BD-593 is on `main`). Logged in [115](115-decisions-log.md).

### 20.4 Built (2026-10-17, BD-595, offline; Studio numbers pending)
Option A is in code: `ClassMovement.hoverStep` (feet height = root height above ground minus `HipHeight + root.Size.Y / 2`, cap `heightCap` 6.5, never raises a speed, skipped during a leap) is called from `ClassGlide.client.luau` in the same velocity write as the glide; the dead server loop is deleted. Offline simulation (`tools/verify_class_movement.py`): plain Fly jump unchanged, boosted jump held at 6.43, leap unchanged, glide 12 studs/s.

### 20.5 Studio numbers (2026-10-17, [evidence](evidence/2026-10-17-hover/README.md), CURRENT BUILD BEHAVIOR)
Pteranodon through `EquipSpecies`, island run, feet height sampled on Heartbeat: boosted jump (jump power 99) **6.45 to 6.48** (22.24 with the cap off); leap **10.21** (exempt); glide plateau **-16.2** studs/s (the 12 cap plus one gravity step of the post-step sample). **One miss:** a plain Fly jump rises **6.92** uncapped (the 6.05 of s20.1 and the 5.60 of the offline simulation under-predict: the Humanoid keeps pushing for a few frames), so the 6.5 cap trims it to **6.45**, about 0.47 stud, and "a plain jump is untouched" holds only approximately. Fly still jumps above Ground in theory (jump power 55 vs 50), not measured. Open for LEAD: keep 6.5 and reword ("about 6.5"), or raise `heightCap` to about 7.0 (then a boosted jump held at 7.0 touches the 7-stud `BiteVerticalLimit` edge) and correct the simulation to 6.92.


### 20.6 Decision on the measured numbers (LEAD, owner delegated 2026-10-16, FH2)
Option (a): the cap stays at `heightCap` 6.5 (feet height). A plain Fly jump really rises about 6.9 uncapped (the Humanoid keeps pushing for a few frames after take-off), so the cap trims it to about 6.46, which nobody feels. The s12 wording "about 6 studs" now reads "about 6.5 studs"; a boosted jump stays at 6.5 and below the 7-stud `BiteVerticalLimit`. No new number. The offline simulation keeps its 5.6 / 6.05 model and is labelled as a lower bound.
