# 121 Per-dino auras and trails: migration design and phase 1 (BD-059)

Label: **OWNER DECISION 2026-10-16 (lead, owner's delegation) implemented as an OFFLINE, flag-off phase 1.** Nothing here is wired to a shop, remote or UI, and no real profile was read or written. Sources: [46](46-pattern-fusion-dino-identity-and-cosmetic-progression.md), [49](49-identity-fusion-phase1.md), [53](53-bd064-fusion-server.md), [111 rollback drill](111-rollback-drill.md), [114](114-handbook.md), [115](115-decisions-log.md), [116](116-handbook-conflicts.md).

## 1. Decision
Auras and trails belong to ONE dino instance and are lost when that dino is fused (docs/46). Today purchases are account-wide in `profile.progression.auras` / `.trails` (+ `equippedAura` / `equippedTrail`); shops already say "For: <dino>" (BD-393). The identity sidecar (`dinosaurIdentity.instances[id].cosmetics = {ownedAuraIds, ownedTrailIds, equippedAuraId, equippedTrailId}`, docs/47) already has the per-instance field, so phase 1 adds **no new persisted field and no schema change**.

## 2. Phase 1 (this PR)
- `Config.PerDinoCosmeticsEnabled = false` (default build rule in `release_profiles.py` keeps it off).
- `src/server/CosmeticOwnership.luau`, pure: `legacy`, `usable`, `canEquip`, `grant`, `fusionNotice`. Not required by any service yet.
- Fusion already consumes every donor with its cosmetics and the output starts with none (docs/49). The quote's `lossManifest` already itemises each donor's aura/trail IDs and demands the `consentDigest`. `fusionNotice` turns that into one UI-ready record (`irreversible`, `lostAuraIds`, `lostTrailIds`, `legacyKept`, legacy IDs). No UI rollout.
- PolicyService, Robux, crystal prices, `CrystalPacksEnabled`, `PaidRandomItemsEnabled`: untouched.
- Test: `tools/verify_cosmetic_ownership.py` (in CI).

## 3. Legacy purchases: decision and why
**Option chosen: keep legacy account purchases account-wide ("grandfathered"), never reassign them, never consume them in fusion.** With the flag on, a dino may wear its own purchases plus every legacy one.
Rejected: "assign to the currently equipped dino". It guesses wrong (the equipped dino may be a throwaway), would silently take looks away from every other dino, and a later fusion of that one dino would destroy what the player paid for. It also needs a profile write per player, which cannot be proven safe offline. Keeping legacy account-wide means nobody loses anything they paid, and the migration is a pure read.
Consequence to confirm with the owner: legacy items remain usable by all dinos and are not subject to the "lost on fusion" rule; only purchases made after per-dino shopping ships are instance-bound. A later phase may let a player voluntarily move a legacy item to one dino (copy to instance, remove from account) with a confirm step.

## 4. Safety properties
| Property | How |
| --- | --- |
| Lazy | No pass over profiles. Ownership is computed when asked; the instance field is written only by a later shop phase on purchase. |
| Idempotent | `grant` of an owned item returns the same state (`already_owned`); reads are pure. |
| Rollback-safe | `progression.auras/trails` are never edited, so flag off or Build 020 reads exactly the legacy view; per-dino fields are inside the existing sidecar, which Build 020 preserves byte for byte and the sidecar reconciler already protects (docs/111, `protected_identity`). |
| No rewrite | Copy-on-write; tested that the input profile is byte-identical after `grant`. |
| Fusion | Consent still required when a donor owns cosmetics; output has none; account legacy sets unchanged (asserted). |

## 5. Next phases (not done)
1. Shop purchase writes `grant` inside the existing purchase `UpdateAsync` (needs owner review of price/Robux path; keeps PolicyService gating).
2. Equip validates with `canEquip` per instance; client reads per-dino state.
3. Fusion Menu shows `fusionNotice` (itemised irreversible-loss warning, docs/72 copy).
4. Optional voluntary legacy-to-dino move.
Status lives only in [Kanban](07-kanban.md) BD-059.
