# 121 Per-dino auras and trails: migration design and phase 1 (BD-059)

Label: **OWNER DECISION 2026-10-16 (lead, owner's delegation) implemented as OFFLINE, flag-off phases 1-2 (phase 2 wires the shops, section 5).** No real profile was read or written. Sources: [46](46-pattern-fusion-dino-identity-and-cosmetic-progression.md), [49](49-identity-fusion-phase1.md), [53](53-bd064-fusion-server.md), [111 rollback drill](111-rollback-drill.md), [114](114-handbook.md), [115](115-decisions-log.md), [116](116-handbook-conflicts.md).

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

## 5. Phase 2 (BD-059): shop wiring behind the same flag
Label: CURRENT CODE BEHAVIOUR with `PerDinoCosmeticsEnabled = true`; default build and playtest profile keep it **false**. Offline tests only, no Studio or phone evidence.
- **Purchase**: `ProfileRepository.progressionAction` (same remote, same token) routes `buyAura/buyTrail/equipAura/equipTrail` to `CosmeticOwnership.apply` inside the existing `UpdateAsync`. The crystal charge and the sidecar grant are ONE write with the token's `recentOperations` record (exactly-once; a repeated token returns `duplicate`). Price and trail level rules are the same as `ProgressionRules.apply`. The outcome also stores `instanceId`.
- **Which dino**: the equipped stack (species + variant key) maps to ONE instance, the lowest instance sequence of that stack (`equippedInstanceId`). No instance or identity unavailable: refused with `no_dino_instance`; a purchase never silently becomes account-wide.
- **Equip**: only that dino's own plus legacy items (`not_owned` otherwise). A legacy item sets the account equip as today and clears this dino's own choice; equipping "" clears both so the account fallback does not reappear.
- **Reads**: `progressionView` (used by `ProfileRepository.progression` and the synced `ProgressionJson`/`EquippedAura`) shows own + legacy items and this dino's equipped choice, so the shops, "For: <dino>" cards and growth/speed multipliers need no client change. Nothing in `progression.auras/trails/equippedAura/equippedTrail` is written by a per-dino purchase (rollback view, Build 020 keeps the sidecar byte for byte, tested in `verify_rollback`).
- **Fusion confirm data**: with the flag on, `quoteFusion` and the `FusionAction` quote response carry `cosmeticNotice` (from `CosmeticOwnership.fusionNotice`: `irreversible`, `lostAuraIds`, `lostTrailIds`, legacy IDs kept). The Fusion Menu already lists each donor's cosmetics from `lossManifest` and requires consent; no new UI text.
- Open: when several identical dinos are stacked, the bound instance is the lowest sequence, which may not be the one the player thinks they hold (identical dinos are interchangeable until fused). Owner Studio check needed before flipping the flag.

## 6. Still not done
1. Optional voluntary legacy-to-dino move.
2. Studio and phone verification; owner decision to enable the flag.
Status lives only in [Kanban](07-kanban.md) BD-059.
