# 111 - Rollback drill (BD-320): offline results and owner steps

**Status: OFFLINE ONLY.** `python tools/verify_rollback.py --runner <luau>` runs the real current
`ProfileRepository` and a frozen copy of the Build 020 reader against ONE mocked DataStore. It proves
validation and transaction logic. It does **not** prove a real publish revert, real DataStore versioning,
Studio behaviour or a phone. BD-320 stays open until the owner performs the steps in section 3.

## 1. What was compared

- **OLD reader** = Build 020 = commit `a9edf8e` ("Promote tested Build 020 integration"). The seven files it needs
  (`ProfileRepository`, `RewardMath`, `ProgressionRules`, `ProgressionConfig`, `Config`, `EggGenetics`, `EggTraits`)
  are frozen unmodified in `tools/fixtures/build020/`. They are test fixtures, never packaged into a place.
- **CURRENT** = this branch with the **playtest profile flags** (`IdentityPersistentEnabled` and
  `IdentityFusionPreviewEnabled` on), because that is the data-richest case.
- Sample profile written by CURRENT code: 86 hatched dinosaurs with identity sidecar, one Gold fusion with a
  6-parent ledger, `settings` with `peaceful=true` / `teleportShops=false`, run egg bank (545), egg nests, queue,
  settled-run list.

## 2. Results (all asserted in `verify_rollback`)

| Case | Result |
| --- | --- |
| Build 020 loads a CURRENT profile (settings, peaceful, teleportShops, sidecar, fusion ledger, nests, bank) | Loads. **Unknown fields are preserved byte-for-byte** (every write is an `UpdateAsync` of the whole table), also after Build 020 renew, claim and release |
| Roll forward again after a Build 020 session that hatched an egg | Loads. The sidecar is reconciled to the changed grouped counts; no instance is lost (or identity is suspended, never emptied) |
| Same code, identity/fusion flags turned off | Loads. Sidecar, fusion ledger and settings untouched. Flags on again: reconciled |
| Build 020 profile read by CURRENT code (no settings, no peaceful, no sidecar, no rarityScale) | Loads. Settings read as defaults; **no defaults are written back**; all counts, crystals, queue and operation log kept; `rarityScale` added once |
| `metrics.rarest` 4 or 5 (an Epic or Legendary species was caught) | **Build 020 fails closed (`SchemaError`, no write).** The player is locked out until roll-forward. See risks |
| Potions added after Build 020 in `progression.potions` or an active loot buff | **Build 020 fails closed**, same as above |
| `emerald` counters, `progression.shop`, `revealSkip`, nest `weatherId`, extra settings keys, unknown nest fields | Build 020 accepts and preserves them |
| Future `schemaVersion`, missing `schemaVersion`, missing `collection` / `recentOperations`, `eggs` as a string, truncated JSON string, number or `false` stored as the value, unknown equipped species, negative crystals, eggNests / runEggBank / pendingNests over their structural ceilings | Both readers: `SchemaError`, and **the stored value is byte-identical afterwards**, including after `commitRunSettlement`, `setSettings`, `renew` and `release` on the unloaded player |
| DataStore outage on a new player | `LoadFailed`; **no defaults profile is written**. Existing player: `LoadFailed`, stored profile untouched; recovers when the store returns. Failed mid-session saves leave the last committed profile intact |
| Live lease held by another server | `SessionBusy`, no write (both readers). An expired lease from the other build is taken over (no permanent lock) |
| **Corrupted `profile.settings`** (string, number, boolean, array, junk keys, out-of-range volumes) | **FIXED in this PR.** CURRENT used to reject any non-table value as `SchemaError` (lock-out over a cosmetic field). Now it loads, the UI reads valid defaults, load and renew leave the stored value alone, and the next normal settings save replaces it. Build 020 ignores the field |

**Where "never overwrite unreadable data" is enforced:** every `UpdateAsync` transform in `ProfileRepository.luau`
runs `isValidProfile` first and returns `nil` (which cancels the write) on failure. The only place a defaults
profile is created is `load` when the stored value is exactly `nil`. A DataStore error throws before any write and
ends as `LoadFailed`.

## 3. Owner steps for a REAL rollback

Nothing here is automated, and the repo never runs these against a live store.

**Pick the right target.** Roll back to the **previous playtest tag** (`playtest-m1-bNNN-r(K-1)`, runbook section 6),
not to Build 020. The default profile of every build, Build 020 included, uses store `BeDino_PrivateTest_v1`. The
playtest profile uses `BeDino_Playtest_M1_v1`. A Build 020 place would simply not see playtest progress (everyone
looks reset, nothing is deleted), and players with Epic/Legendary catches or newer potions would be locked out of the
store it does read.

1. **Stop the damage.** Creator Hub: set the experience to Private, or shut down all servers (runbook section 8, step 1).
2. **Republish the previous known-good place.** Either Creator Hub, Places, Version History, **Restore** the
   version recorded in the release record; or `git checkout <prev tag>`, `python tools/build.py --profile playtest`,
   check the manifest `place_sha256` against the release record, publish. Then **Shut down all servers** so no
   server runs the bad build. Mixed old and new servers are safe for data (one lease owner per profile) but confusing.
3. **Flags.** `IdentityPersistentEnabled`, `IdentityFusionPreviewEnabled`, `CrystalPacksEnabled` and
   `PaidRandomItemsEnabled` are `Config.luau` constants baked in per profile build (`tools/release_profiles.py`). They
   cannot be flipped at runtime. To switch only fusion/identity off, change the profile rule in a PR, rebuild, republish.
   The sidecar stays untouched while off (tested). **Never** turn the two paid flags on during a rollback.
4. **Check.**
   - Join with a test account that has `settings` saved and, if possible, `metrics.rarest >= 4` (Epic caught).
     Expect `ProfileState = Loaded` on the previous playtest tag. On a Build 020 target expect `SchemaError` for the
     Epic account: that is the documented fail-closed behaviour, not data loss.
   - Developer Console / Output: count `[Be Dino] ... attempt N failed` warnings, `SchemaError`, `SaveFailed`,
     `LeaseLost`. A spike after the rollback means the target cannot read the stored data: go to step 5.
   - Confirm the version label and `place_sha256`, append a **rollback** row to the release record.
5. **Players still locked out (`SchemaError`)?** Prefer **rolling forward** to a fixed build. If impossible, rotate the
   store (runbook section 8, step 4: increment `PlaytestProfileDataStoreName`, tag, publish). The old store stays as
   evidence.
6. **Restoring one DataStore key (last resort, one tester, owner decision).** Roblox keeps older **versions** of each key
   for a limited time (documented as 30 days; confirm in the current Roblox docs). In Studio with API Services
   enabled, on a scratch place using the same universe's store, with the player offline and no live lease:
   `DataStore:ListVersionsAsync(key)` to list versions, `DataStore:GetVersionAsync(key, versionId)` to read one,
   and compare. **Write it to a different key first** (for example `u:<id>:restore`) and inspect it. Only then, after
   an explicit owner decision, write it back to `u:<id>` with `UpdateAsync` (not `SetAsync`) so the lease check still
   applies. Do not use `RemoveAsync`. Note the key, version id, date and reason in the release record. Data Stores
   Manager in Creator Hub can also view and edit single keys.
7. **Roll forward** after the fix: publish the new tag, repeat the checks, append the record row.

## 4. Fields added since Build 020 and their rollback behaviour

| Field (profile) | Written by | Build 020 behaviour |
| --- | --- | --- |
| `settings` (`v`, `sound`, `effects`, `weather`, `calm`, `jumpSize`, `peaceful`, `teleportShops`) | BD-264/288, docs/101 | Ignored and kept. CURRENT reads missing or corrupt as defaults |
| `rarityScale` = 5 | BD-044/rarity tiers | Ignored and kept |
| `metrics.rarest` 4-5 | species tiers Epic/Legendary | **Build 020 rejects (> 3)** |
| `revealSkip` (tiers 1-5) | BD-044 | Ignored and kept |
| `runEggBank`, `eggNests` (nests v2, `weatherId`), `nests`, `pendingNests`, `settledRuns` | BD-044/090/156 | Ignored and kept. Build 020 cannot claim bank or v2 nests, so those eggs wait for roll-forward |
| egg fields `kind`, `source`, `traitRollVersion` `bd045-genes-v2` | BD-044/045 | Ignored by validation; Build 020 can claim such queue eggs (tested) |
| `dinosaurIdentity` sidecar (`instances`, `eggs`, `fusions` ledger with `parentIds`, `parentEggIds`, `nextId`, `ownerKey`, `suspendedReason`) | BD-060/064/057 | Ignored and kept. Build 020 edits grouped counts only, so the sidecar can go stale; CURRENT reconciles on the next load, or suspends identity without deleting it |
| `collection[species].emerald` | fusion ladder | Ignored and kept (a Build 020 player cannot use Emerald) |
| `progression.shop` | BD-051 | Ignored and kept |
| `progression.potions` / `buffs` with ids added after Build 020 (loot, uncommon, epic) | BD-051, docs/68 | **Build 020 rejects unknown potion ids** |
| `equippedVariantKey` | BD-150 | Ignored and kept |
| low-poly / culling / world-kit settings | client only, **not persisted** | Nothing to roll back (no attribute or profile field) |

`ProfileSchemaVersion` is still 1 everywhere. All changes are additive, which is why most data survives a rollback. The
two exceptions above come from Build 020 validating values (`rarest <= 3`, known potion ids) rather than from new keys.

## 5. Risks and open items

1. **Epic/Legendary and new-potion lock-out on Build 020** (BD-354). Fail-closed is safe but unusable. This only
   matters for rollbacks past the tiers/potion work, which the previous-playtest-tag rule avoids.
2. A rollback target older than the playtest profile reads a **different store**: progress looks reset until roll-forward.
3. Build 020 operating on a new profile can desync the sidecar from the grouped counts. Reconcile handles it (tested
   once, for a claim). A bigger desync could suspend identity features for that player until counts match again.
4. Eggs in the run bank and v2 nests are not claimable by Build 020, and a fusion result is only a grouped count there.
5. When the next playtest tag is published, its reader becomes the real rollback target: vendor it into
   `tools/fixtures/` and extend this drill (BD-355).
6. Not covered offline: Roblox DataStore throttling and size (4 MB value limit; `IdentityProfileHardLimitBytes`
   guards the sidecar), real version restore, Studio, devices.
