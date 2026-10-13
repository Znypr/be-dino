# BD-060 dinosaur identity foundation

Implemented 2026-10-12 on `codex/bd-060-dinosaur-identity`, based on fetched GitHub
main `ad5245c`. Task status lives only in [Kanban](07-kanban.md). This foundation
changes source; it does not supersede historical Build 020 engine acceptance.

## Data and compatibility

`DinosaurIdentity` is a pure server module with no DataStore access, RNG, remote,
prices or shop operations. Additive `profile.dinosaurIdentity.version = 1` leaves
existing profile schema, grouped collection, global cosmetics and equipped-species
contracts intact. IDs combine owner key and a persisted monotonic sequence
(`u:123/d:42`), unique across players and copies. The sequence is never reused.

Each instance stores species, current stage, a defensive copy of known genes
(pattern, both color IDs, primary-color percentage and condition), BIG, Shiny,
event mutation, origin and separate owned/equipped aura/trail fields. Multiple
styles are supported by ownership sets. Account cosmetics are not copied to every
individual, reassigned, or confiscated. Shops still operate as before (BD-059 pending).
A server-only `dinosaurDetails` accessor returns defensive copies, including the
shared original egg snapshot, for later selection-menu integration; no menu added.

Successful hatches credit one distinct ID per existing 1/2/3-copy quantity inside
the same memory transaction as the grouped credit. Failed Cracked eggs credit none.
Existing operation replay returns the same IDs. One egg snapshot serves all its
copies; it retains committed genes/traits, event, queue timestamps and reward.
New run/shop eggs carry their actual source context and gene-roll version; overflow
preserves that metadata and original allocated egg ID even when the old queue
allocates a different refill ID. Old metadata is not backfilled. Crystal-shop
funding is explicitly unknown, not asserted earned-only or eligible for paid RNG.
The version identifies genes only; it does not promise reconstructible full hatch odds.

`fusionRecord` prepares one NEW output record from caller-supplied fresh traits.
It validates matching species/pattern and distinct immediate parents, records
operation/recipe/odds versions and bounded parent trait/origin snapshots. Parent
fusion origins reference their operation IDs rather than recursively embedding
ancestry. Output cosmetics start empty; parent cosmetics are omitted. This helper
neither rolls traits nor consumes inputs, debits currency or exposes a fusion remote.
The future atomic fusion transaction must archive parent operation/egg references
in a durable ledger before consumption; this PR does not implement that ledger or
claim a complete parent tree across live fusion generations.

## Safe migration and deployment boundary

Reconciliation returns a new sidecar without changing its input. It enumerates
plain Base/Gold/Diamond, separate event counts and genetic variants independently;
variant/event counts are not added to Base a second time. Sorted groups and saved
sequence IDs make retries and reconnects stable. Existing traits are checked against
their group. Legacy origin is `legacy_unknown`, without an egg, fabricated pattern,
condition, color or retrospective RNG; known saved traits are preserved. No historical
run-operation log is used to guess which copy came from which egg.

Integration is hard-gated to `localPreview`: unpublished Studio, GameId 0 and the
existing memory-profile setting. Persistent profiles never receive identity migration
from this code. Existing production collection/equip/legacy 50-copy conversion and
all prices are preserved. No Studio session, real profile or published game was
operated during this work. Robux/paid-random flags remain unchanged and disabled.

In memory previews, grouped grants/conversions reconcile the sidecar atomically.
Old conversions retain `legacy_unknown` output provenance, not a fabricated new
fusion history. Any removal of a cosmetic-bearing individual fails closed. A later
live migration must explicitly resolve old cosmetic rights and the old mutation
API, choose stable per-instance equipment and verify rollback before rollout.

The prototype now refuses migration above 3,000 living instances, without truncating
counts or writing a partial result. Worst-case one-origin-per-dinosaur measurement
showed that the earlier 10,000 ceiling could not fit a single DataStore value. This
is a development safety ceiling, not a new production inventory limit. A rejected
legacy profile keeps its grouped collection untouched. Profiles above the ceiling
need lazy materialization, compaction or sharding before persistent rollout.

## Verification

Pinned Luau 0.741 was used, matching CI. Commands:

```powershell
python tools/verify_sources.py --compiler <luau-compile>
python tools/verify_identity.py --runner <luau>
python tools/verify_progression.py --runner <luau>
python tools/build.py
python -m unittest discover -s tests -v
```

- 227 current Luau sources compile.
- Dedicated identity harness: safe/idempotent migration, unknown legacy origins,
  owner isolation, malformed-count/trait rejection, exact 3,000-copy migration,
  3,001-copy fail-closed rollback and protected-copy rollback;
  150 eggs producing 300 distinct new copies with exactly 150 shared egg snapshots;
  1/2/3 quantities, zero-copy failure, repeated egg rejection, reconnect stability,
  source-copy immutability, bounded lineage and no cosmetic transfer.
- Actual ProfileRepository harness: memory load/hatch/duplicate claim/release/reload
  preserves individual IDs and eggs; accessor mutations do not affect saved data;
  published Studio retains persistent collection path with no identity sidecar.
  Existing retry-transform, outage, lease, settlement, overflow, shop, failed-hatch,
  ordering, equipped-species and old conversion checks remain covered.
- All 37 Python packaging/artwork/economy tests pass after an isolated temporary
  environment installed the existing Pillow/NumPy test dependencies.
- Identity batch reconciliation took approximately 0.08 seconds offline on this
  machine. This is not Roblox server CPU, phone FPS or DataStore latency evidence.

Storage is linear in living individuals and distinct referenced eggs. Shared origins
avoid copying the egg payload three times, and lineage records hold only immediate
parents. Unreferenced hatch snapshots are pruned during reconciliation; the future
fusion ledger must preserve needed history before pruning. Existing CollectionJson
remains grouped; full identities are not broadcast as an attribute. Reconciliation
currently copies and scans the sidecar on each memory transaction; incremental
indexes/sharding require profiling before very large collections are enabled.

## Studio and isolated-store acceptance — 2026-10-13

The generated branch place was opened as an unpublished Studio file (`GameId = 0`,
`PlaceId = 0`). A temporary in-session probe exercised the actual
`ProfileRepository` transaction path for 20 settlements. It created 17 living
identities, including two successful multi-copy hatches and five failed Cracked
hatches. Every successful 1/2/3 quantity received distinct IDs, duplicate claims
returned the committed IDs, failed hatches created no identity, and
`release()`/`load()` preserved the selected ID and original egg. Studio reported
`BD060_Status=PASS`; the repository probe was not saved or published.

Durability was tested separately in the private test experience `test 11`
(`PlaceId 126133743767784`, universe `10766866974`) with an unsaved probe and the
exact branch `DinosaurIdentity` source. The probe used only the isolated namespace
`BeDino_BD060_Acceptance_20261013_v1`, key
`durable:identity-foundation`; it never used the configured profile store or a
player key. Phase 1 migrated a 53-copy legacy collection, hatched three distinct
copies and wrote it. After stopping and starting Play, phase 2 structurally verified
the same 53 IDs, `nextId`, traits, egg genes and three-copy origin. Both phases
reported PASS. An initial JSON-string comparison was discarded because map-key
order is not semantic; its rejected `UpdateAsync` transform left phase 1 intact.

Roblox `HttpService:JSONEncode` measured complete representative profiles with a
distinct full egg-origin record for every dinosaur:

| Dinosaurs | Serialized bytes | 4 MiB value limit | Encode time |
|---:|---:|---:|---:|
| 500 | 468,320 | 11.2% | 0.004 s |
| 1,000 | 938,806 | 22.4% | 0.008 s |
| 5,000 | 4,722,389 | 112.6% | 0.053 s |
| 10,000 | 9,472,285 | 225.8% | 0.115 s |

The figures are Studio server measurements on this machine, not a latency budget.
They establish that 500 and 1,000 worst-case records fit, while 5,000 and 10,000 do
not fit one DataStore value. `tools/measure_identity_storage.py` mirrors the
worst-case growth curve in CI. The 3,000 guard leaves material room for the rest of
the profile, but persistent enablement still requires a byte preflight and a chosen
large-inventory design. The 150-egg/300-copy test remains comfortably below this
guard.

Migration retry and rollback behavior is therefore bounded as follows: migration
is deterministic and idempotent; legacy copies receive `legacy_unknown`; malformed,
wrong-owner, over-capacity or cosmetic-protected reconciliation returns an error
from a defensive copy; the caller's collection and existing identity sidecar remain
unchanged. Persistent integration remains hard-disabled, so no production profile
can enter this path from this PR. Accounts above 3,000 copies are a known rollout
blocker rather than silently truncated accounts.

## Required BD-057 fusion integration

> **Update 2026-10-13:** BD-057 Phase 1 ([49](49-identity-fusion-phase1.md))
> implements items 2, 3, 5, 6 and 7 for Gold, plus the Gold/Diamond part of item 1
> (fused records project onto the plain stage bucket) and item 4 for ledger-backed
> fusion origins. `reconcile()` now returns `missing_fusion_ledger` instead of
> `fusion_not_integrated`. Emerald projection, odds (BD-064) and persistent rollout
> remain open. The list below is the original BD-060 requirement, kept for traceability.

`fusionRecord()` is a bounded data-contract builder. Its result deliberately does
not pass `reconcile()`: reconciliation now returns `fusion_not_integrated` explicitly.
BD-057 must change all of the following together before inserting such a record:

1. Replace the grouped collection as reconciliation authority with an identity-aware
   inventory projection that represents Base, Gold, Emerald and Diamond instances
   with independently rolled genes. A synthetic `fusion/<id>` bucket cannot be
   matched to today's grouped bucket keys.
2. Allocate the result ID from the persisted owner-scoped `nextId`; never accept a
   client ID. Validate donor ownership, stage, species, recipe pattern, uniqueness,
   locks/equipment and exact expected revisions on the server.
3. In one idempotent `UpdateAsync`, save the precommitted outcome and versions,
   archive the bounded parent/egg references in a durable operation ledger, consume
   every donor once, insert exactly one result, advance `nextId`, update the grouped
   compatibility projection and record an operation replay result.
4. Teach validation/reconciliation to accept fusion origins and Emerald only after
   that inventory model exists. Preserve fused records during unrelated grouped
   grants; never let surplus reconciliation delete them.
5. Define donor protection and explicit consent for equipped, favorited, rare or
   cosmetic-bearing donors. The result starts with empty aura/trail ownership; donor
   cosmetics expire only in the committed fusion transaction.
6. Preserve lineage references before egg pruning, bound ancestry without recursive
   profile growth, and retain resolvable placeholders when ancestor instances no
   longer live.
7. Add stale-writer, concurrent fusion, retry/reconnect, capacity/byte-budget and
   rollback tests. The RNG/odds policy work remains BD-064; reveal UI remains BD-065.

Until those changes land, callers may construct and inspect a fusion record in tests
but must not attach it to a live identity sidecar.

CI runs the new harness alongside existing checks. The generated review place was
rebuilt and source-roundtrip tested locally; no published place was replaced. CI
also produces the review build artifact. Rebuild from source for any future
disposable Studio verification.

## Remaining verification gates

Competing-session tests for the future identity write path, byte preflight under the
final compressed/sharded representation, large-account rollout/rollback approval
and owner review are pending. The current 150-egg test
exercises identity storage directly; it does not change the existing run reward
formula or prove 150 eggs can enter the current five-slot/overflow queue (BD-044).
Per-instance equip/selector, cosmetic purchase migration, full durable fusion ledger,
atomic donor consumption, fresh fusion RNG and exact odds remain subsequent tasks.
BD-060 remains Review / test. The PR is safe to review and merge only as a disabled
foundation: persistent migration stays off, and the 3,000-copy guard makes oversized
local migration fail closed. It is not approval to enable production identities or
fusion.
