# 64 - Feature intake template

Owner request 2026-10-14: every new feature answers these questions BEFORE any build, so the game stays cohesive. Copy this list into a new `docs/NN-intake-<name>.md`, answer each in 1-3 bullets (write "n/a, because ..." rather than skipping), and have the lead review before tasks enter the Kanban. Mark every statement **Seen** (verified in repo) or **Proposal**.

1. **Player intention.** Which feeling/need does it serve (progress, surprise, mastery, guidance, social)? Which loop moment: spawn, run, settle, hatch reveal, shop, collection, fusion?
2. **New or extension?** Name the existing system it extends (toast, NextGoal, potion shop, nests, fusion...) or state it is new and why nothing existing can carry it.
3. **Logical fit.** Game loop position, screens touched, systems and dependencies (config, remotes, profile fields, other BD tasks). What breaks if it is off?
4. **Graphical fit.** Screen placement, phone safety (safe insets, `TouchLayout` thumbstick/jump zones), overlap with HUD (crystals, goal line, Home, shop entry), behavior while a modal or hatch reveal is open.
5. **UI visuals.** Backboard/frame/panel variants: reuse from `resources/ui/v2/components` (buttons, headers, cards common/rare/legendary, popup-body, progress-track, reward-burst) or new. List each new piece.
6. **UI icons.** Count, purpose, rough look, v2 style (chunky, soft outline, flat 2-3 tone fill, transparent PNG, 1:1, readable at 32 px). List every icon; reuse from `resources/ui/v2/icons` and `scalable` first. IDs come only from the owner upload (`UIIconAssets`); never invent.
7. **Animations.** Each one, its purpose, duration, and the motion-off alternative (`Theme.MotionEnabled` false: no tween, instant state change).
8. **Audio.** Reuse from the 17-sound pack (`assets/audio/sfx`, doc 63) or genuinely new. Silent-safe: `Sfx.play` is a no-op while ids are empty. Respect throttle gaps.
9. **Copy/tone.** Title max ~28 characters, body ~40, sentence case, verb first, no jargon, at most one exclamation mark and only for celebration, numbers with units, one fixed spelling per concept (Crystals, eggs, nests).
10. **Data/server.** Server-authoritative? Idempotent (operation id / token like `ProfileRepository.recentOperations`)? Persistence: additive profile field, size in bytes, migration. Rate limits, abuse (client-sent progress, replay, multi-account), fail-closed behavior.
11. **Performance.** Max live instances, per-frame cost (prefer tweens/pools, no per-frame loops), memory on low-end Android, behavior during 40-400 egg batches.
12. **Metrics/engagement hook.** Which behavior should change (more runs, shop visits, fusion starts)? How do we know (attribute counters, playtest question, session-length note)?
13. **Acceptance + checks.** Offline tests (pure Luau modules), Studio checks, Android phone-landscape checks, motion-off check, sound-off check. Evidence goes to the Kanban, not into the doc.
14. **Task breakdown.** Single tasks: suggested ID, size S (under half a day) / M (about 1 day) / L (2+ days, split if possible), owner role (design, UI, server, art, QA), dependency order.
15. **Open questions for the owner.** Max 3, only decisions the lead cannot make, each with a recommended answer. The lead decides easy/medium ones and records them.

**Rule of thumb:** if the answers to 2 and 4 are "new system" and "new screen area", look again for an extension first.
