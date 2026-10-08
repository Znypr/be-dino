# Live multiplayer test attempt — 2026-10-08

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
