# Immediate run eggs and timed Egg Nests

2026-10-08, Build 021. Implements the owner's distinction between individual caught eggs and separate timed reward bundles.

- During runs, the green egg icon shows the number of earned eggs, derived from the existing catch thresholds. Catch score remains the internal economy input.
- Run settlement retains existing dinosaur-copy and crystal rewards, adds immediately ready individual eggs to the existing reveal queue, and separately grants the same number of Egg Nests. Current private-test thresholds award 1/2/3 eggs and nests at 10/100/500 catches.
- Each nest contains 3–6 individual eggs, rolled once on the server before its settlement transaction. Species, condition, colors, event metadata and Shiny/BIG flags are persisted. Each shell produces one dinosaur unless its Cracked condition fails; collecting more nests creates more opportunities for rare dinosaurs, without guaranteeing a rarity.
- Nests have their own saved queue, a sequential 60-second private-test timer, and offline elapsed time. These tuning values remain configurable. Existing egg queues, balances and inventory survive the additive migration.
- The NESTS menu shows nest icons, egg counts and countdowns. Opening the first ready nest atomically moves its contents into the existing egg reveal queue. The same hatch animation presents those individual eggs. A full reveal queue keeps the nest intact and asks players to reveal ready eggs first.
- Nest capacity is 30. Run entry reserves space for up to three egg/nest rewards; in-run egg purchases preserve this reservation. Opening nests requires sanctuary. Old queued eggs and pending overflow remain accessible through REVEAL READY EGGS.
- The nest icon also appears in run results; the green egg appears beside the caught-egg result and in the live counter. Timer and quantity remain live UI elements.

Owner-uploaded image IDs: caught egg `104481541835155`, Egg Nest `127462994652706`. GetProductInfo confirmed both creator IDs as experience owner User `7285577648`. Bindings are reproducible through `tools/bind_ui_icons.py`; empty IDs retain native egg fallbacks.

Validation: `tools/verify_egg_nests.py` exercises the real repository with repeated UpdateAsync transforms, duplicate settlement/open/claim, 3- and 6-egg bundles, FIFO timing, simulated offline readiness, rejoin, overflow retention and datastore-outage rollback. Existing gameplay and egg-genetics checks also run. Studio presentation and published multiplayer checks are recorded separately; source tests alone do not certify those.

Completion check, 2026-10-13: all 226 Luau sources compile with pinned Luau 0.741; the nest transaction harness passes; all 37 packaging/artwork tests pass. Build 021 was regenerated from the current sources. The earlier owner Studio test loaded Build 021, its OpenEggNest remote and both new ImageLabels with IsLoaded=true. Eight changed scripts were applied to the owner place's Edit model with source checks and a ServerStorage source backup; the experience was not published. Full timed-menu interaction, physical-phone and published multiplayer acceptance remain unverified. On continuation, the current Studio Client bridge was not reachable for additional UI checks.
