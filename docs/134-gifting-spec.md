# 134 Gifting (spec only, 2026-10-16)

**Status: SPEC. Nothing is built.** Owner request (2026-10-16): "there should be a gifting feature where you can gift people in the lobby or people offline (by typing their username) bundles or skins; I could also gift people things for free using the admin panel." Per the owner correction, a new feature is elaborated here and queued on the board first (BD-450..BD-453, all Backlog). Everything below is a proposal; **the section 10 questions were decided by the LEAD on 2026-10-16 under the owner's delegation ("take full autonomy, do decisions for me")**, recorded in [115](115-decisions-log.md) "LEAD decisions 2026-10-16 (owner delegated)". The owner may overrule any of them. Every Robux part is decided in principle only; enabling it needs the owner's go-ahead.

## 1. Goals
- A player can buy a skin, bundle or crystal pack **for someone else**: a player in the same server, or any player by typing a username (online elsewhere or offline).
- The recipient sees a friendly "You got a gift from <name>!" popup; delivery happens exactly once.
- The owner can grant the same items (and crystals) **for free** from the admin panel to an online or offline user.
- Safe for a children's audience and Roblox rules. Off by default, behind flags, until the owner tests.

## 2. Constraints (handbook and policy)
- **Robux line ([114 s11a](114-handbook.md)):** Robux buys looks and convenience only. Giftable with Robux: skins ([97](97-dino-skins.md): Plushy, Clay, Bricks), cosmetic bundles, crystal packs (crystals only). Never giftable: dinos, species, eggs, rarity, luck, stat or fusion advantages.
- **No random gifts.** Every gift is a fixed, named item shown before purchase. No gift egg, no "mystery" bundle. This keeps gifts out of `PaidRandomItemsEnabled` / `PolicyService` territory ([43](43-player-access-and-paid-random-policy.md)); `PolicyService` is still checked before any Robux prompt (a restricted player cannot buy gifts).
- **No trading, no transfers.** Only a NEW purchase or an admin grant creates a gift. Items a player already owns can never be sent. No gift-back, no re-gift.
- **Text filter:** any gift message goes through `TextService:FilterStringAsync` (non-chat broadcast filter, because the reader may be offline) with a 40 character cap; a failed filter sends no message, not the raw text. Short preset messages are the default.
- **Children audience ([72](72-ui-copy-and-asset-standards.md)):** short plain words, no stranger-DM feel. A recipient can turn "Accept gifts from other players" off in Settings (default is an open question, section 10). No chat, no reply box.
- **No PII in logs:** log UserIds only, never names, messages or avatar data. Display names are shown only inside the popup.
- **Server authority:** the client only asks. The server validates recipient, item, price and flags. Rate limits on requests (3 per minute per player) and on admin grants.
- **Flags, all default false and pinned off in the default AND playtest profiles** (`tools/release_profiles.py`): `GiftingEnabled` (Robux gifting), `AdminGiftsEnabled` (free admin gifts, also needs `AdminPanelEnabled`), `GiftClaimEnabled` (the claim path; required by either of the two).
- Session 1 has **no products or passes** ([125](125-friends-playtest-go-no-go.md) Creator Hub setup), so Robux gifting cannot be tested then.

## 3. Player flow: gift to someone in the server
1. Player opens the Shop and taps **Gift** on an item (skin, bundle, crystal pack).
2. A list of other players in the server appears (avatar head + display name). Tap one; the item and the person are shown big: "Gift Plushy to Sam?".
3. Optional: pick a preset message or type up to 40 characters.
4. **Send gift** opens the normal Roblox purchase prompt for the gift product. Buyer pays; recipient never pays.
5. After the receipt: buyer toast "Gift sent!"; recipient popup "You got a gift from <name>!" with a **Thanks!** button (popup system: [80](80-notifications.md)).

## 4. Player flow: gift by username (online elsewhere or offline)
1. **Gift** > "Type a username". Server resolves with `Players:GetUserIdFromNameAsync` (pcall, cached 60 s, rate limited).
2. The client shows the avatar and display name returned by the server for confirmation: "Is this Sam?" Yes / No.
3. Refuse: self (`UserId == buyer`), unknown names, non-positive ids. Copy: "We could not find that player."
4. Same item, message and purchase steps as section 3.
5. If the recipient is online in another server or offline, the gift waits in their inbox (section 6) and shows the popup at their next join (or within a minute if they are online).

## 5. Admin flow (free)
- Owner-only: reuse the admin panel authorization (`AdminRules.isAdmin`: creator, group rank 255, `Config.AdminUserIds`, unpublished Studio). The check is the first line of the handler, like every admin action.
- New **Gift** page: pick an online player or type a username (same confirm-by-avatar step), pick a catalog item or a crystal amount (1 to 50,000 per grant, clamped), optional preset message, **Send free gift**.
- Rate limit: 10 grants per minute per admin.
- Logs: `[BD-GIFT] admin=<userId> to=<userId> item=<id> id=<giftId>` plus an audit record in the Gifts store (`audit_<yyyymm>` key, capped list). No names, no message text.
- Admin gifts use source "admin"; they never touch `metrics.robux`. Today `AdminService` is runtime-only by design (`tools/verify_admin.py` forbids profile/DataStore access there), so the gift path lives in a separate `GiftService` and that check is extended, not weakened.

## 6. Data model
New DataStore **Gifts**, name derived from the profile store (`<ProfileDataStoreName truncated to 43>_Gifts`) so the playtest store stays isolated. Profiles are never written from another server.
- `inbox_<recipientUserId>` = `{gifts = {[giftId] = Gift}}`, at most 25 pending. Written only with `UpdateAsync` that adds a gift if its id is absent (idempotent).
- `Gift` = `{id, source = "robux"|"admin", from = userId, fromName, item = catalogId, crystals? (admin custom), msg?, at}`.
- `intent_<buyerUserId>` = `{pending = {recipient, item, msg, productId}, done = {[purchaseId] = Gift}}` (last 20 done). Needed because `ProcessReceipt` only carries ProductId and PlayerId, not the recipient.
- Gift ids: Robux = `R` + PurchaseId (so a re-delivered receipt yields the same id); admin = `A` + GUID.
- **Giftable catalog** (shared pure module `GiftRules`): `{id, kind = "crystals"|"skin"|"bundle", label, crystals?, skins?, productId}`. Product ids are owner-supplied (`Config.GiftProducts`, empty by default).
- **Profile additions (add-only, optional, ignored by the Build 020 reader per [111](111-rollback-drill.md)):** `ownedSkins = {[skinId] = true}`, `claimedGifts = {[giftId] = timestamp}` (cap 5,000, fail closed like `purchaseReceipts`).
- Private state ([112](112-private-state.md)): the pending-gift count and popup payload go through the owner-only `PrivateState` channel, never Player attributes.

## 7. Exactly-once delivery
1. **Buy:** server stores `intent`, prompts the product. In `ProcessReceipt`: if `done[purchaseId]` exists, re-deliver the same Gift (idempotent) and return Granted. Else read the intent, build the Gift, **add it to the recipient inbox**, mark `done` on the buyer record, return `PurchaseGranted`. Any store failure returns `NotProcessedYet` (Roblox retries).
2. **Claim (the recipient's own server):** on join after the profile loads, and every 60 s while online: read the inbox; run one `ProfileRepository` transaction (`UpdateAsync` on the profile, lease-checked) that, for each gift not in `claimedGifts`, applies it (crystals under `MaxCrystals`, skins into `ownedSkins`) and records `claimedGifts[id]`. Crystals that would exceed the cap leave the gift pending rather than losing it.
3. **Cleanup:** after the profile commit, remove those ids from the inbox. A crash between 2 and 3 only causes a harmless no-op re-claim (already in `claimedGifts`).
4. A receipt redelivered after the gift was claimed and removed re-adds it, and `claimedGifts` blocks a second grant.
- `ProcessReceipt` stays the single Marketplace entry point; the gift branch is delegated to `GiftService`. `tools/verify_robux_line.py` must be extended (allowed purchase files, "gift credits only catalog items, no power words").

## 8. Failure cases
| Case | Behaviour |
|---|---|
| Username unknown / self / invalid | Kid-friendly message, no prompt |
| `GetUserIdFromNameAsync` fails (HTTP, throttled) | "Try again in a minute", no prompt |
| Recipient inbox full (25) | Blocked before the prompt: "Their gift box is full" |
| `PolicyService` restricts buyer | Gift button hidden |
| Prompt closed / not paid | Nothing happens; intent expires after 10 min |
| Store write fails during `ProcessReceipt` | `NotProcessedYet`; retried by Roblox |
| Intent missing at receipt (server hop) | Gift goes to the BUYER's own inbox with a note (never lost, never to a wrong person) |
| Recipient at crystal cap | Gift stays pending: "Make room, then open your gift" |
| Recipient has "no gifts" setting | Prompt refused before purchase; admin gifts bypass it |
| Recipient banned/deleted account | Gift stays in the inbox (25 cap); admin can clear |
| Lease lost / profile busy during claim | Retry next tick, no partial apply |
| Message fails the text filter | Sent without the message |

## 9. Test plan
Offline Luau (`tools/verify_gifts.py`, added to the CI workflow together with the flag-gating checks):
1. Receipt idempotency: same PurchaseId twice gives one inbox entry; redelivery after claim does not re-grant.
2. Exactly-once claim: two servers claim concurrently (mock store), one grant.
3. Offline claim: gift written while the recipient has no session; granted on load.
4. Admin allow-list: non-admin, negative id outside Studio, flag off all refused; rate limit; amount clamp; no profile write from the admin handler.
5. Flag gating: all flags false in `Config`; handlers return "unavailable"; release profiles pin the flags off.
6. Rules: self, invalid ids, forbidden item kinds (egg, dino, species) rejected; every catalog entry free of power words.
7. Crystal cap defers, never loses; `claimedGifts` cap fails closed.
8. Re-run `verify_robux_line`, `verify_private_state`, `verify_rollback` (the Build 020 reader still loads profiles with the new optional fields), `verify_multiplayer_sim`, `verify_release`.
Not testable offline, owner/Studio later: real product prompts, `GetUserIdFromNameAsync`, `TextService` filtering, popup layout on a phone.

## 10. Questions for the owner (all decided by the LEAD, owner delegated 2026-10-16)
Marker used below: **LEAD decision (owner delegated 2026-10-16)**. The owner may overrule. Robux gifting stays flag-off: "decided in principle, enable needs owner go-ahead".

1. Who may receive: anyone, friends only, or recipient opt-in? (Recommended: friends only by default for a children's game, plus the Settings switch.) **LEAD decision (owner delegated 2026-10-16): friends only.** The recipient's Settings row "Gifts" has two values, "From friends" (default) and "Nobody"; there is no "Anyone" at launch. The buyer's server checks the friendship (`Player:IsFriendsWith` for players in the server, `Players:GetFriendsAsync` paging for a typed username) before the purchase prompt. The recipient's choice is mirrored into the Gifts store (`pref_<userId>`, written on join and on change) so an offline check works; a missing record means "From friends". Admin gifts bypass it. Reason: children's game, no stranger contact, simplest to explain, and the spec's own recommendation.
2. Which items are giftable at launch: skins only, or also crystal packs and bundles? What goes in a bundle? **LEAD decision (owner delegated 2026-10-16): skins first.** Robux gifting launches with skins only (fixed, named, account-wide entitlements, [137](137-dino-skins-spec.md)). Crystal packs become giftable only after `CrystalPacksEnabled` has been playtested. A "bundle" is a fixed, named set of skins shown before buying; no eggs, dinos, species, luck or anything random in any bundle. Admin free gifts can send skins and crystals from day one (no Robux). Reason: skins are the only item with an owner record to receive, and crystal packs are themselves still untested.
3. Skins per species or per account ([97](97-dino-skins.md) open decision 1)? A gifted skin needs an owner record for it. **LEAD decision (owner delegated 2026-10-16): per ACCOUNT, per style** (`ownedSkins[styleId]`), the same answer as [137](137-dino-skins-spec.md) Q1. Reason: one purchase fits every species, no 88-product trap for children, survives fusion, and gives gifts exactly one owner record.
4. Gift prices: same as buying for yourself, or a small markup? **LEAD decision (owner delegated 2026-10-16): the same price, no markup.** Each gift product mirrors its own-use product. Reason: a markup would feel like a trap for kids and invites questions from parents; the Robux amounts themselves are the owner's to set in Creator Hub.
5. Show the sender's name or just "a friend" (privacy)? **LEAD decision (owner delegated 2026-10-16): show the sender's display name, no anonymous gifts.** Because only friends can send, the name is already known; it appears only inside the popup and is never logged (UserIds only). Reason: anonymity helps abuse and is not needed in a friends-only flow.
6. Is a typed message wanted at all, or presets only (safer, no filter dependency)? **LEAD decision (owner delegated 2026-10-16): presets only at launch** (about 6 short kid phrases such as "Have fun!", chosen from a fixed list). Free text is deferred until the owner has tested `TextService` filtering on real accounts. Reason: no filter dependency, no free text between children.
7. Should admin gifts show a "from the Be Dino team" label? **LEAD decision (owner delegated 2026-10-16): yes**, admin gifts always read "A gift from the Be Dino team!", the admin's own name is never shown. Reason: clear, warm, and no personal data.
8. Owner tasks (Creator Hub): create one gift developer product per catalog item, record ids in `Config.GiftProducts`, set prices. Add these to [120](120-pending-owner-uploads-checklist.md) when the build task starts. **LEAD decision (owner delegated 2026-10-16): acknowledged, unchanged.** The products are created only when BD-453 starts and after the skins products exist (BD-459); `GiftingEnabled` stays false and pinned off. Enabling any Robux gifting needs the owner's explicit go-ahead.

### 10.1 What the decisions change in sections 2 to 8
- Player flow (s3, s4): the player list shows only the buyer's friends who are in the server; a typed username must resolve to a friend, else "We could only send gifts to friends." Self and unknown names stay refused.
- Message step: a preset picker, no text box, so the `TextService` row in s8 ("Message fails the text filter") does not apply at launch.
- Failure table: add "Recipient is not a friend or has Gifts set to Nobody" (refused before the prompt, kid copy "Gifts are only for friends").
- Catalog (`GiftRules`): kind `crystals` is added only after crystal packs are playtested; `bundle` means a fixed list of skin ids.
- Build order: BD-451 core and BD-452 admin gifts do not depend on any Robux product; BD-453 (Robux gifting) now also waits for BD-459 (skins Robux purchase).

## 11. Recommended priority
- **Not for session 1.** Session 1 is 4 players with no products or passes ([125](125-friends-playtest-go-no-go.md)); the board's open P0/P1 work is the reward loop, fusion, cave hub and phone checks. Gifting also depends on skins existing ([97](97-dino-skins.md) says implementation not started) and on the Robux line being playtested.
- **Admin free gifts: P2**, the first piece after session 1. No Robux and no policy risk, and it is immediately useful to reward playtesters.
- **Player gifting with Robux: P3**, after skins exist, `CrystalPacksEnabled` has been playtested and the owner has created products. It has the highest policy surface (usernames, text, children), so it ships last.
- Order: BD-450 (spec accepted) > BD-451 (core) > BD-452 (admin page) > BD-453 (Robux gifting).

## Handbook check
Robux line s11a kept (no power, no random); no trading; flags off; no art made; Place1.rbxl untouched; economy numbers unchanged. Nothing here was built or verified in Studio.
