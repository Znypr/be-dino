# Multiplayer test results — 2026-10-08

## Initial attempt (superseded by retry below)

Target: newbuild, place 111259822927673, universe 10769812255.
Open Studio Config identifies redesign-019; current repository work is newer.

Creator Dashboard Audience reach gives the concrete live blocker:
Game unplayable, missing content maturity rating, Unrated. Account publishing
reach is Ages 16+ and trusted friends; current experience reach is Private.
Znyprr has Playtest access from the prior pass. Roblox's current rules require
Limited > Playtesters and publishing eligibility for playtest-only accounts:
https://create.roblox.com/docs/production/publishing/kids-and-select

Opened the content questionnaire and asked the owner to complete it. No rating,
audience change, paid fee, or game publication was submitted by this test.
Evidence: evidence/2026-10-08-multiplayer/live-unrated-blocker.jpg.

Attempted StudioTestService.ExecuteMultiplayerTestAsync with five clients.
A disposable server fixture would verify five profile/character loads, reward
isolation, duplicate run settlement, locked equip, renewal and memory reload.
Temporarily gated memory-only profiles on the exact test arguments, preventing
live DataStore writes. Studio's spawned process hung at startup; its log reports
MainThreadHangs and RBXCRASH-HangDetected. No gameplay PASS result was returned.
Restored the original ProfileRepository Source and removed the disposable script.
Computer Use was stopped with the physical Escape key; no further UI actions.

Remaining: real owner/alt same-server join, 3–5 live players, non-owner assets,
gameplay isolation and replication, real persisted save/rejoin, mobile/load
performance, repeated join/leave stability. These are blocked/not executed,
not passing. Re-run after rating and Limited Playtesters availability, and after
recovering Studio's multiplayer launch.

## Successful retry

The owner completed the questionnaire (Minimal). Audience is now Limited,
Playtesters only; Friends is unchecked. Znyprr has Play access, without Edit.
The alt successfully joined published newbuild. Its visible build banner is
redesign-019: this validates the older published build, not newer repository assets.
Compy renders in the world and Sanctuary. All six collection previews are visible;
this does not independently prove that every preview uses a permitted 3D mesh
rather than a fallback image. Starter inventory: one Base Compy, zero Gold and
Diamond, discovered 1/6, zero crystals.
The alt exited the Roblox client and launched a new client from the same game
page successfully. Welcome/game UI loaded with zero crystals and no visible
profile-lock error. This is a basic reconnect pass, not earned-reward persistence.

StudioTestService retries with **two and five clients passed** in disposable
BeDino-019-DisposableAcceptance.rbxlx (GameId/PlaceId 0, memory-only profiles).
The server asserted all participants had loaded profiles and characters. Two
sampled clients saw the full player count: 2/5 respectively, and 30/75 replicated
MeshPart instances. These counts are replication evidence, not visual or FPS tests.
Server checks passed reward isolation, duplicate run settlement without another
inventory/revision grant, locked Tyrannosaur equip rejection, lease renewal and
release/reload of the in-memory collection. `persistent=false` in both results:
**no real DataStore persistence result is claimed**. Both temporary QA scripts
were removed; no gameplay source or place publication was changed by this retry.

Evidence: evidence/2026-10-08-multiplayer/limited-playtesters.jpg,
alt-compy-live.jpg, alt-collection-before-rejoin.jpg, alt-collection-bottom.jpg.

Remaining acceptance: actual owner+alt simultaneous same-server play, 3–5 real
players/devices, earned reward save/rejoin against DataStore, repeated join/leave
and competing-session behavior, mobile/FPS/long-session load, and non-owner tests
of the latest assets after a verified release. A configured server size of 50 is
not evidence of a 50-player load test. Paid-random access plan: docs/43-player-access-and-paid-random-policy.md.
