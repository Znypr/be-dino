# BD-057 Phase 1 handoff (WIP, not ready for PR)

Started in a claude.ai chat session on 2026-10-13. Continue in Claude Code.
Baseline: `50116b8` (`claude/be-dino-development` == `main` at start).
Toolchain used: Luau 0.741 (same as CI). Delete this file before opening the PR,
or fold its content into `docs/47-dinosaur-identity-foundation.md` / a new doc.

## Task (owner request)
Isolated, nonproduction, server-authoritative fusion: 10 distinct same-species,
same-egg-pattern Base dinosaur identities -> exactly one NEW Gold individual.
- Validate ownership, saved identity, species/pattern, protection, cosmetic-loss consent.
- Consume all 10; one new server-allocated ID; keep parent lineage + original egg refs.
- Success guaranteed once a valid transaction is accepted.
- Atomic, idempotent, safe for duplicate requests and failed writes.
- Ladder supports Emerald/Diamond without inventing recipe costs.
- Trait RNG boundary only; controlled test outcomes until BD-064 approves odds.
- No changes to production migration, legacy 50->Gold, real saves or paid features.

## Done so far (uncommitted work is in this commit)
1. `src/server/DinosaurIdentity.luau`
   - `reconcile` accepts fusion records only when backed by `state.fusions[operationId]`
     with matching `resultId`; otherwise `missing_fusion_ledger`.
   - Fused records sort first, so grouped surplus deletion spends legacy copies and
     fails closed (`protected_identity`) rather than deleting a fused output.
   - Eggs referenced by ledger `parentEggIds` are retained (lineage survives consumption).
   - `fusionRecord` bucketKey is now the plain stage bucket (`compy/gold`) as the grouped
     compatibility projection.
2. `src/server/IdentityFusion.luau` (new, pure):
   - `Recipes`: gold = 10 base donors approved; emerald/diamond have `donorCount=nil`
     -> `recipe_not_approved`. `GroupedProjection` gold/diamond only.
   - `quote(state, ownerKey, stage, donorIds)`: validates count, distinct, owner prefix,
     existence, stage, locked/favorited, saved pattern, species/pattern match; returns
     ingredient summary (no probabilities), itemized loss manifest (cosmetics + Shiny/BIG/
     mutation donors), `consentDigest`, `requestDigest`, `quoteDigest` (frozen snapshot).
   - `prepareOutcome(quote, roller, validateGenes)`: call once outside UpdateAsync; no
     roller -> `odds_not_approved`; schema-validates traits; pattern locked by recipe.
   - `apply(profile, ownerKey, request, outcome, now)`: copy-on-write. Ledger replay ->
     `duplicate` / `token_conflict`; recomputes quote -> `stale_quote`, `consent_required`;
     decrements grouped buckets per donor, +1 grouped target stage, allocates ID from
     `nextId`, builds record, removes donors, writes durable ledger, re-runs reconcile,
     byte preflight (`MaxSidecarBytes` 3.2 MB estimate) -> `storage_limit`.
   - `lineage(state, operationId)` for future Dino Details.
3. `src/shared/Config.luau`: `IdentityFusionPreviewEnabled = false`.
4. `src/server/ProfileRepository.luau`: `setFusionTestRoller`, `quoteFusion`,
   `fuseDinosaurs` gated on unpublished Studio memory profiles + flag + injected roller.
   No remote. `dinosaurDetails` adds `lineage` for fused records.
5. Harnesses: `verify_identity.py` boundary assertion updated to `missing_fusion_ledger`;
   `verify_progression.py` loads the new module. All existing Luau harnesses PASS.

## Remaining
- [ ] New `tools/verify_fusion.py` (pure module) covering: happy path (10 consumed, one new
      ID, nextId+1, grouped other buckets unchanged, input profile deep-unchanged, empty
      cosmetics, ledger + parent eggs retained); invalid donors (9/11, duplicate, missing,
      no pattern, wrong species/pattern/stage, locked, non-string); wrong owner; consent
      missing/wrong/correct; duplicate replay + token conflict; stale quote; overlapping
      concurrent fusion -> `donor_missing`; commit-then-throw retry; rollback on
      `storage_limit` / `invalid_outcome` / `odds_not_approved` / grouped mismatch;
      emerald/diamond `recipe_not_approved`; lineage after later hatches; legacy Gold
      decrement keeps fused record or fails closed; record without ledger rejected.
- [ ] Repository-level tests in `verify_progression.py` local section (flag on, test roller,
      outage, lease loss, duplicate confirm, reload keeps result + lineage).
- [ ] Add `verify_fusion.py` to `.github/workflows/build-generated-place.yml`.
- [ ] Run full suite incl. `python -m unittest discover -s tests -v`, `tools/build.py`.
- [ ] Docs: implementation + evidence, Kanban BD-057 status (In progress/Review, not Done),
      explicit "not Studio-verified" statement.
- [ ] Push `claude/be-dino-development`, open PR to `main` (never merge directly).

## Open design notes to confirm with owner
- Shiny/BIG/mutation donors require consent (treated as "valuable"); auto-fill policy is BD-065.
- `locked`/`favorited` flags block donors outright (no override); fields don't exist yet in UI.
- Byte budget is an estimate, not Roblox JSONEncode; Studio measurement pending.
