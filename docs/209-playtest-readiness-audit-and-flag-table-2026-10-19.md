# 209 Playtest readiness audit and flag table (2026-10-19)

Label: **CURRENT BUILD BEHAVIOR, offline audit.** Written 2026-10-19 on `origin/main` `d1325ba0` (after PR #544) by a read-only audit agent. Nothing was published, uploaded or changed in Roblox, Studio or Creator Hub. No flag, id or profile was changed. The default profile (Build 020 mirror) is untouched. Offline evidence only: nothing here was run in Studio, on a phone, on a published server or against a real DataStore. The owner's click list is [182](182-publish-pack-friends-playtest.md) section 0 and its new section "Changes since 2026-10-18".

Plain summary: the playtest build passes every offline gate. No flag that must stay off is on. Five switches deserve a yes from the owner before friends join (section 2.2). Details, the full flag table, the data-safety check and the problems found follow.

## 1. Gate results (all offline, `origin/main` `d1325ba0`, Windows, pinned Luau runner)

| Gate | Command | Result |
| --- | --- | --- |
| Build the playtest place | `python tools/build.py --profile playtest` | built `BeDino-Build020-playtest.rbxlx`, 486 scripts; one known warning (the six inert Robux product ids still listed in Config, see 2.4) |
| Freshness | `python tools/playtest_freshness.py build/BeDino-Build020-playtest.rbxlx` | "built from d1325ba0 ... up to date", exit 0 |
| Dry-run release | `python tools/release_playtest.py --dry-run` | 185 of 186 steps passed in 19.8 minutes (gates, both builds, both verify_release runs, session-1 smoke, 178 CI commands, unit tests). The one failed step, "working tree still clean after the run", was this audit's own uncommitted docs; the first gate (clean tree, HEAD on origin/main, CI green on this commit, BD-004 ids, no streaming, no paid flag) passed. Proposed tag `playtest-m1-b020-r1` (not created), rollback target NONE YET (first publish) |
| verify_release, default | `python tools/verify_release.py` | passed, 41 keys enforced |
| verify_release, playtest | `python tools/verify_release.py --profile playtest` | passed, 45 keys enforced (same product warning) |
| Session 1 smoke | `verify_session1_smoke` (inside the dry run) | passed, 148 of 148 checks, 0 static problems, DataStore 2,147 writes, 0 throttled |
| Switch-on | `verify_switch_on.py` | passed: every off flag is rehearsed or excluded (12 excluded with a reason), paid line closed |
| All-on rehearsal | `run_rehearsal.py --profile all-on-rehearsal` | 175 passed, 0 failed (every CI verifier against the playtest Config with all built-but-off flags on; Robux and test switches stay off) |
| Rollback | `verify_rollback.py` | passed, 360 checks (Build 020 reader against a profile written by the current code) |
| Profile golden | `verify_profile_golden.py` | passed, 181 steps, stored profile byte for byte |
| Robux line | `verify_robux_line.py` and `--selftest` | passed (3 mutations caught): crystal-only products, flags off, PolicyService and odds gates present |
| Paid random gate | `verify_paid_random_gate.py` | passed: truth table and wiring |
| Load, playtest flags | `verify_load.py --gate-playtest` | passed: 12 players 400-egg burst peaks at 53 percent of the write budget on the busiest store, 0 throttled |

## 2. The flag table

"Default" is the Build 020 mirror (also what CI builds). "Playtest" is what the friends get. Every row below differs between the two, except section 2.3 (on in both) and 2.4 (off in both). Verdicts: **safe for friends**, **needs owner OK**, **must stay off**.

### 2.1 Differs between default and playtest (23 values)

| Flag | Default to playtest | What it does, in one plain line | Owner doc | Verdict |
| --- | --- | --- | --- | --- |
| `ReleaseProfile` | development to playtest | A label only; the Fusion button opens the new Fusion menu, never the old page | [55](55-playtest-release-runbook.md), [157](157-playtest-profile-newest-features.md) | safe for friends |
| `ProfileDataStoreName` | `BeDino_PrivateTest_v1` to `BeDino_Playtest_M1_v1` | Friends save into a fresh store; no Build 019/020 profile is read or written | [55](55-playtest-release-runbook.md), [111](111-rollback-drill.md) | safe for friends |
| `IdentityPersistentEnabled` | off to on | Every dino gets a saved identity (where it came from, its parents); stored in an extra profile field | [49](49-identity-fusion-phase1.md), [53](53-bd064-fusion-server.md) | **needs owner OK** (with the next row) |
| `IdentityFusionPreviewEnabled` | off to on | The Fusion menu: put copies in, get one stronger dino back; inputs are used up; odds are placeholder numbers | [90](90-fusion-ladder-v2.md), [155](155-fusion-ladder-source-vs-docs-audit.md), [43 policy](43-player-access-and-paid-random-policy.md) | **needs owner OK** (random result, destroys dinos; fine for friends only because nothing is bought with Robux) |
| `WorldArtMode` | Legacy to BiomeKit | New trees, rocks and landmarks | [68](68-world-art-on-and-potion-catalog.md) | safe for friends (falls back to plain models if Mesh/Image APIs are off) |
| `WorldArtDensity` | 1 to 1.25 | More props (about 3,500, under the 8,000-part limit) | [68](68-world-art-on-and-potion-catalog.md) | safe for friends (phones unmeasured, BD-085) |
| `FoodArtMode` | Legacy to Kit | Food looks like berries, fruit, eggs, amber | [68](68-world-art-on-and-potion-catalog.md) | safe for friends |
| `LowPolyDinos` | off to on | The new low-poly dino models; each species falls back to the old look if a load fails | [107](107-offline-mobile-budget.md) | safe for friends |
| `CaveHub` | off to on | The cave hub with the shop stalls and the Sanctuary | [104](104-cave-hub-design.md), [125](125-friends-playtest-go-no-go.md) addendum | safe for friends |
| `ClassMovementEnabled` | off to on | Class feel: glide, dash, class walk speed | [115](115-decisions-log.md) BD-423 | safe for friends |
| `RunTelemetryEnabled` | off to on | The server prints anonymous run counts to its log (see 2.5) | [122](122-session-telemetry.md), [167](167-reference-and-playtest-tools.md) | safe for friends |
| `PlaytestFeedbackEnabled` | off to on | The "Tell us!" button, bottom-left; faces and 140 characters, filtered, no names logged | [128](128-playtest-feedback.md) | safe for friends |
| `ObjectivesEnabled` | off to on | Goals and daily tasks; the first three starter goals; free crystals and XP as rewards (placeholder numbers) | [66](66-intake-mini-objectives.md) | safe for friends |
| `CombatEnabled` | off to on | Dinos fight with bites and hearts instead of the instant bigger-eats-smaller rule; calm wild predators | [101](101-hp-combat-classes-animations.md), [157](157-playtest-profile-newest-features.md) | **needs owner OK** (never tried on a phone or by two real players; replaces how predation works; the handover doc 198 still says "combat stays off", see 4) |
| `SpecialFoodsEnabled` | off to on | Rare golden drumsticks and similar foods with bonus points (placeholder points) | BD-207, [157](157-playtest-profile-newest-features.md) | safe for friends |
| `PerDinoCosmeticsEnabled` | off to on | A dino can own several auras and trails bought with crystals and switch between them; fusing destroys them (a warning is shown) | [121](121-per-dino-cosmetics-migration.md) | **needs owner OK** (spends earned crystals; irreversible loss on fusion; the default rule says "owner Studio check" first and none was done) |
| `FastTravelPerk` | off to on | A crystal perk to travel to the shops (placeholder price, no Robux) | [115](115-decisions-log.md) D22 | safe for friends |
| `GeneBoostEnabled` | off to on | Patterns and colours give up to +15 percent growth and +7 percent walk speed, computed on the server | [186](186-pattern-colour-indexes-and-slower-species.md) s6 | safe for friends (placeholder numbers) |
| `FoodLayerEnabled` | off to on | The designed food map (3,600 foods in small clusters) | [187](187-food-map-grid-and-smart-test-bot.md) | safe for friends (pace not seen by a human yet, BD-575, BD-1076; some foods may sit in rocks, BD-1098 is fixed in #541) |
| `FoodRespawnTiersEnabled` | off to on | Rich foods come back slowly (amber 120 s, drumstick 150 s) so one food cannot be farmed | [194](194-studio-test-bot-and-pace-numbers.md) | safe for friends |
| `PatternColourIndexEnabled` | off to on | The Patterns and Colours tabs of the Index, "New!" ribbons, a red dot on the Dinos button, the "Boost N of 5" hatch line | [186](186-pattern-colour-indexes-and-slower-species.md) s7 | safe for friends (plain tinted tiles, no pattern art yet) |
| `ShopPromptBubbleEnabled` | off to on | A speech bubble above each cave stall with the key E (X on a gamepad) | [180](180-shop-and-npc-interaction-design.md) | safe for friends |
| `SecretSpeciesEnabled` | off to on | Nine silly secret creatures can hatch from free eggs (flat 0.5 percent per egg); never from shop eggs | [149](149-secret-species.md), [173](173-secret-roster-bind.md) | **needs owner OK** (the cockatoo and the eagle are placeholder models the owner has not accepted; the chicken is a "test mesh") |

The rows marked **needs owner OK** are four switches here (Combat, Secret species, Fusion with its pair, Per-dino cosmetics); the fifth is the movement guard of section 2.3. Together they are the five of section 2.2.

### 2.2 The five switches that need the owner's yes

| # | Switch | Why ask | What happens if the owner says no | How to switch it off |
| --- | --- | --- | --- | --- |
| 1 | `CombatEnabled` | Fights replace the old "bigger eats smaller" rule. Never played by two real people or on a phone (BD-252, BD-316). A broken bite would remove hunting for everyone. | Instant predation like Build 020; the calm wild predators go too. | One rule in `tools/release_profiles.py` (`_flag_off`), rebuild. |
| 2 | `SecretSpeciesEnabled` | Two secret models (cockatoo, eagle) are lead placeholders; the chicken is the old test mesh. Friends may see them. | Secrets cannot hatch; Index shows nothing new. | One rule, rebuild. |
| 3 | `IdentityPersistentEnabled` + `IdentityFusionPreviewEnabled` | Fusion destroys the dinos you put in and gives a random result; odds are placeholder numbers; it writes a new saved field. No Robux is involved, so the paid-random rules do not apply. | Fusion button says "coming soon" (as in the default build). | Two rules, rebuild; saved data stays untouched. |
| 4 | `PerDinoCosmeticsEnabled` | Friends spend crystals on auras and trails that are lost in a fusion; nobody has looked at it in Studio. | The old shared cosmetics stay. | One rule, rebuild. |
| 5 | `MovementGuardWindowEnabled` (on in BOTH profiles) | An anti-cheat with guessed margins (jitter 0.3 s, slack 6 studs, BD-611). With real lag, dash, glide or a potion it may pull an honest friend back. | Cheaters could move faster than normal. | One line in `src/shared/Config.luau` (`false`), rebuild. Watch `movement_rejects` in the telemetry. |

### 2.3 On in BOTH profiles (not release rules)

| Flag | What it does | Verdict |
| --- | --- | --- |
| `AdminPanelEnabled` | Owner panel (F2) and the FOOD counter, see 2.5 | safe for friends (only the experience creator can use it) |
| `AdminUserIds` | Empty list: no extra admins | safe for friends (keep it empty) |
| `StudioLocalProfilesEnabled`, `StudioTestWalletEnabled` (and `StudioTestCrystals` 1,000,000) | Test wallet and local profiles. The server uses them only when `RunService:IsStudio()` and `game.GameId == 0` (unpublished Studio). A published server has a real GameId, so they do nothing | safe for friends (guards checked in `ProfileRepository.luau` line 40, `ProfileShop.luau`, `GiftService.luau`) |
| `NpcPredatorsEnabled` | Calm wild predators; only works while Combat is on | follows Combat |
| `MovementGuardWindowEnabled` | The sliding speed check | **needs owner OK** (switch 5) |
| `WriteBudgetEnabled`, `WriteFairShareEnabled` | Protect the save store from write floods | safe for friends |
| `WorldGeneratedMeshes` | Loads the owner's generated meshes; a failed load keeps the kit model | safe for friends |

### 2.4 Required OFF in the playtest build (all are off; `verify_release` enforces it)

| Flag | Why it stays off | Verdict |
| --- | --- | --- |
| `CrystalPacksEnabled`, `PaidRandomItemsEnabled` | Robux and paid random items ([43](43-player-access-and-paid-random-policy.md)). The six pack products still exist in the experience but the owner confirmed all six are off sale (BD-612 stays open as a code gap: a receipt would still be honoured, but nothing can be bought) | **must stay off** |
| `AutoOpenRequiresPass` | Locks a setting behind a Robux pass | **must stay off** |
| `GiftingEnabled`, `AdminGiftsEnabled`, `GiftClaimEnabled` | Gifting: the Robux sender is not built, the admin sender is an owner switch | **must stay off** |
| `DinoSkinsEnabled` | No skin models exist | **must stay off** |
| `ChestTestGrantEnabled`, `CollectionTestGrantEnabled`, `MutationTestSetupEnabled` | Free test grants (the remotes are not even created while off) | **must stay off** |
| `SecurityTestHarnessEnabled`, `ArtTestHarnessEnabled`, `QaOverlayEnabled`, `DemoDirectorEnabled`, `DuplicateSettlementProbe` | Debug, art, QA and demo tools | **must stay off** |
| `HatchV2`, `HatchV2Preview` | The paint-bucket hatch uses a placeholder model | **must stay off** |
| `FoodPickupAtMouth`, `PredationAtMouth` | They change the egg pace; the owner keeps the pace until a human run is measured (BD-527, MR6) | **must stay off** |
| `StreamingEnabled` (Workspace) | Needs the BD-502 gates | **must stay off** |

Nothing in 2.4 is on in the playtest build (read from the built place by `verify_release`, 45 keys enforced).

### 2.5 The specific questions

- **Admin panel and the "Admin food slider".** Visible only to a player the server marks `IsAdmin` (the panel is not even built for anyone else). The server decides in `AdminRules.isAdmin`: the experience creator (user `znyprs`, creator id of the place), or rank 255 of a group creator, or a user id in `Config.AdminUserIds` (empty), or an unpublished Studio test. The collaborator alt `Znyprr` is NOT an admin. Every request is re-checked on the server (`AdminService.handle`, 0.15 s limit, ranges clamped), so a friend who edits the client can open nothing. **Weather forcing** (`startWeather`, `stopWeather`) is one of those server-checked actions; the Studio round saw it work because in unpublished Studio every player counts as admin. In the published game only the owner can call it. One thing to know: the sliders (Food worth, Growth speed, Run speed, Mutation chance) change the whole server, not only the owner. Do not touch F2 while friends play, or their eggs and pace will not be honest. The FOOD counter on screen follows the same rule (Studio or admin, not on touch).
- **"Tell us!" feedback button.** Visible to every friend on purpose. It sends three face answers and up to 140 filtered characters, at most once per 2 minutes. No name or user id is logged.
- **Test chests, `TestGrants`, `StudioLocalProfiles`.** The three test-grant flags are off and the remotes do not exist while off. The Studio-only flags are inert on a published server (2.3).
- **Telemetry.** What the server prints: run length, eggs, end reason, hatches, shop and fusion counts, movement set-backs, "rate limited" counts, script errors (with player names scrubbed), a random per-server id. No user id, no name, no profile data. It also sends a custom event with the player to Roblox's own analytics (`AnalyticsService:LogCustomEvent`); that is the normal Roblox dashboard count, not our log. The friends do not need to be told more than "we count runs".
- **Secret species flag.** See switch 2.
- **GeneBoost, FoodLayer, FoodRespawnTiers, PatternColourIndex, ShopPromptBubble, CaveHub, per-dino cosmetics:** rows in 2.1. The first six are safe; per-dino cosmetics is switch 4.

## 3. Data safety (offline proof)

1. **The playtest store is not the live store.** Build 019/020 and the default profile use `BeDino_PrivateTest_v1` (2 keys on the Creator Hub page). The playtest build uses `BeDino_Playtest_M1_v1`, set from `Config.PlaytestProfileDataStoreName`, checked by `verify_release` against the built place. Leaderboards (`<store>_<board>_v1`) and the Gifts store derive from the profile name, so they follow. These are the only three `GetDataStore` calls in `src/`. Nothing in the playtest build can read or write the live store.
2. **New additive profile fields are versioned and old readers ignore them.** `progression.discovered` (discovery log, now also accent colours): add-only, backfill is idempotent, a junk value is tolerated (`verify_rollback` asserts byte-identical after a Build 020 load, claim, renew and release). `profile.settings.indexSeen` (seen count for the Index dot): written only when above 0, clamped to 0 to 1,000, inside the settings table that already has a version field `v`; Build 020 keeps unknown settings keys (listed as accepted in [111](111-rollback-drill.md) s4). Starter goals are rows of `profile.objectives` (`v = 1`; created only by a first real mutation while the flag is on; a newer `v` is never read or reordered; a corrupt value reads as empty). `schemaVersion` is unchanged at 1.
3. **Rolling back cannot corrupt a profile.** Every `UpdateAsync` runs `isValidProfile` first and cancels the write on failure; a defaults profile is only created when the stored value is exactly `nil`. `verify_rollback` (360 checks) runs the real current repository and a frozen Build 020 reader on one mock store, in both directions. Two lock-out classes exist (Epic or Legendary catches and post-Build-020 potion ids make Build 020 refuse the profile), but Build 020 reads another store, so friends cannot meet them. First publish: there is no previous playtest build to roll back to, so the drill uses two Roblox versions of the same file. A broken playtest store is fixed by rotating the name (`_v1` to `_v2`), never by editing profiles.
4. **Honest limits.** A real Creator Hub restore, real DataStore versioning and a published revert are not covered (BD-320 stays the owner's drill). Roblox says "Restore" alone does not publish; the Studio publish after Restore is in [182](182-publish-pack-friends-playtest.md) section 5.

## 4. Real problems found

| # | Finding | Severity | What was done |
| --- | --- | --- | --- |
| 1 | Questionnaire answer for Paid Random Items may be out of date; Roblox lists the experience as non-compliant for Australia, Belgium, Brazil and UK (under 18) and the Netherlands, so some friends could be blocked | P1 (owner check) | Row BD-1136; step in [182](182-publish-pack-friends-playtest.md) s9.4. Nothing changed |
| 2 | Admin sliders (Food worth, Growth, Run speed) change the whole server. If the owner moves one while friends play, their eggs and pace change and the pace numbers are polluted | P2 | Row BD-1137; the rule "do not touch F2 while friends play" is in 182 s9.3. Access to the admin tools is safe (2.5) |
| 3 | Five switches ship on without the owner having said yes to them one by one (2.2) | P1 (owner decision) | Row BD-1138; step 0 in 182 s9.4 |
| 4 | `MovementGuardWindowEnabled` is on in BOTH profiles with guessed margins. The docs ([145](145-session1-readiness-2026-10-17.md), BD-611) say "measure first"; the learned rule 11 of [160](160-agent-brief.md) says a limit-weakening setting does not ship without measured margins (this one tightens, so the risk is honest players being set back) | P2 | Covered by BD-611 and the report line "Set back by the anti-cheat" (`playtest_report.py`); in switch 5 |
| 5 | [198](198-handover-2026-10-18.md) said "combat itself stays off"; the playtest profile sets `CombatEnabled` on (docs/157 NF1) | doc | Fixed in this PR |
| 6 | [157](157-playtest-profile-newest-features.md) had one update line (BD-1081) twice | doc | Fixed in this PR |
| 7 | BD-004 text says the id slot is not filled (it is, BD-1030); docs/125 s2/s3, docs/145 s3, docs/148 and docs/55 differ from later owner decisions | doc | Row BD-1139; [182](182-publish-pack-friends-playtest.md) s8 already lists the older mismatches |
| 8 | Phones are allowed (Devices Phone and Computer) but nobody has measured a phone (BD-085, P0 Backlog); the new Index tabs, bubbles and small-window layouts are offline-proof only | known | Already open: BD-085, BD-1085, BD-1004. Tell friends phones are experimental |
| 9 | A pace number from a real child is still missing (BD-575): the bot gets 6 to 7 times the target. The designed food map and slow respawn were tuned only with the bot | known | Already open: BD-575, BD-1076, BD-1093. The first session is the measurement |
| 10 | BD-612: the code would honour a pack receipt although the flag is off; safe only because all six products are off sale (owner confirmed 2026-10-18, seen read-only by the lead) | known | Already open: BD-612. Keep the packs off sale |

**No verify fails on current main. No flag that must stay off is on. No P0 found.**

## Handbook check
Plain words in the owner parts; no game code, flag, id or profile changed; paid lines stay off; nothing was published; the verdict on every flag is a recommendation, the owner decides. Mismatches are named with both sources.
