# 229 UI motion presets (BD-1182), 2026-11-13

Status: **Review / test**. Code and offline tests are done. **Not seen in Studio, not seen on a phone, nobody has watched any of it move.**
Why: [228](228-ui-toybox-proposal.md) board 6 (the motion spec of the "Toybox" UI proposal). The numbers are the proposal's (a LEAD design proposal, **not an owner decision**); every number is PROVISIONAL until the owner has seen it in Studio.

Labels: the behaviour below is **CURRENT BUILD BEHAVIOR of the playtest profile only**. The default build is unchanged (flag off).

## 1. The numbers (one place: `src/shared/UIMotion.luau`)

| Preset | Number | From | Reduce Motion |
| --- | --- | --- | --- |
| Window opens | 0.3 s, one "Back" ease-out: starts at 70%, peaks at 103%, rests at 100% | docs/228 | simply there (0 s) |
| Window closes | 0.15 s, hidden at 0.16 s | docs/228 | at once |
| Cards | 70 ms apart, 0.4 s each, at most 8 staggered; card 9 and later appear with card 8 | docs/228 | all at once |
| Button press | sinks 5 px in 80 ms | docs/228 | no sink |
| Button release | pops to 103% in 80 ms, back to rest in 0.12 s | 103% docs/228; 0.12 s LEAD fill-in | no pop |
| News line | top centre, 2.5 s; the same line again while it shows becomes "x2", "x3" and its 2.5 s start again; counter stops at x99 | 2.5 s and the stack docs/228; restart and x99 LEAD fill-ins | shows 2.5 s and stacks, no drop-in |
| Reward | flies to the wallet in 0.5 s, wallet bumps to 118% (0.25 s up and down), the number counts up in 0.5 s as a whole number | 0.5 s and 118% docs/228; 0.25 s and count-up 0.5 s LEAD fill-ins | no flight, no bump, the final number at once |
| Shimmer | every 2.8 s on Legendary and Mythic, one 0.6 s sweep | 2.8 s docs/228; 0.6 s LEAD fill-in | no shimmer |

Why 70%: the standard "Back" ease-out (Roblox `Enum.EasingStyle.Back`, constant 1.70158) goes 10% of its travel past the goal. A peak of 103% therefore needs a travel of 30%. The file works the start out from the peak, so changing `WindowOpenPeak` moves the start by itself. That Roblox's Back uses this constant is the textbook value, **not measured in Studio**.

`UIMotion.luau` is pure: no engine service, no clock, no random. Each function takes the time or the index as an argument and a `reduce` switch (Reduce Motion = `not Theme.MotionEnabled`, the Calm motion setting).

## 2. What is wired (flag on)

- **Menu window open** (`Bootstrap.open` -> `src/client/MotionFx.luau`): when a closed window opens, the panel pops in with the 0.3 s back-out. Changing screens inside an open window does not pop again.
- **Menu window close** (`Bootstrap.close` -> `MotionFx.close`): the scrim fade, the small shrink (96%) and the slide take 0.15 s (0.12 s before), and the window is hidden at 0.16 s (0.13 s before). This is one window for every menu: Crystal Shops, Potion Shop, Eggs, Dino Index, Settings and the rest.
- **Button press** (`Theme.decorate` in `src/shared/UITheme.luau`, so every decorated button in the game): a press sinks the button 5 px in 80 ms and no longer shrinks it to 96%; the release lifts it, pops it to 103% and settles (at 103.5% while a mouse still hovers, as before). Leaving the button lifts it without a pop. The sink is **added** to the button's position step by step, so a layout pass that moves the button while it is pressed is never undone.

## 3. What is NOT wired (numbers and tests only)

- **Card stagger:** no screen calls `UIMotion.card` yet. The shop and Index cards appear as before.
- **News line:** there is no top-centre news line in the game yet; `newsPush` / `newsText` are ready for it (BD-1180, HUD tiles).
- **Reward fly-to-wallet, wallet bump, count-up:** not wired. The wallet lives in Bootstrap, which has 12 bytes left under its size ceiling; the flying crystal also needs a picture and a look in Studio. Today's wallet number already counts up in 0.28 s; that is unchanged.
- **Legendary shimmer:** not wired. The shine itself is UI art (docs/72: no code-drawn final art), so it waits for the kit (BD-1177).

## 4. Flag, files, tests

- `Config.MotionPresetsEnabled`: **false** in Config and in the default profile, **true** in the playtest profile (standing rule [157](157-playtest-profile-newest-features.md)), in the rehearsal list. Free, no Robux. Flag off: `MotionFx.luau` is never required, a button makes no sink object, and every tween is the old one (the test compares them tween for tween).
- **No server change, nothing stored, no economy change, no new art, no sound.**
- Bootstrap: two hook lines. To pay for them one old comment was shortened; Bootstrap is 70,888 bytes (ceiling 70,900, 70,893 before), top-level locals unchanged.
- Files: `src/shared/UIMotion.luau` (pure numbers and timing), `src/client/MotionFx.luau` (window open / close), `src/shared/UITheme.luau` (button), `src/client/Bootstrap.client.luau` (two hooks).
- `python tools/verify_ui_motion.py --runner <luau.exe>` (in CI): every number, the open curve sampled each millisecond (start 70%, peak 103%, rest 100%), the stagger cap, the stack counter, the count-up, Reduce Motion (0 s and the end state for every preset), the real `Theme.decorate` in an engine mock with the flag on and off, the real `MotionFx` with a recording Theme, the flag wiring, **71 mutants**.

## 5. Not verified, and open points

- **Nothing was watched.** Whether the 70% -> 103% pop feels calm (docs/87) or too bouncy, whether 5 px reads as a press without the 3D button art of BD-1177, and whether the pop is visible at all at 80 ms: the owner judges in Studio.
- **Phone:** on a phone the window fills the screen, so the 103% peak pushes its edge about 3% off screen for a moment. Not looked at.
- **"Close 0.15 s fade":** the window is not a `CanvasGroup`, so the panel itself cannot fade; only the scrim fades, with the same small shrink and slide as before. A real fade means making the panel a `CanvasGroup`, which changes how it is drawn and needs a Studio and phone look first.
- **Buttons inside a list or grid layout** ignore their position, so they do not sink; they still pop on release.
- **Hover is 103.5%, the pop is 103%:** with a mouse the release pop is a hair smaller than the hover size it then returns to. Harmless, but it means the pop is mostly a touch effect.
- **"x3" and the copy rule:** docs/72 says no "1.25x" style numbers for children. "x3" here is a count ("three times"), as the board row asks; the owner may prefer "3x" or "(3)".
- The press sink adds one small `NumberValue` named `PressSink` under each button that has been pressed (flag on only).

## 6. How to overturn

- Off again in test builds: set the playtest rule of `MotionPresetsEnabled` to false (one line in `tools/release_profiles.py`).
- Other numbers: `src/shared/UIMotion.luau`; the test pins the docs/228 numbers, so change both.
