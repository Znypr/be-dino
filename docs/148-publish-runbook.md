# 148 Publish runbook: the owner's click-by-click steps (BD-004, BD-020, BD-320)

Label: **OWNER STEPS + LEAD PREPARATION** (written 2026-10-17). Nothing here has been done: nothing was published, no Roblox account was touched, no tag was created, no id or release flag was changed. It turns [55 playtest release runbook](55-playtest-release-runbook.md) s2, s4, s8, [111 rollback drill](111-rollback-drill.md) s3, [115 decisions](115-decisions-log.md) (RB1, ST1, ST4, MR6) and the owner steps of [145](145-session1-readiness-2026-10-17.md) into short steps. The tools: `tools/release_playtest.py`, `tools/verify_release_ids.py`, `tools/release_ids.json`. Where the older docs differ on a number (max players: 55 says 8, 125/129/145 say 4), the newer owner decision wins: **4 players for session 1**.

Why this takes minutes: the lead does all the building and checking in one command; you only click in Creator Hub and Studio. Steps 1 to 3 gate session 1. The times are estimates.

## Lead side (before you start, about 20 minutes of computer time, no clicking from you)

| What | Command | Result |
| --- | --- | --- |
| 1. You answer step 1 below | the lead puts both numbers and "new" or "legacy" into `tools/release_ids.json`, and the same two numbers into `src/shared/Config.luau`, in one PR (no other id changes) | `python tools/verify_release_ids.py --require-filled` passes |
| 2. Merge it, wait for green CI | `git fetch origin` | the commit is on `origin/main` |
| 3. One command | `python tools/release_playtest.py` | gates, both builds, `verify_release`, session-1 smoke, every CI verifier, unit tests, manifest `build/release/<tag>.release.json`, a tag NAME proposal and the rollback target |
| 4. Rehearsal any time | `python tools/release_playtest.py --dry-run` | same run, never refuses early, shows what would block |

The script never publishes, never creates or pushes a tag. It refuses to run (exit 2) when the working tree is dirty, HEAD is not a green commit of `origin/main`, the BD-004 ids are empty or do not match Config, the ids are the legacy experience while `Config.DeveloperProducts` still lists Robux products (hard stop), or any shipped profile has `StreamingEnabled` or a paid-random flag on. Tag after the script passes: the lead (or you) runs the two `git tag` / `git push` lines it prints.

## Owner steps

Each step: what to click, how long, and the one thing to send back to the lead.

### Step 1. Which experience is the playtest one? (BD-004) - 2 min
1. Open Creator Hub, Creations. Open each experience in turn; the experience name is at the top and its number (the universe) is in the address bar.
2. For the one you want friends to play: open Places, click the start place; its number (the place id) is in the address bar.
3. Is it the old Build 019 test experience (universe 10769812255) or a new one? If you do not know, say so.
- **Send back:** `name, universe id, place id, new or legacy`. The lead fills the slot. If it is the legacy one, the lead clears the six Robux product ids in Config first (hard stop in the script), and you check in step 2 that the experience sells nothing.

### Step 2. Creator Hub settings - 8 min
Open the playtest experience in Creator Hub, then Configure (settings) and Places.
1. **Allow Mesh & Image APIs:** turn it ON (Security or Game Settings, depending on the page). The low-poly dinos and world meshes need it.
2. **Max players:** set it to **4** (Places, then the start place).
3. **Devices:** tick **Computer only** unless you accept that a phone friend is the first phone measurement (BD-085).
4. **Access:** set to **Private** or **Limited**, and add only the named friends as playtesters (Play, not Edit). Public off. Friends-of-friends off.
5. **Monetization:** make sure there are **no developer products, passes or subscriptions** in this experience. If this is the legacy experience, open Monetization > Developer Products and take every item off sale (this is the check behind the hard stop).
6. **Maturity questionnaire:** fill it in truthfully for this build (an unrated experience cannot be played by others).
7. **Other Security switches:** Allow HTTP Requests OFF. Third-party sales and teleports OFF. Studio Access to API Services OFF (turn it on only on purpose, it makes Studio write to the real playtest store).
- **Send back:** one line `settings done`, or the name of the setting you could not find (a screenshot is fine).

### Step 3. Publish the checked place - 5 min
The lead gives you the exact file: `build/BeDino-Build<NNN>-playtest.rbxlx`, plus the tag name and its `place_sha256` from the manifest.
1. Close every other Studio window (three open Studios gave 15 fps).
2. In Studio: File > Open from File, pick that `.rbxlx`.
3. Look at the version label in the game: it must read `BUILD redesign-<NNN>` (the number the lead told you).
4. File > **Publish to Roblox As...**, pick the **existing playtest experience** and its start place (never the legacy one unless step 1 said it is the playtest one). Click Overwrite.
5. In Creator Hub > Places > Version History, note the new version number.
6. In Creator Hub: **Restart servers for updates** (or Shut down all servers for a hard cut).
- **Send back:** the Roblox version number. The lead writes the release-record row (docs/55 s6) and creates the tag.

### Step 4. Alt-account smoke - 15 min (needs a second Roblox account)
Use an account that is not you and is on the playtester list (step 2). Join the live experience from the Roblox page. Owner joins too if you can.
1. Can the alt open the experience page and press Play? (The one old attempt said "currently not available" and the reason was never found.) If not, **stop and tell the lead exactly what the page says**.
2. **No admin panel** on the alt: no F2 panel, no FOOD counter, no test wallet.
3. **Assets load:** the dinos are low-poly with colours (not grey blocks), trees and rocks are there, UI pictures show, the cave opens, and sounds play. Missing pictures or grey meshes are the failure to report (that is docs/55 D4).
4. **Save survives a rejoin:** play for 2 minutes (collect food, go home), change a setting (for example Sound), note the crystals and egg count, leave the game, wait one minute, join again. Settings, crystals and eggs must be the same. Owner view: the version label and `ProfileMode` say Persistent.
5. If an error is shown, open the Developer Console (type `/console` in chat) and copy any red lines mentioning `SaveFailed`, `LeaseLost` or `SchemaError`.
- **Send back:** `pass` or `fail` for each of the four lines, plus a screenshot of anything wrong.

### Step 5. Rollback drill (BD-020, BD-320, RB1) - 10 min
The point: prove you can undo a bad publish before friends arrive. The target is always the **previous playtest tag**, never Build 019/020 (RB1).
1. The lead tells you the target. First release ever: there is no previous tag, so the drill uses two Roblox versions of the same build: version A is the one from step 3, then publish the **same `.rbxlx` again** (step 3 items 4 to 6) as version B.
   Later releases: version A is the previous playtest tag's version, version B is the new one.
2. In Creator Hub > Places > Version History, **Restore** version A. Shut down all servers.
3. Join with the alt. Check the version label changed back to A's number and the profile loads (`ProfileState = Loaded`; your stuff from step 4 is still there).
4. Publish version B again (roll forward): Studio, File > Publish to Roblox As, same place. Restart servers. Join again; the label shows B and the profile still loads.
5. Write both Roblox version numbers down.
- **Send back:** `restored A=<number>, rolled forward B=<number>, profile loaded both times: yes or no`. The lead closes BD-020 / BD-320 with that as the evidence and adds a `rollback` row to the release record.

### Step 6. Say go - 1 min
- **Send back:** `go` for a session with named friends (4 players max, 1 to 2 hours, desktop, private, progress may reset, no Robux, placeholder economy numbers), or what stopped you.

## What the lead does with each answer

| You send | The lead does |
| --- | --- |
| Step 1 answer | fills `tools/release_ids.json` and Config in one PR; runs `python tools/release_playtest.py`; hands you the file, tag name and sha |
| Step 3 version number | fills the docs/55 s6 release-record row, creates the annotated tag (never from this script), pushes it |
| Step 4 results | pastes them in BD-020 and BD-317; every `fail` becomes a new BD row, not a silent fix |
| Step 5 numbers | marks BD-020 and BD-320 with the evidence |

## If something goes wrong
Stop the damage first: Creator Hub, set the experience to Private or shut down all servers. Then the rollback in [55 s8](55-playtest-release-runbook.md) and [111 s3](111-rollback-drill.md): restore the previous playtest tag's version. A corrupted test profile is fixed by rotating the store name (`BeDino_Playtest_M1_v1` to `_v2`), not by editing profiles. Never turn `CrystalPacksEnabled` or `PaidRandomItemsEnabled` on during a rollback, and never publish a `playtest-streaming` place (scratch profile, `StreamingEnabled` stays OFF in every shipped profile: [115](115-decisions-log.md) ST1 and ST4).

## Not covered here (still open, see 145)
Phone measurement (BD-085, BD-322), the 4-player live run (BD-319, BD-364), the lead's Studio pass (145 s5), the streaming gates (BD-502), and the food pace choice (BD-527; `FoodPickupAtMouth` stays false, MR6). The script prints a warning if `FoodPickupAtMouth` or `StreamingEnabled` is on in the playtest place.
