# 108 Low-poly dinos in the playtest profile (BD-225)

Lead decision 2026-10-16: friends playtests use the cheap low-poly dinos (docs/107: legacy 1,424-2,400 parts per dino, low-poly far fewer). `tools/release_profiles.py`: default profile requires `LowPolyDinos = false`, playtest profile sets it to `true`; `tools/verify_release.py` checks both (tests in `tests/test_release.py`).

## Studio evidence (own temp copy of the playtest build, Play mode, one player)
- 22 of 22 low-poly models loaded, 0 failed (workspace attributes LowPolyDinosLoaded/Failed). Fallback to the legacy visual on a failed load is unchanged.
- Player dino: Compy then Tyrannosaurus set through the character `SpeciesId` attribute: low-poly visual, scaled by species (T-Rex about 5.6 x 10.3 x 11.3 studs). Walking (MoveTo at speed 22) moves the Weld C0 poses (max delta 0.18), so LowPolyAnimator and the squash/jump layer still run. Screenshot: evidence/2026-10-16-lowpoly-playtest/01-player-trex-lowpoly.jpg.
- 12 low-poly clones added 97 Workspace instances in total (one MeshPart per body part). No game errors and no EditableImage budget errors in the console.
- Previews: 66 `DinosaurPreview.add` calls (22 species x base, gold, silhouette). **Bug found and fixed:** before the fix 48 of 66 showed the flat picture, because `DinosaurPreview` and `ModelPreview` ran the legacy "authored creature" checks on the low-poly model and destroyed it for the 16 authored species (all except Compy, Raptor, Triceratops, Stegosaurus, Ankylosaurus, T-Rex). After the fix 66 of 66 are low-poly. Screenshot: 02-previews-12-species-lowpoly.jpg. Index, hatch reveal, shops and the fusion menu all go through that one function. Guarded by `tools/verify_lowpoly_dinos.py`.

## Honest limits
Not done in this pass: clicking through the hatch, shop and fusion menus, a real egg hatch, keyboard walking (injected keys did not move the character), a 12-dino lineup screenshot (the game camera overrides a scripted one), phone and published-server checks. These are BD-323, BD-325 and BD-322. NPC predators keep their own visual (BD-324).
