# 178 Publish pack for the friends playtest in "newbuild" (BD-004, BD-317, BD-320, BD-1013)

Written 2026-10-18. Label: **OWNER STEPS + READ-ONLY CHECK OF THE ROBLOX PAGES.** Nothing was published, nothing was changed in Creator Hub or Studio, no flag, id, profile or build was changed. The lead only LOOKED at the settings pages (Claude in Chrome, Edge, owner logged in, no switch clicked, tabs closed). Pictures: [evidence/2026-10-18-publish-pack/](evidence/2026-10-18-publish-pack/).

**Owner decision 2026-10-18 (chat):** the friends playtest goes into the EXISTING experience **newbuild** (universe 10769812255, place 111259822927673). Private, invite only. Devices: Phone and Computer. The six crystal packs are taken off sale. This answers the question in [148](148-publish-runbook.md) step 1.

How to read the marks. **SEEN** = the lead saw it on the real page on 2026-10-18. **UNVERIFIED** = written from the docs or from memory of Roblox's pages; nobody has done it yet. If a screen looks different, write down what you see and tell the lead. Read first if you want more: [148](148-publish-runbook.md), [55](55-playtest-release-runbook.md), [111](111-rollback-drill.md), [125](125-friends-playtest-go-no-go.md), [175 phone kit](175-phone-test-kit.md), [167 report tool](167-reference-and-playtest-tools.md).

## 0. The short answer: your clicks in 10 lines

1. **Roblox Settings: verify your ID / age (13+).** The page says "Enable Mesh / Image APIs" is greyed out until you do (SEEN). Without it the world art and dino patterns fall back to plainer looks.
2. Creator Hub > newbuild > **Game details**: tick **Enable Mesh / Image APIs** > Save (after step 1).
3. Creator Hub > newbuild > Places > newbuild > **Access**: set **Maximum Visitor Count** to **4** (it says 50 now) > Save.
4. Studio: **Game Settings > Basic Info > Devices**: tick **Computer** and **Phone** (UNVERIFIED: I did not find Devices on any Creator Hub page I could read).
5. Creator Hub > newbuild > **Permissions > Early testers > Add early testers**: add your friends (up to 10, they must be your Roblox friends). Check each friend is 16 or older, or a trusted friend: the page says "Ages 16+ and trusted friends" (SEEN).
6. Open `build/BeDino-Build020-playtest.rbxlx` in Studio. Check the label reads `BUILD redesign-020` (UNVERIFIED for a new build: the lead tells you the number).
7. Studio: **File > Publish to Roblox As...** > newbuild > the **newbuild** place > Overwrite. Write down the new number in Version History.
8. Creator Hub > newbuild > **Server management > Restart Servers**.
9. **Rollback drill** (section 5), then **go**: join with a friend, play 10 minutes, fill in the form (section 6).
10. **Stop button** (section 7): Manage audience > Manage access to private, remove the early testers, Restart Servers.

## 1. What the settings pages say today (SEEN, read only, 2026-10-18)

| Thing | What the page says | Pictures | Ok for the playtest? |
| --- | --- | --- | --- |
| Experience and ids | name **newbuild**, universe 10769812255, one place **newbuild**, place id 111259822927673 (in the link of the place card) | [01](evidence/2026-10-18-publish-pack/01-overview.jpg) | **YES** matches Config.luau, docs/42, docs/78 and `tools/release_ids.json` (see section 8) |
| Who can play | Overview: "Game access: **Limited**". Manage audience: "newbuild is ready to test! **Only available to you and your collaborators.**" | [01](evidence/2026-10-18-publish-pack/01-overview.jpg), [02](evidence/2026-10-18-publish-pack/02-manage-audience.jpg) | **YES, private** |
| Collaborators (Permissions > Access) | owner `znyprs`, plus **Znyprr** with "Playtest this experience" (your alt) | [07](evidence/2026-10-18-publish-pack/07-permissions-access.jpg) | yes for the alt |
| Early testers (Permissions > Early testers) | **"No early testers. Add up to 10 friends to preview your game."** | [08](evidence/2026-10-18-publish-pack/08-permissions-early-testers.jpg) | **NO friends added yet** (your step 5) |
| Audience reach | "**Ages 16+ and trusted friends**". Not done: Verify identity, "Reach 250 highly engaged players" (0), Kids and Select fee. Done: content rating, 2-step verification | [01](evidence/2026-10-18-publish-pack/01-overview.jpg), [02](evidence/2026-10-18-publish-pack/02-manage-audience.jpg) | **WATCH:** a friend under 16 who is not a trusted friend may not get in. UNVERIFIED how Early testers interact with this. Ask your friends' ages first |
| Content rating | Content Maturity Label **Minimal**, questionnaire completed. "Paid Random Items" listed as non-compliant for Australia, Belgium, Brazil (under 18), UK (under 18), Netherlands | none (text read) | yes; the build has no paid random items (flags off) |
| Maximum players (place Access page) | **50** | [03](evidence/2026-10-18-publish-pack/03-place-access.jpg) | **NO**, docs/148 says 4 for session 1 (your step 3) |
| Enable Studio access to API services | **ON (ticked)** | [04](evidence/2026-10-18-publish-pack/04-game-details-api-services.jpg) | see section 2c |
| Enable Mesh / Image APIs | **OFF, greyed out**: "You must be 13+ ID verified to access this API." | [04](evidence/2026-10-18-publish-pack/04-game-details-api-services.jpg) | **NO** (your steps 1 and 2) |
| Devices | **not found** on any Creator Hub page I could read (Game details, Manage audience, Places, Access) | none | UNVERIFIED, set it in Studio Game Settings (your step 4) |
| Developer products (the six crystal packs) | all 6 exist. List column "Current price": **Offsale** for all six. Each product's own page: **"Item for sale" is OFF** for all six (500, 1500, 4000, 10000, 25000, 90000). "Managed pricing" shows Enabled | [05](evidence/2026-10-18-publish-pack/05-developer-products.jpg) | **YES, all 6 off sale** (you confirmed 3 of 6; the lead saw all 6) |
| Data stores | one store: **BeDino_PrivateTest_v1**, 2 keys, 987 B. No playtest store yet | [06](evidence/2026-10-18-publish-pack/06-data-stores.jpg) | yes (section 2d) |
| Versions | newest saved: version 17 (14 Oct 2026, 17:33), 16 (13 Oct), 15 to 8 (8 Oct). Server management says **"Last published on Oct 8, 2026 at 3:23"**: the live game is the OLD Build 019 | [09](evidence/2026-10-18-publish-pack/09-version-history.jpg) | note it, section 5 |
| Active servers | none ("--") | none | yes |

Not read (not found or not asked): the Avatar and Chat settings (the Chat page there is only "Quick Words"), Security switches such as HTTP requests and third-party sales (UNVERIFIED; docs/148 wants them off).

## 2. The publish pack

### 2a. Open the playtest build
1. The lead makes the file: `python tools/build.py --profile playtest`, result `build/BeDino-Build020-playtest.rbxlx` (the lead copies it to a short folder and starts Studio with the file as an argument; that is the lead's way, not a click list). **You** can double-click the file, or Studio > File > Open from File.
2. Close every other Studio window (three open Studios gave 15 fps, [148](148-publish-runbook.md)). The file opens with GameId 0, so playing in it does not touch Roblox data (SEEN in earlier tests, [42](42-live-multiplayer-test.md)).
3. Look at the label in the game: `BUILD redesign-020` (UNVERIFIED for this commit; the lead tells you the number).
4. **Publish:** File > **Publish to Roblox As...** > pick **newbuild** > the place **newbuild** (place id 111259822927673) > **Overwrite**. UNVERIFIED (nobody has published from this file). Never "Create new experience". After it: Creator Hub > newbuild > Places > newbuild > **Version History**, write down the top version number.
5. Creator Hub > newbuild > **Server management > Restart Servers** (the page shows a "Restart Servers" button, SEEN; nothing was clicked).
6. After publishing, the open Studio window is tied to newbuild. With "Studio access to API services" ON (2c), pressing Play there can write to the real playtest store. Close Studio, or do not press Play in that window.

### 2b. Experience settings
- **Private:** already so (table). Leave "Release publicly on Roblox" alone.
- **Permissions:** Permissions > Early testers > Add early testers (see step 5). Friends only. UNVERIFIED which of "Early testers" or "Access > Playtest" is the right door for a friend; Early testers exists and says "up to 10 friends to preview your game" (SEEN); your alt already uses Access.
- **Devices:** Computer + Phone. UNVERIFIED place. Mismatch: [148](148-publish-runbook.md) step 2 says "Computer only" for session 1, the owner decision above wins. The phone numbers are still unmeasured (BD-085); tell the friends the phone is experimental.
- **Avatar / Chat:** keep Roblox defaults (basic chat). The game has no custom chat. UNVERIFIED, I saw only the Quick Words page.
- **Max players:** 4 (Places > newbuild > Access > Maximum Visitor Count).
- **Mesh / Image APIs:** see step 1 and 2. [105](105-lowpoly-patterns-and-tiers.md) and [125](125-friends-playtest-go-no-go.md) s6 say it must be ON; the page says it needs ID verification. If you cannot verify: the game has fallbacks (plain egg tint, kit models), so a friend can still play, but the playtest then shows fallback looks (UNVERIFIED live).
- **Monetization:** nothing for sale (SEEN). Do not create passes or products.

### 2c. Studio access to API services
SEEN: it is **ON** today (Game details). That is what a Studio test of saving needs. Mismatch: [148](148-publish-runbook.md) step 2 says OFF unless on purpose, [55](55-playtest-release-runbook.md) says only while you test Studio against the real store. Plain answer: live servers save with or without it. If you do not plan to press Play in a Studio window tied to newbuild, switch it OFF before the friends come (Game details > untick > Save). If you want it ON, remember the warning in 2a item 6.

### 2d. Data store names, and why no live profile is touched
| What | Name | Where it is set |
| --- | --- | --- |
| Build 020 / default profile store (the "live" data) | `BeDino_PrivateTest_v1` | `Config.ProfileDataStoreName`; SEEN on the data stores page: 2 keys, 987 B |
| Playtest profile store | `BeDino_Playtest_M1_v1` | `Config.PlaytestProfileDataStoreName`; the playtest build replaces `ProfileDataStoreName` with it (`tools/release_profiles.py`, `verify_release` passes: it checks the name) |
| Playtest leaderboards | `BeDino_Playtest_M1_v1_<board>_v1` | derived (`Leaderboards.luau`) |
| Gifts store | `BeDino_Playtest_M1_v1_Gifts` | derived (`GiftService.luau`); gifting is off, so nothing is read or written |

The playtest names are different from the Build 020 name, so the playtest never reads or writes a Build 020 profile. They do not exist yet; Roblox creates the store at the first save. **Rollback rule RB1** ([115](115-decisions-log.md), [111](111-rollback-drill.md)): roll back only to the **previous playtest tag**, never to Build 020 (it uses another store and refuses profiles with newer data). A broken test store is fixed by **rotating the name** (`_v1` to `_v2`, lead does it in a PR), never by editing profiles. Progress in the playtest is disposable ([55](55-playtest-release-runbook.md) s9).

## 3. The release ids (BD-004) and the gate

`tools/release_ids.json` is still empty on purpose. The lead checked all four sources: Config.luau (PlaytestUniverseId 10769812255, PlaytestPlaceId 111259822927673), docs/42, docs/78 and the live Places page (the place card link holds 111259822927673) all agree. **No id mismatch.** What the checks say (offline, 2026-10-18, main `24d58826`):

| Check | Result |
| --- | --- |
| `python tools/verify_release_ids.py` (CI form, repo slot empty) | passes: "Release id slot ok (empty)" |
| `python tools/verify_release.py --profile playtest` | **passes**, 40 keys enforced; one WARNING that `DeveloperProducts` still lists 6 Robux product ids (inert, see below) |
| `python tools/verify_load.py --runner <luau> --gate-playtest` | **passes** (8 and 12 players, playtest flags, 40 and 400 egg bursts, equip spam; no throttle drops) |
| `python tools/release_playtest.py --dry-run` (first 24 of 160 CI commands read before the pipe I used closed it) | the **only BLOCK is the empty BD-004 slot** (plus "working tree is clean" while my evidence folder was uncommitted); both builds, both `verify_release` runs, the session-1 smoke and every CI verifier shown passed |
| Slot filled with these ids, kind "legacy" (rehearsal in a scratch copy, not committed) | **HARD STOP**: Config.DeveloperProducts lists 6 product ids |
| Slot filled, kind "new" | error: those ids are the "legacy" experience of docs/55 s2 |

Why the slot is NOT filled in this PR: newbuild IS the experience docs/55 s2 calls "legacy" (same ids), so the tool needs `ExperienceKind` "legacy", and for "legacy" it refuses while `Config.DeveloperProducts` lists the six Robux ids. CI runs `verify_release_ids.py` on every PR, so filling the slot today would make CI red. The tool cannot see Creator Hub, so the "I took them off sale" fact does not count for it. **One decision for the lead (not made here, it loosens a guard):** pick one of (a) clear the six ids in `Config.DeveloperProducts` (also closes the receipt hole BD-612; but the "table must not be emptied" remark in BD-612 and `PaidRandomGate` need a look first), or (b) add an optional slot field such as `ProductsOffSaleConfirmedOn` that turns the hard stop into a warning, with a test. Then the one-line edit is: `tools/release_ids.json` gets `"PlaytestUniverseId": 10769812255, "PlaytestPlaceId": 111259822927673, "ExperienceKind": "legacy", "AnsweredOn": "2026-10-18"` (Config already holds both numbers, so nothing else changes). `python tools/release_playtest.py` refuses until then (exit 2).

Mismatch between docs: [55](55-playtest-release-runbook.md) s2 says the newbuild ids are NOT the Milestone 1 place; [42](42-live-multiplayer-test.md), [78](78-lead-handoff.md) and Config say they are; the owner's decision today settles it for newbuild.

## 4. Order on the day (about 40 minutes)
1. Steps 1 and 2 of section 0 (ID check can take a day; if it does, publish without it and say so to the friends).
2. Steps 3 to 5, then publish (2a), then the rollback drill (section 5), then invite.

## 5. The rollback drill (BD-020, BD-320, RB1): what to do and what proves it

Purpose: show you can undo a bad publish before friends arrive. First release ever: there is no earlier playtest tag, so the drill uses two Roblox versions of the same file ([148](148-publish-runbook.md) step 5).

1. Publish the file (2a). Write down the top Version History number as **A**.
2. Publish the **same file** again (2a item 4). Write down the new top number as **B**. Restart Servers.
3. Creator Hub > Places > newbuild > **Version History** > **Restore** on A. **Important, SEEN on that page: "Choosing to restore a previous version will only save the version. In order to publish the previous version, open and publish it in Studio."** So restore alone changes nothing for players. Mismatch: [148](148-publish-runbook.md) step 5, [111](111-rollback-drill.md) and [125](125-friends-playtest-go-no-go.md) s7 say "Restore, then shut down servers" without the Studio publish step. Correct: after Restore, open the place from Creator Hub (Edit in Studio) and File > Publish to Roblox, then Restart Servers. UNVERIFIED: the exact number the page gives that republished copy (write it down as **A2**).
4. Join with the alt (Znyprr, already a playtester). **Proof A:** the game loads, `ProfileState` is Loaded (your stuff from before is still there), and Server management shows a newer "Last published on" time. Because A and B are the same file the `BUILD` label stays the same; the proof is the Roblox version numbers and the saved profile.
5. Roll forward: Studio File > Publish (the checked file again) = **B2**. Restart Servers. Join again: the profile still loads.
6. Send the lead: `A=<n>, B=<n>, A2=<n>, B2=<n>, profile loaded both times: yes or no`.
- Optional visible check (lead suggestion, UNVERIFIED): version 13 on the Version History is the old Build 019 (label `redesign-019`). Restoring and publishing it shows the label change, but it reads another data store (`BeDino_PrivateTest_v1`), so it proves the label and the publish route, not the profile.
- If something breaks: Stop button (section 7), then RB1.

## 6. First session: you and two friends (10 minutes of play)

Before: the lead sends the friends one short note: "private test, no Robux, your progress may be erased, phones are experimental". Phone friends: the lead may give the [175 phone kit](175-phone-test-kit.md) form (optional).

| Step | Do | Report |
| --- | --- | --- |
| 1 | Join from the experience page on roblox.com (Play). Owner joins first. | Could everyone get in? If a friend sees "not available", write the exact words and their age group |
| 2 | Check: no admin panel (no F2 panel, no FOOD counter), no Robux prompt anywhere, pictures and dinos are not grey boxes | any grey box, missing picture, silence |
| 3 | Play 10 minutes: eat, go home, watch eggs hatch, buy one potion, try Fusion once | what was confusing, boring, wow |
| 4 | Leave, wait 1 minute, join again | settings, crystals and eggs the same? |
| 5 | Press **Tell us!** (bottom-left) and send the face answers; short text only | each friend once (limit: 1 per 2 minutes) |
| 6 | Owner, while the server runs: press F9 > Server Logs and copy every line | red lines with `SaveFailed`, `LeaseLost`, `SchemaError`; the log is gone when the server closes, copy it first |

After: the lead runs `python tools/playtest_report.py server.log --out report.md` ([167](167-reference-and-playtest-tools.md) s7): runs, eggs, drop-off, traffic lights. With fewer than 4 visits the lights are only hints. Each bug becomes a kanban row with the build number. Ask the friends the five questions of [125](125-friends-playtest-go-no-go.md) s6 (first minute clear? run length? best moment? most confusing screen? play again?). UNVERIFIED: the F9 Server Logs tab for a place you are not editing, and the whole report path on real data (no real playtest has run).

## 7. The stop button, and bringing the crystal packs back

**Stop now (any problem):**
1. Creator Hub > newbuild > **Manage audience** > **Manage access** > make sure it is private to you and collaborators (UNVERIFIED which options the panel gives; it opened nothing readable when the lead clicked it, so the lead did not use it).
2. **Permissions > Early testers**: remove the friends. Then only you and collaborators can join (UNVERIFIED but follows from the pages).
3. **Server management > Restart Servers** (SEEN). A hard "shut down all servers" is the Roblox.com game page > Configure/Shut down (UNVERIFIED; the Creator Hub Server management page only showed "Restart Servers" and a server browser).
4. If saves are corrupted: rotate the store (RB1, 2d), never edit profiles.

**Bring the crystal packs back later** (not before the shop is ready and the owner says go): Creator Hub > newbuild > Monetization > Developer products > a pack > switch **Item for sale** ON > Save, one at a time, and the build must have `CrystalPacksEnabled` true (a separate owner go-ahead, paid flags stay off now). BD-612 (receipts honoured when the flag is off) should be fixed first. Ids: 3717200374 (500), 3717200467 (1500), 3717200523 (4000), 3717200920 (10000), 3717200940 (25000), 3717200979 (90000), in `resources/monetization/crystal-products.json`.

## 8. Mismatches found (all become questions, none decided silently)
1. **Mesh / Image APIs is OFF and cannot be turned on until you verify your ID.** Docs say ON.
2. **Max players is 50** on the page; docs/148 says 4 (docs/55 says 8; newer owner decision wins: 4).
3. **Restore does not publish** ([148](148-publish-runbook.md) step 5, [111](111-rollback-drill.md), [125](125-friends-playtest-go-no-go.md) s7 omit the Studio publish).
4. **Devices: "Computer only"** (148) vs **Computer + Phone** (55, 125, owner today). Owner today wins. Setting not found in Creator Hub.
5. **Studio access ON** vs docs/148 "OFF". Plain choice in 2c.
6. **Audience reach "Ages 16+ and trusted friends"**: friends under 16 may be blocked; nowhere in the docs.
7. **newbuild = the "legacy" experience** of docs/55 s2: the id tool needs kind "legacy" and then hard-stops on the six product ids, even though all six are off sale (section 3). Needs the lead's decision.
8. **Live game is still Build 019**: "Last published Oct 8" while Version History shows saves on 13 and 14 Oct (versions 16, 17). Those saves were never published (UNVERIFIED reading of the two pages).
9. docs/148 step 4 tells the owner to join "from the Roblox page"; docs/42 recorded an earlier "currently not available" that was solved by the content questionnaire (now Minimal, done).

## Handbook check
Plain words in the owner sections; no game code, flag, id, profile or build changed; paid lines stay off; no publish, no Creator Hub change (only page reads and a tab switch to Early testers); no screenshots contain an email address; the pictures show only the owner's own experience and the usernames of the owner and the alt. Publishing, Robux, account and Studio settings stay the owner's steps.
