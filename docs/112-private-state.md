# 112: Owner-only player state (BD-360)

Status: CURRENT BUILD BEHAVIOR (branch claude/private-data-replication). Verified offline and in one Studio play session; no two-client or phone test.

## Problem
`Player` attributes replicate to every client. About 35 were set per player, including `CollectionJson` (6.9 KB mid-game), egg and nest queues and settings, resent to 11 other players on each change, and readable by any player.

## Design
- `src/shared/PrivateStateCore.luau`: classification table (PRIVATE / PUBLIC), the server buffer (order kept, deduped against what was last sent) and the client cache with snapshot and delta messages (`k = "s"` or `"d"`, sequence `v`).
- `src/server/PrivateState.luau`: `set(player, name, value)`, `get`, `snapshot`, `forget`. Values live in server memory. The client says `hello` over `BeDinoRemotes.PrivateState`; the server answers with a full snapshot (at most one per client per 2 s, BD-618; a hello inside that time is answered by one trailing snapshot, so a resync is never lost), then sends deltas coalesced for 0.2 s. A set back to the value the client already has sends nothing. `forget` runs in `ProfileRepository.release`. Nothing is sent after PlayerRemoving; values stay readable until release.
- `src/client/PrivateState.luau`: `get/num/str(name)`, `onChanged(name, fn)`, `onAnyChanged`, `isReady()`. Public names fall through to the Player attribute, so UI code uses one getter. Before the first snapshot reads give nil/0/"" (the screens' existing empty states). A delta applies fully before any listener runs, so `LastClaimedChestId` always sees its `LastChest*` values.
- A missed delta (sequence gap) asks for a new snapshot ("resync"); a rejoin is a new client and receives a full snapshot.

## Classification
PRIVATE (47 names): see `PrivateStateCore.PrivateNames`. PUBLIC: render fields (`Equipped*`, `AccountLevel`), state (`ProfileState`, `Location`, `WorldReady`, `IsAdmin`...), run ids and scores, and tiny status strings used by tests and admin hooks (docs/79). `LastSettledRunId` is private so the client sees it together with the queues the settlement just wrote.

BD-436 adds `DiscoveryJson` (counts only: colours, patterns, mutations found; never the id lists) and `LastChestNewJson` (first-time finds of the last hatched egg, drives the `NEW!` ribbon), both PRIVATE.

## Sizes (12-player sim, mid-game after 10 runs of 40 eggs)
| | before | after |
| --- | ---: | ---: |
| Player attribute bytes (to all clients) | 8,279 | 453 |
| Owner-only bytes | 0 | 7,826 |
| 12 players, full resync to 11 receivers each | 1,092,828 | 59,796 |
Real Studio: 27 attributes, 527 bytes on the local player (some are client-set).

## Tests
`tools/verify_private_state.py`: static classification (every Player SetAttribute receiver and name, no private name set or read as an attribute, every private name set via PrivateState), runtime snapshot/coalescing/order/dedupe/owner-only/gap/reconnect/loading checks on the real modules, size report, public < 2 KB. Other harnesses stub `PrivateState` onto `attrs`.

## Not migrated / open
Status and diagnostic attributes (small, public on purpose); `Equipped*` stay public (other clients render them, also copied to the Character); `LastRunId/EndAt/EndReason/scores`. Fusion ledger and the run egg bank are only exposed as counts and queue summaries (they were never attributes). A snapshot is one RemoteEvent message: a huge collection should be chunked later. No two-client Studio test yet.
