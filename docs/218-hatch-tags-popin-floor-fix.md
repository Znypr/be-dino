# 218 Hatch tags: the pop-in floor fix (BD-1153) and the colour chip (BD-1154)

Label: **CURRENT BUILD** change plus **OFFLINE EVIDENCE** (Luau mock, 2026-10-19). **Not Studio evidence.** A Studio re-check is row BD-1159.

## 1. Cause (confirmed in the code, matches docs/217 section 3)

`ModalCompact.floorPass` raises every text in the open screen to 14 px on screen. It computed the floor as `ceil(14 / scale)`, where `scale` was the product of EVERY `UIScale` between the label and the panel (`ancestorScale`). A hatch ribbon, stop tag or card is created with its own `UIScale` of 0 and grows to 1. Near 0 the floor is huge (14 / 6e-8 = 229112335). The engine clamps `TextSize` to 1 .. 100, so the word was drawn at 100, and then `designValue` read the clamped 100 as the new design size (`CmBaseText = 100`), so it never came back. `HatchTagLayout` itself answered 24 to 28 at every scale (the BD-1145 cap in `TagFit.floorSize` is right and stays); the floor pass wrecked the answer afterwards. The old offline mock had no pop-in `UIScale` and ran every tween at once, so everything stayed green.

The old module run against the new smoke reproduces the Studio numbers exactly: the word 100 px, design size 100, 21,591 failed readings.

## 2. What changed

| Part | Change |
| --- | --- |
| `src/client/ModalCompact.luau` `ancestorScale` | Only WINDOW scales count at any value: the scroller fit `BodyFit` and the hatch card fit `HatchBodyFit`. Every other `UIScale` counts only once it is at 1 or more. A pop-in, bounce or fade that is still under 1 counts as 1, so a word never grows because its tag is still small. (docs/217 suggested "ignore under 0.5"; the Fusion result card pops from 0.6 and a tag at 0.55 grew its word to 42 px, so the rule is stricter: nothing under 1.) When the scale reaches 1 nothing changes, so no second pass is needed. |
| `saneFloor` | The floor never asks for a word over 40 px (or twice the design size if that is more) or a button over 100 px (or twice the design size). |
| `floorPass` | `CmBaseText` / `CmBaseH` stay the size the screen asked for. `CmText` stores what the label really holds after the write (the engine's clamp), never the request. Each pass recomputes from the design size, so it is idempotent. |
| `src/shared/HatchTagLayout.luau` `chipPlan` | BD-1154: the colour name and the tier tag share the chip by measure (TagFit). Name first: the biggest size (up to 24) that still leaves the tag room, never under the 14 px floor of the window; if even the floor size leaves no room the tag goes UNDER the name (the chip grows taller); if the chip is too narrow for that, it grows wider (210 up to 252 px). |
| `src/client/HatchSequence.luau` `showChip` | Draws the chip from that plan (measured sizes, not shrink-to-fit). |

## 3. Where else the floor pass meets an animated `UIScale`

The floor pass only runs over the open modal body (`c.body`). Looked at every `UIScale` in `src/`:

| Place | In the body? | Covered |
| --- | --- | --- |
| Hatch ribbons, stop tags (`HatchSequence.ribbon`, `Chip.new` StopTag), rarity pill, `HatchBodyFit` | yes | real hatch screen in the mock, tweens run frame by frame, the pass runs every frame |
| Fusion result holder (pops from 0.6) and pattern step (from 0.7) in `FusionMenu` | yes | same rule; the synthetic table has 0.6, 0.7, 0.9 |
| Index cards | no `UIScale` pop-in (checked: none in `DinoIndexScreens`, `IndexTabs`, `PatternColourCards`) | nothing to cover |
| Run reward amount (`SmallScreens`, 0.92 to 1) and the hatch banner (`Bootstrap`, 0.7 to 1) | the label's OWN scale, which `ancestorScale` never counts | not affected |
| Toasts, rare-find banner, stall bubble, Goals panel, weather title, gift popup | no, they live on the screen layer, outside the modal body; the floor pass never reaches them | not affected |
| Colour chips, pattern chip, condition chip | parented to the effect layer, not the body | not in the pass; the colour chip now uses measured sizes (BD-1154) |

The pattern chip and the condition chip are still shrink-to-fit with a 14 design px minimum; they were not part of the Studio report and are unchanged.

## 4. Checks (all offline)

* `tools/small_window_smoke.luau` (`verify_small_window.py`): a word under a `UIScale` of 0, 1e-8, 0.001, 0.14, 0.3, 0.49, 0.5, 0.6, 0.7, 0.9 and 1 at 6 window sizes, three passes each, on its way up and settled: always 14 to 40 px, design size unchanged, equal to a word that never popped in; the same under a real window scale of 0.3 (cap). The REAL hatch screen with tweens that run for real (the mock tween used to jump to the goal): the pass runs every frame, every ribbon and stop-tag word stays in 14 to 40 with `CmBaseText` equal to the size it was asked. The mock now clamps `TextSize` to 1 .. 100 like the engine. Colour chips: 26 colour and tier pairs (all 16 colours plus the longest words with the longest tier words) at 11 window sizes.
* `tools/text_floor_smoke.luau` (`verify_text_style.py`): the same synthetic pop-in table at 12 window sizes.
* `tools/verify_tag_fit.py`: the pure chip plan for 16 colours x 6 tier words x 7 scales.
* Mutants (each must fail): every `UIScale` multiplied in, only under 0.5 ignored, no cap, the clamp stored as the design size, the old chip boxes, the tier tag that ignores the name, a chip that never grows wider, a name that shrinks under 14, an unmeasured tier tag.

## 5. Not verified

Studio. The real font, the real tween curve (Back easing overshoot), the real engine clamp and `AbsoluteSize` were not available; the offline estimate of word width is TagFit's (a little wider than the real font). Phone, gamepad, Shiny and Blood Moon hatch were not tried. Re-check row: BD-1159.
