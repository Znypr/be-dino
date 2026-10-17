# 149 Secret silly creatures: data and rules (BD-604, BD-228)

**Label: CURRENT BUILD BEHAVIOR = nothing changes (flag off). The rules below are LEAD decisions SS1 to SS6 ([115](115-decisions-log.md), owner delegated 2026-10-16), PROVISIONAL and overturnable.** Task: BD-604 (Review / test). Follow-up integration: BD-606 (Backlog). The owner asked for the creatures in BD-228 (drop method, rarity, class were open), BD-600 (parakeet) and BD-602 (fox).

## 1. What exists
`Config.SecretSpeciesEnabled = false`, **pinned OFF in the default and the playtest release profile** (`tools/release_profiles.py` `COMMON_RULES`, enforced by `tools/verify_release.py` on the source and on both built places). With it off nothing in the game differs: same egg rolls, same profiles, same Index. With it on **and a filled model slot** the game rolls, stores, hatches and lists secret species as below. All seven slots are empty today, so even `true` changes nothing a player can see except the Index cards.

| Id | Name | Class (SS5) | Drop weight (PROVISIONAL) | Model slot (`assetId`) | Test mesh, NOT bound (docs/77) |
|---|---|---|---:|---|---|
| chickosaurus | Chickosaurus | Ground | 20 | empty | v3 test mesh 108391746824463 (Game studio) |
| pigeon | Pigeon | Ground | 20 | empty | none yet |
| dodo | Dodo | Ground | 14 | empty | none yet |
| duck | Duck | Ground | 18 | empty | none yet |
| penguin | Penguin | Water | 12 | empty | none yet |
| budgiesaurus | Budgiesaurus | Fly | 10 | empty | 111728956844490 (v1) / 107910518074360 (v2): being redone |
| foxosaurus | Foxosaurus | Ground | 6 | empty | 119604460832523: outdated (glasses, beanie), being redone as a plain blue fox (BD-602, P3) |

## 2. The rules
- **Secret, not a tier (SS1).** `src/shared/SecretSpeciesConfig.luau` (pure data and rules). The seven are not in `Config.SpeciesOrder`, `SpeciesRarities`, `SpeciesDisplayNames` or `ChestSpeciesWeights`: the 22-species Index number, the odds text and the five tiers are untouched, and a secret never raises `metrics.rarest`.
- **The roll (SS2).** `RewardMath.computeChestReward(rng, eggCount, origin)`. Only the two earned-egg call sites in `ProfileRepository` pass an origin: `"run"` (`commitRunSettlement`) and `"nest"` (`rollNestEggs`, free nests). The crystal shop, the legacy claim fallback and everything else pass none and can never roll. With the flag on and an eligible origin the roll comes **after** the normal species and quantity draws: one draw decides a hit (`Secret.Chance = 0.005`, flat), a hit takes one more draw to pick a secret by weight among the secrets whose model slot is filled. If no model is ready the roll does nothing at all (no draw, no field).
- **Egg metadata (SS2).** `reward.secretRollVersion = "bd228-secret-v1"` on every egg that went through the roll, and `reward.secretSpeciesId` on a hit. The normally rolled species stays in `reward.speciesId`, so an older reader sees a valid egg. About 45 bytes per egg, only while the flag is on and a model is ready.
- **The hatch.** `applyHatch` swaps in the secret only when the flag is on, the egg is not a failed Cracked egg (that roll is lost), the roll version matches and the model slot is still filled (`Secret.resolve`). It creates the collection entry lazily (`{base, gold, diamond, events, variants}`) the first time, then credits it like any species (copies, variants, identity, discovery). `metrics.rarest` is not raised.
- **Reveal (SS3).** The ribbon line under the name reads "Secret" (no percent), the colour and sound are tier 5 (calm Legendary, nothing extra). Eggs that carry a secret reveal last in their batch. The client never auto-skips an unknown species (BD-525), so a secret is always shown.
- **Index (SS4).** With the flag on, 7 secret cards follow the 22 in the same grid (24 per page: two on page 1, five on page 2). Hidden: "???" name, "Secret" line, a silhouette only if a model exists, else a plain "?". Found: the normal card with the Secret line. A gold line "N / 7 secrets found" sits under the list. "Collected X of 22" does not count secrets.
- **Not yet (BD-606).** A secret cannot be equipped or mutated by request (`knownSpecies` is still the normal 22), so no profile ever stores a secret id in `equippedSpeciesId` or `reward.speciesId`. That is what keeps Build 020 able to load every profile (RB1).
- **Fusion.** By instance id, any species: six Chickosaurus fuse to a Gold Chickosaurus in the test.

## 3. How to make a secret species real (checklist for the model task)
1. Generate the mesh (shared low-poly v3 style, solid eyes, `docs/77` line `secret_dino_*` goes from pending to in game).
2. Add the `LowPolyDinoAssets` entry and the `ScaleLadder` row (size rule, docs/115 SZ1 to SZ3), with the same class as the secret row.
3. Put the asset id in the species row `assetId` in `SecretSpeciesConfig` (`verify_secret_species` fails if a filled slot has no registry entry of the same id and class).
4. Studio: Index card, hatch line, the Compy-sized dino beside the others.
5. Owner flips `SecretSpeciesEnabled` for a private test (a release decision; it is pinned off in both profiles until then, so also relax the pin on purpose).

## 4. Evidence
`python tools/verify_secret_species.py --runner <luau>` (in CI), real modules on the Luau runner:
- flag-off identity: a golden hash over 16,000 `computeChestReward` rolls taken from the unmodified module, equal with no origin, with `"run"`, with `"nest"`, and also with the flag ON while every slot is empty; `SecretSpeciesConfig` is never required with the flag off;
- no roll for `shop`, `crystal_shop`, `gift`, `paid`, `robux`, legacy, mis-spelled or non-string origins (18 cases), and none for 200,000 origin-less rolls, even at a 100% chance with every slot filled; the random source is not touched;
- flat 0.5%: 975 hits in 200,000 run rolls and 982 in 200,000 nest rolls (allowed 858 to 1142 = 4.5 sigma), 485 / 100,000 for 1-egg runs and 468 / 100,000 for 400-egg runs (no run-size effect); species split follows the weights; only ready secrets drop;
- the real `ProfileRepository` on the mocked DataStore: flag off writes nothing secret; flag on with empty slots gives byte-identical egg digests; filled slots record the roll on 400 of 400 eggs, hatch into a lazy collection entry, keep `metrics.rarest`, sort last, work for nests, never for a crystal-shop egg; an emptied slot or a turned-off flag hatches the normal species; six secret donors fuse to Gold;
- RB1: the frozen Build 020 reader loads a profile with secret egg metadata and a secret collection entry, keeps every field byte for byte, hatches a secret-tagged egg as its normal species, and the current build reloads the result.
Mutation checks (a removed model gate, a shop origin, a chance that grows, a raised `rarest`, a flag-less hook) each fail the verifier.
**Not verified:** the Index cards and the hatch line in Studio or on a phone, any model, the real 0.5% with players.

## 5. Policy
Run and nest eggs are earned for free; the crystal shop and any Robux route never roll a secret (docs/43). The chance is disclosed nowhere yet: before the flag is ever turned on in a build that has any paid or Robux-linked route to eggs, the odds copy (`OddsCopy`, `ShopOdds`) must still say what a shop egg can be (it never can be a secret), and a Roblox policy review stays a release gate (`PaidRandomItemsEnabled`).
