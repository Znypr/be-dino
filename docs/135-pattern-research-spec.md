# 135 Pattern research (BD-063) specification
n> **Status: PARKED (owner 2026-10-16).** Duplicates are already the input of the fusion ladder; no extra sink is planned now. Kept for reference only.

Status: **SPEC ONLY, NOT BUILT, NOT OWNER-APPROVED.** Nothing in this file is in code. [docs/46](46-pattern-fusion-dino-identity-and-cosmetic-progression.md) section "Targeted pattern research" lists three candidate options and says "select one with owner before implementation". [docs/115](115-decisions-log.md) has no decision on it, so the implementation step is blocked until the owner answers section 9. All numbers below are PROVISIONAL.

## 1. Problem
Ladder ([docs/90](90-fusion-ladder-v2.md)): Gold = 6 Base of one species (any pattern), Emerald = 3 Gold, Diamond = 2 Emerald, both same species AND same pattern. Gold fixes the pattern, so a player who wants a specific species+pattern Emerald depends on Gold luck. A rare species is very slow (Triceratops: about 253 / 2,063 / 5,612 casual runs for Gold / Emerald / Diamond, docs/90 section 3). Spare copies of the wrong pattern currently only feed Gold or sit unused. The owner asked for a nonrandom, earned-only sink.

## 2. Recommended option (owner must confirm): "Pattern Study" progress, no substitute donors
Of the three docs/46 candidates, recommend **A: same-species research bar**, because it needs no new currency or trait-bearing items and cannot be mistaken for a paid-random input:
* Per **species + pattern** cell, the account has a research counter (0..Target).
* The player "studies" spare dinosaurs of that **species** (any pattern other than the chosen one, or the chosen one when surplus): each study consumes ONE chosen instance and adds a fixed number of points to the chosen cell.
* When the bar is full, the cell is **Mastered**. Mastery gives a deterministic **recipe discount for that cell only**: the Emerald recipe for that species+pattern needs **2 Gold instead of 3** (never 0, never fewer donors than 2, Diamond unchanged). Mastery never creates a donor, a Gold, a trait, or odds weight.
* Points are fixed per study; no RNG, no Robux, no premium path, not tradable, not giftable.

Rejected for now: B (salvage into a material) adds a currency and a slot; C (objectives) is a larger separate system. Both stay in docs/46 as future ideas.

## 3. PROVISIONAL numbers (to be tuned by `tools/simulate_fusion_ladder.py` extension)
| Item | Value | Why |
| --- | ---: | --- |
| Points per studied Base dino | 1 | simple |
| Points per studied Gold / Emerald | not allowed | tiers are protected (section 6) |
| Target per cell (Mastered) | 12 | two Gold-recipes worth of Base donors (6 + 6), so study is a real sink but cheaper than finding the exact pattern 3 more times |
| Discount at Mastered | Emerald needs 2 Gold (from 3) | the only effect |
| Daily cap | none (cost is the dino itself) | no farming exploit, input is consumed |
Success check before building: casual median time to a Mastered-cell Emerald for a Common must drop but stay above Gold time; rare species must not become trivially cheap (simulate Triceratops).

## 4. Flows
1. Open Fusion Menu > Study tab (new, behind flag). Pick species, pick target pattern.
2. List shows eligible spares of that species with the exact result: "Study 5 dinos: +5 (7 of 12)". Quote shows before/after; server re-quotes on confirm.
3. Confirm with the same itemized irreversible-loss dialog fusion uses (protected dinos excluded, intentionally selected valuable ones itemized).
4. Server consumes the instances and adds points exactly once. Reconnect shows the saved bar.
5. On Mastered, the Emerald quote for that cell shows "2 Gold" and says why.

## 5. Data model (additive only)
* Reuse the identity sidecar (docs/47): add optional `dinosaurIdentity.research = { version = 1, cells = { ["<speciesId>:<patternId>"] = points }, applied = { [opId] = true } }` (applied ids capped at 64, oldest dropped). Absent field means 0 for everything. No existing field changes meaning, no schema version bump needed (readers ignore unknown fields; verify_rollback must show the old build loads a profile with the field).
* Pure module `ResearchLogic` (quote, apply, discount lookup) with no Roblox calls, same style as `IdentityFusion`.
* Server remote `ResearchAction` (quote / confirm), validated and rate limited like `FusionAction`; client sends instance ids and a species/pattern only, never points.
* Flag `Config.PatternResearchEnabled = false`, pinned false in default AND playtest profiles; with the flag off the remote refuses and the discount is ignored.

## 6. Edge cases
* Protected, equipped, cosmetic-owning, Shiny, BIG, mutated, Gold+ instances: excluded by default (same protection as fusion); only a Base with a rare trait can be added via the itemized warning.
* Instance already used in a pending fusion quote: reject (`busy`).
* Duplicate confirm / replay of opId: no-op (`already_applied`), exactly-once via `applied`.
* Points above Target are clamped; extra instances are not consumed (quote shows max useful count).
* Species or pattern removed later: cell is kept, ignored by reads.
* Studying the target pattern itself is allowed but the UI warns a Base of that pattern is also a Gold donor.
* Rollback: the field is ignored by older builds; a discounted Emerald already made stays valid. Disabling the flag stops new study and the discount.
* No lineage lie: studied dinos are consumed, not parents; the Emerald's parents are still the 2 Gold donors.
* Roblox paid-random policy: inputs are earned-only, no random outcome, so no random-item disclosure is needed; study of Robux-linked instances is excluded anyway.

## 7. Tests (when approved)
Luau: quote math and clamp; exactly-once with repeated opId; protected exclusion; flag off refuses and ignores discount; discount only for the mastered cell and never below 2 Gold; profile without the field loads unchanged; no consumption on failed validation; old-profile round trip. Python: simulator extension and `verify_*` for the flag pin in both profiles and the no new top-level local rule in `Bootstrap.client.luau`.

## 8. Not in scope
Substitute donors or vouchers, trading, Robux, daily caps, art/sound (assets need registry lines in docs/77 when added).

## 9. Open owner questions
1. Confirm option A (study bar, discount only) or choose B/C.
2. Is the reward "Emerald needs 2 Gold" acceptable, or should mastery give something else (cosmetic title, small stat)?
3. Target of 12 points per cell and 1 point per Base: ok, or different?
4. May a Base of the target pattern itself be studied?
5. Should Gold and higher be studyable at higher point values?
