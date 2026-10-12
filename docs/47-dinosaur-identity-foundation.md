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

The prototype refuses migration above 10,000 living instances, without truncating
counts or writing a partial result. This is a development safety ceiling, not a new
production inventory limit. Profiles with huge legacy counts need a chunked or
compressed identity strategy and measured serialized-byte budget before rollout.

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
  owner isolation, malformed-count/trait rejection and oversized-profile failure;
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

CI runs the new harness alongside existing checks. The generated place was rebuilt
and source-roundtrip tested locally; archived Build 020 files are not replaced in
this source PR. CI produces the review build artifact. Rebuild from source for any
future disposable Studio verification.

## Remaining verification gates

Disposable engine tests, isolated test-store durable restart/serialization and
competing sessions, measured byte/callback budgets at larger inventories, migration
rollout/rollback design and owner approval are pending. The current 150-egg test
exercises identity storage directly; it does not change the existing run reward
formula or prove 150 eggs can enter the current five-slot/overflow queue (BD-044).
Per-instance equip/selector, cosmetic purchase migration, full durable fusion ledger,
atomic donor consumption, fresh fusion RNG and exact odds remain subsequent tasks.
BD-060 must not be marked fully complete based only on these offline passes.
