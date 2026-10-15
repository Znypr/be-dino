# BD-057 Phase 1: safe server-authoritative identity fusion

Implemented 2026-10-13 on `claude/be-dino-development`, based on `50116b8`
(BD-060 merge). Task status lives only in [Kanban](07-kanban.md). Owner intent is
[the fusion specification](46-pattern-fusion-dino-identity-and-cosmetic-progression.md);

> **2026-10-15: the ladder is now 6 / 3 / 2 with an any-pattern Gold ([90](90-fusion-ladder-v2.md)); counts below are history.**
>
> **2026-10-14 update:** the recipe is now Gold = 15 Base / Emerald = 4 Gold / Diamond = 2 Emerald (50/10/3 on 2026-10-13): see [58](58-fusion-ladder-50-10-3.md). The 10-donor text below is historical.
the identity sidecar this builds on is [BD-060](47-dinosaur-identity-foundation.md).

**Scope: a disabled, development-only transaction foundation.** It is not playable
fusion, not a Fusion Menu, not trait odds and not a production migration. It passed
one unpublished Studio memory-profile check (below) and has never run against a
persistent profile or DataStore.

> **Update 2026-10-13 (BD-064):** this document describes the Phase 1 state. Since then a
> provisional odds roller, persistent-identity flag and the `FusionAction` remote were added;
> see [53](53-bd064-fusion-server.md) and [52](52-fusion-remote-contract.md). Statements below
> about "no remote", "no odds" and "not persisted" are historical to Phase 1.

## What it does

Ten distinct dinosaur identities of the same species, Base stage and saved egg
pattern are fused into **one NEW Gold** individual with its own server-allocated ID.

| Requirement | Implementation |
| --- | --- |
| Ownership and saved identity | Every donor ID must carry the profile's owner prefix (`u:<id>/d:<n>`), exist in `profile.dinosaurIdentity` and have `traitsKnown` + a saved `genes.patternId`. Legacy `legacy_unknown` copies without a saved pattern are ineligible (`missing_pattern`). |
| Species / pattern / stage | All donors share species and pattern and are at the recipe's source stage (`species_mismatch`, `pattern_mismatch`, `wrong_stage`). Exactly 10 distinct string IDs (`wrong_donor_count`, `duplicate_donor`, `invalid_donor_id`). |
| Protection | `locked` / `favorited` donors are refused outright (`donor_locked`). |
| Cosmetic-loss consent | The quote returns an itemized loss manifest: each donor's owned aura/trail IDs, equipped aura/trail, and Shiny/BIG/event-mutation flags. If it is non-empty the request must echo the exact `consentDigest` (`consent_required`). |
| Consume all 10 | All 10 donor identities are removed and the grouped Build 020 projection is decremented per donor bucket in the same transform; Gold is incremented once. |
| One new ID | Allocated from the persisted monotonic `nextId`; never from the client. |
| Lineage | The new record stores bounded immediate-parent snapshots (traits + origin, no cosmetics). A durable ledger entry `dinosaurIdentity.fusions[operationId]` records parent IDs, distinct parent egg IDs, parent fusion operation IDs, recipe/odds versions and the committed outcome. Reconciliation keeps eggs referenced by the ledger, so original eggs survive consumption. `dinosaurDetails` returns `lineage` for fused records. |
| Guaranteed success | The target stage comes from the recipe, never from the roller. Once a request validates, the only failures are storage/consistency guards that roll back everything; there is no random failure. |
| Atomic | `IdentityFusion.apply` is copy-on-write and returns `nil, reason` on any failure, so the `UpdateAsync` transform aborts with the stored profile unchanged. A whole-sidecar `reconcile` and a byte preflight run before the commit. |
| Idempotent | `operationId = "fusion:" .. token`. A replay of the same token and donor set (any order) returns the committed result without odds, rolls or consumption. The same token with a different request is `token_conflict`. |
| Duplicate / stale / concurrent requests | The quote freezes every donor's full payload into `quoteDigest`; any change before commit is `stale_quote`. A second fusion that overlaps already consumed donors fails with `donor_missing`. |
| Failed writes | Traits are precommitted once outside `UpdateAsync` (`prepareOutcome`), so transform retries cannot reroll. Commit-then-throw retries see the ledger and replay. |
| Emerald / Diamond | `Recipes.emerald` and `Recipes.diamond` exist with `donorCount = nil` and fail closed with `recipe_not_approved`. No costs were invented. Emerald also has no grouped projection yet (`projection_unsupported`). |
| Trait RNG boundary | A roller `{version, roll(summary, patternId)}` is injected. The summary holds only neutral ingredient counts (Shiny/BIG/mutation/condition/colors), no probabilities. No production roller exists (`odds_not_approved`); BD-064 owns the formula. The pattern is recipe-locked and overwritten after the roll. |

## Files

- `src/server/IdentityFusion.luau` (new, pure): `Recipes`, `quote`, `prepareOutcome`,
  `apply`, `lineage`, `encodedSize` byte estimate, `MaxSidecarBytes = 3,200,000`.
- `src/server/DinosaurIdentity.luau`: `reconcile` accepts fusion records only when
  backed by a ledger entry with matching `resultId` (`missing_fusion_ledger`), checks
  them against the plain stage bucket (`compy/gold`), sorts them first so a grouped
  decrement (legacy Gold → Diamond) spends legacy copies, and fails closed
  (`protected_identity`) rather than deleting a fused result. `fusionRecord` uses the
  plain stage bucket key.
- `src/server/ProfileRepository.luau`: `setFusionTestRoller`, `quoteFusion`,
  `fuseDinosaurs`. All return `fusion_disabled` unless the session is an unpublished,
  memory-only Studio profile **and** `Config.IdentityFusionPreviewEnabled` is true.
  There is no remote and no client flow (BD-065).
- `src/shared/Config.luau`: `IdentityFusionPreviewEnabled = false`.

Unchanged: production identity migration (still hard-gated off), Build 020 legacy
50 → Gold / Gold → Diamond conversion, real saves, prices, shops and paid features.

## Verification (2026-10-13, offline)

Pinned Luau 0.741 (matching CI) on Windows; Python 3.14 with Pillow/NumPy in an
isolated environment.

```powershell
python tools/verify_fusion.py --runner <luau>
python tools/verify_progression.py --runner <luau>
# plus every other CI check, tools/verify_hatch.py, tools/build.py and
python -m unittest discover -s tests -v
```

- **`tools/verify_fusion.py`** (new, in CI) exercises the pure module over a fixture
  built through the real BD-060 `hatch`/`reconcile` path:
  - happy path: 10 consumed, one new ID, `nextId + 1`, Gold guaranteed, empty
    cosmetics, input profile byte-identical, other grouped buckets unchanged, ledger
    and four distinct parent eggs retained, reload reconciles unchanged;
  - invalid donors: 9 / 11 / non-list / extra keys, duplicate, missing, foreign owner,
    non-string, no saved pattern, wrong stage/species/pattern, locked, favorited,
    wrong owner key, unknown stage, invalid tokens;
  - consent: itemized aura/trail/equipped and Shiny/BIG/mutation losses; missing and
    wrong digests roll back; the digest changes when the loss set changes;
  - idempotency: commit-then-throw replay, rerolled retry still returns committed
    traits, order-insensitive tokens, token conflict, stale donor/forged digests,
    overlapping concurrent fusion → `donor_missing`;
  - rollback with byte-identical input for `storage_limit`, `odds_not_approved`,
    invalid/forged outcomes (wrong pattern, stage, request), grouped mismatch,
    corrupt ledger, missing identity, identity capacity and the Emerald projection gate;
  - lineage: parent eggs survive later hatches and grants; `lineage()` returns copies;
    legacy Gold decrement keeps the fused record, removing the last Gold fails closed;
    ledgerless, mismatched or malformed fused records are rejected;
  - storage: 20 sequential fusions archive 200 parent eggs; estimated growth is about
    7 KB per fusion, well under the preflight ceiling.
- **`tools/verify_progression.py`** adds a repository section on the real
  `ProfileRepository` memory path with ten donors hatched through `claimChest`:
  default-off flag, refusal without a roller, stale digest, foreign IDs, invalid token,
  an injected write outage (`save_failed`, nothing consumed), lease loss (`lease_lost`,
  nothing consumed), a successful fusion with synced `CollectionJson` and lineage,
  duplicate confirm without reroll, token conflict, consumed-donor reuse,
  release/load keeping result + lineage + replay, zero persistent DataStore calls, and
  a published repository returning `fusion_disabled` even with the flag on.
- All existing harnesses pass; 228 Luau sources compile; `tools/build.py` builds
  `BeDino-Build020.rbxlx`; 37 Python unit tests pass.

Writing these tests found and fixed one defect in the earlier WIP: `reconcile` still
applied the grouped genes-presence check to fused records, so every fusion was
rejected with `gene_mismatch`. Parent egg IDs in the ledger are now distinct.

## Unpublished Studio check (2026-10-13)

A local copy of the PR build (`BeDino-Build020.rbxlx`, commit `1a33656`) was opened
in Roblox Studio and confirmed unpublished (`GameId = 0`, `PlaceId = 0`). In that
unsaved copy only, `IdentityFusionPreviewEnabled` was set to `true` in Config's
source for one Play session, then reverted; the file was not saved or published.
The checks ran through the Studio MCP server's server-side Luau. That context loads
its own `ProfileRepository` instance, so they used a stand-in test player
(`UserId -57`) on that instance's memory store, separate from the joined player's
profile. Real Roblox `HttpService` JSON round-trips, `Random` and the
unpublished-only gate were exercised.

- Ten Wavy-Stripes Compies were hatched through the real `commitRunSettlement` /
  `claimChest` path (24 one-egg runs with fixed, schema-valid egg genes; species stayed
  the real random draw).
- 20 of 20 checks passed: quote; `odds_not_approved` without a roller and nothing
  consumed; roller accepted; stale digest, foreign donor ID and Emerald refused; fusion
  committed with grouped Gold +1, all ten donors consumed, a new Gold record with the
  recipe-locked pattern, traits from the controlled outcome, empty cosmetics, lineage
  with 10 parents and 9 distinct original eggs; duplicate confirm returned the same
  result without a reroll; token conflict; consumed-donor reuse → `donor_missing`;
  release/reload kept result and lineage; replay after reload returned the same result.
- Roblox `HttpService:JSONEncode` matched `IdentityFusion.encodedSize` exactly for
  synthetic sidecars: 290,317 bytes (300 hatched + 10 fusions) and 964,904 bytes
  (1,000 hatched + 10 fusions). The estimate is exact for this data, not proven for
  every possible string.
- Observation: an earlier attempt used 500-catch runs, and each credits 500 direct
  copies under the Build 020 run reward. After about five such runs the test profile
  held 2,522 copies, and the next run exceeded the 3,000-identity guard
  (`identity_capacity`, rolled back as designed). The donors were then collected with
  one-egg, 10-catch runs. A new Studio profile starts with one Compy.

## Not performed / not verified

- No published-place or multi-client Studio run, and no fusion inside the game's
  own `Bootstrap`-loaded repository instance (no remote exists to reach it).
- No DataStore, private test experience, real profile or production save was touched.
- No competing-server test: lease loss and outages are mocked.
- No client remote, UI, reveal wheel or mobile test exists.

## Remaining limitations and open owner decisions

- **Owner decisions (gameplay):** Shiny/BIG/mutation donors are treated as valuable
  and require consent; `locked`/`favorited` block donors with no override (those
  fields have no UI yet). Auto-fill policy belongs to BD-065. These are working
  defaults, not approved rules.
- No trait odds: BD-064 must approve the formula, versioning and disclosure before
  any production roller exists. Paid-random eligibility of donors is not evaluated.
- Emerald needs an approved recipe and an additive grouped/schema change; Diamond
  needs an approved cost. Higher-tier donors (fused Gold inputs) are untested.
- The ledger is never trimmed. Roughly 7 KB per fusion (estimate) is linear growth
  inside the 3,000-identity / single-value sidecar, so compaction or sharding is still
  required before persistent rollout (as for BD-060).
- Persistent enablement still requires the BD-060 rollout gates, cosmetic purchase
  migration (BD-059) and Studio/DataStore acceptance of this transaction.
