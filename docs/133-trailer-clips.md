# 133. Trailer clips: demo and weekly-update videos

**Status: tooling, dev only.** Nothing here ships in the game or changes gameplay. Kid-friendly rules ([72](72-ui-copy-and-asset-standards.md)) and brand colours ([114](114-handbook.md) section 5.1: gold #FFD22B titles on panel #2A2835) apply to every card. Title cards made by these tools are **placeholders**; real branding art is an owner task ([77](77-asset-registry.md) line needed when it exists).

## Pieces
| Piece | Where |
| --- | --- |
| Director (client, Studio only) | `src/client/DemoDirector.client.luau`, helpers `src/shared/DemoShots.luau` |
| Shot lists (JSON) | `tools/demo/shots/`: `hatching_showcase`, `class_feel`, `cave_tour`, `weekly_update_template` |
| Start snippet | `python tools/demo/run_shot.py NAME [--aspect 9:16]` |
| Recorder | `tools/demo/record.py` (ffmpeg gdigrab, 60 fps) |
| Editor | `tools/demo/edit.py` (trim, crossfade concat, cards, 16:9 + 9:16, music, GIF) |
| Checks | `tools/verify_demo_director.py`, `record.py --selftest`, `edit.py selftest` |

## Safety
The director does nothing unless `RunService:IsStudio()` **and** `Config.DemoDirectorEnabled = true`. The flag is false in source and pinned off in the default and playtest profiles (`tools/release_profiles.py`), so a build with it on fails `verify_release`. Flip it locally in Studio only; never commit it. Triggers fire only the existing Studio test remotes (`TestGrantChests`, `TestSetMutationCopies`, `TestGrantSpecies`), each still gated by its own flag on the server (`ChestTestGrantEnabled` etc.); no server code was added.

## Lead: make a demo clip
1. Locally set `DemoDirectorEnabled = true` (and any test flag the shot needs, e.g. `ChestTestGrantEnabled`). `python tools/build.py`, open in Studio, Play.
2. Run `python tools/demo/run_shot.py cave_tour` and paste the printed line in the **client** command bar. The director waits for the value, hides the HUD, fades in the letterbox, plays the shots and restores everything.
3. Record: start `python tools/demo/record.py --out raw/cave.mp4 --duration 25` just before pasting (length = sum of shot durations + about 2 s). Keep the Studio window visible and not minimised; `--list-windows` shows titles.
4. Edit: `python tools/demo/edit.py build raw/cave.mp4 --out out/cave --intro "The Cave" --outro "Be Dino!" --aspects 16:9 9:16 --gif`. For 9:16 use `--focus 0.5` (centre), or move it toward 0 or 1 to keep the subject; `--pad` letterboxes instead of cropping.
5. Revert the local flag edits.

## Owner: weekly-update clip
Copy `tools/demo/shots/weekly_update_template.json` to a new name, change the `lowerThird` lines to the week's news (short, kid words, at most 60 characters) and the camera positions to the place you want to show, then follow the lead steps. Add `--music path/to/track.mp3` for sound (none is bundled; use only music you may use). Post the `_16x9.mp4` or `_9x16.mp4`; share the `.gif` in chat.

## Shot list format (`version` 1)
`name`, `aspect` (`16:9` or `9:16`, sets the title safe area), optional `hideHud` and `letterbox` (default on), `shots[]` each with `duration` (seconds, at most 60; whole clip at most 180), `camera`, optional `title` (at most 40 chars), `lowerThird` (at most 60), `triggers[]`.
Cameras: `static {pos, look}`, `orbit {center, radius, height, startDeg, endDeg}`, `dolly {from, to, look, lookTo?}`, `pushin {from, look, distance}`, `track {offset, lookHeight}` (follows the local player); all take `ease` (`linear`, `inSine`, `outSine`, `inOutSine`, `inQuad`, `outQuad`, `inOutQuad`, `outCubic`, `inOutCubic`).
Triggers (`at` seconds into the shot): `remote {remote, repeatCount?, gap?, args?}`, `teleport {spot | pos}` (`spot` is a CaveHubLayout id such as `heart`, `nests`, `fusion`, `index`), `hud {visible}`, `note {text}`.

## Known limits
No trigger yet spawns a chosen class or forces a hatch party with chosen rarities, because no Studio remote for that exists; equip the species by hand (`class_feel` prints a reminder) and use `TestGrantChests` for eggs. Adding such a remote is a separate gated server task. Camera and recorder behaviour in Studio is not proven by CI; the lead's first run is the evidence.
