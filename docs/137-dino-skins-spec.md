# 137 Dino skins: full spec (docs only, 2026-10-16)

**Status: SPEC. Nothing here is built.** Task: BD-224 (this spec) and new Backlog rows BD-454..BD-459. Extends [97](97-dino-skins.md) (owner idea and decisions), which stays the idea record. Owner rule: features are specced and prioritized before being built. Everything below is a **proposal**; **the 15 questions of section 15 were decided by the LEAD on 2026-10-16 under the owner's delegation ("take full autonomy, do decisions for me")**, summarised in [115](115-decisions-log.md) "LEAD decisions 2026-10-16 (owner delegated)". The owner may overrule any of them. Every Robux part is decided in principle only: flags stay off and enabling Robux sales needs the owner's go-ahead. Facts already decided by the owner are marked OWNER.

## 1. Decided so far (OWNER, do not reopen)
- Base look for every dino is **low-poly** (faceted, flat-shaded, generated mesh, split into body parts) ([97](97-dino-skins.md), [115](115-decisions-log.md) D14, [114 s7](114-handbook.md)).
- Robux skins: **Bricks, Clay, Plushy, Balloon** (Balloon decided 2026-10-16, defeat = pops and flutters away softly). Animated-movie and Anime are **unlockable** (crystals or a season pass, still open).
- Skins are **cosmetic only**; never stats, growth, size, speed or odds. Robux line ([114 s11a](114-handbook.md)): looks only; `PolicyService` is not needed unless a skin is ever random (it is not: fixed, named, shown before buying).
- Every skin has a gentle, funny defeat animation (about 1.5 s, no gore, Reduce Motion = fade). Hook exists: `LowPolyPose.sampleDefeat(..., skin)` and the visual attribute `LPSkin` (Base, Plush, Clay, Bricks), behind `Config.LowPolyDinos` (false) ([97](97-dino-skins.md) BD-249).
- Auras and trails belong to ONE dino instance and are lost on fusion ([115](115-decisions-log.md), [46](46-pattern-fusion-dino-identity-and-cosmetic-progression.md)).
- Gifting ([134](134-gifting-spec.md)) depends on skins: a gifted skin needs an owner record, `ownedSkins`.

## 2. What a skin is (three layers, kept separate)
| Layer | Meaning | Belongs to |
|---|---|---|
| **Entitlement** | "I may use style X" (Plushy, Clay, ...) | The ACCOUNT (`ownedSkins`) |
| **Model availability** | "Species S has a Plushy model" | The GAME (asset registry, not the player) |
| **Equipped choice** | "This dino copy currently wears Plushy" | The dino INSTANCE (`skin`), plus an account default |

Recommendation (OWNER decides, Q1): **buy a skin STYLE once for the whole account** (one purchase, usable on every species that has the model); **equip it per dino instance**; a "Default skin" setting applies to dinos with no choice. Reasons: a per-species price (22 x 4 = 88 products) is unmanageable and feels like a trap for children; a per-instance purchase would be destroyed by fusion (consumed inputs, [46](46-pattern-fusion-dino-identity-and-cosmetic-progression.md)) and conflicts with the account-level `ownedSkins` already specced in [134 s6](134-gifting-spec.md). Unlike auras and trails (instance-bound by owner decision), a skin purchase therefore **survives fusion** because the entitlement lives on the account; only the equipped choice on the consumed inputs disappears (the new output starts on the account default, see s4).
Rejected alternatives: per-species purchase (product explosion), per-instance purchase (lost on fusion, refund pressure).

## 3. Skin catalog (first set)
| Id | Name | Acquire | Defeat | Notes |
|---|---|---|---|---|
| `Base` | Low-poly (default) | Free, always | stars, flop, poof | Always available, also the fallback |
| `Plush` | Plushy | Robux (flag) | deflates with a soft "pfff" | Stitched seams, fabric tint |
| `Clay` | Clay | Robux (flag) | squishes flat, reshapes | Fingerprint texture |
| `Bricks` | Bricks | Robux (flag) | falls into bricks, clicks back | Per-brick-region gene colour |
| `Balloon` | Balloon | Robux (flag) | pops, flutters away softly | OWNER 2026-10-16; see Q9 |
| `Anime`, `Movie` | Anime / Animated-movie | Crystals or season pass (Q3) | to decide | Later, after the first four ship |

Later candidates ([97](97-dino-skins.md)): crystal low-poly, golden statue (fusion reward), glow/neon. `LPSkin` currently knows Base, Plush, Clay, Bricks; adding `Balloon` is a small additive change when its task is built.

## 4. How skins combine with everything else
- **Fusion tiers (Base > Gold > Emerald > Diamond):** the tier is a **sheen and trim layer on top of any skin** ([97](97-dino-skins.md)), not a separate model. Gold Bricks = gold-tinted bricks with a metal sheen; the tier layer reads the existing tier attribute and applies a shared overlay (one material tweak, no per-skin per-tier model). Skins never contribute to fusion odds, rarity or prestige ([46](46-pattern-fusion-dino-identity-and-cosmetic-progression.md): bought cosmetics never feed rarity).
- **Fusion output:** a fused dino is a NEW instance and starts on the account default skin (Base unless set). The entitlement is account-wide, so a skin is never an item in the irreversible loss warning (auras and trails still are, unchanged).
- **Gene colours and patterns:** must stay visible on every skin in the skin's own way: Plush = tinted fabric with the pattern as stitched/printed panels; Clay = tinted clay with the pattern pressed in; Bricks = one gene colour per brick region, pattern as brick colour groups; Balloon = glossy gene-colour film. Existing pattern masks (`tools/verify_lowpoly_patterns.py`) are the starting point. **The technique must be proven on ONE species first** (Compy) before any rollout (BD-455).
- **Conditions (Dirty, Cracked, Rainbow, Astra), Shiny, BIG, event mutations:** keep their current visual cue on every skin (a skin must not hide Shiny sparkle or Astra glow). Condition, Shiny and mutation VFX attach to the same anchors as today, above the skin; each skin passes a "can I still tell it is Shiny/Astra?" check in the pilot.
- **Auras and trails:** independent of skins (instance-bound, bought separately). A skin may not hide an aura; budgets in [126](126-fx-budgets.md) and BD-432 apply. Bricks and Balloon spawn no extra particles beyond the defeat moment (idle flavour is animation/sound only).
- **Classes (Ground, Fly, Water, Armored):** the same rig and part names for every skin of a species, so class movement ([101](101-hp-combat-classes-animations.md)) works unchanged; a skin never changes hit boxes, size or collision.
- **Index / collection:** a dino page shows the dino in its equipped skin; Index "owned" logic is by species and genes, never by skin. Skins create no new collection entries.

## 5. Shop flow and Robux line
1. **Skins tab** in the Shop (layout rules in [72](72-ui-copy-and-asset-standards.md), shared FxUi card style). Cards: large 3D preview of the player's own favourite/last-used dino wearing the skin, name, price, one short line ("Falls into bricks!"). Owned skins show **Wear** instead of the price.
2. **Buy:** Robux developer product or game pass per skin STYLE (one product each, ids owner-supplied in `Config.SkinProducts`, empty by default). Normal Roblox purchase prompt; the server grants `ownedSkins[id]` in `ProcessReceipt` (single Marketplace entry, idempotent via `purchaseReceipts` as today). **Exact item and price shown before paying; no random, no unknown-contents bundle.** Because it is fixed and direct, `PolicyService` is not required for skins; Robux buttons are hidden unless `SkinsRobuxEnabled` and the existing Robux release flags allow them.
3. **Equip:** on the dino page ("Skin" row with thumbnails of owned styles) and a quick picker; the server validates ownership and model availability, then sets the instance `skin`. Equip is free and instant.
4. **Try before buy:** the preview is the try-on; no free trial equip inside a run.
5. **Gifts:** skins are a giftable catalog kind in [134](134-gifting-spec.md); the same `ownedSkins` record receives them. Admin free grants use the same path (BD-452).
6. Crystals: only for the later unlockable styles (Q3). Never crystal-and-Robux for the same item at launch (one clear line).
Copy rules ([72](72-ui-copy-and-asset-standards.md)): short plain words for kids; no "limited time" pressure text; no countdowns.

## 6. Preview UI
- Reuse the dino-card viewport (Index/dino page) so no new rendering stack is needed; a skin carousel rotates through owned and shop skins on the SAME dino; tap the dino to play its defeat animation once ("Watch it fall!"), skipped under Reduce Motion (shows the fade).
- Phone first: one card visible at a time, thumb reachable, no horizontal scrolling inside scrolling lists.
- Locked styles still preview in full colour (previewing is the sales surface); a species without a model for that style shows "Coming soon" instead of a broken or Base-looking preview.
- Defeat sound previews only on tap, never auto-play.

## 7. Data model (additive, safe for the Build 020 reader, [111](111-rollback-drill.md))
Profile (all optional, ignored by older readers):
- `ownedSkins = {[skinId] = true}` (account entitlements; the same field [134](134-gifting-spec.md) reserves, so there is exactly ONE owner record).
- `defaultSkin = skinId?` (account default; invalid or unowned falls back to `Base`).
- Dino instance record: `skin = skinId?` (absent = use the account default). No other instance field changes.

Rules:
- A missing, unknown or unowned `skin` always renders `Base` (fail safe); the server clamps on load and on equip.
- Unknown skinIds from a newer build are kept untouched (forward compatible) but render Base.
- Writes go through the existing lease-checked `ProfileRepository` transaction; no new DataStore. Entitlements are added only by receipt, gift claim or admin grant; removed only by an owner/admin revoke (Q10).
- Config: `src/shared/SkinCatalog.luau` (pure module): `{id, label, kind = "free"|"robux"|"crystals", productId?, defeat, sheen}`; tested offline.
- `LPSkin` stays the single render input; the server stamps it from the validated instance `skin`. The owned list uses the owner-only `PrivateState` channel ([112](112-private-state.md)); other players only ever see the equipped style through the visual attribute.
- Remotes: `SkinAction` (equip, setDefault), rate limited and validated; there is no purchase remote (purchases only through Marketplace).

## 8. Asset pipeline per skin
Rule: **generated meshes only** for 3D, no code-drawn art ([114 s12](114-handbook.md), D15). Per species and style:
1. Prompt the Roblox mesh generator (`generate_mesh`) with the species reference ([100](100-species-visual-reference.md)) plus the style words (stitched plush toy, claymation, toy brick, glossy balloon). Generate the body as parts (body, head, tail, legs, plus jaw/wings/fins per class) so the existing animator ([101](101-hp-combat-classes-animations.md)) drives every skin with the same part names and pivots.
2. Check with `tools/verify_mesh_sanity.py` and `tools/verify_lowpoly_budget.py`; register like the existing low-poly meshes; add a line to [77](77-asset-registry.md) for every asset.
3. Materials and textures are generated materials or Blender renders, never code-drawn; the owner judges the look in Studio before any release.
4. Per-skin extras: Bricks needs a brick-region colour map for gene tinting; Plush a seam decal; Clay a fingerprint normal map; Balloon a gloss tweak plus a pop effect. Gene colour passes reuse the existing pattern/colour system, not hand work per species.
5. Anything that must be uploaded to Roblox goes on [120](120-pending-owner-uploads-checklist.md). No asset ids are invented.

**Which species first:** Compy, Raptor, Triceratops (the three low-poly pilot species, [97](97-dino-skins.md)). The first skin proof is **Compy only, Bricks and Plushy** (BD-455): Compy is the first dino every player owns, and Bricks/Plushy are the two hardest tests (hard-edged vs soft deformation; per-region gene colour vs fabric tint). Then Raptor and Triceratops (Ground and Armored shapes), then Fly and Water representatives, then the rest. Never sell a style for a species without a verified model.

## 9. Performance and budget
- One skin per dino at a time; no per-skin extra scripts per dino. Animation stays in the single `LowPolyAnimator` loop.
- Part and triangle budget: a skin variant stays within the same caps as the Base model of that species (`verify_lowpoly_budget.py`). Bricks (many small parts) is the risk: proposal is a fixed brick-region count per species (about 3 x the species body-part count, tuned in the pilot), MeshParts not Unions.
- Only skins actually worn in the server are loaded (lazy, streamed with the dino); never all 88 variants at start.
- Defeat effects: pooled, one-shot, under 1.5 s, counted inside the phone FX budget (`tools/qa/phone_budgets.json`, [126](126-fx-budgets.md)); crowd rule (proposal): when more than 6 dinos are defeated within 2 s, nearby ones fall back to the cheap fade.
- Texture sizes follow the existing low-poly cap; measured on the phone profile before rollout (BD-458).
- Evidence required: phone frame time with 4 players wearing mixed skins (friends playtest cap 4, [125](125-friends-playtest-go-no-go.md)).

## 10. Tests and verification
Offline (new `tools/verify_skins.py`, added to CI):
1. `SkinCatalog` shape: unique ids, valid kinds, Robux skins have no stat/power words and no random/"mystery" wording (extends `verify_robux_line.py`).
2. Equip validator: unowned, unknown and species-without-model all refused; Base fallback on load.
3. Receipt: idempotent grant (same PurchaseId twice = one entitlement); entitlement survives a simulated fusion; a gift claim writes the same `ownedSkins`.
4. Add-only schema: a Build 020 profile still loads with the new fields present (`verify_rollback`).
5. Flags: `SkinsEnabled` and `SkinsRobuxEnabled` false in `Config` and pinned off in default and playtest profiles (`tools/release_profiles.py`); the remote answers "unavailable" when off.
6. Defeat hook: `sampleDefeat` returns bounded values for every skin and class, no motion under Reduce Motion (extends `verify_lowpoly_dinos.py`).
7. Re-run `verify_robux_line`, `verify_private_state`, `verify_lowpoly_*`, `verify_mesh_sanity`, `verify_release`, `verify_doc_ids`.

Studio/owner only (not provable offline): real product prompts, the look of each skin, gene colour readability, phone frame time, sound by ear, shop layout on a phone. None may be reported accepted without evidence.

## 11. Rollout flags and phases
Flags (default false; pinned off in default AND playtest profiles until the owner decides, since session 1 has no products):
- `SkinsEnabled` (render and equip of owned/free skins; requires `LowPolyDinos`; also gates the Skins tab, so no third flag).
- `SkinsRobuxEnabled` (Robux buttons and the receipt branch; also needs the existing Robux release flags and owner-created products).

Phases: P0 spec accepted (owner answers s15) > P1 Compy pilot (Bricks, Plushy), Studio-only > P2 data model, equip and preview UI, skins free in Studio only > P3 the three pilot species, defeat sounds judged by ear > P4 shop and Robux receipts once products exist > P5 widen species by class > P6 Balloon, Anime, Movie. **LEAD gate (owner delegated 2026-10-16, section 15 Q8, Q15):** P1 may run in parallel with other work; P2 onwards waits for the owner's phone verdict on the low-poly base; P4 Robux sales may not go live until the three pilot species and one species per class have the style; Anime and Movie (crystals only) are P6.

## 12. Dependencies and conflicts
- Needs `LowPolyDinos` as the base look (false in default, true in the playtest profile).
- Gifting ([134](134-gifting-spec.md)) needs `ownedSkins` (defined here); BD-453 is blocked on skins existing.
- Open PR "Fused tiers: Shiny + sparkles, own colours kept" touches tier visuals; re-check the s4 tier overlay when both land.
- BD-432 (aura/trail v4) shares the FX budget with skin defeat effects.
- Wording conflict, not a decision: [97](97-dino-skins.md) still has a "Base (cartoon)" table row while the owner decision says low-poly; this spec treats low-poly as the Base look and the old label as historical.

## 13. Recommended priority (vs the board summary)
Board (2026-10-16): 397 tasks, Backlog P0 6 / P1 35 / P2 31 / P3 8. Live work is the reward loop, fusion, cave hub, combat and phone checks; session 1 (4 friends, no products) is the gate ([125](125-friends-playtest-go-no-go.md)).
- **BD-224 / BD-454 (spec acceptance) were P1; the build work is P2, after session 1.** **Update (LEAD, owner delegated 2026-10-16):** BD-454 is Done (the 15 decisions are recorded in section 15 and docs/115); BD-224 and BD-455 move P1 -> P2: no skin can be sold in session 1, the P1 backlog already has 30 rows, and the pilot only waits for a free generator slot. Their original text follows. Skins are a looks/monetization layer, not the core loop; they cannot be sold in session 1, and the base low-poly look needs the owner's phone verdict first.
- Order: BD-454 (owner answers) > BD-455 (Compy pilot, P1: cheap and answers the biggest unknown, gene colours on a skin) > BD-456 (data model + equip, P2) > BD-457 (preview UI + shop tab, P2) > BD-458 (phone perf + species rollout, P2) > BD-459 (Robux receipts, P3); BD-453 (Robux gifting) follows BD-459.
- The Compy pilot goes early only if a generator slot is free; it must not displace P0 reward-loop or phone-check tasks.

## 14. Risks
Brick part counts on phones; gene-colour readability on Clay/Plush; kids confusing "skin" with power (copy says "looks only"); chargebacks (revoke path); art effort of 22 species x styles (mitigated by class-by-class rollout and "Coming soon").

## 15. Owner questions (all decided by the LEAD, owner delegated 2026-10-16)
Marker: **LEAD decision (owner delegated 2026-10-16)**. The owner may overrule. Anything about Robux is "decided in principle, enable needs owner go-ahead".

1. **Skin ownership:** one purchase per STYLE for the whole account (recommended), per species, or per individual dino? (Same as [97](97-dino-skins.md) open decision 1 and [134](134-gifting-spec.md) Q3.) **LEAD decision (owner delegated 2026-10-16): one purchase per STYLE for the whole account** (`ownedSkins`). Reason: no 88-product trap for children, survives fusion, and gifting gets exactly one owner record.
2. **Equip scope:** equipped per dino copy with an account default (recommended), or one account-wide skin for all dinos? **LEAD decision (owner delegated 2026-10-16): per dino copy plus an account default.** Reason: a child can dress their favourite dino differently, and a fused output simply starts on the default.
3. **Anime / Animated-movie:** unlock with crystals, a season pass, or both? What price or pass cost? In the first release or later? **LEAD decision (owner delegated 2026-10-16): crystals only, later (phase P6), not in the first release; no season pass.** The crystal price is PROVISIONAL and set when those styles are built (a long-term goal priced above the 500-crystal fast-travel perk). Reason: they are the earnable looks, with no Robux twin and no pass or timer pressure for children.
4. **Prices:** Robux price for each of Bricks, Clay, Plushy, Balloon (same for all?), and any crystal price for unlockables. **LEAD decision (owner delegated 2026-10-16): all four Robux skins sit in ONE price tier** (no style is "better" or dearer than another); the Robux amount is the owner's to set when creating the products in Creator Hub (`Config.SkinProducts` stays empty until then), and crystal prices are decided with Q3. Reason: equal pricing is fair and simple to read; money amounts are the owner's call. Decided in principle, enabling needs the owner's go-ahead.
5. **Fusion:** confirm a skin purchase survives fusion (account entitlement) and a fused output starts on the account default skin, not a donor's. **LEAD decision (owner delegated 2026-10-16): confirmed.** A skin is never in the irreversible-loss warning. Reason: a bought look must never be destroyed by a game mechanic.
6. **Tier look:** is a sheen/trim overlay on any skin the right Gold/Emerald/Diamond look, or should tiers get their own full skin variants? **LEAD decision (owner delegated 2026-10-16): a sheen and trim overlay on top of any skin, no per-tier skin models.** This matches the owner's tier rule (same colours and pattern under a tinted coat with an outline, [114](114-handbook.md) s8.6). It does not settle docs/116 Q12 (separate tier art for Emerald and Diamond), which waits for the owner to accept Gold. Reason: one shared overlay keeps 4 skins x 22 species x 3 tiers out of the asset budget.
7. **Species order:** confirm Compy first (Bricks + Plushy), then Raptor and Triceratops; which Fly and Water species next? **LEAD decision (owner delegated 2026-10-16): confirmed.** Order: Compy, then Raptor and Triceratops (both Ground; the "Ground and Armored shapes" line in s8 is read as Ground), then one representative per remaining class: Ankylosaurus (Armored), Pteranodon (Fly), Plesiosaurus (Water), then the rest by class. Reason: the class representatives test every rig family before a wide rollout.
8. **Partial sale:** may a style be on sale before every species has a model ("Coming soon" for the rest), or only once all 22 have it? **LEAD decision (owner delegated 2026-10-16): a style may be sold only when the three pilot species AND at least one species of every class (Ground, Fly, Water, Armored) have it; the rest show "Coming soon" and the card lists the supported dinos.** Never a Compy-only sale. Reason: a child must not pay for a look that fits almost none of their dinos, and waiting for all 22 would delay everything. So the Robux receipts phase (P4) cannot go live before the class representatives exist (the first slice of P5). Decided in principle, enabling needs the owner's go-ahead.
9. **Balloon:** it was described as procedural (no art upload); confirm it goes through the same generated-mesh pipeline as the others. **LEAD decision (owner delegated 2026-10-16): both rules are kept.** Balloon is a treatment of the generated low-poly Base mesh (inflated shading, a glossy gene-colour film capped at the tier-gloss limit, a pop effect) and needs no extra mesh upload; no geometry is built in code. If the Compy pilot shows it does not read as a balloon, it gets a generated mesh through the normal pipeline. Reason: honours the owner's "no art upload needed" and the generated-mesh rule (D8/D15) at once.
10. **Revoke:** may the owner revoke a skin entitlement (chargeback, abuse) from the admin panel? **LEAD decision (owner delegated 2026-10-16): yes, admin only** (`AdminRules.isAdmin`, rate limited, logged by UserId only, no names). A revoked style makes equipped dinos fall back to Base on the next load. Reason: Roblox chargebacks and abuse need a way out, and it touches nothing else in the profile.
11. **Defeat sounds:** who makes the quiet per-skin sounds ([97](97-dino-skins.md) brief) and when does the owner judge them by ear? **LEAD decision (owner delegated 2026-10-16): the pilot reuses the existing soft defeat cue; per-skin sounds are made through the normal sound pipeline (brief, registry line in [77](77-asset-registry.md), handbook s7 rules) and ship only after the owner has listened.** Agents never call a sound fine; it stays "unheard". Reason: agents cannot hear, and silence beats a harsh sound.
12. **Visibility:** should other players see your skin in lobby and arena (recommended yes)? **LEAD decision (owner delegated 2026-10-16): yes.** Performance guard: skins render fully only on the nearest 8 dinos; farther ones show Base (the same nearest-first rule as FX, [114](114-handbook.md) s8.3). Reason: showing off is the point of a cosmetic, and phone budgets stay safe.
13. **Free skin:** should one cosmetic skin be earnable free in play (a milestone reward), or are all four Robux-only? **LEAD decision (owner delegated 2026-10-16): all four stay Robux-only; the free looks are Base (always free) and the crystal-unlocked Anime and Movie styles from Q3.** Reason: no extra unlock system, and an earnable route already exists.
14. **Seasonal/limited skins:** none at launch (recommended for kids, no pressure); confirm. **LEAD decision (owner delegated 2026-10-16): confirmed, none at launch, and no "limited time" copy or countdown on any skin.** Reason: handbook s2 (no pressure timers) and a children's audience.
15. **Pilot timing:** does the skin pilot wait for the owner's phone verdict on the low-poly base look, or run in parallel? **LEAD decision (owner delegated 2026-10-16): run the Compy pilot (BD-455) in parallel when a generator slot is free, Studio-only and flag off; everything after it (BD-456 onwards, any shop work) waits for the owner's phone verdict on the low-poly base look.** Reason: the pilot is cheap and answers the biggest unknown (gene colours on a skin) without committing the profile schema or the shop.

## Handbook check
- Facts checked against AGENTS.md, [97](97-dino-skins.md), [114](114-handbook.md) s11a/s12, [115](115-decisions-log.md) D14 and the Balloon decision, [134](134-gifting-spec.md) and [46](46-pattern-fusion-dino-identity-and-cosmetic-progression.md).
- Robux line kept: looks only, fixed named items, no random, no power; `PolicyService` not needed unless random. Flags default off and pinned off in default and playtest profiles. No code, no art, no asset ids, no economy numbers changed; `Place1.rbxl` untouched. Nothing was verified in Studio.
- Proposals (account-level entitlement, tier overlay, part caps, crowd fallback) are labelled and need owner answers in section 15.
