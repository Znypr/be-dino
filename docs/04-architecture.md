# Technical architecture
Proposal, not implemented. Goal: small modules with explicit authority and durable progression.

## Toolchain
Typed Luau in Git, Rojo for syncing/building into Roblox Studio, pinned tool versions selected during setup.
Keep dependencies minimal. Run formatting/static analysis in CI, then Roblox-specific tests in Studio.
Rojo supports filesystem-based workflows and version control: [official documentation](https://rojo.space/docs/v7/).
Start with one Roblox place containing lobby and arena. Use separate test and production experiences/data namespaces.

## Proposed layout
- src/shared: types, item definitions, public config, pure calculations.
- src/server: RunService module (name distinct from Roblox service in code), FoodService, PredationService, RewardService, InventoryService, EggService, ProfileRepository.
- src/client: input, camera, HUD, collection and egg controllers, audio/VFX.
- assets: manifest and original reproducible source assets.
- tests: pure rules and integration scenarios.
- docs: decisions, board and evidence.

Do not build an ECS, matchmaking layer or distributed service system before the simple loop proves it needs one.

## Authority boundary
Client sends bounded intents such as startRun, requestEndRun, equipSpecies, claimEggs, mutateSpecies.
Server owns scores, pickup ownership, eating eligibility, reward draws, inventory changes and queue timestamps.
Validate shape, finite values, ownership, state, distance and request rate. Do not accept client-supplied reward amounts or victim death.
Roblox recommends validating all client input and rate limiting server-triggered logic: [security guidance](https://create.roblox.com/docs/scripting/security/client-server-boundary).
Server-observed character positions can still reflect client-owned physics. Add movement plausibility checks and reject implausible pickup/eating paths; server-side distance checks alone are insufficient.

## Run lifecycle
Lobby -> Active -> Ending -> Settled -> Lobby.
One runId and one terminal transition. Manual exit, death and disconnect all enter the same finalization path.
Persist fixed reward outcomes keyed by runId. A repeated finalization returns the recorded result.
Do not require distributed atomicity across attacker and victim profiles: victim reward settlement is independent; attacker growth is temporary. Any persistent kill reward needs its own idempotent event identifier.

## Persistence
One bounded profile per user: schemaVersion, revision, species/mutation counts, equipped key, eggs, recent settlement IDs, last checkpoint, session lease metadata.
Use a reviewed persistence solution or a carefully tested UpdateAsync wrapper; choose during BD-005. Do not assume UpdateAsync alone solves session races.
Define lease acquisition/renewal/expiry and stale-server write rejection. Never allow two servers to mutate the same live profile.
On load failure, block progression and offer retry; never overwrite an existing profile with defaults.
Bounded retry/backoff, autosave/checkpoints and shutdown handling. Shutdown saving is best effort, not a guarantee.
Persist a mutation's deduction and output together in one profile transaction. Persist egg consumption and inventory reward together.
Precompute immutable reward outcomes outside any retried update callback and reuse the same operation ID.
Compact old settlement IDs only after defining the maximum replay window; do not leave unbounded arrays.
Roblox data stores provide persistent storage, but network operations can fail and require handling: [Data stores](https://create.roblox.com/docs/cloud-services/data-stores).

## Failure promises
Durably committed collections/eggs must survive reconnect and stale-server contention.
An uncheckpointed active run may lose recent progress after a process crash; define checkpoint interval and communicate this alpha limitation.
Do not display 'saved' until persistence confirms. Retry ambiguous operations by ID rather than issue new rewards.
Never store credentials in the repository or client scripts.

## Performance proposal
Use bounded food population and spatial lookup; avoid one frame loop per food item.
Batch cosmetic updates; stream or pool visuals only when profiling supports it.
Start with 8-player private test target and 300 active pickups; these are load-test parameters, not platform limits.
Acceptance proposal: sustained 30 FPS or better on the agreed lower-end test phone, responsive controls, and no growing memory trend in a 20-minute session.
Record actual hardware, client/server timings, player count and build. Emulation does not establish real mobile performance.

## Observability and delivery
Events: run_started, first_food, run_ended(reason), reward_committed, egg_claimed, mutation_completed, save_failed.
Collect only operational IDs/aggregates needed for diagnostics; no free-text personal data.
Every build references a commit. Tag a known-good build before the test and retain a tested rollback path.
Schema changes require backwards-compatible migration tests; code rollback does not automatically undo persistent data changes.

## Reward contract update (confirmed direction)
Store catchScore separately from growthScore. Reward calculation returns a bounded list of {speciesId, mutationId, count} stacks plus chest grants, keyed by runId and rewardConfigVersion. Store counts as validated nonnegative integers and define numeric bounds before implementation.
RunRewardConfig and ChestRewardConfig are separate tables; chest claims must not reuse or alter settled run loot. Preserve immutable outcomes through retries. Aggregate duplicates before saving or sending UI payloads; never instantiate one world object per awarded copy.
Three-species alpha catalog uses the same contracts as the eventual multi-species, multi-rarity catalog. Reward eligibility and mutation rules must not depend on UI labels or color.
