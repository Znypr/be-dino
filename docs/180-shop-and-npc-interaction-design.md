# 180 Shop and NPC interaction design (BD-1016, research and spec only)

Written 2026-10-18. **Status: spec done; option A BUILT 2026-10-18 (BD-1017) behind `Config.ShopPromptBubbleEnabled` (playtest only), offline proof only, Studio/phone check is BD-1018** (see the LEAD entry in [115](115-decisions-log.md); the bob of s6 was dropped, lines are capped at 24 characters). No game code, no Studio and no profile change in this task; the default build is unchanged. Owner words (2026-10-18, with a screenshot of an orange shop stall in the cave, a round yellow "Open" button floating next to a small green dino): "the shop interactions should be like messages with buttons to click like E to interact, research other Roblox games and how they do it like Grow a Garden or Steal an Egg."

Every statement below is labelled **OWNER TARGET**, **CURRENT BUILD** (read from `src/` today) or **RESEARCH** (read in a browser or on a page, with what was and was not seen). Read with [87 feel](87-vision-and-feel-guide.md), [72 UI copy](72-ui-copy-and-asset-standards.md), [104 cave hub s8](104-cave-hub-design.md) and [114 handbook s6.2](114-handbook.md).

## 1. The answer in short
- **CURRENT BUILD:** a stall shows ONE round yellow "Open" button (96 px) with a small "[G]" under it on keyboards. It says nothing about WHICH stall it is, and the key is G, not E.
- **RECOMMENDED (option A, small):** a friendly **message bubble** above the stall: the stall name, one warm line, and a big key button "[E] Open" (PC), "Tap to open" (phone) or the controller glyph. One press opens the existing shop window. No hold, no auto-open.
- **Key E:** possible and safe at home (section 4). It needs a recorded decision because docs/114 s6.2 and `tools/verify_cave_gate.py` say "G, because E is LEAP". Leap only works in a run; the stalls only work at home.
- **Effort:** small (about one day with the offline checks), plus a short Studio check on desktop, phone view and gamepad.

## 2. How it works today (CURRENT BUILD)

### 2.1 Files and numbers
| What | File | Facts |
|---|---|---|
| Stall prompts (the five menu stalls) | `src/client/HubWalkUpClient.luau`, rules in `src/shared/HubWalkUpRules.luau` | One invisible 1-stud part per stall at the sign, 3 studs above the floor (`PromptHeight`). `ProximityPrompt`: `HoldDuration 0`, `MaxActivationDistance 10`, `RequiresLineOfSight false`, `Style Custom`, key **G**, gamepad **ButtonL1**. `ActionText` is "Open NESTS", "Open POTIONS", "Open FUSE", "Open SHOP", "Open DINOS" but a custom style never shows it. Made only when `Config.CaveHub` is true (playtest profile: on; default profile: off). |
| The button you see | same file, `PromptShown` handler | A `BillboardGui` 96 x 96 px, `AlwaysOnTop`, 2 studs above the anchor, round yellow `TextButton` "Open" (FredokaOne 22, dark purple text and outline). Below it a "[G]" label, only when `UserInputService.KeyboardEnabled`. Tapping or clicking the button calls `InputHoldBegin()` and `InputHoldEnd()`. While shown, G and L1 are bound with `ContextActionService` and sink the input. |
| What a press does | same file | `HubWalkUpRules.trigger`: only when `RunState` is "Sanctuary", no hub trip is running, no `ModalScrim` is visible, and 0.5 s after the last open. Then `ctx.open(destination)` or `ctx.openFusion()`: the same shop windows the HUD rail opens. Walking up never opens anything (owner 2026-10-16). |
| Stalls that have a prompt | `HubWalkUpRules.stations()` from `CaveHubLayout` | NESTS (eggs), POTIONS, FUSE, SHOP (auras, trails, conditions tiles), DINOS (collection). The QUIET SPOT (settings), TOP DINOS and ISLAND gate have no stall prompt. |
| The Heart "Show off" spot | `src/server/CaveShowOff.luau` | A different prompt: default Roblox look, text "Show off", 9 studs, hold 0, **default key E**, default gamepad X. So the same cave shows **[E]** at the Heart and **[G]** at the stalls. |
| Station signs | `src/shared/HubSignCopy.luau`, `CaveHubProps` | Words on the stone sign and a small lamp-lit word above it (readable up to 90 studs). Copy rule: 14 characters, no digits, no jargon. |
| Rail and fast travel | `Bootstrap.client.luau` rail buttons, `HubTravelClient.luau` | Rail buttons open the same windows from anywhere at home (or teleport you to the stall if the Crystal Shop perk is bought, or draw a moss trail). Not changed by this spec. |
| Default profile (Build 020 parity) | `Config.CaveHub = false` | No stalls, no prompts. Shops open from the rail buttons only. |

### 2.2 What a player sees today (from the code; not seen in Studio by this task)
- **PC:** walk to within 10 studs of a sign. A round yellow "Open" button fades in near the sign with "[G]" under it. Press G, or click the button: the shop window opens. Nothing tells you which stall it is except the stone sign you are looking at. A new player who expects "E" presses E and nothing happens (E is Leap, and at home Leap does nothing).
- **Phone:** the same round button, no key hint. Tap it: the window opens. The button is 96 px wide, a good target.
- **Gamepad:** the button shows, but **no glyph**: the hint hides unless a keyboard is connected. L1 works, but nothing says so.
- **Gaps:** (1) "Open" has no object ("Open what?"). (2) No friendly message. (3) Key G is odd for a child who knows "E" from other Roblox games. (4) The button stays visible, and still tappable, when a window is already open, so a tap can fall through (the code only blocks the press, silently). (5) Heart prompt and stall prompts look different. (6) `inputType` from `PromptShown` is ignored; keyboard vs touch is guessed with `KeyboardEnabled` (a touch laptop is both).

## 3. Research: how Roblox games do it (RESEARCH, 2026-10-18)
Method: Claude in Chrome (Edge/Chrome, new tab, read only, no login, no download), plus web search. Pictures were taken as paused-video frames and one wiki image; see section 3.7. **What I could not see is said plainly.** Videos, sounds and timings were not watched or heard.

### 3.1 Roblox itself (official docs, read in full)
- `ProximityPrompt` shows three things: object name (`ObjectText`), action (`ActionText`) and the key (`KeyboardKeyCode`, default **E**; `GamepadKeyCode`, default **ButtonX**).
- `HoldDuration` (0 = a tap), `MaxActivationDistance`, `RequiresLineOfSight` (default **true**), `Exclusivity` (default one prompt per key: if two in-range prompts share a key, only one shows, chosen by where the camera points), `ClickablePrompt` (when false the UI cannot be clicked, except on mobile).
- **Custom look:** set `Style = Custom`, listen to `ProximityPromptService.PromptShown(prompt, inputType)` and `PromptHidden`, build your own UI, and send a click or tap back with `prompt:InputHoldBegin()` and `InputHoldEnd()`. `Triggered` still fires, so server logic stays on it. `inputType` is Keyboard, Gamepad or Touch.
- **Roblox's own sample UI:** a round key chip with the key letter, the action text beside it, the object text small above; on **touch it is scaled up 1.6x and shows a tap-hand icon** (`rbxasset://textures/ui/Controls/TouchTapIcon.png`); on gamepad it shows the button glyph from `UserInputService:GetImageForKeyCode`. Tweens fade it in and out in about 0.06 to 0.2 s.
- **New:** `MaxIndicatorDistance` (default 0 = off) shows a small dot while you are farther than the activation distance but near, `IndicatorShown` / `IndicatorHidden` events, and `ProximityPromptService.MaxIndicatorsVisible`. Needs a Studio check that the engine build supports it.
- Forum advice (summary): do not trust `TouchEnabled` alone (touch laptops); forward taps with `InputHoldBegin/End`; disconnect per-prompt connections on hide (our code already does this with `Once`).

### 3.2 Grow a Garden (Sam's seed shop, gear, sell)
- **Seen (wiki text and pictures):** each shop is a small stall with a striped roof and a wooden **SEED SHOP** sign; the shop keeper (Sam) stands behind the counter with a name bar and a friendship bar above him. A row of **big word buttons at the top of the screen** (SEEDS, GEAR, GARDEN, SELL, PETS) jumps you to a stall (wiki: clicking "SEEDS" teleports you in front of Sam). A separate "Shop" button sits on the left edge.
- **Seen (window):** one panel opens beside the stall so the world stays visible: a green title bar with a calm restock line ("New seeds in 1m 40s"), a yellow RESTOCK button and a red X; big cards with a picture, name, stock, price and a rarity word; sold out is a grey button that says "NO STOCK".
- **Read (guides, not seen):** with a cooked meal in your hand the same keeper offers **Feed** instead of Buy (hold E on PC per one guide; the mobile control is not said anywhere I found). Empty-handed, talking to Sam opens the shop.
- **Not seen:** the exact walk-up prompt. In one paused frame a small icon sits beside the keeper's name bar just before the window appears, but the trigger (press, tap, or walking up) is not proven.
- **Good for kids:** name above the keeper, easy-to-find stalls, one clear window with a big X, jump buttons for anyone who does not want to walk. **Not copied:** many timers and Robux nudges.

### 3.3 Steal a Brainrot, Steal an Egg
- **Steal a Brainrot (read, not seen):** you buy a character off a conveyor by pressing **E** next to it with enough cash; there is no shop window, the prompt sits on the thing itself. (A "hold E" claim in one guide is about a different game.) A captured short did not show the prompt, so the look is **not observed**.
- **Steal an Egg (read, not seen):** a green **Shop** button on the left edge opens a window of passes; eggs are objects in the world. I found no shop keeper to talk to.
- **Good for kids:** the price and the action live on the object; one press. **Risk:** pressing E next to a thing is easy to do by accident when many things are close together; our stalls are 48+ studs apart, so no clash.

### 3.4 Bee Swarm Simulator
- **Read, not seen:** NPC bears give quests and exchanges through a **dialogue**: you walk up, interact, and pick from a few options (for example "Exchange Presents"; translator NPCs offer "give" or "leave"). Shop tents and the dealer shop details were not found.
- **Pattern:** speech bubble plus 2 to 3 option buttons (our option B).

### 3.5 Adopt Me
- **Read, not seen:** eggs are sold by named places and NPCs (the Nursery; a Cracked Egg for 350 from one NPC, a Pet Egg for 600 from another). One low-quality guide says you tap the egg and choose Buy. The captured short showed a spin wheel, not a shop, so nothing was seen.
- **Pattern (general knowledge, unverified):** tap the item, then a small window with a price button.

### 3.6 Blox Fruits
- **Read, not seen:** dealers and quest givers are NPCs you talk to; the reliable pages only name the NPCs and where they stand. One weak page says E talks. The Yes / No style dialogue is **general knowledge, unverified**.

### 3.7 Pictures
`docs/reference/shop-interactions/` holds 4 Grow a Garden pictures (the shop window, the stall with the top buttons, the window over the world, the player at the stall) and `contact-sheet.png` (made with `tools/reference_sheet.py`, [167](167-reference-and-playtest-tools.md)). `sources.json` has the page, the date and the licence note for each. They are LOOK ONLY, not art. **For the other games (Steal a Brainrot, Steal an Egg, Bee Swarm, Adopt Me, Blox Fruits, Pet Simulator 99) no usable frame was captured:** the short clips I opened did not show a prompt (a wheel, a thief chase, a tiny phone-screen clip), the browser screenshot tool stopped drawing for about 20 minutes (the window was not painting; it came back later), and I did not want to burn the time. A follow-up for a person with the games open is in BD-1018.

### 3.8 What the research says, in five lines
1. Stalls are easy to find: a big sign, a keeper with a name above. We have the sign; we lack the name on the prompt.
2. The press is one tap or one key. Hold-to-act is only used for special things (feeding, stealing), not for opening a shop.
3. The shop is ONE window that leaves the world visible, with ONE big close X.
4. Phone players get a button, not a key hint; Roblox itself scales the touch prompt up 1.6x.
5. Games with several choices (Bee Swarm, Blox Fruits) use a short speech bubble with 2 or 3 buttons before anything opens.

## 4. The key: E or G (mismatch, decision needed)
- **Mismatch:** the owner now says "like E". docs/114 s6.2 and docs/104 s8 say key G, "because E is LEAP, F is BITE, C and B open Collection and Eggs", and `tools/verify_cave_gate.py` line 124 asserts `PromptKey == "G"` and `~= "E"`.
- **What the code shows (CURRENT BUILD):** `requestLeap` (Bootstrap) and the server `LeapService` only act when `RunState == "Active"`; bite (`CombatHud`) only when `RunState == "Active"`. The stalls only open when `RunState == "Sanctuary"`. So at home **E and gamepad X do nothing else**.
- **One catch:** `Bootstrap.client.luau` calls `leapRemote:FireServer()` on every E press before it checks anything, if the press was not already used by another handler. Binding E with `ContextActionService` (sink, high priority) while the prompt is on screen makes Bootstrap skip it (`if processed then return`). The server ignores a Leap outside a run, so even without the sink the only effect would be a wasted remote call.
- **Recommendation (LEAD decision, to record in [115](115-decisions-log.md), owner may overrule):** PC key **E**, gamepad **ButtonX** (the Roblox defaults, also what the Heart prompt already uses). Update `HubWalkUpRules.PromptKey`, the `verify_cave_gate` assertion and docs/114 s6.2 in the build task. Keep G as a second key? No: one key, one glyph.

## 5. Options

### Option A: message bubble with a key button (RECOMMENDED)
A speech-style bubble above the stall, always facing the player:
```
   PC                           Phone                        Gamepad
 .--------------------.       .--------------------.       .--------------------.
 |  Potions           |       |  Potions           |       |  Potions           |
 |  Fresh potions!    |       |  Fresh potions!    |       |  Fresh potions!    |
 |  [ E ]  Open       |       |  [hand]  Tap to open|      |  [ X ]  Open       |
 '---------v----------'       '---------v----------'       '---------v----------'
```
Press the key, tap anywhere on the bubble, or press the controller button: the existing shop window opens. **For kids:** the whole bubble is the target (232 x 112 px, far above 44 px), words are short, it says which stall it is, it uses the key they already know from other games.

### Option B: stall speech bubble with 2 or 3 choices
```
 .--------------------------.
 |  Hi! Need something?     |
 |  [ Buy eggs ] [ Potions ]|
 |  [ Bye! ]                |
 '--------------------------'
```
Closest to "messages with buttons", and what Bee Swarm does. **Cost:** every shop gets one extra tap before it opens; most of our stalls have ONE window, so the choice buttons would all go to the same place. The SHOP stall already has its own choice screen inside the window (`ShopTiles` landing). Medium effort (a new dialog UI, more copy, more art). **Use later** only if a stall gains a second real choice.

### Option C: window opens by itself when you walk up
Fastest, no key to learn. **Rejected:** owner decision 2026-10-16 (docs/114 s6.2: "A shop or station NEVER opens because the player walked near it"; the dwell auto-open was removed on purpose). It also pops windows over children who are only passing by, and `verify_cave_gate` asserts no auto-open API exists. A "step back to close" rule is not needed when the window never opens by itself: closing stays on the big X and Escape.

### Recommendation
**A now, B only where a stall truly has two choices, C no.** Reasons for children: big targets, short words, the same key as other Roblox games, nothing opens by surprise, no hold on any device, and it is a small change next to B.

## 6. Exact states (option A)
| State | When | What the player sees and hears |
|---|---|---|
| Far | more than 10 studs from the sign | Nothing new. The stone sign and its lamp-lit word are the landmark. (Optional, later: a small glowing dot from 22 studs with `MaxIndicatorDistance`, only if Studio supports it.) |
| In range, idle | within 10 studs, at home, no window open | The bubble fades in over 0.15 s (instant with Reduce Motion) with the stall name, one warm line and the key button. It floats up and down by 3 px every 2.5 s (still with Reduce Motion). No sound. |
| Pressed | key, tap or controller press | The button squashes to 92% for 0.08 s (no squash with Reduce Motion), one soft `ui_click` cue (the existing cue, volume 0.4 through `Sfx.Master`; unheard by agents), the bubble fades out in 0.1 s, the window opens. The 0.5 s gap in `HubWalkUpRules.trigger` stays. |
| Window open | any shop window or `ModalScrim` visible | The bubble is **hidden** (`prompt.Enabled = false` on every stall prompt) so a tap cannot fall through. When the window closes it comes back after 0.3 s. |
| Not now | in a run, a hub trip is running, or still loading | The bubble is hidden, not shown as a dead button. (Today it shows and does nothing.) Rail buttons keep their "At home" hint. |
| Too far | you walk beyond 10 studs | The bubble fades out in 0.1 s. A window that is already open stays open until the X (no auto close). |
| Two stalls close together | never (pads are 48+ studs apart) | `Exclusivity` stays at the default. |

## 7. Copy (docs/72 style: short words, no jargon, no digits, no "menu", "station", "teleport")
| Stall | Name line (same as the sign) | Message line (max 28 characters) |
|---|---|---|
| nests | Nests | Come and see your eggs! |
| potions | Potions | Fresh potions here! |
| fusion | Fuse | Make a stronger dino! |
| style | Shop | Auras and trails! |
| index | Dinos | Meet all your dinos! |
| Heart (show off) | Show off | Let everyone see you! |

Button line: PC "Open" next to the key chip `E`; phone "Tap to open"; gamepad "Open" next to the X glyph. **PROPOSED copy**, the owner or lead may change any line; tone from [87](87-vision-and-feel-guide.md). Put the message lines in `HubSignCopy` (one table, one `acceptable()` check, 28 character cap) so the existing sign check also guards them.

## 8. Look (no code-drawn art)
- Colours from `UITheme.Colors` only: cream bubble panel, dark purple text, the existing gold button (255, 210, 43 family; the current prompt already uses 255, 200, 70). Font FredokaOne, name 20 px, message 16 px, button 20 px. All text at least 14 px.
- Shapes are plain `UICorner` and `UIStroke` frames (the same as every menu today). The key chip uses the key's letter as text. **Gamepad and touch glyphs come from Roblox's own engine images** (`UserInputService:GetImageForKeyCode`, `TouchTapIcon.png`), as Roblox's default prompt does. Those are not our art; register them as "engine asset, placeholder for an owner icon" in [77](77-asset-registry.md). An own tap-hand icon is an optional art task (P3, [72](72-ui-copy-and-asset-standards.md) flow).
- Size at 640 x 360: the bubble is 232 x 112 px, a third of the screen height. That is large; use 200 x 96 when `ViewportSize.Y < 480` (the target stays above 96 px wide). Check in the Studio phone emulator.

## 9. Accessibility
- **Reduce Motion** (`UITheme.MotionEnabled == false`): no bob, no squash, instant show and hide. The bubble is still found by its text and shape.
- **Text size** ("Text size Normal / Big" is specified in [103](103-ui-research-popular-games.md); read the setting if it exists in the build, else ignore): Big = 1.25x text, bubble grows to fit, never below the sizes above.
- Not by colour alone: key chip shows a letter or glyph; text contrast dark purple on cream and gold is high.
- Input: choose the glyph from `PromptShown`'s `inputType`, and re-check on `UserInputService.LastInputTypeChanged` so a player who picks up a controller sees the right button. Touch laptops get the key hint while a keyboard is the last input.
- One soft cue only; nothing is loud or sharp ([87](87-vision-and-feel-guide.md)).

## 10. Where it plugs into the code
| Change | File |
|---|---|
| **New** client module (~120 lines): builds and removes the bubble from `PromptShown`; reads `BubbleTitle` and `BubbleLine` attributes from the prompt; handles tap, key, gamepad, Reduce Motion, hide-while-a-window-is-open | `src/client/HubPromptBubble.luau` (new) |
| Call it, delete the old round-button block (about 30 lines move out) | `src/client/HubWalkUpClient.luau` |
| Key, gamepad button, sizes, `bubbleLines(station, inputKind)` as a pure function | `src/shared/HubWalkUpRules.luau` |
| Message lines and the 28 character rule | `src/shared/HubSignCopy.luau` |
| Heart "Show off": `Style = Custom`, attributes `HubWalkUp`, `BubbleTitle`, `BubbleLine`, so it gets the same bubble and the key E stays | `src/server/CaveShowOff.luau` |
| Key text, docs | `docs/114` s6.2, `docs/104` s8, `docs/116` (row for the E mismatch), `docs/77` (engine glyphs) |

**Bootstrap risk:** `Bootstrap.client.luau` has only about 190 bytes under its ratchet and no spare local registers (BD-1008 in [the kanban](07-kanban.md), `verify_local_budget`). **Do not touch Bootstrap.** The bubble belongs in the new module because `HubTravelClient` already requires `HubWalkUpClient` (and `verify_cave_gate` asserts Bootstrap is untouched). The only coupling to Bootstrap is the E press, solved by the `ContextActionService` sink the code already uses for G.

**Other risks:** (1) engine glyph images may not load in every client; fall back to the key letter. (2) `RequiresLineOfSight` is false on purpose (stalls are in alcoves); keep it. (3) A big dino's root may be farther from the sign than 10 studs when its nose is at the sign: check with the biggest dino and raise to 12 if needed. (4) Hiding prompts while a window is open must also restore them after fast travel and after a window closes by Escape: use the existing `ModalScrim` visibility signal, not a timer. (5) Touch: the whole bubble is a `TextButton` inside the billboard, never a world click. (6) Gamepad: `ButtonX` also has no other use at home; keep the sink so it cannot bite. (7) Keep the paid and debug lines closed; this touches no purchase, remote or save.

## 11. Test plan
- **Offline (no Studio):** extend `tools/verify_hub_walk_there.py` (message copy: length, no digits, no forbidden word, one per station) and `tools/verify_cave_gate.py` (key is E, gamepad X, no auto-open API, Bootstrap untouched); add `tools/verify_hub_prompt_bubble.py` running `HubWalkUpRules.bubbleLines` for every station and input kind (keyboard, touch, gamepad) and checking sizes (target at least 96 px wide, text at least 14 px). Also run `verify_local_budget`, `verify_server_module_size`, `verify_doc_ids`, `verify_handbook`, `verify_rollback`, `verify_profile_golden`, `verify_switch_on` and the playtest rehearsal ([152](152-switch-on-rehearsal.md)). Add the CI line to `.github/workflows/build-generated-place.yml`.
- **Studio (BD-1018):** playtest profile, desktop view: walk to each of the 5 stalls and the Heart; check the bubble text, E opens, nothing opens by walking, the bubble hides when a window is open and returns after closing, Reduce Motion on and off. Phone emulator 640 x 360 and a real phone if the owner has one (BD-085): tap the bubble, size, thumb reach. Gamepad: glyph shown, X opens. A picture of each state goes to `docs/evidence/review-2026-10-17/`. **Not claimed until done.**
- Sound: unheard until the owner listens.

## 12. Effort and kanban
- **Option A: small** (about one day: ~120 new lines, ~40 changed, 3 checks, one Studio pass). **Option B: medium** (a dialog window, copy for each stall, art, tests; about three days). Option C: not wanted.
- Rows: **BD-1016** (P1, Backlog, this spec: done) and sub-rows **BD-1017** (P2, build option A) and **BD-1018** (P2, Studio and phone check, plus screenshots of the other games' prompts). Touches [BD-289](07-kanban.md) (walk-up prompts), BD-293 (cave acceptance on a phone), BD-391/405 (fast travel), BD-085 (phone measuring).
- Decisions for the owner: only one, and it is delegated: **LEAD decision, 2026-10-18 (owner delegated 2026-10-16):** build option A with key E and gamepad X. Options not picked: B (extra tap), C (breaks the 2026-10-16 owner rule). To overturn: tell the lead; nothing is built yet.
