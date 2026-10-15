# BD-064 fusion server: persistent identities, provisional odds and FusionAction

Implemented 2026-10-13 on `claude/bd-064-fusion-server`, based on main `18856b4`.
Task status lives only in [Kanban](07-kanban.md). Owner intent:
[fusion specification](46-pattern-fusion-dino-identity-and-cosmetic-progression.md)
sections 1, 4, 6 and 7. Builds on [BD-060](47-dinosaur-identity-foundation.md) and
[BD-057 Phase 1](49-identity-fusion-phase1.md). Remote contract for the BD-065 UI:
[52](52-fusion-remote-contract.md).

**Scope:** server code for the Milestone 1 private playtest. Owner decisions
(2026-10-13): Milestone 1 is a private playtest **including fusion**, in a **new
private place with a fresh, empty DataStore** (no legacy saves to migrate there), with
**all Robux/paid features off**. Provisional numbers are allowed when labeled
`PROVISIONAL`. Everything below is **offline-tested only**; Studio and live-DataStore
acceptance are pending.

Both new flags are `false` in committed source, so the shipped build behaves as
before: no persistent sidecar, no fusion. The remote exists and answers
`fusion_disabled`.

## 1. Persistent identities (playtest flag)

| Item | Implementation |
| --- | --- |
| Flag | `Config.IdentityPersistentEnabled` (default `false`). With `IdentityFusionPreviewEnabled` also `true`, fusion runs on persistent profiles. |
| Store wrapper | When the flag is on and the session is not an unpublished Studio memory session, `ProfileRepository` wraps the DataStore: every `UpdateAsync` transform is followed, **in the same transform**, by `DinosaurIdentity.reconcile` of the grouped collection and the sidecar. Sidecar and collection always commit together. |
| Fresh profiles | The load transform creates the sidecar (one `legacy_unknown` record for the starter Compy). |
| Hatches | `claimChest` credits identities through `DinosaurIdentity.hatch` when `identityAvailable(sidecar)`; this is the only change in `claimChest` (the condition, formerly `localPreview and ...`). |
| 3,000-identity guard | Unchanged (`DinosaurIdentity.MaxInstances`). |
| Fail closed for identity only | If reconcile fails (`identity_capacity`, `protected_identity`, corrupt sidecar), the write still commits the profile, but the sidecar is restored to its pre-transform copy and marked `suspendedReason`. Nothing is deleted (fused results and cosmetics survive). Identity features return `identity_unavailable`; hatches credit only the grouped collection. When a later write reconciles again, the mark is cleared automatically (hatches made while suspended become `legacy_unknown` records without egg provenance). |
| Legacy profiles | A profile without a sidecar that cannot reconcile (for example over 3,000 copies) keeps loading and playing with no sidecar. One under the guard gets a sidecar on first load (this is a migration; the playtest store has no legacy saves). |
| Byte preflight | `IdentityFusion.encodedSize` (Studio measured it equal to Roblox `JSONEncode` for identity data) of the **whole profile**. PROVISIONAL budgets under the 4 MiB (4,194,304 B) value limit: `IdentityFusionProfileBudgetBytes = 3,400,000` — a fusion whose post-write profile is larger is rejected with `storage_limit`, nothing consumed; `IdentityProfileHardLimitBytes = 3,800,000` — any persistent write above it first drops that write's identity growth (sidecar restored and suspended `storage_limit`), and if still too large the write aborts with the stored profile unchanged. The existing sidecar ceiling `IdentityFusion.MaxSidecarBytes = 3,200,000` still applies. |
| Unpublished Studio | Unchanged: memory store + reconcile wrapper that errors on failure. |

## 2. Provisional fusion odds (`src/server/FusionOdds.luau`)

Version **`fusion-odds-provisional-v1`**. All values are **PROVISIONAL** module
constants; changing any of them requires a new version string. For `N` donors (10 for
Gold), from IdentityFusion's neutral ingredient summary:

| Wheel | Formula | 10-donor examples |
| --- | --- | --- |
| Shiny | `0.5 × shinyDonors / N` | 0 → 0%, 1 → 5%, **2 → 10%**, 5 → 25%, 10 → 50% |
| BIG | `0.5 × bigDonors / N` | same as Shiny |
| Event mutation | `P(m) = 0.5 × donorsWith(m) / N`; `P(none) = 1 − ΣP(m)` | 2 Ember + 1 Frost → Ember 10%, Frost 5%, none 85% |
| Condition | `donorsWith(c) / N` | 6 Normal, 3 Rainbow, 1 Cracked → 60/30/10% |
| Primary color | `donorsWithPrimary(k) / N` | no color from 0% ancestry |
| Secondary color | `donorsWithSecondary(k) / N` | independent of primary |
| Blend | uniform integer 1..99; 100 when primary == secondary | matches Build 020 eggs |
| Pattern | locked by recipe | never rolled |
| Failure | none: `hatchSuccess = true`, stage guaranteed | a Cracked result does not re-roll hatch failure |

- `FusionOdds.distribution(summary)` returns the **exact** distribution;
  `FusionOdds.rollWith(summary, pattern, nextNumber)` draws one uniform per wheel in a
  fixed order (`shiny, big, mutation, condition, primaryColor, secondaryColor, blend`)
  and inverts the same tables over sorted keys, so quote and roll cannot diverge.
  Uniforms are clamped into `[0, 1)`.
- `FusionOdds.roller(newRng)` implements the IdentityFusion roller contract plus
  `distribution`. Production uses `Random.new()` per roll.
- Rolled genes are validated with `EggGenetics.valid` in `IdentityFusion.prepareOutcome`.
- Traits are rolled **once** outside `UpdateAsync`; retries and replays return the
  committed outcome. Ledger, result record and response carry the odds version.
- Gating: `ProfileRepository` uses the production roller whenever fusion is enabled;
  `setFusionTestRoller` still injects a controlled roller for tests (nil restores
  production).

## 3. FusionAction remote (`src/server/FusionService.luau`)

Started from `Bootstrap.server.luau`. A RemoteFunction
`ReplicatedStorage.BeDinoRemotes.FusionAction` with actions `list`, `details`, `quote`,
`fuse`, exactly as documented in [52](52-fusion-remote-contract.md). Every argument is
type/length/key validated (unknown keys such as `traits` are `bad_request`), donor IDs
are only looked up inside the caller's own profile, responses are rebuilt from
whitelisted fields, and a PROVISIONAL per-player limit applies
(`FusionRequestsPerWindow = 20` per `FusionRateWindowSeconds = 10`). New repository
functions: `fusionStatus`, `listDinosaurs`, `fusionDetails`; `quoteFusion` now adds
`odds`/`oddsVersion`.

**Paid-random gate:** fusion is randomized synthesis. A profile is treated as
Robux-linked when `Config.CrystalPacksEnabled` is on or `metrics.robux > 0`; such
profiles need `Config.PaidRandomItemsEnabled` and a passed `PolicyService` check
(`PaidRandomEligible`), otherwise `random_items_unavailable`. Milestone 1 has Robux off,
so playtest profiles are not affected. This is a conservative gate, not a policy
certification.

## Files

- New: `src/server/FusionOdds.luau`, `src/server/FusionService.luau`,
  `docs/52-fusion-remote-contract.md`, this document.
- Changed: `src/server/ProfileRepository.luau` (identity gating helpers, persistent store
  wrapper, fusion section, the one `claimChest` condition), `src/shared/Config.luau`
  (keys next to `IdentityFusionPreviewEnabled`), `src/server/Bootstrap.server.luau`
  (start FusionService), `tools/verify_fusion.py`, `tools/verify_progression.py`,
  rebuilt `build/BeDino-Build020.*`.
- Not changed: client files, run settlement/chest economy logic (BD-044), RewardMath.

## Verification (2026-10-13, offline)

Pinned Luau 0.741 on Windows (Git Bash), Python 3.14 with Pillow/NumPy. Every command
in the CI workflow's "Check Luau sources and behavior" step passed, plus
`tools/bind_artwork.py --check`, `tools/build.py` (230 scripts, `BeDino-Build020.rbxlx`)
and `python -m unittest discover -s tests` (37 tests OK).

`tools/verify_fusion.py` (new sections):

- **Normalization:** 0/1/2/5/10 Shiny (and BIG) donors → exactly 0/5/10/25/50%; mixed
  donors give Ember 10%, Frost 5%, none 85%, condition 60/30/10%, colors 80/10/10%;
  each wheel sums to 1; outcomes with 0% ancestry are absent; malformed summaries fail
  closed.
- **Parity:** 200,000 seeded rolls match every quoted probability within 5 standard
  errors (Shiny, BIG, each mutation and no-mutation, condition, both colors, P(equal
  colors) → blend 100); blend spans exactly 1..99 with mean ≈ 50; zero Shiny donors
  never give Shiny; ten give ≈ 50%; every rolled gene passes `EggGenetics.valid`; edge
  uniforms 0 and 1 stay inside the wheels.
- **Determinism:** the same seed yields the same outcome; ledger, result record and
  outcome carry `fusion-odds-provisional-v1`; a retried transform with a different
  seed returns the committed traits; plain donors can only yield their own colors and
  condition, never Shiny/BIG/mutation.

`tools/verify_progression.py` (new sections, real `ProfileRepository` over the mocked
DataStore with repeated transforms):

- **Persistent identity:** committed defaults off; fresh profile gets a sidecar; 12
  hatched eggs credit 24 persisted identities with egg snapshots; quote carries exact
  odds; write outage → `save_failed`, nothing consumed; lease loss → `lease_lost`,
  nothing consumed; byte preflight → `storage_limit`, nothing consumed; production
  roller fusion commits Gold +1, consumes 10, records odds version; duplicate confirm;
  reload keeps result, lineage and replay; forcing 3,500 grouped copies suspends
  identity (`identity_capacity`) without deleting the fused result, keeps saves and run
  rewards working, skips identity hatch credit, and resumes when counts recover; hard
  byte ceiling drops identity growth (`storage_limit`) and otherwise aborts the write
  unchanged; a 5,000-copy legacy profile without sidecar loads, plays and reports
  `identity_unavailable`; a small legacy profile migrates; a Robux-linked profile is
  `random_items_unavailable`.
- **FusionService:** remote creation; exact contract keys for list entries, quote, odds
  and fuse result; sorted paging with `nextCursor`; details with original egg and
  lineage; wrong owner, unapproved Emerald, stale quote, consumed-donor reuse; forged
  `traits`/`resultId` refused; 34 malformed shapes and extra arguments →
  `bad_request`; 2,000 randomized requests never throw and never fuse; 20 requests per
  window then `rate_limited` (malformed requests count, per player, window resets);
  disabled flag → `fusion_disabled`.
- Existing unpublished-Studio fusion test updated: the quote now carries production
  odds, and an invalid injected roller is still refused with `odds_not_approved`.

## Not verified / Studio pending

- No Roblox Studio run of this branch (Studio MCP was out of scope for this task): the
  remote, `Random`, real `HttpService` JSON size parity on whole profiles, and
  `OnServerInvoke` serialization of the responses are untested in Roblox.
- No real DataStore, private place or competing server. Outages and lease loss are
  mocked.
- No client UI (BD-065 is built separately against [52](52-fusion-remote-contract.md)).
- Owner sign-off on the PROVISIONAL coefficients, budgets and rate limit is pending.

## Studio acceptance checklist for the playtest place

1. New private place, fresh DataStore name, set `IdentityPersistentEnabled = true` and
   `IdentityFusionPreviewEnabled = true` in that build only; confirm all paid flags off.
2. Join, play runs, hatch ≥ 10 same-species/same-pattern eggs; `FusionAction` `list`
   shows them with genes.
3. `quote` shows 0% Shiny for plain donors; fuse; rejoin; confirm the Gold, lineage and
   `duplicate` replay; compare `HttpService:JSONEncode(profile)` length with
   `IdentityFusion.encodedSize(profile)`.
4. Two servers: confirm lease handling (`SessionBusy` / `lease_lost`) with real
   DataStore sessions.

## Open risks

- The fusion ledger is never trimmed (~7 KB per fusion estimate); with the 3,000
  identity guard and the 3.4 MB fusion budget a heavy player eventually hits
  `storage_limit` for fusion. Compaction/sharding remains required before a public
  release.
- Suspension is automatic and silent apart from `identity_unavailable`; hatches made
  while suspended lose egg provenance once identity resumes.
- `encodedSize` matched Roblox for identity data in Studio; non-ASCII strings could be
  underestimated (the 3.8 MB ceiling leaves ~390 KB headroom).
- Locked/favorited fields have no setter yet; consent for Shiny/BIG/mutation donors
  remains a working default (BD-057).

> **2026-10-15: the ladder is now 6 / 3 / 2 with an any-pattern Gold ([90](90-fusion-ladder-v2.md)); counts below are history.**
>
> **2026-10-14 update:** donor counts are per recipe (15/4/2; 50/10/3 on 2026-10-13), odds normalize by the actual donor count N, `FusionService.MaxDonorIds` is 15: see [58](58-fusion-ladder-50-10-3.md).
