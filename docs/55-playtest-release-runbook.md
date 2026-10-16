# Milestone 1 private playtest: release, load/device and rollback runbook

**Status 2026-10-13: tooling and procedure prepared; owner publish pending.** Covers
BD-004 (private place record), BD-019 (device/load) and BD-020 (private release and
rollback) in [Kanban](07-kanban.md), which alone owns their status. Nothing in this
document has been published to Roblox. The offline load results below show how
ProfileRepository transactions and DataStore budgets behave. They are **not** device,
frame-time or live-DataStore evidence.

Owner decisions this follows: Milestone 1 is a **private playtest that includes fusion**,
in a **new private experience with a fresh, empty DataStore**. **All Robux and
paid-random features stay off.** Target devices are **desktop and one Android phone**.

## 1. Release configuration (`--profile playtest`)

`python tools/build.py` is unchanged. It still produces the development build
`build/BeDino-BuildNNN.rbxlx`, which CI checks and uploads. This file and its manifest are **generated and not committed** (ignored since BD-419, so merges no longer conflict on them); regenerate locally with `python tools/build.py` or download the CI artifact `BeDino-current-build`.

`python tools/build.py --profile playtest` packages the same sources and rewrites a few
values in the **generated** Config only. `src/` is never modified. The output goes to
`build/BeDino-BuildNNN-playtest.rbxlx` (git-ignored), with a manifest that records the
profile, `git_commit`, `git_dirty`, the overrides applied and any warnings. If a rule
fails, no place is written.

`python tools/verify_release.py --profile playtest [--place FILE]` re-checks the
packaged Config inside the `.rbxlx` and the manifest's `place_sha256`. It refuses a
place that was built from a dirty tree (`--allow-dirty` is for rehearsals only).
CI runs `verify_release.py --profile default` after every build. Once the
BD-004 IDs are recorded, CI also builds, verifies and uploads the playtest place as
the `BeDino-playtest-build` artifact.

All rules live in **one place**, [`tools/release_profiles.py`](../tools/release_profiles.py):

| Key | Default build | Playtest build | Why |
|---|---|---|---|
| `PaidRandomItemsEnabled`, `CrystalPacksEnabled` | must be `false` | must be `false` | No Robux and no paid-random items ([43](43-player-access-and-paid-random-policy.md)) |
| `CollectionTestGrantEnabled`, `ChestTestGrantEnabled`, `MutationTestSetupEnabled` | must be `false` | must be `false` | No debug grants in any build that could be published |
| `SecurityTestHarnessEnabled`, `ArtTestHarnessEnabled`, `DuplicateSettlementProbe` | must be `false` | must be `false` | Test harnesses and probes |
| `ReleaseProfile` | must be `"development"` | **set** `"playtest"` | Marks the generated place |
| `ProfileDataStoreName` | ≤50 chars | **set** from `PlaytestProfileDataStoreName`, must match `BeDino_Playtest_<Tag>_v<N>` | Isolated playtest store |
| `PlaytestUniverseId`, `PlaytestPlaceId` | 0 or an ID | **must be positive** | BD-004 record (see §2) |
| `IdentityPersistentEnabled`, `IdentityFusionPreviewEnabled` | must be `false` | **set** `true` | BD-064 persistent identities + fusion ([53](53-bd064-fusion-server.md)); on only in the generated playtest place |
| any key defined twice | error | error | A later duplicate key in a Luau table literal would silently win |

- **Safety flags are required, never patched.** If a test grant is left on in source,
  the release stops. It is not quietly switched off.
- **Studio-only flags** (`StudioLocalProfilesEnabled`, `StudioTestWalletEnabled`) may stay
  `true`. The server only honours them when `RunService:IsStudio() and game.GameId == 0`.
  `verify_release` fails if that guard disappears from `src/server`.
- **`DeveloperProducts`** still lists six Robux products that belong to the *old* experience.
  They have no effect in the new one. Purchase prompts are hidden while
  `CrystalPacksEnabled=false`, and random crystal eggs/condition upgrades stay blocked
  while `PaidRandomItemsEnabled=false`. **Do not create developer products or game passes
  in the playtest experience.**
  - Emptying the table would make the random crystal egg shop available as a crystal-only
    (non-Robux) feature. That is an **owner decision** and is not part of this profile.
- **Adding a future release key** (for example a BD-064/065 fusion or menu flag): append
  one `Rule(...)` to `PROFILES["playtest"]`. Use `missing="warn"` until the key reaches
  main, then `"error"`.

## 2. BD-004: where the private experience IDs are recorded

When the new experience exists, the owner (or an agent working from the owner's message):

1. Sets `PlaytestUniverseId` and `PlaytestPlaceId` in [`src/shared/Config.luau`](../src/shared/Config.luau).
   They sit right after `ProfileDataStoreName` and are marked `TODO(BD-004)`. Get the
   values from either:
   - **Creator Hub → Creations → the experience**: the URL and Overview show the
     *Universe/Experience ID*; **Places → start place** shows the *Place ID*.
   - **Studio** with the published place open: run `print(game.GameId, game.PlaceId)` in
     the command bar.
2. Adds a row to the **release record** (§6) with both IDs.
3. Updates **BD-004** in [Kanban](07-kanban.md) to Done, citing that commit.

Until then, `verify_release.py --profile playtest` and `build.py --profile playtest` fail
with `PlaytestUniverseId = 0: must be a positive integer Roblox ID (TODO(BD-004) ...)`.
The legacy private test experience from [42](42-live-multiplayer-test.md) (universe
10769812255 / place 111259822927673) is **not** the Milestone 1 place.

DataStores are scoped per experience, so the new experience starts empty whatever the
store name is. The playtest store name (`BeDino_Playtest_M1_v1`) gives a reset lever
*within* that experience (§8). Leaderboard OrderedDataStores derive their names from
`ProfileDataStoreName`, so they reset with it.

## 3. Pre-release gates (all must be true for the tagged commit)

**Code and CI**
- [ ] The milestone PRs are merged to main with their own Review/test evidence: BD-044
  reward loop, BD-053/054 movement and Android touch, BD-064 fusion server and
  persistent identities, BD-065 Fusion Menu.
- [ ] GitHub Actions *Build generated Roblox place* is green on the exact commit: binding
  checks, `verify_sources`, every `verify_*` runner including `verify_load`,
  `measure_identity_storage --check`, `build.py`, `verify_release --profile default`, all
  unit tests and the playtest build/verify step.
- [ ] `python tools/verify_release.py --profile playtest --place build/BeDino-BuildNNN-playtest.rbxlx`
  passes on a clean checkout of the tag, and so does
  `python tools/verify_load.py --runner <luau> --gate-playtest` (persistent identities + fusion on).
- [ ] The known-issues list (§7) is written, and no open P0 issue remains (data loss,
  duplication, security, cannot play).

**Studio checks** (playtest `.rbxlx` opened as an **unpublished** file first: GameId 0, memory-only profiles)
- [ ] The version label reads the expected `BUILD redesign-NNN`, and the HUD/attribute
  `ProfileMode` reads *Studio preview (not saved)*.
- [ ] In the command bar: `require(game.ReplicatedStorage.Shared.Config).ReleaseProfile == "playtest"`,
  `ProfileDataStoreName` is the playtest name, and both paid flags are `false`.
- [ ] Explorer search for `qa`, `probe`, `TestGrant` and `shop-multiplayer` finds no stray QA
  scripts. `tools/qa/*` is never packaged; also check nothing was pasted in by hand.
- [ ] Full loop: sanctuary → run → settle → sequential egg reveals → collection → fusion
  (10 → Gold) through the Fusion Menu → rejoin.
- [ ] **Test → Clients and Servers** with 2, then 4, then 8 clients (§9 matrix): no
  `SaveFailed`, `LeaseLost` or `SchemaError`, and no Output errors.

**Android checklist** (one physical phone, live private experience after the publish below)
- [ ] Record device model, Android version, RAM, Roblox app version and network (Wi-Fi/mobile).
- [ ] Landscape: joystick, jump, leap and camera usable. HUD buttons do not overlap the
  joystick or system bars. Shop, collection, Fusion Menu and egg reveal are scrollable
  and readable.
- [ ] A 20-minute session with at least 3 runs and a 15+ egg reveal batch: note frame
  rate (Developer Console via `/console` in chat → Memory; Roblox Settings → Performance
  Stats where available), heat and battery drop.
- [ ] Background the app for 60 s and resume. Switch between Wi-Fi and mobile data. Kill
  and rejoin: the profile loads (a `SessionBusy` message may appear for up to 90 s, then
  must clear).
- [ ] The desktop client and the phone share one server: they see each other and
  rewards stay isolated.

## 4. Owner steps: publish to the private experience (Studio / Creator Hub)

Only the owner does these steps. Agents never publish.

1. **Create the experience** (first release only): in Studio, open the playtest
   `.rbxlx`, then **File → Publish to Roblox As… → Create new experience**. Name it e.g.
   *Be Dino! Playtest*, under the owner account. Record the IDs (§2), commit them, let
   CI pass, then continue from step 3 with a place rebuilt from that commit.
2. **Access and settings** (Creator Hub → the experience → *Configure*, and Studio →
   *Game Settings*):
   - *Audience / Access*: **Private**, or **Limited → Playtesters only**, inviting named
     testers ([42](42-live-multiplayer-test.md) shows the earlier flow). **Friends
     unchecked** unless intended. Not public.
   - Complete the *content maturity questionnaire* truthfully for this build. An unrated
     experience is unplayable for others.
   - *Devices*: Computer and Phone. Tablet and console are untested.
   - *Places → Max players*: **8** for the first sessions. 12 maximum, which is what the
     load harness covers.
   - *Security*: **Enable Studio Access to API Services** only in this playtest
     experience, and only while you deliberately test Studio against the real playtest
     store. Live servers use DataStores regardless. Studio sessions with it on write to
     the real playtest store, so prefer unpublished files for routine checks. Allow HTTP
     Requests off. Third-party sales/teleports off.
   - *Monetization*: **no developer products, passes or subscriptions**. Paid flags stay
     false in source.
3. **Build from the tag** (§6): use the `BeDino-playtest-build` CI artifact for the tagged
   commit, or run `git checkout <tag> && python tools/build.py --profile playtest`. Then
   run `verify_release --profile playtest --place …` on it.
4. **Publish**: open that exact `.rbxlx`. Check the `ReleaseProfile` command-bar line from
   §3. Then **File → Publish to Roblox As…** and pick the *existing* playtest experience
   and start place (not the legacy experience). Note the new version number in Creator
   Hub → Places → *Version History*.
5. **Restart servers**: Creator Hub → *Restart servers for updates*, or *Shut down all
   servers* for a hard cut.
6. **Smoke test live**: owner desktop plus one invited tester (or alt) join one server.
   Check the version label, `ProfileMode` *Persistent*, an empty starter profile, one run
   with settlement and reveal, then leave and rejoin. Then run the Android checklist.
7. Fill in the release record (§6). In Kanban, mark BD-020 with the evidence, and
   BD-019 with the device/load results.

## 5. Load and device testing (BD-019)

### Offline harness: `python tools/verify_load.py --runner <luau>`

The harness runs the **real, unmodified** `src/server/ProfileRepository.luau` and its
dependencies in Luau with:
- a virtual clock and cooperative coroutines;
- a mocked DataStore with 60–310 ms latency, 2% 1.5–3 s spikes, a 1% transient error rate
  (exercising the repository's retries) and a 10% chance that UpdateAsync re-runs the
  transform;
- a per-server **UpdateAsync-class budget of 60 + 10 × players requests per minute**,
  modelled as a refilling bucket with a FIFO throttle queue of 30.

Two servers share one store, so players can hop between them. Simulated players join,
run, collect map crystals (64 crystals with 90 s respawn), settle runs (15% send a
duplicate end-run), reveal every egg at the 5 s cadence, equip, buy potions, hop servers
and leave. The run takes about 2 s, and CI runs it on every push.

Results on main Build 020 + this branch (2026-10-13):

| Scenario | Requests (A/B) | Peak 60 s window / accrued budget | Throttled | Failed ops | Notes |
|---|---:|---:|---:|---:|---|
| **8 players, 15 min** (gated) | 720 / 101 | 80 / 140 (57%) | 0 | 0 | 884 transforms for 808 writes, 13 transient errors retried, 2 server hops, all eggs drained, all leases released |
| **12 players, 15 min, playtest flags** (persistent identities + fusion; BD-044 payout; `--gate-playtest`) | 996 / 87 | 90 / 180 (50%) | 0 | 0 | profile 64 KB after 15 min, key writes <=10/min and <=475 KB/min (the pre-BD-044 payout reached 528 KB and 4.7 MB/min) |
| **12 players, 15 min** (gated) | 1064 / 116 | 99 / 180 (55%) | 0 | 0 | max profile 14.9 KB; per-key ≤12 writes and ≤160 KB per minute |
| 12 players each revealing a 15-egg batch | 627 / 42 | 167 / 180 (93%) | 0 | 0 | absorbed by the bucket; little headroom |
| 12 players each revealing a 150-egg batch | 2634 / 33 | 181 / 180 (101%) | 0 | 0 | sustained at the budget for about 13 min; any extra writes would queue |
| 8 players + 1 client spamming equip at the 0.5 s cooldown | 898 / 50 | 164 / 150 (109%) | 0 | 0 | one client alone uses about 90 writes/min, roughly 60% of the server budget |

Analytic BD-044 projection, with all players revealing at once at one UpdateAsync per
egg every 5 s, plus renewals and maximum crystal pickups: 8 players need 155/min against
140 (110%), and 12 players need 211/min against 180 (117%). A 150-egg batch keeps that
up for 12.5 minutes.

What this means:
- **Build 020 as shipped fits comfortably** at 8–12 players, at about 55–60% of budget.
  The biggest traffic sources are map crystal pickups (one UpdateAsync each, up to about
  43/min server-wide) and lease renewals (2/min per player).
- **Recommendation for BD-044 (reward loop):** do not keep "one UpdateAsync per revealed
  egg" for 15–150 egg batches. Commit the run's egg outcomes in the settlement write.
  Then either reveal them client-side from the committed outcomes, or claim them in
  batches (e.g. one write per 10 eggs or per 30 s). The 150-egg case otherwise has zero
  headroom.
- **Risk for all write remotes:** the per-remote cooldowns (equip 0.5 s, progression
  0.4 s) still let one client issue about 90–150 writes/min. Equip toggling and
  aura/trail equips are free to repeat. A per-player write budget in ProfileRepository
  (for example ≤10 writes/min sustained, with bursts) would stop one client from starving
  everyone else's saves. That file belongs to other workstreams, so this is a follow-up,
  not part of this change.
- The harness counted many same-key writes less than 6 s apart (reveals every 5 s, plus
  pickups). Current Roblox limits are expressed as per-key throughput (well within limits
  here). The older 6-second same-key guidance is reported only as information.
- **Not modelled**: OrderedDataStore leaderboard writes (separate budgets), `GetAsync`,
  MessagingService, physics, replication, frame time, memory and real DataStore latency.
  `measure_identity_storage` separately shows identity sidecars reach the 4 MiB key limit
  well before 10,000 dinosaurs, which BD-064 must cap.

### Manual device/load matrix

Record build/tag, place version, device, client count, duration, result and evidence
link for every row.

| # | Where | Clients | Scenario | Pass evidence |
|---|---|---|---|---|
| L1 | Studio Test → Clients and Servers (unpublished) | 2 | Full loop on both. Same-pickup race. Predation between them | One grant per pickup. One terminal outcome. No Output errors |
| L2 | Studio Clients and Servers | 4 | 10 min, everyone runs, reveals and fuses | No SaveFailed/LeaseLost. Server Output shows no throttle warnings |
| L3 | Studio Clients and Servers | 8 | 15 min (PC permitting); open the Developer Console on server | Server heartbeat, memory and DataStore budget (`DataStoreService:GetRequestBudgetForRequestType` in the server command bar) noted every 5 min |
| D1 | Live private experience | desktop + Android | Android checklist (§3) on one server | Checklist complete with screenshots |
| D2 | Live | 3–5 real players | 20–30 min observed session | No P0. Rejoin keeps all rewards. Same-server isolation |
| D3 | Live | 1 | Rejoin within 90 s after a crash or kill | `SessionBusy` clears. No duplicate or lost reward |
| D4 | Live, non-owner | 1 | Latest creature/egg/UI assets visible to a non-owner tester | Screenshots. No fallback where an asset is expected |

## 6. Versioning, tagging and the release record

- Tag name: **`playtest-m1-bNNN-rK`**, e.g. `playtest-m1-b021-r1`. Use an annotated tag on
  the main commit whose CI is green. K increments for each republish of the same build.
  The owner creates and pushes tags: `git tag -a playtest-m1-b021-r1 -m "..." && git push origin playtest-m1-b021-r1`.
- Publish only a place whose manifest says `profile: playtest`, `git_dirty: false`, and
  whose `git_commit` equals the tag's commit.

**Release record** (append a row for each publish or rollback; keep old rows):

| Date | Tag | Commit | place_sha256 (manifest) | Store name | Universe / Place ID | Roblox version # | Action | By |
|---|---|---|---|---|---|---|---|---|
| _pending_ | | | | `BeDino_Playtest_M1_v1` | _TODO(BD-004)_ | | first publish | Znypr |

## 7. Known-issues template

Publish this to testers with each release and keep it updated:

```
Be Dino! playtest <tag> — known issues (updated <date>)
Supported: Windows/Mac desktop, Android phone. Untested: iOS, tablet, console.
Progress is test data and may be reset (see data policy).
| ID | Severity (P0/P1/P2) | Area | Symptom | Workaround | Status / fix tag |
|----|---------------------|------|---------|------------|------------------|
How to report: <channel>, include device, time, what you did, screenshot.
```

P0 means data loss, duplication, security or inability to play. A P0 blocks the session
and triggers rollback (§8). P1 core failures block wider invitations. P2 cosmetic issues
may remain.

## 8. Rollback procedure

**Decide quickly**: roll back on any P0, any `SchemaError`/`SaveFailed` spike, or a
fusion/identity bug that mutates profiles.

1. **Stop the damage**: set the experience to *Private*, or shut down all servers.
2. **Republish the previous known-good build.** Either:
   - Creator Hub → Places → *Version History* → **Restore** the version listed in the
     release record; or
   - rebuild the previous tag (`git checkout <prev tag>; python tools/build.py --profile playtest`),
     check that its `place_sha256` matches the record, and publish it.

   Then *Restart servers for updates*. Add a row with Action = rollback.
3. **DataStore compatibility**:
   - Schema changes are **additive**. Older builds keep unknown fields, because every
     write is an UpdateAsync of the full profile.
   - Profiles carry `schemaVersion`. A build whose `ProfileSchemaVersion` is lower than
     the stored profile treats it as invalid and fails closed (`SchemaError`, no
     overwrite). So **rolling back past a schema bump locks affected players out** until
     roll-forward or store rotation. That is safe, but unusable.
   - Rolling back from a persistent-identity build (BD-064) to an older build leaves the
     identity sidecar untouched while the older code edits counts.
     `verify_identity` covers offline migration and rollback reconciliation. Check it
     again in the BD-064 PR before relying on a cross-identity rollback.
4. **Corrupted test profiles (fusion/identity bug)**: rotate the store instead of
   hand-editing profiles.
   1. Increment `PlaytestProfileDataStoreName` (`_v1` → `_v2`) in Config and commit.
   2. Let CI pass, tag `…-rK+1`, build, verify, publish.
   3. Every tester starts fresh in the new store, with leaderboards reset too. The old
      store stays untouched as evidence for the bug.
   4. Record the rotation in the release record and known issues.

   Editing single keys in the Data Stores Manager is a last resort for a single tester
   and must be noted.
5. **Offline compatibility evidence and the owner steps for a real rollback:** [docs/111](111-rollback-drill.md) (`tools/verify_rollback.py`).
6. **Rollback drill (BD-020 acceptance)**: before inviting testers, publish r1, then
   republish r0 (or restore the previous version), confirm the version label changed,
   and roll forward again. Record both version numbers.

## 9. Data-reset policy for the playtest

- Playtest progress is **disposable test data**. It is never migrated into a future
  public experience, and no Robux is involved, so there are no purchase obligations.
- Resets happen only through store rotation (§8). Use it at milestone boundaries, after
  a P0 data bug, or when a schema change is not backward compatible. Announce the reset
  in the known-issues note before publishing.
- Do not grant compensation items by hand. Debug grants stay off in every published
  build, and `verify_release` enforces that.
- Profile keys are `u:<UserId>`. If Roblox sends a right-to-erasure request for a tester,
  delete that key in each playtest store version (Data Stores Manager) and note it.
