# BD-005: persistence and remote contracts

Status: specified for the private alpha. Implementation of durable storage remains BD-011.

## Persistence choice
Use Roblox `DataStoreService` through a small project-owned `UpdateAsync` repository. Do not add an external profile library for the first test. The repository must implement session ownership, revision checks, bounded retries and idempotent operations before any durable rewards are enabled.

A profile load failure blocks progression and offers retry. It must never fall back to a blank writable profile. Shutdown saving is best effort only; committed mutations must already have gone through `UpdateAsync`.

## Profile schema v1
One bounded profile per user:

```text
schemaVersion: 1
revision: integer >= 0
session: {
  leaseId: server GUID,
  jobId: game.JobId,
  expiresAt: server unix timestamp
}
equippedSpeciesId: string
collection: { [speciesId]: { base: integer, gold: integer } }
eggs: bounded array of { eggId, kind, readyAt, rewardOperationId? }
recentOperations: bounded array/map of committed operation IDs
lastCheckpoint: { committedAt, lastSettledRunId? }
```

Unknown schema versions block writes until migrated. Unknown species or mutation keys are rejected rather than silently created.

## Session ownership
- Lease acquisition and every durable write use `UpdateAsync`.
- A server may acquire when no lease exists, its own lease is present, or the old lease is expired.
- Initial private-test target: 90-second lease with renewal about every 30 seconds. These are implementation defaults, not gameplay tuning.
- A write is valid only when the stored `leaseId` still equals the server's lease and the expected revision has not gone backwards.
- A stale server that loses the lease stops durable mutations and must not overwrite the newer session.
- Rejoin after an unclean shutdown may wait for lease expiry rather than risking two writers.

## Operation IDs and immutable outcomes
- `runId` is a server-generated GUID when a run begins.
- Run settlement operation ID is derived from `runId`; repeated settlement returns the same already-recorded outcome.
- Reward randomness is computed once on the server, then the exact outcome is persisted. An `UpdateAsync` retry never rerolls.
- Egg claim and mutation each receive a unique server operation ID after the request passes validation.
- `recentOperations` is bounded. Compaction must retain IDs long enough to cover the maximum retry/replay window.
- Client request tokens may only deduplicate transport retries within the current session. They never authorize quantities or rewards.

## Run state contract
Server states are `Active -> Ending -> Settled -> Lobby`. Only the server changes state.

Current Build 005 implements the `Active -> Ending` guard only. Predation, natural death and manual exit all compete through the same terminal function. The first state transition wins; later attempts do nothing. Durable `Settled` behavior is BD-011.

## Remote validation matrix
| Remote intent | Client payload | Server checks | Server-owned result |
|---|---|---|---|
| `RequestEndRun` | none | player has live Active run, request rate, no extra args | start 3-second movement-cancelable exit channel |
| `StartRun` | selected species ID, request token | loaded profile, owned/equippable species, state, rate, bounded strings | new server `runId`, spawn state |
| `EquipSpecies` | species ID, request token | loaded profile, known ID, owns required copy, rate | equipped key persisted |
| `ClaimEgg` | egg ID, request token | loaded profile, known queued egg, server time >= readyAt, rate | immutable reward persisted once |
| `MutateSpecies` | species ID, target mutation, request token | loaded profile, known recipe, sufficient copies, equipped-copy rule, rate | atomic deduction + output |

No remote accepts growth score, catch score, inventory count, reward quantity, victim death, ready timestamp or rarity result from the client.

## Physics and proximity
Roblox character physics may be client-owned, so server-observed position is not automatically trustworthy. Food and predation use bounded server loops, distance/occlusion checks and sampled displacement rejection. This is only a first anti-teleport layer. BD-018 still requires exploit-oriented movement, flood and malformed-input tests.

## Failure behavior
- Load failure: block progression, retry with bounded backoff, do not write defaults.
- Ambiguous durable write: retry the same operation ID and immutable outcome.
- Lease loss: stop durable writes and surface a reconnect/error state.
- DataStore budget/throttle: queue only bounded retries; never spin or flood requests.
- Process crash during an uncheckpointed active run may lose temporary growth/catch progress. Already committed collection/egg/mutation operations must survive.
- Disconnect settlement may only use the last validated server checkpoint once BD-011 implements it.

## BD-011 verification requirements
Test load failure, lease contention, stale-server write, duplicate settlement, duplicate egg claim, mutation retry, server shutdown and rejoin. Passing source review alone is not persistence acceptance.
