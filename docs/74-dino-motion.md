# 74 - Procedural dino action motion (BD-079)

Authored creatures only have looping Idle/Move bone clips. BD-079 adds whole-model, client-only, visual-only procedural motion that works for every species (packaged, authored and fallback visuals). No new Blender clips; real clips can replace these later. Server authority is untouched.

Files: `src/shared/DinoMotion.luau` (pure curves, unit tested), `src/client/DinoMotion.client.luau` (runtime), `tools/verify_dino_motion.py` (CI).

## Actions

| Action | Trigger | Motion |
| --- | --- | --- |
| Eat | own/nearby character `GrowthScore` or `CatchScore` increases (0.1 s delay so growth rescale finishes first) | 0.18 s squash-and-stretch pulse, 3-particle munch puff, `Sfx.play("pickup")` for the local player only |
| Jump | Humanoid -> Jumping | 0.22 s stretch (skipped if a leap just started) |
| Land | Humanoid Freefall -> Landed/Running | 0.28 s squash + 5-particle dust puff |
| Leap | player attribute `LeapReadyAt` increases (set by LeapService) | 0.5 s stretch along heading, slight nose-up; landing squash comes from Land |
| Turn | yaw rate of the root, scaled by horizontal speed | bank up to 0.25 rad, exponential smoothing (~0.1 s), exact 0 at rest |
| Bite | new replicated character attribute `BiteSeq`, incremented by PredationService on the predator when a catch lands (one line) | 0.22 s forward lunge (0.2 body lengths) with nose-down |
| Death/eaten | character `RunState` becomes `Ending` | 0.4 s tip-over, shrink to 0.6, fade out; terminal. Existing respawn/settlement unchanged |

No leap/land sound exists in `Sfx.Sounds`, and no ids were added.

## Safety rules (tested in `verify_dino_motion.py`)

Scale factors stay within 0.6..1.4 even with every action stacked; offsets are fractions of the model's own bounding box (BIG safe), clamped to 0.35; no NaN; deterministic in (events, time); each kind returns EXACTLY to rest; retriggering restarts rather than stacks; death is terminal.

## Runtime and perf budget

- One shared Heartbeat. Characters at rest cost nothing beyond a yaw/lean number update (local: per frame; others: 20 Hz, only within 120 studs; beyond that, state is restored and cleared).
- Nothing runs when `Theme.MotionEnabled` is false; any active pose is restored immediately.
- Part data is captured only when an action starts (sizes, offsets, transparency, bounding box), reused tables, no Instances created per frame. Particles: 6 pooled emitters total (3 dust, 3 munch), 3-5 particles per puff.
- Any visual rescale or rebuild (`VisualScale`, `SpeciesId`, mutation, genes, `DinoAttached`) restores the exact rest values first, so ResourceVisuals never resizes a distorted model.
- Pose is written as `Weld.C0` (packaged DinoVisual) or `CFrame` (WeldConstraint LocalMeshVisual) plus part `Size`/`Transparency`; the physics root is never changed.

## Studio checks (not run in CI)

1. Eat food: pulse at each pickup, no permanent size or tilt drift after many pickups and after a growth threshold rescale.
2. Jump/land with a Compy and a T-rex: stretch then squash, dust at feet; BIG dino looks proportionate.
3. Leap: stretch along heading, no double takeoff stretch, landing squash.
4. Turn hard while running: smooth bank, returns level when straight. Confirm WeldConstraint visuals (LocalMeshVisual) keep the written CFrame offset and return exactly (the one assumption verified only in Studio).
5. Two clients: other player's bite lunge and eaten tip-over/fade; then normal respawn after the existing 2 s delay, no stuck transparent parts.
6. Settings -> motion OFF: all of the above stops and the model is at rest.
