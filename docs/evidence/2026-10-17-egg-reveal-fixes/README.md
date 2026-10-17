# BD-519 and BD-525: egg reveal fixes (2026-10-17, Studio)

Method: `python tools/build.py --profile playtest` to an own file, new Studio window, Play, Food worth x10 (admin slider, real mouse), real clicks on EXPLORE ISLAND, HOME, OPEN EGGS, OPEN, AUTO > Help > Common, Next egg. The dino was fed by a client script that steers the Humanoid (same effect as holding a movement key). Two builds: BEFORE = origin/main plus read-only log lines (the log lines changed no behaviour), AFTER = the fix. No attribute, queue or profile value was written by hand.

## BD-519: egg drawn at the top-left corner on the first OPEN

Root cause: `open()` in `src/client/Bootstrap.client.luau` ran `render("hatch")` first. `HatchSequence.play` (inside render) sets the shared modal body to anchor (0.5, 0.5) at BODY_CENTER (430, 299). `open()` then did `body.Position = (18, 106)` and tweened it to (18, 98) for the slide-in. With the centre anchor, that put the middle of the whole hatch stage (egg and all) at the panel's top-left corner. The next Heartbeat puts the body back, so later opens looked fine for one frame; the first OPEN of a session hitches while assets load, so the bad frame stayed on screen.

Numbers (RenderStepped log of the egg frame; Studio rendered about 15 fps):

| Build | Frame 1 egg position | Frame 2 and on |
| --- | --- | --- |
| before | (6, 8), body (-254, 8) | (418, 202) |
| after | (418, 202), body (158, 202) | (418, 202) |

Images (the first frame was held for 6 s on purpose to stand in for the loading hitch, one `Stepped` busy-wait on the first frame):
- `01-BD-519-before-egg-top-left-first-frame.jpg`: the same picture as the owner's [BD-170 image](../2026-10-17-stuck-BD-170/01-egg-drawn-top-left-at-first-open.jpg).
- `02-BD-519-after-egg-centred-first-frame.jpg`: same stall, egg in the panel centre.

Fix: for `hatch` the slide is skipped, any running body tween is cancelled (new `Theme.cancel`), and the body starts from its settled home before `render`. Not covered: phone-size window.

## BD-525: Common on AUTO still showed one "plain" Common egg

Root cause. A live log of every claim result (species text, rarity, settings, notable flag, condition) over about 40 eggs with only Common on AUTO showed: the species is read correctly, the rarity is right, and every skipped egg was a non-notable Common. The Common eggs that stayed on screen were Rainbow ones (`notable=true`, `cond=rainbow`), for example a Common Dimorphodon, "Egg 8 of 30" (`03-...jpg`). Rainbow and Astra eggs are never auto-opened by design, but the hatched dinosaur never shows its egg condition (BD-174), so the reveal looked like a plain Common. Nest eggs (the 11-egg batch of the original report) get +2 condition levels, so they have many more Rainbow/Astra eggs.

Also found by reading the code, not seen live: the 8 s claim watchdog in `hatchState.next` read the shared `hatchPending`. An older claim's timer could fire while a later claim was in flight and reset `autoHatching`, after which Common eggs would be shown. Each claim now has its own serial.

Changes:
- the decision is `EggsLogic.autoOpenDecision` (species parse, rarity, notable rules); an unreadable or unknown species is now never skipped (it used to default to a Common compy);
- per-claim watchdog;
- when the player's AUTO setting covers the rarity and the egg stays only because it is Rainbow or Astra, the reveal heading reads "Rainbow egg! Always shown" (`04-...jpg`, a Common Compy, Egg 3 of 49). BIG, Shiny and mutated eggs already say so on the reveal (`05-...jpg`, a BIG Compy, plain heading).
- `06-BD-525-after-auto-opened-summary.jpg`: the auto-opened summary of the 80-egg batch (counts per rarity).

After-fix Studio run, Common only on AUTO: 80 + 49 eggs; every egg shown was Uncommon or better, BIG, or a Rainbow Common with the new heading. Output: no errors or warnings except the usual UIBlox lines.

Verifier: `tools/verify_eggs_screen.py` (`--runner` luau): species parse for all 22 species and counts 0 to 3, 10 unreadable texts, all 32 AUTO settings x 5 rarities x 9 egg kinds (plain, dirty, cracked, failed splat, rainbow, astra, shiny, big, mutation) with and without the pass gate, the heading rule, and static guards on `Bootstrap` for the handler, the watchdog and the hatch slide.

Not covered: the lock state with `AutoOpenRequiresPass` on, phone size, a second player.
