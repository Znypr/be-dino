# BD-579: first Studio look at the gifting features (numbers only)

Date 2026-10-17, 15:21 to 15:28 local. Build: `main` + PR #416 (BD-452 admin Gift page) + PR #417 (BD-570 popup and Settings row),
profile `playtest`, with `GiftClaimEnabled` and `AdminGiftsEnabled` set to `true` in the private output file
`C:/Users/znypr/dtmp/gifts.rbxlx` only (sed on the built file; no flag change is in the repo, `git diff` shows none).
`AdminPanelEnabled` was already true. `GiftingEnabled` (Robux gifts) stayed false.

**Numbers-only mode.** The PC had been idle for hours and the Studio window rendered 0 frames (`RenderStepped` fired 0 times in 2 s, viewport 1 x 1),
so no picture could be taken and mouse clicks were not possible (`VirtualInputManager` input needs RobloxScript). Everything below was driven in Play
(one player, unpublished Studio = admin, `ProfileMode` "Studio preview (not saved)") through the real remotes `AdminGiftAction` and `GiftAction`,
the real client modules (`GiftSettings` controller `press` / `choose`, the real `SettingsMenu.build`) and by reading the real GUI instances.
No button was physically clicked; the call its click handler makes was made. Because no frame ran, the popup's 0.28 s bounce stayed at scale 0.88
(sizes read in that state are 0.88 x the real ones; real sizes are quoted below).

## Step table

| # | Step | Result | What was read |
| --- | --- | --- | --- |
| 1 | Flags on: remotes and UI exist | PASS | `GiftAction` and `AdminGiftAction` RemoteFunctions present; `BeDinoAdminUI` has `AdminTabs` (buttons "Tools", "Gift", each 196 x 48) and `AdminGiftPage`; `GiftPopup` ScreenGui built (Enabled false until a gift arrives) |
| 2 | Pick yourself (Gift page `pick`) | PASS | `{ok, username "znyprs", userId 7285577648, displayName "znypr"}` |
| 3 | Send before Yes | PASS (refused) | `not_confirmed`; sends to others also `not_confirmed` |
| 4 | Yes (`confirm`), send crystals 250 + preset "have_fun" | PASS | `queued`, label "A gift from the Be Dino team!"; server log `[BD-GIFT] admin from=.. to=.. item=crystals_custom` |
| 5 | Send skin `skin_plush` + preset "enjoy" | PASS | `queued`, same label |
| 6 | Claim (live loop, 60 s) | PASS | claimed 33 to 40 s after sending; wallet 1,000,000 (Studio test wallet) to 1,000,250 |
| 7 | Popup hidden while the welcome ("How to play") menu is open, shown after it closes | PASS | `GiftPopup.Enabled` false with `ModalScrim` visible; true after the menu closed |
| 8 | Popup copy and buttons, team gift | PASS (one copy bug, see 9) | Title "A gift from the Be Dino team!" (22 px), detail "Crystals - Have fun!" (18 px), buttons "Nice!" and "Turn gifts off" (20 px, 110 x 48 and 170 x 48 at scale 1); no Mute button for a team gift; no refuse button |
| 9 | Popup says how many crystals | FAIL, fixed here | custom admin crystals showed only "Crystals". Now "250 crystals - Have fun!" (`GiftService.showNext`, verifier check added). Not re-run in Studio (offline `verify_gifts` only) |
| 10 | "Nice!" shows the next notice, then closes | PASS | second popup "Plushy skin - Enjoy!"; after the second Nice! `GiftNoticeJson` empty, `Enabled` false |
| 11 | Admin gift ignores recipient "Nobody" | PASS | setting "nobody", team gift of `skin_clay` still claimed (detail "Clay skin", no message) |
| 12 | "Turn gifts off" | PASS | `press("turnOff")` ok, popup closed, `GiftAction get` = nobody |
| 13 | Settings row "Gifts from" (Controls tab, real `SettingsMenu.build`) | PASS | label "Gifts from" 28 px at y 232; buttons EVERYONE / FRIENDS / NOBODY, each 168 x 48 at x 270 / 450 / 630; EVERYONE selected by default; the two key-help lines start at y 290 (no overlap); body is 824 x 402 |
| 14 | Row saves, rolls back, rejects junk | PASS | choose friends / nobody / everyone each saved (`get` matched); `choose("everybody!")` false and unchanged; raw `setFrom "junk"` and raw `mute` without a popup both `bad_request` |
| 15 | History | PASS | `audit` newest first: admin, admin, claimed, claimed, ...; items and giftIds only, no names or text |
| 16 | Take back | PASS | claimed skin: `revoked`; again: `already_revoked`. NOTE: an id never sent ("nope") also answered `revoked` (tombstone), see BD-590 |
| 17 | Username lookup (unpublished) | PASS | `Players:GetUserIdFromNameAsync` and `UserService` both work unpublished: "Roblox" returns userId 1, displayName "Roblox"; an unknown valid-looking name `not_found`; 2 letters, spaces, over 20 chars `bad_name` |
| 18 | Avatar head shot on the confirm card | NOT SEEN | needs a rendered window (picture owed) |
| 19 | Offline user: gift queued by username | PASS (queue only) | confirm + send to userId 1 `queued`; `audit` for 1 shows the admin event. The unpublished store is in-memory, so the claim at that user's next join cannot be tried (BD-591) |
| 20 | Bad amounts | PASS | 0 and 50001 `bad_amount` (refused, not clamped); extra key `label` `bad_request` |
| 21 | Roblox-blocked account refused | NOT TESTED | one account. The client reported its block list (no "no blocked-id report" warning in the server log), so `GetCore("GetBlockedUserIds")` works in Studio. BD-591 |
| 22 | Gift page sizes (desktop 1140 x 727 UI) | PASS | panel 420 x 651 at (14, 64); page 400 x 579, canvas 1240 high (scrolls to Take back and Gift history); smallest text 18 px; smallest button or box 44 px high; nothing wider than the scroll bar edge; send button 388 x 56 |
| 23 | Popup spot per screen size (`TouchLayout.giftRect`, the real function) | PASS with a note | 1140 x 727: roomy 480 x 146 at (330, 232); 1920 x 1000: roomy at (720, 347); 844 x 390: compact 420 x 104 at (200, 112); 812 x 375: compact at (168, 106); 667 x 375: compact at (23, 114); 568 x 320: stacked 340 x 156 at (114, 106), clear false (covers 2 HUD pieces). Text >= 16 px and buttons >= 44 px high in every variant. NOTE: the three phone spots from 667 to 844 wide sit over the touch thumb/jump zones (`overZones` true; no zone-free spot exists); the popup is cave-hub only and one tap on Nice! closes it. A real phone check is owed |

## Pictures still owed (BD-589)
Desktop and 844 x 390 pictures of: the Gift page (top; confirm card with avatar; Take back and history at the bottom), the popup (team gift with and without
a message), the Settings row "Gifts from". Take them in a window that renders, then add them to this folder.

## Not covered
Two accounts claiming at the next join, the Roblox-block refusal, the live DataStore and the real phone: BD-591.

## Small fix made
`src/server/GiftService.luau` `showNext`: a custom admin crystal gift now names its amount in the popup ("250 crystals", "1,234 crystals", "1 crystal").
`tools/verify_gifts.py`: one added check. No flag, config or art changed.
