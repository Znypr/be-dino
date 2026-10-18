# 155 Fusion ladder: source versus docs audit (BD-617, 2026-10-18)

Status: **audit only, no `src/` change.** Written for BD-617 after the remote audit ([151](151-remote-audit-2026-10-17.md) F7) named a "6 / 3 / 2 fusion ladder" and a still-wired 50-copy `MutateSpecies`. Checked against `origin/main` at commit `41859285`. Conflicts are in [116](116-handbook-conflicts.md) section J (C-47 to C-51, Q20 to Q22). I decided no number here: the **OWNER TARGET** is the ladder stated in [AGENTS.md](../AGENTS.md) line 44, which is quoted below.

## 1. The owner target, as the repository file states it
AGENTS.md line 44 (the file in the repository, not a copy pasted into a session): "2026-10-15 owner decision supersedes 15/4/2 (and 50/10/3 before it) ... Gold = 6 Base of the same SPECIES (any pattern; the Gold keeps the most common donor pattern, ties -> smallest pattern id), Emerald = 3 Gold and Diamond = 2 Emerald, both same species + same pattern; [docs/90](90-fusion-ladder-v2.md) ... older [docs/58](58-fusion-ladder-50-10-3.md), [docs/57](57-fusion-ladder-options.md) are history". Decision D4 and lead rule L2 in [115](115-decisions-log.md), handbook [114](114-handbook.md) s9 and BD-335 (Done) say the same.

**Stale premise found (C-47).** The brief for this audit said AGENTS.md has "15 Base / 4 Gold / 2 Emerald (2026-10-14)". That is the text of an OLD copy of AGENTS.md that is injected into an agent's context at session start. The file on `origin/main` was corrected on 2026-10-15/16 and names 6/3/2. Agents must read the file in their worktree, not the injected copy.

## 2. What the SOURCE does today (main)
- **New path (live behind a flag): 6 / 3 / 2.** `src/server/IdentityFusion.luau:21-23` (`donorCount` 6, 3, 2; `Version = "bd057-ladder-6-3-2"` at :12; `MaxDonorCount = 6` at :26). The client mirror `src/shared/FusionSelection.luau:14-16`, the goal HUD `src/shared/NextGoal.luau:9-11`, the remote cap `FusionService.MaxDonorIds = 6` (`src/server/FusionService.luau:14`) and `Identity.MaxFusionParents = 6` (`src/server/DinosaurIdentity.luau:180`) agree. Parity is asserted by `tools/verify_fusion_ui.py:482-491`, `tools/verify_fusion.py:524-527`, and `tools/simulate_fusion_ladder.py:295-296`. **All of this matches the owner target.**
- **Legacy path (live, ungated): 50 Base to Gold, 50 Gold to Diamond.** `src/shared/Config.luau:278-279` (`GoldMutationCost = 50`, `DiamondMutationCost = 50`), `src/server/MutationService.luau:35-39` (the `MutateSpecies` remote and handler), `src/server/ProfileCollection.luau:115-123` (`mutateSpecies`: source stage `base` for Gold, `gold` for Diamond). It has no Emerald step, no odds, no consent, and no lineage ledger ([151](151-remote-audit-2026-10-17.md) F7).
- **The client contradicts itself.** `src/client/Bootstrap.client.luau:967` tells the player "6 Base to Gold; 3 Gold to Emerald; 2 Emerald to Diamond", while the same panel spends `Config.GoldMutationCost` / `DiamondMutationCost` (50) at :981 and :1001 and fires `MutateSpecies` at :1008 ("CONFIRM FUSION"). The button at :998 reads "PATTERN FUSION: 6 -> NEW GOLD" and opens the new menu.

## 3. Which flags gate which path (`tools/release_profiles.py`)
| Path | Flag | default profile | playtest profile | Notes |
|---|---|---|---|---|
| New: `FusionAction` answers, Fusion Menu opens | `IdentityFusionPreviewEnabled` | pinned OFF (`release_profiles.py:132`) | set ON (`:154`) | Also needs an unpublished memory profile or `IdentityPersistentEnabled` (`src/server/ProfileFusion.luau:49`); the playtest profile sets that ON. The remote object exists in both, but answers `fusion_disabled` when off (`FusionService.luau:112, 140`). |
| Legacy server: `MutateSpecies` remote | **none** | LIVE | LIVE | `MutationService.start` creates and serves it unconditionally. A `rg MutateSpecies` over `src/` finds no flag check. |
| Legacy test setup: `TestSetMutationCopies` | `MutationTestSetupEnabled` | pinned OFF (`release_profiles.py:103`, COMMON) | pinned OFF | Gates only the setup remote, not `MutateSpecies`. |
| Legacy client panel (Fusion page with 50 cost) | none; `FusionSelection.navTarget` (`FusionSelection.luau:953-957`) | reachable: FUSION nav opens it when the flag is off (probe says `disabled`, profile is `development`) | not reachable from the nav (new menu wins) | An exploiter in the playtest build can still fire the remote by hand ([151](151-remote-audit-2026-10-17.md) F7). |

## 4. Every place that states or implements a ladder number, or the legacy path
Status values: **matches** = equals the owner target (6/3/2, Gold keeps plurality pattern). **legacy** = an old number or path, correctly labelled history or intentionally kept. **conflicting** = presented as current, or live code that behaves against the target.

### 4.1 Source and tools
| Where (file:line) | Value | Status |
|---|---|---|
| `src/server/IdentityFusion.luau:12, 21-23, 26` | 6 / 3 / 2, version `bd057-ladder-6-3-2` | matches |
| `src/shared/FusionSelection.luau:14-16, 560, 828` | 6 / 3 / 2; copy "6 Base, 3 Gold or 2 Emerald", tab sub "6 Base" | matches |
| `src/shared/NextGoal.luau:9-11` | 6 / 3 / 2 | matches |
| `src/server/FusionService.luau:14`, `src/server/DinosaurIdentity.luau:180` | max 6 | matches |
| `src/client/FusionMenu.luau:4, 47, 214` | slot grids 3x2, 3x1, 2x1 (6 / 3 / 2); count read from the recipe | matches |
| `src/client/Bootstrap.client.luau:967, 998` | text "6 Base to Gold ..."; "PATTERN FUSION: 6 -> NEW GOLD" | matches (text), but see :981 |
| `src/client/Bootstrap.client.luau:981, 1001-1008` | cost 50 from `Config.*MutationCost`, `fuse:FireServer` to `MutateSpecies`, Gold to Diamond with no Emerald | **conflicting** (C-48, C-49) |
| `src/shared/Config.luau:278-279` | `GoldMutationCost = 50`, `DiamondMutationCost = 50` ("provisional balance") | **conflicting** (C-48) |
| `src/server/MutationService.luau:35-39` | `MutateSpecies` remote, ungated | **conflicting** (C-48) |
| `src/server/ProfileCollection.luau:115-145` | Base 50 to Gold, Gold 50 to Diamond | **conflicting** (C-48) |
| `tools/verify_progression.py:210-227` | asserts 150 Base to 100 after one Gold, then a Diamond from 50 Gold | legacy (tests the legacy path, passes) |
| `tools/remote_fuzz_cases.luau:106, 386-392` | 20 parallel `MutateSpecies`, "with 50 copies make exactly one Gold" | legacy |
| `tools/remote_fuzz_cases5.luau:197`, `tools/profile_golden.luau:237-242`, `tools/verify_remote_fuzz.py:55` | fire / name `MutateSpecies` | legacy |
| `tools/verify_fusion.py:524-527, 671-680`; `tools/verify_fusion_ui.py:86-88, 381-394, 482-491`; `tools/fusion_ui_smoke.luau:481` | 6 / 3 / 2 assertions | matches |
| `tools/verify_fusion.py:299, 392` | synthetic `donorCount = 6` and `10` in odds fixtures | legacy (N for odds math only, harmless; label it) |
| `tools/simulate_fusion_ladder.py:2-5, 200, 204, 295-296` | v2 6 / 3 / 2, and a CI assert that `IdentityFusion` is 6/3/2 | matches |
| `tools/simulate_fusion_ladder.py:10-14, 43` | docstring says "DEFAULT scenario = ... 15 / 4 / 2"; `GOLD_DONORS = 15`, CLI default `--gold-donors` | **conflicting** (C-51): the docstring contradicts its own first paragraph; the 15 only feeds the `--legacy` model |
| `build/*.rbxlx` (Build017, Fusion, Hatch3, Latest, UI) | contain the old `MutateSpecies` client and server | legacy (generated place files, not edited) |

### 4.2 Docs
| Where (file:line) | Value | Status |
|---|---|---|
| `AGENTS.md:44` | 6 / 3 / 2, 15/4/2 and 50/10/3 struck as history | matches (the owner target) |
| `docs/90-fusion-ladder-v2.md:3-40` | 6 / 3 / 2, any-pattern Gold | matches |
| `docs/114-handbook.md:297`; `docs/115-decisions-log.md:11, 43, 85`; `docs/116-handbook-conflicts.md` C-7; `docs/125:53`; `docs/135:7`; `docs/96:36-52`; `docs/113:24`; `docs/145:185` | 6 / 3 / 2 | matches |
| `docs/03-game-design.md:35, 41`; `docs/46-pattern-fusion-dino-identity-and-cosmetic-progression.md:13-25` | 10, 15/4/2 or 50 shown struck or marked HISTORICAL beside the 6/3/2 line | legacy (correctly labelled) |
| `docs/57-fusion-ladder-options.md:5-6, 219-235`; `docs/58-fusion-ladder-50-10-3.md:3, 5, 14, 23`; `docs/49:7-9`; `docs/53:180-182`; `docs/54:14-16` | 15/4/2 or 50/10/3 under a SUPERSEDED / "counts below are history" banner | legacy (correctly labelled) |
| `docs/54-bd065-fusion-menu.md:20, 94` | "15 same-species + same-pattern Base dinos ... All 15 are consumed" in the body | legacy (the banner at :14 covers it; low risk) |
| `docs/57:235` | "`--check` (CI) asserts the recipes in `IdentityFusion.luau` are 15/4/2" | legacy, wrong about the tool: `simulate_fusion_ladder.py:296` asserts 6/3/2 |
| `docs/52-fusion-remote-contract.md:28-29` | "1..15 strings ... 15 for Gold, 4 for Emerald, 2 for Diamond" stated as the live contract, no banner | **conflicting** (C-50): code accepts at most 6 |
| `docs/67-ui-fixes-fusion-eggs-icon.md:10` | menu title "Pattern Fusion: 15 Base -> 1 NEW Gold" | **conflicting** (C-50): no banner; the menu says 6 |
| `docs/89-catch-rate-4.md:31` | "Gold = 15 Base of the same species + pattern", "ladder ... needs an owner review" | **conflicting** (C-50): the review happened (docs/90) |
| `README.md:45` | "50 Base to 1 Gold and 50 Gold to 1 Diamond ... private-test prices" in the feature table | **conflicting** (C-50): reads as current |
| `docs/34-studio-handoff.md:65`; `docs/20-gold-mutation-test.md:7-10`; `docs/15-economy-simulation.md:18, 53`; `docs/28-ui-overhaul.md:20`; `docs/61:27, 90`; `docs/02:30`; `docs/08:28` | 50 Base / 50 Gold, Build 010 to 020 era | legacy (era documents; docs/20, 02, 61 carry no banner, so add one line) |
| `docs/13-persistence-remote-contracts.md:62` | `MutateSpecies` listed as a current contract row | legacy (true until BD-617 is done) |
| `docs/04-architecture.md:25` | "mutateSpecies" in the client intent list | legacy |
| `docs/07-kanban.md:115` | 6 / 3 / 2 | matches |
| `docs/07-kanban.md:216, 223, 224` | rows still lead with "Consume 10 ...", "manual 15/4/2-donor selection", "2026-10-14 owner ladder: 15/4/2"; a "Board audit 2026-10-16" note says historical | legacy (annotated; wording is confusing but not wrong) |
| `docs/07-kanban.md:560, 600-613, 675` | 50 Base / 50 Gold evidence from Build 020 | legacy (evidence of that build) |
| `docs/07-kanban.md:998` (BD-335) | Done: 6/3/2 chosen, "fix any doc still saying 15/4/2" | matches; this audit lists what the fix missed |
| `docs/07-kanban.md:1207` (BD-617) and `docs/151:21, 39, 100, 135` | the legacy path is still wired | matches the finding |

## 5. What this means
1. The **new** fusion path, its tests and its menu all say 6 / 3 / 2. There is no 15/4/2 left in any `src/` file or active verifier except the `simulate_fusion_ladder.py` docstring and its `--legacy` default.
2. The **legacy** 50-copy path is the one real conflict. It is live in every profile, bypasses the flag that gates all other fusion, skips Emerald, and the client panel advertises 6/3/2 while charging 50. In the default (development) build the FUSION nav button opens exactly that panel, because the flag is off there. In the playtest build only a hand-fired remote reaches it.
3. Five docs still present an old number as current (README, 52, 67, 89, plus one wrong statement in 57). None of them is a decision; each is a missed update.

## 6. Recommended minimal fix list (not done here; BD-617 stays Backlog)
Ordered smallest first. Items 1 to 3 touch `src/` and are for a separate PR; no number is chosen by any of them.
1. **Close the hole first:** make the `MutateSpecies` handler refuse (a one-line early return with `LastMutationStatus = "fusion_moved"`) whenever `IdentityFusionPreviewEnabled` is on, and keep its tests by running them with the flag off. This is the option BD-617 already names.
2. **Fix the contradicting panel:** either remove the CONFIRM FUSION button and the "fusion" / "fusionConfirm" pages (`Bootstrap.client.luau:977-1010`), or stop it reading `Config.*MutationCost`. Then delete `GoldMutationCost` / `DiamondMutationCost` (or rename them `Legacy...`) and the `verify_progression.py`, `remote_fuzz_cases*.luau`, `profile_golden.luau` cases in the same change. Needs the answer to Q21.
3. **Make `DinosaurIdentity.reconcile` respect locked and favorited dinosaurs** (BD-617 second half).
4. **Docs, no owner input needed:** add a SUPERSEDED line to `docs/52` (:28-29, change the cap to 6), `docs/67` (:10), `docs/89` (:31), `README.md` (:45) and one-line banners to `docs/20`, `docs/02`, `docs/61`; fix `docs/57:235`.
5. **Tool text:** rewrite the `simulate_fusion_ladder.py` docstring (:10-14) to say the 15/4/2 text belongs to `--legacy`, and rename `GOLD_DONORS` (:43) to `LEGACY_GOLD_DONORS`.
6. **Process:** add one line to AGENTS.md "Picking numbers" or the handbook: "the AGENTS.md text injected at session start can be days old; read the file in the worktree before quoting a number" (C-47).

**Outcome 2026-10-18 (BD-617, Review / test, offline evidence only).** Items 1 to 3 are done in one change: the `MutateSpecies` remote and the old Fusion pages are removed (not just refused), so the audit's section 3 table row "Legacy server" and "Legacy client panel" no longer exist; `DinosaurIdentity.reconcile` protects locked and favourited dinosaurs. The repository transaction `mutateSpecies` and the two cost numbers stay as unreachable LEGACY code so the golden session keeps its bytes ([115](115-decisions-log.md) NF4 to NF6). Items 4 and 5 were done by BD-630. Item 6 (C-47) stays in [160](160-agent-brief.md) section 1.

## 7. Owner questions (copied to [116](116-handbook-conflicts.md) section J)
- **Q20** Confirm the ladder is still 6 Base (same species, any pattern) / 3 Gold / 2 Emerald, as AGENTS.md line 44 says. Options: (a) yes, no change; (b) change it (say the numbers).
- **Q21** What happens to the old 50-copy `MutateSpecies`? Options: (a) remove the remote and the old panel (recommended by BD-617); (b) keep it behind a new flag that is pinned OFF, as a test tool only; (c) keep it as a separate player feature.
- **Q22** If (b) or (c): may it still turn 50 Gold into a Diamond without an Emerald, or must Diamond come only from 2 Emerald? (Target text says Emerald before Diamond.)

## 8. Checks run
`python tools/verify_doc_ids.py`, `python tools/verify_handbook.py`, `python tools/verify_kanban_merge.py --base origin/main --head HEAD`; results are in the PR. No Studio, no `src/` edit.
